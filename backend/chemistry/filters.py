"""
chemistry/filters.py — Molecular property filters.

Filters generated SMILES down to viable drug candidates using:
  1. SMILES validity (RDKit null check)
  2. Lipinski Ro5
  3. SA Score (synthetic accessibility)
  4. Novelty (Tanimoto similarity < threshold vs reference set)
"""

from __future__ import annotations

import logging
import os
import sys

from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem, Descriptors

logger = logging.getLogger(__name__)

# SA Score import — lives in rdkit.Contrib
try:
    from rdkit.Contrib.SA_Score import sascorer
except ImportError:
    # Fallback: try adding Contrib to path manually
    try:
        import rdkit
        contrib_path = os.path.join(os.path.dirname(rdkit.__file__), "..", "Contrib", "SA_Score")
        if os.path.isdir(contrib_path):
            sys.path.insert(0, contrib_path)
            import sascorer  # type: ignore
        else:
            sascorer = None
            logger.warning("SA_Score module not found — SA score filtering disabled")
    except Exception:
        sascorer = None
        logger.warning("SA_Score import failed — SA score filtering disabled")


def passes_lipinski(smiles: str) -> bool:
    """Check Lipinski Rule of Five. Returns True if passes."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    return mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10


def get_sa_score(smiles: str) -> float | None:
    """
    Compute synthetic accessibility score (1 = easy, 10 = hard).
    Returns None if SA_Score module is unavailable or molecule is invalid.
    """
    if sascorer is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        return sascorer.calculateScore(mol)
    except Exception:
        return None


def compute_tanimoto(query_smiles: str, reference_list: list[str]) -> float:
    """
    Returns max Tanimoto similarity between query and any compound in reference_list.
    Uses Morgan fingerprints (radius=2, 2048 bits).
    Returns 1.0 if query is invalid (treat as non-novel).
    """
    query_mol = Chem.MolFromSmiles(query_smiles)
    if query_mol is None:
        return 1.0

    query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, radius=2, nBits=2048)

    max_sim = 0.0
    for ref_smi in reference_list:
        ref_mol = Chem.MolFromSmiles(ref_smi)
        if ref_mol is None:
            continue
        ref_fp = AllChem.GetMorganFingerprintAsBitVect(ref_mol, radius=2, nBits=2048)
        sim = DataStructs.TanimotoSimilarity(query_fp, ref_fp)
        if sim > max_sim:
            max_sim = sim

    return max_sim


def filter_candidates(
    compounds: list[str],
    reference_smiles: list[str],
    novelty_threshold: float = 0.85,
    sa_max: float = 6.0,
) -> list[dict]:
    """
    Apply full filter pipeline to a list of candidate SMILES.

    Filters in order: validity → Lipinski → SA score → novelty.

    Returns list of {smiles, sa_score, novelty_score, passed_lipinski}.
    """
    results = []

    for smi in compounds:
        # 1. Validity
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        canonical = Chem.MolToSmiles(mol)

        # 2. Lipinski
        if not passes_lipinski(canonical):
            continue

        # 3. SA Score
        sa = get_sa_score(canonical)
        if sa is not None and sa > sa_max:
            continue

        # 4. Novelty — Tanimoto vs reference set
        tanimoto = compute_tanimoto(canonical, reference_smiles)
        if tanimoto >= novelty_threshold:
            continue  # Too similar to known compounds

        results.append({
            "smiles": canonical,
            "sa_score": round(sa, 2) if sa is not None else None,
            "novelty_score": round(tanimoto, 4),
            "passed_lipinski": True,
        })

    logger.info("filter_candidates: %d in → %d passed all filters", len(compounds), len(results))
    return results
