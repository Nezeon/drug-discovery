"""
tests/test_full_pipeline.py — End-to-end pipeline test: Agent 1 -> 2 -> 3 -> 4 -> 5

Runs the full science pipeline for Parkinson's Disease:
  1. Disease Analyst    — mines literature, extracts targets
  2. Target Validator   — validates druggability, selects top target
  3. Structure Resolver — fetches protein structure from AlphaFold/PDB
  4. Compound Discovery — generates novel molecular candidates
  5. ADMET Predictor    — screens for safety

Run:  cd backend && python tests/test_full_pipeline.py
"""

import asyncio
import sys
import os
import time

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.state import create_initial_state
from agents.disease_analyst import DiseaseAnalyst
from agents.target_validator import TargetValidator
from agents.structure_resolver import StructureResolver
from agents.compound_discovery import CompoundDiscovery
from agents.admet_predictor import AdmetPredictor


def print_separator(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


async def run_pipeline():
    """Run the full science pipeline end-to-end."""
    print_separator("FULL PIPELINE TEST -- Parkinson's Disease")
    pipeline_start = time.time()

    state = create_initial_state("Parkinson's Disease", job_id="test_full_pipeline")

    agents = [
        ("Agent 1: Disease Analyst", DiseaseAnalyst()),
        ("Agent 2: Target Validator", TargetValidator()),
        ("Agent 3: Structure Resolver", StructureResolver()),
        ("Agent 4: Compound Discovery", CompoundDiscovery()),
        ("Agent 5: ADMET Predictor", AdmetPredictor()),
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
            # Continue to next agent to see how far we get
            continue

        # Print summary after each agent
        _print_agent_summary(label, state)

    # =============================================
    # Final Pipeline Summary
    # =============================================
    total_time = time.time() - pipeline_start
    print_separator(f"PIPELINE COMPLETE -- {total_time:.1f}s total")

    # Print all status updates
    print("--- All Status Updates ---")
    for update in state["status_updates"]:
        # Safely encode for Windows console
        safe = update.encode("ascii", errors="replace").decode("ascii")
        print(f"  {safe}")

    # Print errors
    if state["errors"]:
        print(f"\n--- Errors ({len(state['errors'])}) ---")
        for err in state["errors"]:
            safe = err.encode("ascii", errors="replace").decode("ascii")
            print(f"  [!] {safe}")

    # Final summary
    vt = state.get("validated_target", {})
    compounds = state.get("candidate_compounds", [])
    admet = state.get("admet_results", [])
    structure = state.get("protein_structure", {})

    print("\n--- FINAL RESULTS ---")
    print(f"  Validated target: {vt.get('gene_symbol', 'N/A')} ({vt.get('uniprot_id', 'N/A')})")
    print(f"  Structure:        {structure.get('source', 'N/A')} (pLDDT={structure.get('plddt_avg', 'N/A')})")
    print(f"  Novel candidates: {len(compounds)}")

    pass_count = sum(1 for a in admet if a.get("verdict") == "PASS")
    warn_count = sum(1 for a in admet if a.get("verdict") == "WARN")
    fail_count = sum(1 for a in admet if a.get("verdict") == "FAIL")
    print(f"  ADMET results:    {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL")

    # Top candidate
    if admet:
        # Find best PASS candidate (or WARN if no PASS)
        pass_candidates = [a for a in admet if a["verdict"] == "PASS"]
        if not pass_candidates:
            pass_candidates = [a for a in admet if a["verdict"] == "WARN"]
        if pass_candidates:
            top = pass_candidates[0]
            print(f"\n  TOP CANDIDATE:")
            print(f"    SMILES:  {top['smiles']}")
            print(f"    Verdict: {top['verdict']}")
            print(f"    MW:      {top.get('mw', 'N/A')} | LogP: {top.get('logp', 'N/A')} | TPSA: {top.get('tpsa', 'N/A')}")
            print(f"    hERG:    {top.get('herg', 'N/A')} | Ames: {top.get('ames', 'N/A')} | DILI: {top.get('dili', 'N/A')}")
            if top.get("flags"):
                print(f"    Flags:   {', '.join(top['flags'])}")

    print(f"\n  Total pipeline time: {total_time:.1f}s")
    print_separator("END")

    return state


def _print_agent_summary(label: str, state: dict):
    """Print concise summary after each agent."""
    if "Disease Analyst" in label:
        targets = state.get("candidate_targets", [])
        print(f"  Targets found: {len(targets)}")
        for t in targets[:3]:
            print(f"    - {t['gene_symbol']}: {t['evidence_strength']}, novel={t['novelty_signal']}")
        if len(targets) > 3:
            print(f"    ... and {len(targets) - 3} more")

    elif "Target Validator" in label:
        vt = state.get("validated_target", {})
        if vt:
            print(f"  Winner: {vt.get('gene_symbol', 'N/A')}")
            print(f"  UniProt ID: {vt.get('uniprot_id', 'N/A')}")
            print(f"  Druggability: {vt.get('druggability_score', 0):.4f}")
        else:
            print("  No validated target")

    elif "Structure Resolver" in label:
        ps = state.get("protein_structure", {})
        if ps:
            print(f"  Source: {ps.get('source', 'N/A')}")
            print(f"  pLDDT: {ps.get('plddt_avg', 'N/A')}")
            print(f"  Path: {ps.get('pdb_file_path', 'N/A')}")
        else:
            print("  No structure resolved")

    elif "Compound Discovery" in label:
        cc = state.get("candidate_compounds", [])
        print(f"  Candidates: {len(cc)}")
        for c in cc[:3]:
            print(f"    - {c['smiles'][:50]}... | SA={c.get('sa_score', 'N/A')} | method={c.get('generation_method', 'N/A')}")

    elif "ADMET Predictor" in label:
        ar = state.get("admet_results", [])
        p = sum(1 for a in ar if a["verdict"] == "PASS")
        w = sum(1 for a in ar if a["verdict"] == "WARN")
        f = sum(1 for a in ar if a["verdict"] == "FAIL")
        print(f"  Results: {p} PASS, {w} WARN, {f} FAIL (of {len(ar)})")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
