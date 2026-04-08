"""
agents/target_validator.py — Agent 2: Target Validator

OWNS:       state["validated_target"]
READS:      state["candidate_targets"], state["disease_name"]
WRITES:     state["validated_target"] — single best target: {
                gene_symbol, protein_name, uniprot_id, druggability_score,
                opentargets_score, has_binding_site, is_hub_protein,
                expressed_in_target_tissue, tissue_name, evidence_summary
            }

APIS CALLED:
  - OpenTargets GraphQL (tools/opentargets_client.py)
  - UniProt REST (tools/uniprot_client.py)
  - STRING-DB (tools/string_client.py)
  - Human Protein Atlas (tools/hpa_client.py)
  - Gemini via langchain-google-genai — writes evidence summary

LOGIC:
  1. For each candidate target:
     a. Fetch OpenTargets association score → drop if < 0.4
     b. Fetch UniProt protein info → get uniprot_id, binding sites
     c. Fetch STRING interaction data → flag hub proteins
     d. Fetch HPA tissue expression → check target tissue
  2. Compute composite druggability score
  3. Select top target (highest druggability)
  4. Generate Gemini evidence summary
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

import config
from agents.base_agent import BaseAgent
from orchestrator.state import MolForgeState
from tools import opentargets_client, uniprot_client, string_client, hpa_client

logger = logging.getLogger(__name__)

# Minimum OpenTargets association score to keep a target
MIN_ASSOCIATION_SCORE = 0.4

EVIDENCE_SUMMARY_PROMPT = """
You are a drug target validation expert.

TARGET: {gene_symbol} ({protein_name})
DISEASE: {disease_name}

DATA:
- OpenTargets association score: {opentargets_score:.3f}
- Has known binding site: {has_binding_site}
- Is hub protein (>20 interactions): {is_hub_protein}
- Expressed in target tissue ({tissue_name}): {expressed_in_tissue}
- UniProt function: {function_desc}
- Druggability score: {druggability_score:.3f}

