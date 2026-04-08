"""
Test Agent 4 — Compound Discovery (isolation test).

Creates mock state with validated_target = {uniprot_id: "Q5S007", name: "LRRK2"}
Runs the agent, prints counts, verifies all SMILES valid and novelty < 0.85.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rdkit import Chem
from orchestrator.state import create_initial_state
from agents.compound_discovery import CompoundDiscovery


async def main():
    state = create_initial_state("Parkinson's Disease", job_id="test_agent4")
    state["validated_target"] = {
        "name": "LRRK2",
        "uniprot_id": "Q5S007",
        "druggability_score": 0.87,
        "evidence": "well-validated kinase target",
    }

    print("=" * 60)
    print("TEST: Agent 4 — Compound Discovery")
    print(f"Target: {state['validated_target']['name']} ({state['validated_target']['uniprot_id']})")
    print("=" * 60)

    agent = CompoundDiscovery()
    state = await agent.run(state)

    compounds = state["candidate_compounds"]
    print(f"\n--- Results ---")
    print(f"  Final candidate count: {len(compounds)}")

    if compounds:
        print(f"\n--- First 3 candidates ---")
        for i, c in enumerate(compounds[:3]):
            print(f"  [{i}] SMILES: {c['smiles']}")
            print(f"      SA score: {c['sa_score']}, Novelty: {c['novelty_score']}")
            print(f"      Scaffold: {c['scaffold_origin']}, Method: {c['generation_method']}")

    print(f"\n--- Status Updates ---")
    for u in state["status_updates"]:
        print(f"  > {u}")

    if state["errors"]:
        print(f"\n--- Errors ---")
        for e in state["errors"]:
            print(f"  ! {e}")

    # Assertions
    assert len(compounds) > 0, "FAIL: no candidates generated"

    for i, c in enumerate(compounds):
        mol = Chem.MolFromSmiles(c["smiles"])
        assert mol is not None, f"FAIL: invalid SMILES at index {i}: {c['smiles']}"
        assert c["novelty_score"] < 0.85, f"FAIL: novelty_score >= 0.85 at index {i}: {c['novelty_score']}"

    print(f"\n{'=' * 60}")
    print(f"ALL ASSERTIONS PASSED — {len(compounds)} valid, novel candidates")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
