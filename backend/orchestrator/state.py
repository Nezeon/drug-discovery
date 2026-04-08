"""
orchestrator/state.py — MolForge AI LangGraph shared state schema.

MolForgeState is the single TypedDict that flows through the entire LangGraph
pipeline. Every agent reads from it and writes only to its designated fields.

HIGH RISK — all 8 agents import this. Run gitnexus_impact before ANY change.
DO NOT modify field names or types without approval — it will break every agent.
"""

from __future__ import annotations

import operator
import uuid
from typing import Annotated, Any, TypedDict


class MolForgeState(TypedDict):
    # --- Input ---
    disease_name: str
    job_id: str

    # --- Agent 1 (DiseaseAnalyst) output ---
    candidate_targets: list[dict[str, Any]]
    # Schema: [{name, gene_id, relevance_score, novelty_score, source}]

    # --- Agent 2 (TargetValidator) output ---
    validated_target: dict[str, Any]
    # Schema: {name, uniprot_id, druggability_score, evidence}

    # --- Agent 3 (StructureResolver) output ---
    protein_structure: dict[str, Any]
    # Schema: {pdb_file_path, binding_pocket_coords, plddt_score, source}

    # --- Agent 4 (CompoundDiscovery) output ---
    candidate_compounds: list[dict[str, Any]]
    # Schema: [{smiles, name, source, novelty_score, sa_score, scaffold_origin}]

    # --- Agent 5 (AdmetPredictor) output ---
    admet_results: list[dict[str, Any]]
    # Schema: [{smiles, absorption, distribution, metabolism, excretion, toxicity, verdict}]

    # --- Agent 6 (MarketAnalyst) output ---
    market_data: dict[str, Any]
    # Schema: {patient_population, market_size_usd, daly_score, orphan_flag}

    # --- Agent 7 (CompetitiveScout) output ---
    competitive_data: dict[str, Any]
    # Schema: {trial_count, approved_drug_count, density_label, white_space_flag}

    # --- Agent 8 (OpportunityScorer) output ---
    opportunity_score: dict[str, Any]
    # Schema: {score, rating, commercial_brief, key_flags}

    # --- Agent 9 (BiologicsAnalyst) output ---
    biologics_data: dict[str, Any]
    # Schema: {target, target_class, localization, antibody, peptide, adc, recommended_modality, overall_score}

    # --- Docking results (added post-ADMET) ---
    docking_results: list[dict[str, Any]]
    # Schema: [{smiles, binding_affinity_kcal, method, confidence, details}]

    # --- Synthesis routes (added post-ADMET) ---
    synthesis_routes: list[dict[str, Any]]
    # Schema: [{smiles, feasible, num_steps, fragments, route_description, estimated_difficulty, sa_score}]

    # --- Scorer output ---
    final_candidates: list[dict[str, Any]]
    # Schema: [{smiles, composite_score, binding_score, admet_score, lit_score, market_score, verdict, docking, synthesis}]

    # --- System (Annotated with operator.add for safe concurrent appends) ---
    status_updates: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]


def create_initial_state(disease_name: str, job_id: str | None = None) -> MolForgeState:
    """
    Factory function — returns a valid MolForgeState with all fields at empty defaults.

    Usage:
        state = create_initial_state("Parkinson's Disease")
        state = create_initial_state("Type 2 Diabetes", job_id="job_abc123")
    """
    return MolForgeState(
        disease_name=disease_name,
        job_id=job_id or f"job_{uuid.uuid4().hex[:8]}",
        candidate_targets=[],
        validated_target={},
        protein_structure={},
        candidate_compounds=[],
        admet_results=[],
        market_data={},
        competitive_data={},
        opportunity_score={},
        biologics_data={},
        docking_results=[],
        synthesis_routes=[],
        final_candidates=[],
        status_updates=[],
        errors=[],
    )
