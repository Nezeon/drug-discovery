"""
tests/test_market_pipeline.py — Market Intelligence Layer test (Agents 6, 7, 8)

Creates mock state with disease_name = "Parkinson's Disease"
and validated_target = {gene_symbol: "LRRK2", protein_name: "LRRK2 kinase"}

Runs agents 6, 7, 8 in sequence, prints full output, and validates results.

Run:  cd backend && python tests/test_market_pipeline.py
"""

import asyncio
import json
import sys
import os
import time

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.state import create_initial_state
from agents.market_analyst import MarketAnalyst
from agents.competitive_scout import CompetitiveScout
from agents.opportunity_scorer import OpportunityScorer


def print_separator(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def safe_print(text: str):
    """Print with safe encoding for Windows console."""
    print(text.encode("ascii", errors="replace").decode("ascii"))


async def run_market_pipeline():
    """Run the market intelligence pipeline end-to-end."""
    print_separator("MARKET INTELLIGENCE PIPELINE TEST -- Parkinson's Disease")
    pipeline_start = time.time()

    # Create state with mock validated target (as if science pipeline already ran)
    state = create_initial_state("Parkinson's Disease", job_id="test_market")
    state["validated_target"] = {
        "gene_symbol": "LRRK2",
        "protein_name": "LRRK2 kinase",
        "uniprot_id": "Q5S007",
        "druggability_score": 0.87,
        "name": "LRRK2",
    }

    agents = [
        ("Agent 6: Market Analyst", MarketAnalyst()),
        ("Agent 7: Competitive Scout", CompetitiveScout()),
        ("Agent 8: Opportunity Scorer", OpportunityScorer()),
    ]

    for label, agent in agents:
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

    # =============================================
    # Print full results
    # =============================================
    total_time = time.time() - pipeline_start

    # --- Market Data ---
    print_separator("MARKET DATA (Agent 6)")
    market = state.get("market_data", {})
    if market:
        for key, val in market.items():
            safe_print(f"  {key}: {val}")
    else:
        print("  (empty)")

    # --- Competitive Data ---
    print_separator("COMPETITIVE DATA (Agent 7)")
    competitive = state.get("competitive_data", {})
    if competitive:
        for key, val in competitive.items():
            if key == "approved_drugs":
                print(f"  {key}: ({len(val)} drugs)")
                for d in val[:5]:
                    safe_print(f"    - {d.get('name', 'N/A')} ({d.get('generic', 'N/A')})")
            else:
                safe_print(f"  {key}: {val}")
    else:
        print("  (empty)")

    # --- Opportunity Score ---
    print_separator("OPPORTUNITY SCORE (Agent 8)")
    opportunity = state.get("opportunity_score", {})
    if opportunity:
        for key, val in opportunity.items():
            if key == "commercial_brief":
                safe_print(f"  {key}:")
                safe_print(f"    {val}")
            elif key == "key_flags":
                print(f"  {key}:")
                for flag in val:
                    safe_print(f"    - {flag}")
            else:
                safe_print(f"  {key}: {val}")
    else:
        print("  (empty)")

    # --- Status Updates ---
    print_separator("ALL STATUS UPDATES")
    for update in state.get("status_updates", []):
        safe_print(f"  {update}")

    # --- Errors ---
    if state.get("errors"):
        print_separator(f"ERRORS ({len(state['errors'])})")
        for err in state["errors"]:
            safe_print(f"  [!] {err}")

    # =============================================
    # Validation
    # =============================================
    print_separator("VALIDATION")

    passed = 0
    failed = 0

    # Validate opportunity_score
    if opportunity:
        # Check rating is valid
        rating = opportunity.get("rating", "")
        if rating in ("EXCEPTIONAL", "HIGH", "MEDIUM", "LOW"):
            print(f"  PASS: rating is valid ({rating})")
            passed += 1
        else:
            print(f"  FAIL: rating '{rating}' is not one of EXCEPTIONAL/HIGH/MEDIUM/LOW")
            failed += 1

        # Check score is between 0 and 1
        score = opportunity.get("score", -1)
        if 0 <= score <= 1:
            print(f"  PASS: score is between 0 and 1 ({score:.4f})")
            passed += 1
        else:
            print(f"  FAIL: score {score} is out of range [0, 1]")
            failed += 1

        # Check sub-scores are present
        for sub in ("market_attractiveness", "white_space_score", "unmet_need_score"):
            val = opportunity.get(sub)
            if val is not None and 0 <= val <= 1:
                print(f"  PASS: {sub} = {val:.4f}")
                passed += 1
            else:
                print(f"  FAIL: {sub} = {val}")
                failed += 1

        # Check key_flags is a list
        flags = opportunity.get("key_flags", [])
        if isinstance(flags, list):
            print(f"  PASS: key_flags is a list ({len(flags)} flags)")
            passed += 1
        else:
            print(f"  FAIL: key_flags is not a list")
            failed += 1

        # Check commercial_brief is non-empty
        brief = opportunity.get("commercial_brief", "")
        if brief and len(brief) > 10:
            print(f"  PASS: commercial_brief is present ({len(brief)} chars)")
            passed += 1
        else:
            print(f"  FAIL: commercial_brief is empty or too short")
            failed += 1
    else:
        print("  FAIL: no opportunity_score in state")
        failed += 1

    # Validate market_data has content
    if market and market.get("patient_population"):
        print(f"  PASS: market_data has patient_population = {market['patient_population']}")
        passed += 1
    else:
        print(f"  FAIL: market_data missing patient_population")
        failed += 1

    # Validate competitive_data has density label
    if competitive and competitive.get("density_label"):
        print(f"  PASS: competitive_data has density_label = {competitive['density_label']}")
        passed += 1
    else:
        print(f"  FAIL: competitive_data missing density_label")
        failed += 1

    print_separator(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print(f"  Total pipeline time: {total_time:.1f}s")
    print_separator("END")

    return state


if __name__ == "__main__":
    asyncio.run(run_market_pipeline())
