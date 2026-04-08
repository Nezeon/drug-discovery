"""
chemistry/visualizer.py — RDKit SMILES → 2D SVG renderer.

Converts SMILES strings to 2D molecular structure SVG images.
SVGs are returned via GET /api/molecule/svg/{job_id}/{candidate_index}
"""

from __future__ import annotations

import logging

from rdkit import Chem
from rdkit.Chem import AllChem, Draw
from rdkit.Chem.Draw import rdMolDraw2D

logger = logging.getLogger(__name__)


def smiles_to_svg(smiles: str, width: int = 350, height: int = 250) -> str | None:
    """
    Convert a SMILES string to an SVG string of the 2D structure.

    Returns None if the SMILES is invalid or rendering fails.
    The SVG uses a white background with dark bonds — suitable for
    display on both light and dark UI backgrounds when placed in
    a light container.
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            logger.warning("Invalid SMILES for SVG rendering: %s", smiles[:80])
            return None

        # Generate 2D coordinates
        AllChem.Compute2DCoords(mol)

        # Use the MolDraw2DSVG drawer for high-quality output
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)

        # Drawing options — clean, publication-quality
        opts = drawer.drawOptions()
        opts.bondLineWidth = 1.5
        opts.additionalAtomLabelPadding = 0.15
        opts.padding = 0.12
        opts.backgroundColour = (1.0, 1.0, 1.0, 1.0)  # White background
        opts.legendFontSize = 14

        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()

        svg_text = drawer.GetDrawingText()
        return svg_text

    except Exception as e:
        logger.error("SVG rendering failed for SMILES '%s': %s", smiles[:60], e)
        return None


def smiles_to_svg_dark(smiles: str, width: int = 350, height: int = 250) -> str | None:
    """
    Render with a dark background for direct embedding in the dark UI.
    Uses light-colored bonds and atom labels.
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        AllChem.Compute2DCoords(mol)

        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        opts = drawer.drawOptions()
        opts.bondLineWidth = 1.5
        opts.additionalAtomLabelPadding = 0.15
        opts.padding = 0.12
        opts.backgroundColour = (0.067, 0.067, 0.075, 1.0)  # #111113 surface color

        # Override default atom colors for dark background
        opts.setAtomColour(6, (0.82, 0.82, 0.85, 1.0))   # C — light gray
        opts.setAtomColour(7, (0.36, 0.61, 0.96, 1.0))   # N — blue
        opts.setAtomColour(8, (0.96, 0.72, 0.19, 1.0))   # O — gold
        opts.setAtomColour(9, (0.65, 0.55, 0.98, 1.0))   # F — violet
        opts.setAtomColour(16, (0.96, 0.72, 0.19, 1.0))  # S — gold
        opts.setAtomColour(17, (0.0, 0.85, 0.64, 1.0))   # Cl — emerald

        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()

        return drawer.GetDrawingText()

    except Exception as e:
        logger.error("Dark SVG rendering failed for SMILES '%s': %s", smiles[:60], e)
        return None
