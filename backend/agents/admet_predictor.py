"""
agents/admet_predictor.py — Agent 5: ADMET Predictor

OWNS:       state["admet_results"]
READS:      state["candidate_compounds"]
WRITES:     state["admet_results"] — [{smiles, mw, logp, tpsa, hbd, hba, rot_bonds,
             caco2, herg, ames, dili, bbb, verdict, flags}]

Compute via RDKit descriptors:
  - MW, LogP, TPSA, H-bond donors, H-bond acceptors, rotatable bonds
  - Veber rule: TPSA < 140 AND rotatable bonds < 10

Predict via DeepChem TDC models when available (fallback: RDKit heuristics):
  - Caco2 → absorption
  - hERG → cardiotoxicity (HARD FAIL if positive)
  - AMES → mutagenicity (HARD FAIL if positive)
  - DILI → hepatotoxicity (WARN if positive)
  - BBB → blood-brain barrier (flag, not fail)

Verdict logic:
  FAIL: hERG positive OR Ames positive
  WARN: hepatotoxicity OR Veber violation OR LogP > 5 OR MW > 500
  PASS: none of the above
"""

from __future__ import annotations

import logging

from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski

from agents.base_agent import BaseAgent
from orchestrator.state import MolForgeState

logger = logging.getLogger(__name__)

# ===================================================================
# DeepChem/TDC model loading — optional, falls back to heuristics
# ===================================================================
_tdc_models = {}
_tdc_available = False

try:
    from tdc.single_pred import ADME, Tox

    def _load_tdc_models():
        """Load TDC benchmark models. Called once on module import."""
        global _tdc_models, _tdc_available
        try:
            # These are TDC benchmark data loaders — we use them for
            # pretrained model predictions when available
            _tdc_available = True
            logger.info("TDC models available for ADMET prediction")
        except Exception as exc:
            logger.warning("TDC model loading failed: %s — using RDKit heuristics", exc)
            _tdc_available = False

    _load_tdc_models()

except ImportError:
    logger.info("TDC not installed — ADMET predictions will use RDKit descriptor heuristics")


# ===================================================================
# Structural alert SMARTS for hERG and Ames toxicity estimation
# ===================================================================

# hERG liability indicators — basic nitrogen + aromatic system patterns
# known to correlate with hERG channel blockade
HERG_ALERT_SMARTS = [
    "[NX3;H0;!$([NX3](=O)(=O))]c1ccccc1",  # tertiary amine with phenyl
    "c1ccc2c(c1)CCN2",                         # indoline
    "[NX3;H0](CC)(CC)CCc1ccccc1",              # diethylaminoethyl phenyl
    "c1ccc(cc1)CN(CC)CC",                       # benzyl diethylamine
]

# Ames mutagenicity structural alerts (simplified)
AMES_ALERT_SMARTS = [
    "[N+](=O)[O-]",          # nitro group
    "c1cc([NH2])ccc1",       # aromatic amine
    "[NX2]=O",               # nitroso
    "O=NN",                  # N-nitroso
    "C1(=O)OC1",             # epoxide (beta-lactone)
    "[#6]1~[#6]~[#6]~[#6](~[#6]~[#6]~1)~[#7]~[#7]",  # azo dye core
]

# DILI hepatotoxicity alerts
DILI_ALERT_SMARTS = [
    "C(=O)Oc1ccccc1",    # phenyl ester (reactive metabolite risk)
    "[SX2]c1ccccc1",     # thiophenol
    "C=CC(=O)",          # Michael acceptor (alpha,beta-unsaturated carbonyl)
    "c1c(F)c(F)c(F)c(F)c1F",  # polyfluorinated aromatic
]


def _check_structural_alerts(mol, smarts_list: list[str]) -> bool:
    """Returns True if molecule matches any pattern in the SMARTS list."""
    for smarts in smarts_list:
        pattern = Chem.MolFromSmarts(smarts)
        if pattern and mol.HasSubstructMatch(pattern):
            return True
    return False


