"""
tests/test_target_validator.py — Integration test for Agent 2 (Target Validator).

Tests the full Target Validator pipeline:
  - OpenTargets association scoring
  - UniProt protein info
  - STRING interaction data
  - HPA tissue expression
  - Composite druggability scoring
  - Gemini evidence summary generation

Run:  cd backend && python -m pytest tests/test_target_validator.py -v -s
"""

import asyncio
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.state import create_initial_state
from agents.target_validator import TargetValidator


async def run_test():
    """Run Target Validator on known Parkinson's targets and validate output."""
    print("=" * 70)
    print("  AGENT 2 TEST — Target Validator")
    print("  Disease: Parkinson's Disease")
    print("  Input targets: LRRK2, SNCA, PINK1, GBA1, VPS13C")
    print("=" * 70)

    # Create initial state with mock Agent 1 output
    state = create_initial_state("Parkinson's Disease", job_id="test_agent2")

    # Mock candidate_targets from Agent 1
    state["candidate_targets"] = [
        {
            "gene_symbol": "LRRK2",
            "protein_name": "leucine rich repeat kinase 2",
            "mechanism": "LRRK2 mutations cause autosomal dominant PD via kinase gain-of-function",
            "evidence_strength": "HIGH",
            "novelty_signal": True,
            "existing_drug_count": 0,
            "disgenet_score": 0.88,
            "source_pmids": ["39153957", "39799347"],
        },
        {
            "gene_symbol": "SNCA",
            "protein_name": "synuclein alpha",
            "mechanism": "Alpha-synuclein aggregation forms Lewy bodies, a hallmark of PD pathology",
            "evidence_strength": "HIGH",
            "novelty_signal": True,
            "existing_drug_count": 0,
            "disgenet_score": 0.875,
            "source_pmids": ["40121531"],
        },
        {
            "gene_symbol": "PINK1",
            "protein_name": "PTEN induced kinase 1",
            "mechanism": "PINK1 loss impairs mitophagy leading to dopaminergic neuron death",
            "evidence_strength": "HIGH",
            "novelty_signal": True,
            "existing_drug_count": 0,
            "disgenet_score": 0.72,
            "source_pmids": [],
        },
        {
            "gene_symbol": "GBA1",
            "protein_name": "glucosylceramidase beta 1",
            "mechanism": "GBA1 mutations reduce GCase activity causing lysosomal dysfunction in PD",
            "evidence_strength": "MEDIUM",
            "novelty_signal": True,
            "existing_drug_count": 1,
            "disgenet_score": 0.748,
            "source_pmids": ["40121531"],
        },
        {
            "gene_symbol": "VPS13C",
            "protein_name": "vacuolar protein sorting 13 homolog C",
            "mechanism": "VPS13C mediates ER-lysosome contacts following lysosome damage",
            "evidence_strength": "MEDIUM",
            "novelty_signal": True,
            "existing_drug_count": 0,
            "disgenet_score": 0.755,
            "source_pmids": ["40211074"],
        },
    ]

    # Run agent
    agent = TargetValidator()
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

    # Print validated target
    vt = state["validated_target"]
    print("\n--- Validated Target (Winner) ---")
    print(f"  Gene:           {vt.get('gene_symbol', 'N/A')}")
    print(f"  Protein:        {vt.get('protein_name', 'N/A')}")
    print(f"  UniProt ID:     {vt.get('uniprot_id', 'N/A')}")
    print(f"  Druggability:   {vt.get('druggability_score', 0):.4f}")
    print(f"  OT Score:       {vt.get('opentargets_score', 0):.4f}")
    print(f"  Binding Site:   {vt.get('has_binding_site', 'N/A')}")
    print(f"  Hub Protein:    {vt.get('is_hub_protein', 'N/A')}")
    print(f"  Tissue Expr:    {vt.get('expressed_in_target_tissue', 'N/A')} ({vt.get('tissue_name', 'N/A')})")
    print(f"  Evidence:       {vt.get('evidence_summary', 'N/A')}")

    # --- Assertions ---
    print("\n--- Assertions ---")

    # validated_target must not be empty
    assert vt, "validated_target is empty"
    print("  [PASS] validated_target is not empty")

    # uniprot_id must be present and non-empty
    uniprot_id = vt.get("uniprot_id", "")
    assert uniprot_id, f"uniprot_id is empty — Agent 3 needs this! Got: {vt}"
    print(f"  [PASS] uniprot_id present: {uniprot_id}")

    # druggability_score must be between 0 and 1
    drug_score = vt.get("druggability_score", -1)
    assert 0 <= drug_score <= 1, f"druggability_score out of range: {drug_score}"
    print(f"  [PASS] druggability_score in [0,1]: {drug_score:.4f}")

    # gene_symbol must be present
    assert vt.get("gene_symbol"), "gene_symbol is missing"
    print(f"  [PASS] gene_symbol present: {vt['gene_symbol']}")

    # evidence_summary must be present
    assert vt.get("evidence_summary"), "evidence_summary is missing"
    print(f"  [PASS] evidence_summary present ({len(vt['evidence_summary'])} chars)")

    print("\n" + "=" * 70)
    print("  AGENT 2 TEST PASSED")
    print("=" * 70)

    return state


if __name__ == "__main__":
    state = asyncio.run(run_test())
