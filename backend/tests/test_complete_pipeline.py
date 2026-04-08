"""
tests/test_complete_pipeline.py — Full end-to-end pipeline test including
Market Intelligence (Agents 6-8), 4D Scorer, and Report Generator.

Runs the complete orchestrator graph for "Parkinson's Disease" and prints
a formatted summary of all results.

Run:  cd backend && python tests/test_complete_pipeline.py
"""

import asyncio
import sys
import os
import time
import json

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.state import create_initial_state
from agents.disease_analyst import DiseaseAnalyst
from agents.target_validator import TargetValidator
from agents.structure_resolver import StructureResolver
from agents.compound_discovery import CompoundDiscovery
from agents.admet_predictor import AdmetPredictor
from agents.market_analyst import MarketAnalyst
from agents.competitive_scout import CompetitiveScout
from agents.opportunity_scorer import OpportunityScorer
from scorer.scorer import run_scorer
from report.report_generator import generate_report


def print_separator(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def safe_print(text: str):
    """Print with safe encoding for Windows console."""
    print(text.encode("ascii", errors="replace").decode("ascii"))


async def run_complete_pipeline():
    """Run the full pipeline: Science + Market + Scorer + Report."""
    print_separator("FULL PIPELINE TEST -- Parkinson's Disease")
    pipeline_start = time.time()

    state = create_initial_state("Parkinson's Disease", job_id="test_complete")

    # ==================================================================
    # SCIENCE TRACK (sequential)
    # ==================================================================
    science_agents = [
        ("Agent 1: Disease Analyst", DiseaseAnalyst()),
        ("Agent 2: Target Validator", TargetValidator()),
        ("Agent 3: Structure Resolver", StructureResolver()),
        ("Agent 4: Compound Discovery", CompoundDiscovery()),
        ("Agent 5: ADMET Predictor", AdmetPredictor()),
    ]

    for label, agent in science_agents:
        print_separator(label)
        start = time.time()
        try:
            state = await agent.run(state)
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.1f}s")
        except Exception as exc:
            elapsed = time.time() - start
            print(f"  FAILED after {elapsed:.1f}s: {exc}")
            import traceback
            traceback.print_exc()
            continue

    science_time = time.time() - pipeline_start
    print(f"\n  --- Science track complete: {science_time:.1f}s ---")

    # ==================================================================
    # MARKET TRACK (sequential for test — would be parallel in graph)
    # ==================================================================
    market_start = time.time()
    market_agents = [
        ("Agent 6: Market Analyst", MarketAnalyst()),
        ("Agent 7: Competitive Scout", CompetitiveScout()),
        ("Agent 8: Opportunity Scorer", OpportunityScorer()),
    ]

    for label, agent in market_agents:
        print_separator(label)
        start = time.time()
        try:
            state = await agent.run(state)
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.1f}s")
        except Exception as exc:
            elapsed = time.time() - start
            print(f"  FAILED after {elapsed:.1f}s: {exc}")
            import traceback
            traceback.print_exc()
            continue

    market_time = time.time() - market_start
    print(f"\n  --- Market track complete: {market_time:.1f}s ---")

    # ==================================================================
    # 4D SCORER
    # ==================================================================
    print_separator("4D SCORER")
    start = time.time()
    try:
        state = await run_scorer(state)
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.1f}s")
    except Exception as exc:
        elapsed = time.time() - start
        print(f"  FAILED after {elapsed:.1f}s: {exc}")
        import traceback
        traceback.print_exc()

    # ==================================================================
    # REPORT GENERATOR
    # ==================================================================
    print_separator("REPORT GENERATOR")
    start = time.time()
    try:
        report_path = generate_report(state["job_id"], state)
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.1f}s")
        print(f"  Report: {report_path}")
    except Exception as exc:
        elapsed = time.time() - start
        print(f"  FAILED after {elapsed:.1f}s: {exc}")
        import traceback
        traceback.print_exc()
        report_path = None

    # ==================================================================
    # FORMATTED SUMMARY
    # ==================================================================
    total_time = time.time() - pipeline_start

    vt = state.get("validated_target", {})
    market = state.get("market_data", {})
    competitive = state.get("competitive_data", {})
    opportunity = state.get("opportunity_score", {})
    candidates = state.get("final_candidates", [])

    print_separator("MOLFORGE AI RESULTS")
    safe_print(f"  Disease:     Parkinson's Disease")
    safe_print(f"  Target:      {vt.get('gene_symbol', vt.get('name', 'N/A'))} "
               f"(druggability: {vt.get('druggability_score', 'N/A')})")
    safe_print(f"  Market:      {opportunity.get('rating', 'N/A')} opportunity "
               f"-- {market.get('market_size_usd_estimate', 'N/A')} market")
    safe_print(f"  Competition: {competitive.get('density_label', 'N/A')} "
               f"-- {competitive.get('active_trials', 0)} active trials")

    print(f"\n  CANDIDATES ({len(candidates)} total):")
    for i, c in enumerate(candidates[:10], 1):
        smiles = c.get("smiles", "N/A")
        if len(smiles) > 50:
            smiles = smiles[:50] + "..."
        safe_print(f"  Rank {i:2d}: {smiles}")
        safe_print(f"           {c.get('verdict', 'N/A')} (score: {c.get('composite_score', 0):.4f}) "
                   f"[B={c.get('binding_score', 0):.2f} A={c.get('admet_score', 0):.2f} "
                   f"L={c.get('literature_score', 0):.2f} M={c.get('market_score', 0):.2f}]")

    # Count verdicts
    go_count = sum(1 for c in candidates if c.get("verdict") == "GO")
    inv_count = sum(1 for c in candidates if c.get("verdict") == "INVESTIGATE")
    nogo_count = sum(1 for c in candidates if c.get("verdict") == "NO-GO")
    print(f"\n  Verdicts:    {go_count} GO, {inv_count} INVESTIGATE, {nogo_count} NO-GO")

    if report_path:
        print(f"\n  Report:      {report_path}")

    print(f"  Total time:  {total_time:.1f}s")

    # --- Errors ---
    errors = state.get("errors", [])
    if errors:
        print_separator(f"ERRORS ({len(errors)})")
        for err in errors:
            safe_print(f"  [!] {err}")

    # --- All status updates ---
    print_separator("ALL STATUS UPDATES")
    for update in state.get("status_updates", []):
        safe_print(f"  {update}")

    print_separator("END")

    # Save results JSON
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jobs", state["job_id"])
    os.makedirs(results_dir, exist_ok=True)
    results_path = os.path.join(results_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(dict(state), f, indent=2, default=str)
    print(f"\n  Results JSON: {results_path}")

    return state


if __name__ == "__main__":
    asyncio.run(run_complete_pipeline())
