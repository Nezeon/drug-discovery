"""
scorer/scorer.py — MolForge AI 4D composite scorer.

Combines outputs from the science pipeline (Agents 1-5) and the market pipeline
(Agents 6-8) into a single composite score per candidate compound.

4D Score = Binding x ADMET x Literature x Market

Scoring weights (updated per spec):
  Binding:    0.30
  ADMET:      0.30
  Literature: 0.15
  Market:     0.25

Verdict thresholds:
  GO:          composite_score >= 0.70
  INVESTIGATE: composite_score >= 0.50
  NO-GO:       composite_score < 0.50

HIGH RISK — this file determines final output verdicts for all candidates.
Run gitnexus_impact before editing. Do not change thresholds without approval.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from orchestrator.state import MolForgeState

logger = logging.getLogger(__name__)

# --- Scoring weights (must sum to 1.0) ---
WEIGHT_BINDING = 0.30
WEIGHT_ADMET = 0.30
WEIGHT_LITERATURE = 0.15
WEIGHT_MARKET = 0.25

# --- Verdict thresholds ---
THRESHOLD_GO = 0.70
THRESHOLD_INVESTIGATE = 0.50


def _compute_binding_score(compound: dict[str, Any], admet: dict[str, Any]) -> float:
    """
    Compute Binding Evidence Score (0-1).

    Uses IC50 normalization if available from compound's scaffold_origin / ChEMBL data.
    score = 1 - (log10(IC50_nM) / log10(10000))
    Clamp to [0, 1]. Default 0.5 if no binding data traceable.
    """
    # Try to get IC50 from compound metadata (set during compound_discovery from ChEMBL)
    ic50_nm = compound.get("ic50_nm") or compound.get("seed_ic50_nm")

    if ic50_nm and isinstance(ic50_nm, (int, float)) and ic50_nm > 0:
        # Normalise: IC50 1nM → 1.0, IC50 10000nM → 0.0
        score = 1.0 - (math.log10(ic50_nm) / math.log10(10000))
        return max(0.0, min(1.0, score))

    # Fallback: use novelty_score as a proxy (higher novelty = moderate binding confidence)
    novelty = compound.get("novelty_score", 0.5)
    if isinstance(novelty, (int, float)):
        # Novelty 0.85-1.0 → binding 0.4-0.6 (novel compounds less certain)
        return max(0.3, min(0.7, 0.5 + (1.0 - novelty) * 0.5))

    return 0.5  # Default


def _compute_admet_score(admet: dict[str, Any]) -> float:
    """
    Compute ADMET Safety Score (0-1).

    PASS → 1.0, WARN → 0.6, FAIL → 0.0
    Deduct 0.05 per non-critical flag.
    """
    verdict = admet.get("verdict", "WARN")

    if verdict == "FAIL":
        return 0.0
    elif verdict == "PASS":
        base = 1.0
    else:  # WARN
        base = 0.6

    # Deduct for flags
    flags = admet.get("flags", [])
    deduction = len(flags) * 0.05
    return max(0.0, base - deduction)


def _compute_literature_score(target: dict[str, Any]) -> float:
    """
    Compute Literature Support Score (0-1).

    Uses validated_target's opentargets_score as proxy.
    Falls back to druggability_score.
    """
    # OpenTargets association score is the most direct evidence measure
    ot_score = target.get("opentargets_score")
    if ot_score and isinstance(ot_score, (int, float)):
        return max(0.0, min(1.0, float(ot_score)))

    # Fallback to druggability_score
    drug_score = target.get("druggability_score")
    if drug_score and isinstance(drug_score, (int, float)):
        return max(0.0, min(1.0, float(drug_score)))

    return 0.5  # Default


def _compute_market_score(opportunity: dict[str, Any]) -> float:
    """
    Compute Market Opportunity Score (0-1).

    Directly uses the opportunity_score computed by Agent 8.
    """
    score = opportunity.get("score")
    if score and isinstance(score, (int, float)):
        return max(0.0, min(1.0, float(score)))
    return 0.5  # Default


def score_candidate(
    compound: dict[str, Any],
    admet: dict[str, Any],
    target: dict[str, Any],
    opportunity: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute a composite score for a single candidate compound.

    Args:
        compound:    Entry from state["candidate_compounds"]
        admet:       Matching entry from state["admet_results"]
        target:      state["validated_target"]
        opportunity: state["opportunity_score"]

    Returns:
        Scored dict with all score dimensions and verdict.
    """
    binding_score = _compute_binding_score(compound, admet)
    admet_score = _compute_admet_score(admet)
    literature_score = _compute_literature_score(target)
    market_score = _compute_market_score(opportunity)

    composite = (
        WEIGHT_BINDING * binding_score
        + WEIGHT_ADMET * admet_score
        + WEIGHT_LITERATURE * literature_score
        + WEIGHT_MARKET * market_score
    )

    if composite >= THRESHOLD_GO:
        verdict = "GO"
    elif composite >= THRESHOLD_INVESTIGATE:
        verdict = "INVESTIGATE"
    else:
        verdict = "NO-GO"

    return {
        "smiles": compound.get("smiles", ""),
        "name": compound.get("name"),
        "composite_score": round(composite, 4),
        "binding_score": round(binding_score, 4),
        "admet_score": round(admet_score, 4),
        "literature_score": round(literature_score, 4),
        "market_score": round(market_score, 4),
        "verdict": verdict,
        "novelty_score": compound.get("novelty_score", 0.0),
        "sa_score": compound.get("sa_score"),
        "mw": admet.get("mw"),
        "logp": admet.get("logp"),
        "tpsa": admet.get("tpsa"),
        "flags": admet.get("flags", []),
    }


async def run_scorer(state: MolForgeState) -> MolForgeState:
    """
    LangGraph node function — runs the scorer over all candidate compounds.
    Called after both the science and market pipelines have completed.

    Excludes compounds where ADMET verdict == "FAIL", then ranks the rest
    by composite_score descending.
    """
    state["status_updates"].append("Scorer: ranking all candidates...")

    compounds = state.get("candidate_compounds", [])
    admet_results = state.get("admet_results", [])
    target = state.get("validated_target", {})
    opportunity = state.get("opportunity_score", {})

    # Build a SMILES -> ADMET lookup for fast matching
    admet_by_smiles = {a.get("smiles"): a for a in admet_results}

    scored = []
    excluded_fail = 0

    for compound in compounds:
        smiles = compound.get("smiles", "")
        admet = admet_by_smiles.get(smiles, {})

        # Exclude FAIL compounds from final ranking
        if admet.get("verdict") == "FAIL":
            excluded_fail += 1
            continue

        scored.append(score_candidate(compound, admet, target, opportunity))

    # Sort by composite_score descending
    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    state["final_candidates"] = scored

    go_count = sum(1 for c in scored if c["verdict"] == "GO")
    investigate_count = sum(1 for c in scored if c["verdict"] == "INVESTIGATE")
    nogo_count = sum(1 for c in scored if c["verdict"] == "NO-GO")

    state["status_updates"].append(
        f"Scorer: done — {len(scored)} candidates ranked "
        f"({go_count} GO, {investigate_count} INVESTIGATE, {nogo_count} NO-GO), "
        f"{excluded_fail} excluded (ADMET FAIL)"
    )

    logger.info(
        "Scorer: %d ranked, %d GO, %d INVESTIGATE, %d NO-GO, %d FAIL excluded",
        len(scored), go_count, investigate_count, nogo_count, excluded_fail,
    )

    return state
