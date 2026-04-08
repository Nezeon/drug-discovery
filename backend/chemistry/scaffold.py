"""
chemistry/scaffold.py — RDKit scaffold extraction and clustering.

Extracts Murcko scaffolds from a list of SMILES and clusters them
using Butina clustering for diverse seed selection.
"""

from __future__ import annotations

import logging

from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.ML.Cluster import Butina

logger = logging.getLogger(__name__)


def extract_scaffolds(smiles_list: list[str]) -> list[dict]:
    """
    Extract Murcko scaffold for each SMILES.
    Returns list of {smiles, scaffold_smiles} (skips invalid molecules).
    """
    results = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        try:
            scaffold = MurckoScaffold.GetScaffoldForMol(mol)
            scaffold_smi = Chem.MolToSmiles(scaffold)
        except Exception:
            scaffold_smi = smi  # fallback: use original
        results.append({"smiles": smi, "scaffold_smiles": scaffold_smi})
    return results


def cluster_by_scaffold(compounds: list[dict], cutoff: float = 0.4) -> list[list[int]]:
    """
    Cluster compounds by Morgan fingerprint similarity using Butina algorithm.

    compounds: list of dicts, each must have a "smiles" key.
    cutoff: distance cutoff (1 - similarity). 0.4 means >=60% similar in same cluster.

    Returns list of clusters, where each cluster is a list of indices into compounds.
    Clusters are sorted by size (largest first).
    """
    mols = []
    valid_indices = []
    for i, comp in enumerate(compounds):
        mol = Chem.MolFromSmiles(comp["smiles"])
        if mol is not None:
            mols.append(mol)
            valid_indices.append(i)

    if len(mols) < 2:
        return [valid_indices] if valid_indices else []

    fps = [AllChem.GetMorganFingerprintAsBitVect(m, radius=2, nBits=2048) for m in mols]

    # Build distance matrix (lower triangle)
    nfps = len(fps)
    dists = []
    for i in range(1, nfps):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        dists.extend([1 - s for s in sims])

    clusters_raw = Butina.ClusterData(dists, nfps, cutoff, isDistData=True)

    # Map back to original compound indices
    clusters = []
    for cluster in clusters_raw:
        clusters.append([valid_indices[idx] for idx in cluster])

    # Sort by size descending
    clusters.sort(key=len, reverse=True)
    return clusters


def select_diverse_seeds(
    clusters: list[list[int]],
    compounds: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Pick the best compound from each of the top_n largest clusters.
    "Best" = lowest standard_value (most potent) if available, else first in cluster.
    """
    seeds = []
    for cluster in clusters[:top_n]:
        best_idx = cluster[0]
        best_val = float("inf")
        for idx in cluster:
            val = compounds[idx].get("standard_value")
            if val is not None:
                try:
                    v = float(val)
                    if v < best_val:
                        best_val = v
                        best_idx = idx
                except (ValueError, TypeError):
                    pass
            seeds.append(compounds[best_idx])
            break  # just pick the best from cluster
        else:
            seeds.append(compounds[best_idx])

    # Deduplicate by SMILES
    seen = set()
    unique = []
    for s in seeds:
        if s["smiles"] not in seen:
            seen.add(s["smiles"])
            unique.append(s)
    return unique
