"""
agents/opportunity_scorer.py — Agent 8: Opportunity Scorer

OWNS:       state["opportunity_score"]
READS:      state["market_data"], state["competitive_data"], state["disease_name"]
WRITES:     state["opportunity_score"] — {
                score, rating, market_attractiveness, white_space_score,
                unmet_need_score, commercial_brief, key_flags
            }

GEMINI PROMPT: UNMET_NEED_PROMPT (from CLAUDE.md — SACRED, do not modify)

RUNS IN PARALLEL with the science pipeline. Final agent in the market track.
Converges with the science pipeline at scorer_ranker.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

import config
from agents.base_agent import BaseAgent
from orchestrator.state import MolForgeState

logger = logging.getLogger(__name__)

# --- SACRED PROMPT — from CLAUDE.md, do not modify without approval ---
UNMET_NEED_PROMPT = """
You are a pharmaceutical market analyst assessing commercial opportunity.

DISEASE: {disease_name}
CURRENT TREATMENTS: {current_treatments}
PATIENT POPULATION: {patient_population}
ACTIVE TRIALS: {trial_count}
DISEASE BURDEN (DALY): {daly_score}

Assess the unmet medical need on a scale of 0-1.
Consider: treatment gaps, side effect burden, resistant subpopulations, geographic access.
Return JSON: {{"unmet_need_score": float, "rationale": "2-3 sentences", "key_opportunity": "1 sentence"}}
"""

# --- Commercial brief prompt ---
COMMERCIAL_BRIEF_PROMPT = """
You are a pharmaceutical commercial strategist.

DISEASE: {disease_name}
OPPORTUNITY SCORE: {score:.2f} ({rating})
PATIENT POPULATION: {patient_population}
MARKET SIZE: {market_size}
COMPETITIVE DENSITY: {density}
UNMET NEED: {unmet_need:.2f}
KEY FLAGS: {flags}

Write a 3-sentence commercial brief summarizing the drug discovery opportunity.
Be specific about why this is/isn't attractive.