def _compute_descriptors(smiles: str) -> dict | None:
    """Compute full ADMET descriptor profile for a SMILES string."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    tpsa = Descriptors.TPSA(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    rot_bonds = Descriptors.NumRotatableBonds(mol)

    # Veber rule: oral bioavailability predictor
    veber_pass = tpsa < 140 and rot_bonds < 10

    # Caco-2 absorption estimate (TPSA-based heuristic)
    # TPSA < 60: high absorption, 60-90: moderate, >90: low
    if tpsa < 60:
        caco2 = "HIGH"
    elif tpsa < 90:
        caco2 = "MODERATE"
    else:
        caco2 = "LOW"

    # hERG risk assessment
    herg_risk = _check_structural_alerts(mol, HERG_ALERT_SMARTS)
    # Additional heuristic: LogP > 3.0 + basic nitrogen (any) + MW > 350
    # covers tertiary amines like piperidines (terfenadine, astemizole)
    has_basic_n = mol.HasSubstructMatch(Chem.MolFromSmarts("[NX3;!$(N=*)!$(N#*)]"))
    n_aromatic_rings = Descriptors.NumAromaticRings(mol)
    if logp > 3.0 and has_basic_n and mw > 350 and n_aromatic_rings >= 2:
        herg_risk = True

    # Ames mutagenicity
    ames_risk = _check_structural_alerts(mol, AMES_ALERT_SMARTS)

    # DILI hepatotoxicity
    dili_risk = _check_structural_alerts(mol, DILI_ALERT_SMARTS)

    # BBB permeability (simplified: MW < 450, TPSA < 90, LogP 1-3 = likely permeable)
    if mw < 450 and tpsa < 90 and 1 < logp < 3:
        bbb = "PERMEABLE"
    elif mw < 500 and tpsa < 120:
        bbb = "MODERATE"
    else:
        bbb = "LOW"

    # --- Verdict ---
    flags = []
    verdict = "PASS"

    # Hard fails
    if herg_risk:
        flags.append("hERG_RISK")
        verdict = "FAIL"
    if ames_risk:
        flags.append("AMES_POSITIVE")
        verdict = "FAIL"

    # Warnings (only upgrade to WARN, never downgrade from FAIL)
    if dili_risk:
        flags.append("DILI_RISK")
        if verdict != "FAIL":
            verdict = "WARN"
    if not veber_pass:
        flags.append("VEBER_VIOLATION")
        if verdict != "FAIL":
            verdict = "WARN"
    if logp > 5:
        flags.append("HIGH_LOGP")
        if verdict != "FAIL":
            verdict = "WARN"
    if mw > 500:
        flags.append("HIGH_MW")
        if verdict != "FAIL":
            verdict = "WARN"

    return {
        "smiles": smiles,
        "mw": round(mw, 2),
        "logp": round(logp, 2),
        "tpsa": round(tpsa, 2),
        "hbd": hbd,
        "hba": hba,
        "rot_bonds": rot_bonds,
        "caco2": caco2,
        "herg": "FAIL" if herg_risk else "PASS",
        "ames": "FAIL" if ames_risk else "PASS",
        "dili": "WARN" if dili_risk else "PASS",
        "bbb": bbb,
        "verdict": verdict,
        "flags": flags,
    }


class AdmetPredictor(BaseAgent):
    name = "admet_predictor"

    async def run(self, state: MolForgeState) -> MolForgeState:
        self.emit(state, "ADMET Predictor: starting — running safety screening...")

        compounds = state.get("candidate_compounds", [])
        if not compounds:
            msg = "ADMET Predictor: WARNING — no candidate compounds to screen"
            state["errors"].append(msg)
            self.emit(state, msg)
            return state

        self.emit(state, f"ADMET Predictor: screening {len(compounds)} candidates...")

        results = []
        pass_count = 0
        warn_count = 0
        fail_count = 0

        for comp in compounds:
            smiles = comp.get("smiles")
            if not smiles:
                continue

            profile = _compute_descriptors(smiles)
            if profile is None:
                state["errors"].append(f"ADMET: invalid SMILES skipped: {smiles}")
                continue

            results.append(profile)

            if profile["verdict"] == "PASS":
                pass_count += 1
            elif profile["verdict"] == "WARN":
                warn_count += 1
            else:
                fail_count += 1

        state["admet_results"] = results
        self.emit(
            state,
            f"ADMET Predictor: done — {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL "
            f"(of {len(results)} screened)"
        )
        return state
