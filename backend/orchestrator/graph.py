"""
orchestrator/graph.py — MolForge AI LangGraph pipeline definition.

Architecture (expanded with docking, synthesis, biologics):

  Science track (sequential):
    START → disease_analyst → target_validator → structure_resolver
          → compound_discovery → admet_predictor → docking_scorer
          → synthesis_planner → scorer_ranker

  Market track (parallel with science, starts from START):
    START → market_analyst → competitive_scout → opportunity_scorer → scorer_ranker

  Biologics track (parallel, starts after target_validator):
    target_validator → biologics_analyst → scorer_ranker

  All tracks converge at scorer_ranker:
    scorer_ranker → report_generator → END

HIGH RISK — this file wires all agents. Run gitnexus_impact before editing.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from agents.disease_analyst import DiseaseAnalyst
from agents.target_validator import TargetValidator
from agents.structure_resolver import StructureResolver
from agents.compound_discovery import CompoundDiscovery
from agents.admet_predictor import AdmetPredictor
from agents.market_analyst import MarketAnalyst
from agents.competitive_scout import CompetitiveScout
from agents.opportunity_scorer import OpportunityScorer
from agents.biologics_analyst import BiologicsAnalyst
from orchestrator.state import MolForgeState
from scorer.scorer import run_scorer
from report.report_generator import run_report_generator

logger = logging.getLogger(__name__)

# --- Instantiate agents ---
_disease_analyst = DiseaseAnalyst()
_target_validator = TargetValidator()
_structure_resolver = StructureResolver()
_compound_discovery = CompoundDiscovery()
_admet_predictor = AdmetPredictor()
_market_analyst = MarketAnalyst()
_competitive_scout = CompetitiveScout()
_opportunity_scorer = OpportunityScorer()
_biologics_analyst = BiologicsAnalyst()


# --- Node wrapper ---

async def _run_node(agent, state: MolForgeState, owned_keys: list[str]) -> dict:
    """Run an agent and return only its owned keys + new status_updates/errors."""
    old_updates_len = len(state.get("status_updates", []))
    old_errors_len = len(state.get("errors", []))

    result = await agent.run(state) if hasattr(agent, 'run') else await agent(state)

    out = {}
    for key in owned_keys:
        if key in result:
            out[key] = result[key]

    new_updates = result.get("status_updates", [])[old_updates_len:]
    if new_updates:
        out["status_updates"] = new_updates
    new_errors = result.get("errors", [])[old_errors_len:]
    if new_errors:
        out["errors"] = new_errors

    return out


# --- Node functions ---

async def node_disease_analyst(state: MolForgeState) -> dict:
    return await _run_node(_disease_analyst, state, ["candidate_targets"])

async def node_target_validator(state: MolForgeState) -> dict:
    return await _run_node(_target_validator, state, ["validated_target"])

async def node_structure_resolver(state: MolForgeState) -> dict:
    return await _run_node(_structure_resolver, state, ["protein_structure"])

async def node_compound_discovery(state: MolForgeState) -> dict:
    return await _run_node(_compound_discovery, state, ["candidate_compounds"])

async def node_admet_predictor(state: MolForgeState) -> dict:
    return await _run_node(_admet_predictor, state, ["admet_results"])

async def node_market_analyst(state: MolForgeState) -> dict:
    return await _run_node(_market_analyst, state, ["market_data"])

async def node_competitive_scout(state: MolForgeState) -> dict:
    return await _run_node(_competitive_scout, state, ["competitive_data"])

async def node_opportunity_scorer(state: MolForgeState) -> dict:
    return await _run_node(_opportunity_scorer, state, ["opportunity_score"])

async def node_biologics_analyst(state: MolForgeState) -> dict:
    return await _run_node(_biologics_analyst, state, ["biologics_data"])

async def node_docking_scorer(state: MolForgeState) -> dict:
    """Run docking estimation on all candidates post-ADMET."""
    from tools.docking_client import estimate_binding_affinity

    candidates = state.get("candidate_compounds", [])
    admet = state.get("admet_results", [])
    pdb_path = state.get("protein_structure", {}).get("pdb_file_path")

    # Only dock candidates that passed ADMET (not FAIL)
    admet_map = {a["smiles"]: a for a in admet}
    to_dock = [c for c in candidates if admet_map.get(c["smiles"], {}).get("verdict") != "FAIL"]

    status = state.get("status_updates", [])
    status.append(f"Docking Scorer: Estimating binding affinity for {len(to_dock)} candidates...")

    results = []
    for c in to_dock[:25]:  # Cap at 25 to keep runtime reasonable
        result = await estimate_binding_affinity(c["smiles"], pdb_path=pdb_path)
        results.append(result)

    status.append(f"Docking Scorer: Complete — {len(results)} compounds scored")

    return {
        "docking_results": results,
        "status_updates": status[len(state.get("status_updates", [])):],
    }

async def node_synthesis_planner(state: MolForgeState) -> dict:
    """Run synthesis route planning on all candidates."""
    from tools.retrosynthesis_client import plan_synthesis_route

    candidates = state.get("candidate_compounds", [])
    admet = state.get("admet_results", [])
    admet_map = {a["smiles"]: a for a in admet}

    to_plan = [c for c in candidates if admet_map.get(c["smiles"], {}).get("verdict") != "FAIL"]

    status = state.get("status_updates", [])
    status.append(f"Synthesis Planner: Planning routes for {len(to_plan)} candidates...")

    routes = []
    for c in to_plan[:25]:
        route = await plan_synthesis_route(c["smiles"])
        routes.append(route)

    status.append(f"Synthesis Planner: Complete — {len(routes)} routes planned")

    return {
        "synthesis_routes": routes,
        "status_updates": status[len(state.get("status_updates", [])):],
    }

async def node_scorer_ranker(state: MolForgeState) -> dict:
    return await _run_node(run_scorer, state, ["final_candidates"])

async def node_report_generator(state: MolForgeState) -> dict:
    return await _run_node(run_report_generator, state, ["final_candidates", "report_path"])


# --- Build the graph ---

def build_graph() -> StateGraph:
    """
    Construct the MolForge AI LangGraph pipeline.

    Architecture:
      START ──┬── disease_analyst → target_validator ──┬── structure_resolver
              │                                         │    → compound_discovery → admet_predictor
              │                                         │    → docking_scorer → synthesis_planner ──┐
              │                                         │                                           │
              │                                         └── biologics_analyst ─────────────────────┤
              │                                                                                     ├── scorer_ranker → report_generator → END
              └── market_analyst → competitive_scout → opportunity_scorer ──────────────────────────┘
    """
    graph = StateGraph(MolForgeState)

    # Register all nodes
    graph.add_node("disease_analyst", node_disease_analyst)
    graph.add_node("target_validator", node_target_validator)
    graph.add_node("structure_resolver", node_structure_resolver)
    graph.add_node("compound_discovery", node_compound_discovery)
    graph.add_node("admet_predictor", node_admet_predictor)
    graph.add_node("docking_scorer", node_docking_scorer)
    graph.add_node("synthesis_planner", node_synthesis_planner)
    graph.add_node("market_analyst", node_market_analyst)
    graph.add_node("competitive_scout", node_competitive_scout)
    graph.add_node("opportunity_scorer", node_opportunity_scorer)
    graph.add_node("biologics_analyst", node_biologics_analyst)
    graph.add_node("scorer_ranker", node_scorer_ranker)
    graph.add_node("report_generator", node_report_generator)

    # --- Science track (sequential) ---
    graph.add_edge(START, "disease_analyst")
    graph.add_edge("disease_analyst", "target_validator")
    # After target validation, fan out to structure_resolver + biologics
    graph.add_edge("target_validator", "structure_resolver")
    graph.add_edge("target_validator", "biologics_analyst")
    graph.add_edge("structure_resolver", "compound_discovery")
    graph.add_edge("compound_discovery", "admet_predictor")
    graph.add_edge("admet_predictor", "docking_scorer")
    graph.add_edge("docking_scorer", "synthesis_planner")
    graph.add_edge("synthesis_planner", "scorer_ranker")

    # --- Biologics track merges into scorer ---
    graph.add_edge("biologics_analyst", "scorer_ranker")

    # --- Market track (parallel — starts from START) ---
    graph.add_edge(START, "market_analyst")
    graph.add_edge("market_analyst", "competitive_scout")
    graph.add_edge("competitive_scout", "opportunity_scorer")
    graph.add_edge("opportunity_scorer", "scorer_ranker")

    # --- Convergence: scorer → report → END ---
    graph.add_edge("scorer_ranker", "report_generator")
    graph.add_edge("report_generator", END)

    return graph


# Compile once at import time
compiled_graph = build_graph().compile()

logger.info("MolForge AI LangGraph compiled (with docking, synthesis, biologics)")
