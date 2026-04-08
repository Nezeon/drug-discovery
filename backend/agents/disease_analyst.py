"""
agents/disease_analyst.py — Agent 1: Disease Analyst

OWNS:       state["candidate_targets"]
READS:      state["disease_name"], state["job_id"]
WRITES:     state["candidate_targets"] — list of {
                gene_symbol, protein_name, mechanism, evidence_strength,
                novelty_signal, existing_drug_count, disgenet_score, source_pmids
            }

APIS CALLED:
  - PubMed Entrez (tools/pubmed_client.py)
  - Europe PMC REST (tools/europepmc_client.py)
  - DisGeNET / OpenTargets fallback (tools/disgenet_client.py)
  - ChromaDB (rag/chroma_store.py) — stores abstracts for RAG
  - Gemini via langchain-google-genai — extracts targets from literature

LOGIC:
  1. Fetch abstracts from PubMed + Europe PMC concurrently
  2. Store all abstracts in ChromaDB
  3. Fetch DisGeNET gene-disease associations
  4. Query ChromaDB for most relevant abstracts about targets
  5. Send to Gemini with DISEASE_ANALYST_PROMPT
  6. Parse response, cross-check with known drug counts
  7. Sort by evidence_strength + novelty_signal
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

import config
from agents.base_agent import BaseAgent
from orchestrator.state import MolForgeState
from rag.chroma_store import LiteratureStore
from tools import pubmed_client, europepmc_client, disgenet_client

logger = logging.getLogger(__name__)

# --- Prompt template (from CLAUDE.md — SACRED, do not modify without approval) ---
DISEASE_ANALYST_PROMPT = """
You are a biomedical research expert analyzing scientific literature on {disease_name}.

RECENT ABSTRACTS (last 3 years):
{abstracts}

DISGENET ASSOCIATIONS:
{disgenet_data}

TASK:
Extract all protein targets mentioned in relation to {disease_name}.
For each target return:
- gene_symbol: official HGNC gene symbol
- protein_name: full protein name
- mechanism: how this target relates to disease pathology (1 sentence)
- evidence_strength: HIGH / MEDIUM / LOW based on frequency and recency of mentions
- novelty_signal: TRUE if this target has fewer than 3 approved drugs targeting it

