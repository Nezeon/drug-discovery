"""
agents/compound_discovery.py — Agent 4: Compound Discovery (most complex agent)

OWNS:       state["candidate_compounds"]
READS:      state["validated_target"]
WRITES:     state["candidate_compounds"] — [{smiles, sa_score, novelty_score, scaffold_origin, generation_method}]

LOGIC:
  Phase 1: Fetch ChEMBL actives for validated_target, validate SMILES
  Phase 2: Extract scaffolds, cluster, select top 5 diverse seeds
  Phase 3: Generate analogues via R-group + BRICS (~60 raw candidates)
  Phase 4: Filter — validity + Lipinski + SA score + novelty
  Target output: 15-25 filtered novel candidates
"""

from __future__ import annotations

import logging

from rdkit import Chem

from agents.base_agent import BaseAgent
from orchestrator.state import MolForgeState
from tools import chembl_client
from chemistry.scaffold import extract_scaffolds, cluster_by_scaffold, select_diverse_seeds
from chemistry.generator import enumerate_rgroup_analogues, generate_brics_analogues
from chemistry.filters import filter_candidates
import config

logger = logging.getLogger(__name__)


class CompoundDiscovery(BaseAgent):
    name = "compound_discovery"

    async def run(self, state: MolForgeState) -> MolForgeState:
        self.emit(state, "Compound Discovery: starting — seeding from ChEMBL actives...")

        target = state.get("validated_target", {})
        uniprot_id = target.get("uniprot_id")

        if not uniprot_id:
            msg = "Compound Discovery: ERROR — no uniprot_id in validated_target"
            state["errors"].append(msg)
            self.emit(state, msg)
            return state

        # =====================================================
        # PHASE 1: Fetch ChEMBL actives + validate SMILES
        # =====================================================
        actives = await chembl_client.fetch_actives(uniprot_id, max_results=config.MAX_CANDIDATES * 2)

        if not actives:
            msg = f"Compound Discovery: WARNING — no ChEMBL actives found for {uniprot_id}"
            state["errors"].append(msg)
            self.emit(state, msg)
            return state

        # Validate all SMILES
        valid_actives = []
        for a in actives:
            mol = Chem.MolFromSmiles(a["smiles"])
            if mol is not None:
                a["smiles"] = Chem.MolToSmiles(mol)  # canonicalize
                valid_actives.append(a)

        self.emit(state, f"Compound Discovery: Phase 1 — {len(valid_actives)} valid seeds from ChEMBL (of {len(actives)} fetched)")

        if not valid_actives:
            state["errors"].append("Compound Discovery: all fetched SMILES were invalid")
            return state

        # Reference SMILES for novelty check (all known actives)
        reference_smiles = [a["smiles"] for a in valid_actives]

        # =====================================================
        # PHASE 2: Scaffold extraction + clustering + seed selection
        # =====================================================
        scaffolds = extract_scaffolds(reference_smiles)
        clusters = cluster_by_scaffold(valid_actives, cutoff=0.4)
        seeds = select_diverse_seeds(clusters, valid_actives, top_n=5)

        self.emit(state, f"Compound Discovery: Phase 2 — {len(scaffolds)} scaffolds, {len(clusters)} clusters, {len(seeds)} diverse seeds selected")

        # =====================================================
        # PHASE 3: Generate analogues
        # =====================================================
        raw_analogues = []

        # R-group enumeration on each seed's scaffold
        for seed in seeds:
            scaffold_data = extract_scaffolds([seed["smiles"]])
            if scaffold_data:
                scaffold_smi = scaffold_data[0]["scaffold_smiles"]
                rgroup_mols = enumerate_rgroup_analogues(scaffold_smi, n=15)
                for smi in rgroup_mols:
                    raw_analogues.append({
                        "smiles": smi,
                        "scaffold_origin": scaffold_smi,
                        "generation_method": "r_group",
                    })

        # BRICS recombination across all seeds
        seed_smiles = [s["smiles"] for s in seeds]
        brics_mols = generate_brics_analogues(seed_smiles, n=30)
        for smi in brics_mols:
            raw_analogues.append({
                "smiles": smi,
                "scaffold_origin": "brics_multi",
                "generation_method": "brics",
            })

        self.emit(state, f"Compound Discovery: Phase 3 — {len(raw_analogues)} raw analogues generated (R-group + BRICS)")

        # =====================================================
        # PHASE 4: Filter candidates
        # =====================================================
        raw_smiles = [a["smiles"] for a in raw_analogues]
        filtered = filter_candidates(
            raw_smiles,
            reference_smiles,
            novelty_threshold=config.NOVELTY_THRESHOLD,
            sa_max=config.SA_SCORE_MAX,
        )

        # Merge generation metadata back into filtered results
        smiles_to_meta = {}
        for a in raw_analogues:
            canonical = Chem.MolToSmiles(Chem.MolFromSmiles(a["smiles"])) if Chem.MolFromSmiles(a["smiles"]) else None
            if canonical and canonical not in smiles_to_meta:
                smiles_to_meta[canonical] = {
                    "scaffold_origin": a["scaffold_origin"],
                    "generation_method": a["generation_method"],
                }

        candidates = []
        for f in filtered:
            meta = smiles_to_meta.get(f["smiles"], {})
            candidates.append({
                "smiles": f["smiles"],
                "sa_score": f["sa_score"],
                "novelty_score": f["novelty_score"],
                "scaffold_origin": meta.get("scaffold_origin", "unknown"),
                "generation_method": meta.get("generation_method", "unknown"),
            })

        # Cap at MAX_CANDIDATES
        candidates = candidates[:config.MAX_CANDIDATES]

        state["candidate_compounds"] = candidates
        self.emit(
            state,
            f"Compound Discovery: done — {len(candidates)} novel candidates "
            f"(from {len(raw_analogues)} raw, {len(filtered)} passed filters)"
        )
        return state
