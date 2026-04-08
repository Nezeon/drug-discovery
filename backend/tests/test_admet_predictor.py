"""
Test Agent 5 — ADMET Predictor (isolation test).

Uses 5 known SMILES:
  - Aspirin (should be PASS or WARN, not FAIL)
  - Ibuprofen
  - Caffeine
  - Penicillin G
  - Terfenadine (known hERG blocker — should get FAIL)

Verifies verdict logic and structural alert detection.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.state import create_initial_state
from agents.admet_predictor import AdmetPredictor

# Known compounds for testing
TEST_COMPOUNDS = [
    {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "name": "Aspirin"},
    {"smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "name": "Ibuprofen"},
    {"smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O", "name": "Caffeine"},
    {"smiles": "CC1(C(N2C(S1)C(C2=O)NC(=O)Cc3ccccc3)C(=O)O)C", "name": "Penicillin G"},
    {"smiles": "CC(C)(C)c1ccc(cc1)C(O)CCCN1CCC(CC1)C(O)(c1ccccc1)c1ccccc1", "name": "Terfenadine"},
]


async def main():
    state = create_initial_state("ADMET Test", job_id="test_agent5")
    state["candidate_compounds"] = TEST_COMPOUNDS

    print("=" * 70)
    print("TEST: Agent 5 — ADMET Predictor")
    print("=" * 70)

    agent = AdmetPredictor()
    state = await agent.run(state)

    results = state["admet_results"]
    print(f"\nScreened {len(results)} compounds:\n")

    for r in results:
        # Find the name
        name = "?"
        for tc in TEST_COMPOUNDS:
            if tc["smiles"] == r["smiles"]:
                name = tc["name"]
                break

        print(f"  {name}")
        print(f"    SMILES:  {r['smiles'][:60]}...")
        print(f"    MW={r['mw']}, LogP={r['logp']}, TPSA={r['tpsa']}")
        print(f"    HBD={r['hbd']}, HBA={r['hba']}, RotBonds={r['rot_bonds']}")
        print(f"    Caco2={r['caco2']}, hERG={r['herg']}, Ames={r['ames']}")
        print(f"    DILI={r['dili']}, BBB={r['bbb']}")
        print(f"    VERDICT: {r['verdict']}  Flags: {r['flags']}")
        print()

    print("--- Status Updates ---")
    for u in state["status_updates"]:
        print(f"  > {u}")

    # Assertions
    verdicts = {tc["smiles"]: None for tc in TEST_COMPOUNDS}
    for r in results:
        verdicts[r["smiles"]] = r["verdict"]

    # Terfenadine is a known hERG blocker — should FAIL
    terf_smi = TEST_COMPOUNDS[4]["smiles"]
    terf_verdict = verdicts.get(terf_smi)
    print(f"\nTerfenadine verdict: {terf_verdict}")
    assert terf_verdict == "FAIL", f"FAIL: expected Terfenadine to FAIL (got {terf_verdict})"

    # Aspirin should NOT be FAIL
    asp_smi = TEST_COMPOUNDS[0]["smiles"]
    asp_verdict = verdicts.get(asp_smi)
    print(f"Aspirin verdict: {asp_verdict}")
    assert asp_verdict in ("PASS", "WARN"), f"FAIL: expected Aspirin PASS/WARN (got {asp_verdict})"

    print(f"\n{'=' * 70}")
    print("ALL ASSERTIONS PASSED")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
