"""
tools/preload_models.py — Preload DeepChem TDC models and verify RDKit.

Run once before first use:
    cd backend && python tools/preload_models.py

Forces import of admet_predictor module (which loads TDC models at import time)
and verifies all chemistry dependencies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("Preloading MolForge AI chemistry stack...")

    # 1. Verify RDKit
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles("c1ccccc1")
        assert mol is not None
        print("[OK] RDKit working")
    except Exception as exc:
        print(f"[FAIL] RDKit: {exc}")
        sys.exit(1)

    # 2. Verify SA Score
    try:
        from chemistry.filters import get_sa_score
        score = get_sa_score("c1ccccc1")
        print(f"[OK] SA Score working (benzene SA = {score})")
    except Exception as exc:
        print(f"[WARN] SA Score: {exc}")

    # 3. Load ADMET predictor (triggers TDC model loading if available)
    try:
        from agents.admet_predictor import _compute_descriptors
        result = _compute_descriptors("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
        if result:
            print(f"[OK] ADMET predictor working (aspirin verdict: {result['verdict']})")
        else:
            print("[FAIL] ADMET predictor returned None for aspirin")
    except Exception as exc:
        print(f"[FAIL] ADMET predictor: {exc}")
        sys.exit(1)

    # 4. Check DeepChem/TDC (optional)
    try:
        import deepchem
        print(f"[OK] DeepChem {deepchem.__version__} available")
    except ImportError:
        print("[INFO] DeepChem not installed — using RDKit heuristic ADMET (install deepchem for ML predictions)")

    try:
        from tdc.single_pred import ADME
        print("[OK] TDC available")
    except ImportError:
        print("[INFO] TDC not installed — ML ADMET models unavailable")

    print("\nModels preloaded successfully.")


if __name__ == "__main__":
    main()
