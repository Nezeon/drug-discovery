"""
tools/retrosynthesis_client.py — Synthesis route planning.

Uses RDKit BRICS retrosynthetic analysis to plan synthesis routes.
For production, could integrate with ASKCOS (MIT) or IBM RXN APIs.
"""

from __future__ import annotations

import logging
from rdkit import Chem
from rdkit.Chem import BRICS, AllChem, Descriptors, Draw
from rdkit.Chem.Scaffolds.MurckoScaffold import GetScaffoldForMol

logger = logging.getLogger(__name__)

# Common commercially available building blocks (simplified SMILES)
BUILDING_BLOCKS = {
    "c1ccccc1": "Benzene",
    "c1ccncc1": "Pyridine",
    "c1cc[nH]c1": "Pyrrole",
    "C1CCNCC1": "Piperidine",
    "C1CCNC1": "Pyrrolidine",
    "c1ccc2[nH]ccc2c1": "Indole",
    "c1cnc2ccccc2n1": "Quinazoline",
    "O=C(O)c1ccccc1": "Benzoic acid",
    "Nc1ccccc1": "Aniline",
    "Oc1ccccc1": "Phenol",
    "c1ccc(-c2ccccc2)cc1": "Biphenyl",
    "C1COCCN1": "Morpholine",
    "C1CN2CCN1CC2": "Piperazine",
    "CC(=O)O": "Acetic acid",
    "CCOC(=O)C": "Ethyl acetate",
}


async def plan_synthesis_route(smiles: str) -> dict:
    """
    Plan a retrosynthetic route for a given molecule.

    Uses BRICS decomposition to identify fragments that can be
    obtained from commercial sources, and suggests a forward
    synthesis strategy.

    Returns:
        {
            "smiles": str,
            "feasible": bool,
            "num_steps": int,
            "fragments": [{"smiles": str, "name": str|None, "available": bool}],
            "scaffold": str|None,
            "route_description": str,
            "estimated_difficulty": "easy"|"moderate"|"hard"|"very_hard",
            "sa_score": float,
        }
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {
            "smiles": smiles,
            "feasible": False,
            "num_steps": 0,
            "fragments": [],
            "scaffold": None,
            "route_description": "Invalid SMILES — cannot plan synthesis.",
            "estimated_difficulty": "very_hard",
            "sa_score": 10.0,
        }

    # Get SA score
    try:
        from rdkit.Contrib.SA_Score import sascorer
        sa_score = round(sascorer.calculateScore(mol), 2)
    except Exception:
        sa_score = 5.0

    # BRICS decomposition — find retrosynthetic fragments
    try:
        fragments_smiles = list(BRICS.BRICSDecompose(mol))
    except Exception:
        fragments_smiles = []

    # Analyze fragments
    fragments = []
    available_count = 0
    for frag_smi in fragments_smiles:
        # Clean BRICS dummy atoms [1*], [2*], etc.
        clean_smi = _clean_brics_smiles(frag_smi)
        if not clean_smi:
            continue

        name = _identify_building_block(clean_smi)
        is_available = name is not None or _is_simple_fragment(clean_smi)

        fragments.append({
            "smiles": clean_smi,
            "name": name or _guess_fragment_name(clean_smi),
            "available": is_available,
        })
        if is_available:
            available_count += 1

    # Get Murcko scaffold
    try:
        scaffold = Chem.MolToSmiles(GetScaffoldForMol(mol))
    except Exception:
        scaffold = None

    # Estimate synthesis steps
    num_steps = max(1, len(fragments))

    # Determine difficulty
    if sa_score <= 3.0 and available_count == len(fragments):
        difficulty = "easy"
    elif sa_score <= 4.5:
        difficulty = "moderate"
    elif sa_score <= 6.0:
        difficulty = "hard"
    else:
        difficulty = "very_hard"

    # Build route description
    route_desc = _build_route_description(fragments, difficulty, num_steps, scaffold)

    return {
        "smiles": smiles,
        "feasible": sa_score <= 7.0,
        "num_steps": num_steps,
        "fragments": fragments,
        "scaffold": scaffold,
        "route_description": route_desc,
        "estimated_difficulty": difficulty,
        "sa_score": sa_score,
    }


def _clean_brics_smiles(smi: str) -> str | None:
    """Remove BRICS dummy atom labels and return clean SMILES."""
    import re
    cleaned = re.sub(r'\[\d+\*\]', '[H]', smi)
    mol = Chem.MolFromSmiles(cleaned)
    if mol is None:
        return None
    mol = Chem.RemoveHs(mol)
    return Chem.MolToSmiles(mol)


def _identify_building_block(smiles: str) -> str | None:
    """Check if a fragment matches a known commercially available building block."""
    canonical = Chem.MolToSmiles(Chem.MolFromSmiles(smiles)) if Chem.MolFromSmiles(smiles) else None
    if canonical is None:
        return None

    for bb_smi, bb_name in BUILDING_BLOCKS.items():
        bb_canonical = Chem.MolToSmiles(Chem.MolFromSmiles(bb_smi))
        if bb_canonical and canonical == bb_canonical:
            return bb_name

    return None


def _is_simple_fragment(smiles: str) -> bool:
    """Check if a fragment is simple enough to be commercially available."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    return mol.GetNumHeavyAtoms() <= 12 and Descriptors.MolWt(mol) <= 200


def _guess_fragment_name(smiles: str) -> str:
    """Generate a descriptive name for an unknown fragment."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return "Unknown fragment"

    atoms = mol.GetNumHeavyAtoms()
    rings = Chem.rdMolDescriptors.CalcNumRings(mol)

    if rings > 0:
        return f"Ring system ({atoms} atoms, {rings} rings)"
    return f"Chain fragment ({atoms} atoms)"


def _build_route_description(fragments: list, difficulty: str, steps: int, scaffold: str | None) -> str:
    """Build a human-readable synthesis route description."""
    available = [f for f in fragments if f["available"]]
    unavailable = [f for f in fragments if not f["available"]]

    parts = [f"Estimated {steps}-step synthesis ({difficulty} difficulty)."]

    if scaffold:
        parts.append(f"Core scaffold: {scaffold}.")

    if available:
        names = [f["name"] for f in available[:3]]
        parts.append(f"Available building blocks: {', '.join(names)}.")

    if unavailable:
        parts.append(f"{len(unavailable)} fragment(s) require custom preparation.")

    if difficulty in ("easy", "moderate"):
        parts.append("Route appears feasible with standard medicinal chemistry techniques.")
    elif difficulty == "hard":
        parts.append("Route requires specialized chemistry expertise.")
    else:
        parts.append("Challenging synthesis — consider structural simplification.")

    return " ".join(parts)
