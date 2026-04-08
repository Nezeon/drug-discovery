"""
chemistry/generator.py — Molecular analogue generator.

Generates novel drug candidates from seed scaffolds using:
  1. R-group enumeration (systematic substituent swapping)
  2. BRICS fragmentation + reassembly (RDKit)

IMPORTANT: Every generated SMILES is validated with Chem.MolFromSmiles() before returning.
"""

from __future__ import annotations

import logging
import random

from rdkit import Chem
from rdkit.Chem import BRICS, AllChem, RWMol

logger = logging.getLogger(__name__)

# Common drug-like R-groups for enumeration
R_GROUP_LIBRARY = [
    "C",          # methyl
    "CC",         # ethyl
    "F",          # fluoro
    "Cl",         # chloro
    "OC",         # methoxy
    "C(F)(F)F",   # trifluoromethyl
    "O",          # hydroxyl
    "N",          # amino
    "C#N",        # cyano
    "C(=O)C",     # acetyl
    "CC(C)C",     # isobutyl
    "C1CC1",      # cyclopropyl
    "c1ccccc1",   # phenyl
    "OCC",        # ethoxy
    "NC(=O)C",    # acetamido
    "S(=O)(=O)C", # methanesulfonyl
    "C(=O)O",     # carboxyl
    "C(=O)N",     # carboxamide
    "c1ccncc1",   # pyridyl
    "C1CCNCC1",   # piperidyl
]


def _validate_smiles(smi: str) -> str | None:
    """Return canonical SMILES if valid, None otherwise."""
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def enumerate_rgroup_analogues(scaffold_smiles: str, n: int = 20) -> list[str]:
    """
    Generate analogues by replacing hydrogen atoms on the scaffold with R-groups.
    Returns up to n unique valid SMILES.
    """
    mol = Chem.MolFromSmiles(scaffold_smiles)
    if mol is None:
        return []

    analogues = set()

    # Find atoms that have implicit H (potential R-group attachment points)
    for atom_idx in range(mol.GetNumAtoms()):
        atom = mol.GetAtomWithIdx(atom_idx)
        num_hs = atom.GetTotalNumHs()
        if num_hs == 0:
            continue

        for rg_smi in R_GROUP_LIBRARY:
            if len(analogues) >= n:
                break

            rg_mol = Chem.MolFromSmiles(rg_smi)
            if rg_mol is None:
                continue

            try:
                # Create a combined molecule by connecting R-group to the scaffold
                combined = RWMol(Chem.CombineMols(mol, rg_mol))
                # Bond the first atom of R-group to the scaffold atom
                scaffold_atom = atom_idx
                rg_first_atom = mol.GetNumAtoms()  # first atom index of R-group in combined mol
                combined.AddBond(scaffold_atom, rg_first_atom, Chem.BondType.SINGLE)

                try:
                    Chem.SanitizeMol(combined)
                    new_smi = Chem.MolToSmiles(combined)
                    # Validate
                    if _validate_smiles(new_smi) and new_smi != scaffold_smiles:
                        analogues.add(new_smi)
                except Exception:
                    continue
            except Exception:
                continue

        if len(analogues) >= n:
            break

    return list(analogues)[:n]


def generate_brics_analogues(seed_smiles_list: list[str], n: int = 20) -> list[str]:
    """
    Generate analogues via BRICS fragmentation + recombination.
    Takes a list of seed SMILES, fragments them all, then recombines.
    Returns up to n unique valid SMILES.
    """
    all_frags = set()
    for smi in seed_smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        try:
            frags = BRICS.BRICSDecompose(mol)
            all_frags.update(frags)
        except Exception as exc:
            logger.debug("BRICS decompose failed for %s: %s", smi, exc)

    if len(all_frags) < 2:
        logger.info("BRICS: not enough fragments (%d) for recombination", len(all_frags))
        return []

    # Convert fragment SMILES to mol objects
    frag_mols = []
    for frag_smi in all_frags:
        fmol = Chem.MolFromSmiles(frag_smi)
        if fmol is not None:
            frag_mols.append(fmol)

    if len(frag_mols) < 2:
        return []

    # BRICS build — generates new molecules from fragments
    # BRICSBuild returns a generator, can be very large — limit output
    analogues = set()
    try:
        builder = BRICS.BRICSBuild(frag_mols)
        for _ in range(n * 10):  # sample more than needed, filter later
            try:
                product = next(builder)
                smi = Chem.MolToSmiles(product)
                if _validate_smiles(smi):
                    analogues.add(smi)
                if len(analogues) >= n:
                    break
            except StopIteration:
                break
            except Exception:
                continue
    except Exception as exc:
        logger.warning("BRICS build failed: %s", exc)

    # Also try random pairwise fragment combination as fallback
    if len(analogues) < n and len(frag_mols) >= 2:
        frag_smiles = [Chem.MolToSmiles(fm) for fm in frag_mols]
        random.shuffle(frag_smiles)
        for i in range(min(len(frag_smiles) - 1, n)):
            # Simple concatenation with dot notation (mixture) — crude but adds diversity
            combo = f"{frag_smiles[i]}.{frag_smiles[(i + 1) % len(frag_smiles)]}"
            valid = _validate_smiles(combo)
            if valid:
                analogues.add(valid)
            if len(analogues) >= n:
                break

    # Filter out original seeds
    seed_set = set(seed_smiles_list)
    analogues = {a for a in analogues if a not in seed_set}

    return list(analogues)[:n]