Return ONLY the 3 sentences, no JSON, no quotes.
"""


class OpportunityScorer(BaseAgent):
    name = "opportunity_scorer"

    async def run(self, state: MolForgeState) -> MolForgeState:
        disease = state["disease_name"]
        market = state.get("market_data", {})
        competitive = state.get("competitive_data", {})

        self.emit(state, "Opportunity Scorer: starting — assessing commercial potential...")

        key_flags: list[str] = []

        # ------------------------------------------------------------------
        # Step 1 — Market Attractiveness Score (0-1)
        # ------------------------------------------------------------------
        patient_pop = market.get("patient_population", "Unknown")
        pop_numeric = _parse_population_safe(patient_pop)
        orphan_flag = market.get("orphan_flag", False)
        daly_total = market.get("daly_total", 0)

        if pop_numeric is not None:
            if pop_numeric < 200_000:
                market_attractiveness = 0.95
                key_flags.append("Orphan drug eligible")
            elif pop_numeric <= 2_000_000:
                market_attractiveness = 0.80
            elif pop_numeric <= 20_000_000:
                market_attractiveness = 0.65
            else:
                market_attractiveness = 0.50
        else:
            market_attractiveness = 0.60  # Default mid-range

        # Bonuses
        if orphan_flag:
            market_attractiveness = min(market_attractiveness + 0.10, 1.0)
        if daly_total and daly_total > 10_000_000:
            market_attractiveness = min(market_attractiveness + 0.05, 1.0)
            key_flags.append("High disease burden (DALYs)")

        # ------------------------------------------------------------------
        # Step 2 — White Space Score (0-1)
        # ------------------------------------------------------------------
        density = competitive.get("density_label", "MODERATE")
        curative = competitive.get("existing_drugs_are_curative", True)
        target_competition = competitive.get("target_level_competition", False)

        density_scores = {"WHITE_SPACE": 0.90, "MODERATE": 0.60, "CROWDED": 0.25}
        white_space_score = density_scores.get(density, 0.60)

        if not curative:
            white_space_score = min(white_space_score + 0.10, 1.0)
            key_flags.append("No curative treatment exists")
        if not target_competition:
            white_space_score = min(white_space_score + 0.05, 1.0)
            key_flags.append("Low target-level competition")

        # ------------------------------------------------------------------
        # Step 3 — Unmet Need Score (0-1) via Gemini
        # ------------------------------------------------------------------
        unmet_need_score = 0.50  # Default

        if config.GEMINI_API_KEY:
            self.emit(state, "Opportunity Scorer: assessing unmet medical need via Gemini...")

            # Build treatments summary
            approved_drugs = competitive.get("approved_drugs", [])
            if approved_drugs:
                treatments_text = ", ".join(d.get("name", d.get("generic", "")) for d in approved_drugs[:8])
            else:
                treatments_text = "No approved drugs found"

            trial_count = competitive.get("active_trials", 0)

            prompt = UNMET_NEED_PROMPT.format(
                disease_name=disease,
                current_treatments=treatments_text,
                patient_population=patient_pop,
                trial_count=trial_count,
                daly_score=f"{daly_total:,}" if daly_total else "Unknown",
            )

            try:
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=config.GEMINI_API_KEY,
                    temperature=0.2,
                )
                response = await llm.ainvoke(prompt)
                raw = response.content if hasattr(response, "content") else str(response)
                parsed = self.parse_gemini_json(raw)

                if parsed and isinstance(parsed, dict):
                    raw_score = parsed.get("unmet_need_score", 0.50)
                    unmet_need_score = max(0.0, min(1.0, float(raw_score)))
                    rationale = parsed.get("rationale", "")
                    key_opp = parsed.get("key_opportunity", "")
                    if key_opp:
                        key_flags.append(key_opp)
                    logger.info("Gemini unmet need: %.2f — %s", unmet_need_score, rationale)
                else:
                    state["errors"].append("Opportunity Scorer: Gemini unmet need unparseable")
            except Exception as exc:
                state["errors"].append(f"Opportunity Scorer: Gemini unmet need failed: {exc}")
        else:
            state["errors"].append("Opportunity Scorer: GEMINI_API_KEY not set")

        # ------------------------------------------------------------------
        # Step 4 — Final Opportunity Score
        # ------------------------------------------------------------------
        score = (
            (market_attractiveness * 0.40)
            + (white_space_score * 0.35)
            + (unmet_need_score * 0.25)
        )
        score = round(score, 4)

        if score >= 0.75:
            rating = "EXCEPTIONAL"
        elif score >= 0.55:
            rating = "HIGH"
        elif score >= 0.35:
            rating = "MEDIUM"
        else:
            rating = "LOW"

        self.emit(state, f"Opportunity Scorer: {rating} ({score:.2f})")

        # ------------------------------------------------------------------
        # Generate commercial brief via Gemini
        # ------------------------------------------------------------------
        commercial_brief = ""

        if config.GEMINI_API_KEY:
            try:
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=config.GEMINI_API_KEY,
                    temperature=0.3,
                )

                prompt = COMMERCIAL_BRIEF_PROMPT.format(
                    disease_name=disease,
                    score=score,
                    rating=rating,
                    patient_population=patient_pop,
                    market_size=market.get("market_size_usd_estimate", "Unknown"),
                    density=density,
                    unmet_need=unmet_need_score,
                    flags=", ".join(key_flags) if key_flags else "None",
                )
                response = await llm.ainvoke(prompt)
                commercial_brief = (response.content if hasattr(response, "content") else str(response)).strip()
            except Exception as exc:
                state["errors"].append(f"Opportunity Scorer: Gemini commercial brief failed: {exc}")

        if not commercial_brief:
            commercial_brief = (
                f"{disease} presents a {rating.lower()} commercial opportunity "
                f"with {patient_pop} patients globally. "
                f"The competitive landscape is {density.lower().replace('_', ' ')} "
                f"with an unmet need score of {unmet_need_score:.2f}."
            )

        # ------------------------------------------------------------------
        # Write to state
        # ------------------------------------------------------------------
        state["opportunity_score"] = {
            "score": score,
            "rating": rating,
            "market_attractiveness": round(market_attractiveness, 4),
            "white_space_score": round(white_space_score, 4),
            "unmet_need_score": round(unmet_need_score, 4),
            "commercial_brief": commercial_brief,
            "key_flags": key_flags,
        }

        self.emit(
            state,
            f"Opportunity Scorer: done — {rating} opportunity (score={score:.2f}), "
            f"top flag: {key_flags[0] if key_flags else 'none'}",
        )

        return state


def _parse_population_safe(pop_str: str) -> int | None:
    """Safely parse population strings like '10M', '200K', '1.3B'."""
    if not pop_str or pop_str == "Unknown":
        return None

    pop_str = pop_str.strip().upper().replace(",", "")

    try:
        return int(float(pop_str))
    except ValueError:
        pass

    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if pop_str.endswith(suffix):
            try:
                return int(float(pop_str[:-1]) * mult)
            except ValueError:
                pass
    return None
