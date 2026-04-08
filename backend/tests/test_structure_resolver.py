"""
Test Agent 3 — Structure Resolver (isolation test).

Creates a mock state with validated_target = {uniprot_id: "Q5S007", name: "LRRK2"}
Runs the agent, prints state["protein_structure"], verifies PDB file exists on disk.
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend/ is on the import path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.state import create_initial_state
from agents.structure_resolver import StructureResolver


async def main():
    # Create mock state as if Agent 2 already ran
    state = create_initial_state("Parkinson's Disease", job_id="test_agent3")
    state["validated_target"] = {
        "name": "LRRK2",
        "uniprot_id": "Q5S007",
        "druggability_score": 0.87,
        "evidence": "well-validated kinase target",
    }

    print("=" * 60)
    print("TEST: Agent 3 — Structure Resolver")
    print(f"Target: {state['validated_target']['name']} ({state['validated_target']['uniprot_id']})")
    print("=" * 60)

    agent = StructureResolver()
    state = await agent.run(state)

    print("\n--- state['protein_structure'] ---")
    ps = state["protein_structure"]
    for k, v in ps.items():
        print(f"  {k}: {v}")

    print("\n--- Status Updates ---")
    for u in state["status_updates"]:
        print(f"  > {u}")

    if state["errors"]:
        print("\n--- Errors ---")
        for e in state["errors"]:
            print(f"  ! {e}")

    # Assertions
    pdb_path = ps.get("pdb_file_path")
    assert pdb_path, "FAIL: pdb_file_path is empty"
    assert Path(pdb_path).exists(), f"FAIL: PDB file does not exist at {pdb_path}"
    assert Path(pdb_path).stat().st_size > 0, "FAIL: PDB file is empty"
    assert ps.get("source") in ("alphafold_db", "rcsb_pdb"), f"FAIL: unexpected source: {ps.get('source')}"
    assert ps.get("uniprot_id") == "Q5S007", "FAIL: uniprot_id mismatch"

    print("\n" + "=" * 60)
    print(f"ALL ASSERTIONS PASSED — PDB saved at {pdb_path}")
    pdb_size = Path(pdb_path).stat().st_size
    print(f"PDB file size: {pdb_size:,} bytes")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