Return ONLY a valid JSON array. No markdown. No explanation.
Schema: [{{"gene_symbol": "", "protein_name": "", "mechanism": "", "evidence_strength": "", "novelty_signal": bool}}]
"""

# Known drug counts per gene — local fallback for DrugBank open data
# This covers the most common drug targets; unknown genes default to 0
_KNOWN_DRUG_COUNTS: dict[str, int] = {
    # Well-known targets with many approved drugs
    "DRD2": 15, "HTR2A": 12, "OPRM1": 10, "ADRA1A": 8, "ADRB1": 7,
    "ACE": 8, "HRH1": 7, "PTGS2": 6, "EGFR": 8, "VEGFA": 5,
    "TNF": 4, "IL6": 3, "BRAF": 4, "ABL1": 4, "ALK": 3,
    "ERBB2": 4, "JAK2": 3, "MTOR": 3, "PIK3CA": 2, "CDK4": 2,
    # Parkinson's-relevant targets
    "LRRK2": 0, "SNCA": 0, "PINK1": 0, "PARK7": 0, "GBA1": 1,
    "PRKN": 0, "MAOB": 2, "COMT": 2, "DDC": 1, "TH": 1,
    "SLC6A3": 2, "DRD1": 3, "DRD3": 2, "ACHE": 4,
    # Alzheimer's-relevant targets
    "APP": 1, "PSEN1": 0, "PSEN2": 0, "MAPT": 0, "BACE1": 0,
    "TREM2": 0, "APOE": 0, "GSK3B": 0, "ADAM10": 0, "BIN1": 0,
    # Diabetes-relevant targets
    "INS": 5, "INSR": 2, "GLP1R": 4, "PPARG": 3, "SGLT2": 3,
    "DPP4": 4, "GCK": 1, "KCNJ11": 2, "ABCC8": 2, "SLC5A2": 3,
}


class DiseaseAnalyst(BaseAgent):
    name = "disease_analyst"

    async def run(self, state: MolForgeState) -> MolForgeState:
        disease = state["disease_name"]
        job_id = state["job_id"]

        self.emit(state, f"Disease Analyst: starting — mining literature for {disease}...")

        # ------------------------------------------------------------------
        # Step 1: Fetch abstracts from PubMed + Europe PMC concurrently
        # ------------------------------------------------------------------
        self.emit(state, "Disease Analyst: fetching PubMed + Europe PMC abstracts...")

        try:
            pubmed_abs, epmc_abs = await asyncio.gather(
                pubmed_client.fetch_abstracts(disease, max_results=30),
                europepmc_client.fetch_abstracts(disease, max_results=20),
                return_exceptions=True,
            )
        except Exception as exc:
            state["errors"].append(f"Disease Analyst: literature fetch failed: {exc}")
            pubmed_abs, epmc_abs = [], []

        # Handle exceptions from gather
        if isinstance(pubmed_abs, Exception):
            state["errors"].append(f"Disease Analyst: PubMed error: {pubmed_abs}")
            pubmed_abs = []
        if isinstance(epmc_abs, Exception):
            state["errors"].append(f"Disease Analyst: Europe PMC error: {epmc_abs}")
            epmc_abs = []

        # Deduplicate by PMID
        seen_pmids = set()
        all_abstracts = []
        for ab in pubmed_abs + epmc_abs:
            pmid = ab.get("pmid", "")
            if pmid and pmid in seen_pmids:
                continue
            if pmid:
                seen_pmids.add(pmid)
            all_abstracts.append(ab)

        total_abs = len(all_abstracts)
        self.emit(state, f"Disease Analyst: fetched {total_abs} unique abstracts "
                         f"(PubMed: {len(pubmed_abs)}, Europe PMC: {len(epmc_abs)})")

        # ------------------------------------------------------------------
        # Step 2: Store abstracts in ChromaDB
        # ------------------------------------------------------------------
        lit_store = LiteratureStore()
        try:
            stored = lit_store.store_abstracts(job_id, all_abstracts)
            logger.info("Stored %d abstracts in ChromaDB for job %s", stored, job_id)
        except Exception as exc:
            state["errors"].append(f"Disease Analyst: ChromaDB store failed: {exc}")
            stored = 0

        # ------------------------------------------------------------------
        # Step 3: Fetch DisGeNET gene-disease associations
        # ------------------------------------------------------------------
        self.emit(state, "Disease Analyst: fetching gene-disease associations...")

        try:
            disgenet_data = await disgenet_client.fetch_gene_associations(disease)
        except Exception as exc:
            state["errors"].append(f"Disease Analyst: DisGeNET/OpenTargets error: {exc}")
            disgenet_data = []

        logger.info("Got %d gene-disease associations", len(disgenet_data))

        # ------------------------------------------------------------------
        # Step 4: Query ChromaDB for most relevant abstracts about targets
        # ------------------------------------------------------------------
        query = f"{disease} protein target therapeutic mechanism druggable"
        try:
            relevant_abstracts = lit_store.query_relevant(job_id, query, n_results=15)
        except Exception as exc:
            state["errors"].append(f"Disease Analyst: ChromaDB query failed: {exc}")
            # Fallback: use first 15 abstracts directly
            relevant_abstracts = [
                f"{ab.get('title', '')}\n{ab.get('abstract', '')}"
                for ab in all_abstracts[:15]
            ]

        # ------------------------------------------------------------------
        # Step 5: Build and send Gemini prompt
        # ------------------------------------------------------------------
        self.emit(state, "Disease Analyst: analyzing literature with Gemini...")

        # Format abstracts for prompt
        abstracts_text = ""
        for i, ab_text in enumerate(relevant_abstracts, 1):
            # Truncate very long abstracts to fit context window
            truncated = ab_text[:1500] if len(ab_text) > 1500 else ab_text
            abstracts_text += f"\n--- Abstract {i} ---\n{truncated}\n"

        # Format DisGeNET data
        disgenet_text = ""
        if disgenet_data:
            for gd in disgenet_data[:15]:
                disgenet_text += (
                    f"- {gd['gene_symbol']} ({gd['gene_name']}): "
                    f"score={gd['score']:.3f}, PMIDs={gd['pmids_count']}\n"
                )
        else:
            disgenet_text = "No DisGeNET data available for this disease."

        prompt = DISEASE_ANALYST_PROMPT.format(
            disease_name=disease,
            abstracts=abstracts_text,
            disgenet_data=disgenet_text,
        )

        targets = await self._call_gemini(prompt, state)

        if not targets:
            state["errors"].append("Disease Analyst: Gemini returned no targets")
            # Fallback: build targets from DisGeNET associations only
            targets = self._targets_from_disgenet(disgenet_data)

        # ------------------------------------------------------------------
        # Step 6 & 7: Cross-check drug counts and compute novelty
        # ------------------------------------------------------------------
        enriched_targets = []
        for t in targets:
            gene = t.get("gene_symbol", "")
            if not gene:
                continue

            # Get existing drug count
            existing_count = _KNOWN_DRUG_COUNTS.get(gene, 0)

            # Re-compute novelty_signal based on actual drug counts
            novelty = existing_count < 3

            # Find DisGeNET score for this gene
            dg_score = 0.0
            for gd in disgenet_data:
                if gd["gene_symbol"].upper() == gene.upper():
                    dg_score = gd["score"]
                    break

            # Collect source PMIDs from relevant abstracts (via metadata)
            source_pmids = self._find_pmids_for_gene(gene, all_abstracts)

            enriched_targets.append({
                "gene_symbol": gene,
                "protein_name": t.get("protein_name", ""),
                "mechanism": t.get("mechanism", ""),
                "evidence_strength": t.get("evidence_strength", "MEDIUM"),
                "novelty_signal": novelty,
                "existing_drug_count": existing_count,
                "disgenet_score": dg_score,
                "source_pmids": source_pmids[:5],  # Cap at 5 PMIDs
            })

        # ------------------------------------------------------------------
        # Step 8: Sort by evidence_strength + novelty_signal
        # ------------------------------------------------------------------
        evidence_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        enriched_targets.sort(
            key=lambda t: (
                evidence_order.get(t["evidence_strength"], 0),
                1 if t["novelty_signal"] else 0,
                t["disgenet_score"],
            ),
            reverse=True,
        )

        # Cap at 10 targets
        enriched_targets = enriched_targets[:10]

        # Write to state
        state["candidate_targets"] = enriched_targets

        top_name = enriched_targets[0]["gene_symbol"] if enriched_targets else "none"
        self.emit(
            state,
            f"Disease Analyst: done — {total_abs} abstracts, "
            f"{len(enriched_targets)} candidate targets extracted. "
            f"Top target: {top_name}",
        )

        return state

    async def _call_gemini(
        self, prompt: str, state: MolForgeState
    ) -> list[dict[str, Any]]:
        """Call Gemini to extract targets from literature. Returns parsed list."""
        if not config.GEMINI_API_KEY:
            state["errors"].append("Disease Analyst: GEMINI_API_KEY not set")
            return []

        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=config.GEMINI_API_KEY,
                temperature=0.1,
            )
            response = await llm.ainvoke(prompt)
            raw_text = response.content if hasattr(response, "content") else str(response)

            parsed = self.parse_gemini_json(raw_text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                # Gemini sometimes wraps list in a dict
                return parsed.get("targets", parsed.get("results", [parsed]))
            return []

        except Exception as exc:
            state["errors"].append(f"Disease Analyst: Gemini call failed: {exc}")
            logger.error("Gemini call failed: %s", exc)
            return []

    @staticmethod
    def _targets_from_disgenet(disgenet_data: list[dict]) -> list[dict]:
        """Fallback: build minimal target entries from DisGeNET if Gemini fails."""
        targets = []
        for gd in disgenet_data[:10]:
            targets.append({
                "gene_symbol": gd["gene_symbol"],
                "protein_name": gd["gene_name"],
                "mechanism": "Associated via gene-disease databases",
                "evidence_strength": "HIGH" if gd["score"] > 0.5 else "MEDIUM",
                "novelty_signal": True,  # Will be re-evaluated in step 6
            })
        return targets

    @staticmethod
    def _find_pmids_for_gene(gene_symbol: str, abstracts: list[dict]) -> list[str]:
        """Find PMIDs of abstracts that mention a gene symbol."""
        gene_upper = gene_symbol.upper()
        pmids = []
        for ab in abstracts:
            text = ((ab.get("title") or "") + " " + (ab.get("abstract") or "")).upper()
            if gene_upper in text:
                pmid = ab.get("pmid", "")
                if pmid:
                    pmids.append(str(pmid))
        return pmids
