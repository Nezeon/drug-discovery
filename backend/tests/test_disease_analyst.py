"""
tests/test_disease_analyst.py — Integration test for Agent 1 (Disease Analyst).

Tests the full Disease Analyst pipeline:
  - PubMed + Europe PMC abstract fetching
  - ChromaDB storage + retrieval
  - Gemini target extraction
  - Novelty scoring

Run:  cd backend && python -m pytest tests/test_disease_analyst.py -v -s
"""

import asyncio
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.state import create_initial_state
from agents.disease_analyst import DiseaseAnalyst


async def run_test():
    """Run Disease Analyst on Parkinson's Disease and validate output."""
    print("=" * 70)
    print("  AGENT 1 TEST — Disease Analyst")
    print("  Disease: Parkinson's Disease")
    print("=" * 70)

    # Create initial state
    state = create_initial_state("Parkinson's Disease", job_id="test_agent1")

    # Run agent
    agent = DiseaseAnalyst()
    state = await agent.run(state)

    # Print status updates
    print("\n--- Status Updates ---")
    for update in state["status_updates"]:
        print(f"  {update}")

    # Print errors if any
    if state["errors"]:
        print("\n--- Errors (non-fatal) ---")
        for err in state["errors"]:
            print(f"  [!] {err}")

    # Print extracted targets
    targets = state["candidate_targets"]
    print(f"\n--- Extracted Targets ({len(targets)}) ---")
    for i, t in enumerate(targets, 1):
        print(f"\n  [{i}] {t['gene_symbol']} — {t['protein_name']}")
        print(f"      Mechanism: {t['mechanism']}")
        print(f"      Evidence: {t['evidence_strength']} | Novel: {t['novelty_signal']} | Drugs: {t['existing_drug_count']}")
        print(f"      DisGeNET score: {t['disgenet_score']:.3f}")
        print(f"      Source PMIDs: {t['source_pmids']}")

    # --- Assertions ---
    print("\n--- Assertions ---")

    # At least 3 targets returned
    assert len(targets) >= 3, f"Expected >= 3 targets, got {len(targets)}"
    print(f"  [PASS] {len(targets)} targets extracted (>= 3)")

    # Check that LRRK2 or SNCA appears (known Parkinson's targets)
    gene_symbols = [t["gene_symbol"].upper() for t in targets]
    known_parkinsons = {"LRRK2", "SNCA", "PINK1", "GBA1", "PRKN", "PARK7", "MAOB", "DRD2"}
    found_known = known_parkinsons.intersection(set(gene_symbols))
    assert len(found_known) > 0, f"Expected at least one known Parkinson's target, got: {gene_symbols}"
    print(f"  [PASS] Found known Parkinson's targets: {found_known}")

    # Print first 3 source PMIDs
    all_pmids = []
    for t in targets:
        all_pmids.extend(t.get("source_pmids", []))
    unique_pmids = list(dict.fromkeys(all_pmids))[:3]
    print(f"  [INFO] First 3 source PMIDs: {unique_pmids}")

    # All targets must have gene_symbol
    for t in targets:
        assert t["gene_symbol"], f"Target missing gene_symbol: {t}"
    print("  [PASS] All targets have gene_symbol")

    # Evidence strength must be HIGH/MEDIUM/LOW
    valid_evidence = {"HIGH", "MEDIUM", "LOW"}
    for t in targets:
        assert t["evidence_strength"] in valid_evidence, f"Invalid evidence: {t['evidence_strength']}"
    print("  [PASS] All evidence_strength values are valid")

    print("\n" + "=" * 70)
    print("  AGENT 1 TEST PASSED")
    print("=" * 70)

    return state


if __name__ == "__main__":
    state = asyncio.run(run_test())