Write a 2-sentence evidence summary explaining why this target is a strong candidate for drug development against {disease_name}.
Return ONLY the 2-sentence summary. No JSON. No markdown. No explanation beyond the summary.
"""


class TargetValidator(BaseAgent):
    name = "target_validator"

    async def run(self, state: MolForgeState) -> MolForgeState:
        disease = state["disease_name"]
        candidates = state["candidate_targets"]

        self.emit(state, f"Target Validator: starting — evaluating {len(candidates)} candidate targets...")

        if not candidates:
            state["errors"].append("Target Validator: no candidate targets to validate")
            self.emit(state, "Target Validator: done — no candidates to evaluate")
            return state

        # Determine target tissue for this disease
        tissue = hpa_client.get_tissue_for_disease(disease)
        self.emit(state, f"Target Validator: target tissue for {disease} -> {tissue}")

        # ------------------------------------------------------------------
        # Steps 1-4: Evaluate each candidate in parallel
        # ------------------------------------------------------------------
        evaluation_tasks = [
            self._evaluate_target(t, disease, tissue, state)
            for t in candidates
        ]

        evaluated = await asyncio.gather(*evaluation_tasks, return_exceptions=True)

        # Filter out failures and low-scoring targets
        valid_targets = []
        for result in evaluated:
            if isinstance(result, Exception):
                state["errors"].append(f"Target Validator: evaluation error: {result}")
                continue
            if result is None:
                continue
            valid_targets.append(result)

        self.emit(
            state,
            f"Target Validator: {len(valid_targets)}/{len(candidates)} targets passed validation",
        )

        if not valid_targets:
            state["errors"].append("Target Validator: all targets filtered out")
            # Fallback: use the first candidate with minimal info
            fallback = candidates[0]
            state["validated_target"] = {
                "gene_symbol": fallback.get("gene_symbol", ""),
                "protein_name": fallback.get("protein_name", ""),
                "uniprot_id": "",
                "druggability_score": 0.3,
                "opentargets_score": 0.0,
                "has_binding_site": False,
                "is_hub_protein": False,
                "expressed_in_target_tissue": True,
                "tissue_name": tissue,
                "evidence_summary": "Fallback target — insufficient validation data available.",
            }
            self.emit(
                state,
                f"Target Validator: done — fallback to {fallback.get('gene_symbol', 'unknown')} (no targets passed filters)",
            )
            return state

        # ------------------------------------------------------------------
        # Step 5: Sort by druggability score, select top 1
        # ------------------------------------------------------------------
        valid_targets.sort(key=lambda t: t["druggability_score"], reverse=True)
        winner = valid_targets[0]

        # Print all evaluated targets for debugging
        for t in valid_targets:
            logger.info(
                "  Target %s: druggability=%.3f, OT=%.3f, binding=%s, hub=%s, expr=%s",
                t["gene_symbol"], t["druggability_score"], t["opentargets_score"],
                t["has_binding_site"], t["is_hub_protein"], t["expressed_in_target_tissue"],
            )

        # ------------------------------------------------------------------
        # Step 6: Generate Gemini evidence summary
        # ------------------------------------------------------------------
        self.emit(state, f"Target Validator: generating evidence summary for {winner['gene_symbol']}...")
        evidence_summary = await self._generate_evidence_summary(winner, disease, state)
        winner["evidence_summary"] = evidence_summary

        # Write to state
        state["validated_target"] = winner

        self.emit(
            state,
            f"Target Validator: done — {winner['gene_symbol']} selected "
            f"(druggability={winner['druggability_score']:.3f}). "
            f"Evaluated {len(valid_targets)} targets.",
        )

        return state

    async def _evaluate_target(
        self,
        target: dict,
        disease: str,
        tissue: str,
        state: MolForgeState,
    ) -> dict | None:
        """
        Evaluate a single candidate target across all 4 data sources.
        Returns enriched target dict or None if it should be dropped.
        """
        gene = target.get("gene_symbol", "")
        if not gene:
            return None

        logger.info("Evaluating target: %s", gene)

        # Run all 4 API calls concurrently
        try:
            ot_result, uniprot_result, string_result, hpa_result = await asyncio.gather(
                opentargets_client.fetch_associations(disease, gene),
                uniprot_client.fetch_protein_info(gene),
                string_client.fetch_interaction_score(gene),
                hpa_client.fetch_tissue_expression(gene, tissue),
                return_exceptions=True,
            )
        except Exception as exc:
            state["errors"].append(f"Target Validator: parallel fetch failed for {gene}: {exc}")
            return None

        # Handle individual failures
        if isinstance(ot_result, Exception):
            state["errors"].append(f"Target Validator: OpenTargets error for {gene}: {ot_result}")
            ot_result = {}
        if isinstance(uniprot_result, Exception):
            state["errors"].append(f"Target Validator: UniProt error for {gene}: {uniprot_result}")
            uniprot_result = {}
        if isinstance(string_result, Exception):
            state["errors"].append(f"Target Validator: STRING error for {gene}: {string_result}")
            string_result = {"interaction_count": 0, "avg_score": 0.0, "is_hub_protein": False}
        if isinstance(hpa_result, Exception):
            state["errors"].append(f"Target Validator: HPA error for {gene}: {hpa_result}")
            hpa_result = {"expressed_in_target_tissue": True, "expression_level": "UNKNOWN", "tissue_name": tissue}

        # Step 1: Check OpenTargets association score
        ot_score = ot_result.get("association_score", 0.0) if ot_result else 0.0

        # Use DisGeNET score as additional evidence if OT score is low
        disgenet_score = target.get("disgenet_score", 0.0)
        combined_evidence = max(ot_score, disgenet_score)

        if combined_evidence < MIN_ASSOCIATION_SCORE:
            logger.info("  %s dropped: combined evidence %.3f < %.3f", gene, combined_evidence, MIN_ASSOCIATION_SCORE)
            return None

        # Step 2: Extract UniProt info
        uniprot_id = uniprot_result.get("uniprot_id", "")
        has_binding = uniprot_result.get("has_binding_site", False)
        protein_name = uniprot_result.get("protein_name", "") or target.get("protein_name", "")
        function_desc = uniprot_result.get("function_description", "")

        # Step 3: STRING interaction data
        is_hub = string_result.get("is_hub_protein", False)

        # Step 4: HPA tissue expression
        expressed = hpa_result.get("expressed_in_target_tissue", True)
        expression_level = hpa_result.get("expression_level", "UNKNOWN")

        # ------------------------------------------------------------------
        # Step 5: Compute composite druggability score
        # druggability = (opentargets_score × 0.4) +
        #                (has_binding_site × 0.25) +
        #                (is_hub_protein × 0.2) +
        #                (expressed_in_target_tissue × 0.15)
        # ------------------------------------------------------------------
        druggability = (
            (combined_evidence * 0.4)
            + ((1.0 if has_binding else 0.0) * 0.25)
            + ((1.0 if is_hub else 0.0) * 0.2)
            + ((1.0 if expressed else 0.0) * 0.15)
        )

        return {
            "gene_symbol": gene,
            "protein_name": protein_name,
            "uniprot_id": uniprot_id,
            "druggability_score": round(druggability, 4),
            "opentargets_score": round(ot_score, 4),
            "has_binding_site": has_binding,
            "is_hub_protein": is_hub,
            "expressed_in_target_tissue": expressed,
            "tissue_name": hpa_result.get("tissue_name", tissue),
            "expression_level": expression_level,
            "function_description": function_desc,
            # Evidence details for downstream use
            "genetic_evidence": ot_result.get("genetic_evidence", 0.0) if ot_result else 0.0,
            "clinical_evidence": ot_result.get("clinical_evidence", 0.0) if ot_result else 0.0,
            "literature_evidence": ot_result.get("literature_evidence", 0.0) if ot_result else 0.0,
            "interaction_count": string_result.get("interaction_count", 0),
            "evidence_summary": "",  # Will be filled for the winner
        }

    async def _generate_evidence_summary(
        self, target: dict, disease: str, state: MolForgeState
    ) -> str:
        """Generate a 2-sentence Gemini evidence summary for the winning target."""
        if not config.GEMINI_API_KEY:
            return f"{target['gene_symbol']} is a validated drug target for {disease}."

        prompt = EVIDENCE_SUMMARY_PROMPT.format(
            gene_symbol=target["gene_symbol"],
            protein_name=target["protein_name"],
            disease_name=disease,
            opentargets_score=target["opentargets_score"],
            has_binding_site=target["has_binding_site"],
            is_hub_protein=target["is_hub_protein"],
            tissue_name=target.get("tissue_name", "unknown"),
            expressed_in_tissue=target["expressed_in_target_tissue"],
            function_desc=target.get("function_description", "Not available"),
            druggability_score=target["druggability_score"],
        )

        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=config.GEMINI_API_KEY,
                temperature=0.2,
            )
            response = await llm.ainvoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            return text.strip()
        except Exception as exc:
            state["errors"].append(f"Target Validator: Gemini summary failed: {exc}")
            return f"{target['gene_symbol']} is a validated drug target for {disease} with a druggability score of {target['druggability_score']:.2f}."
