"""
agents/competitive_scout.py — Agent 7: Competitive Scout

OWNS:       state["competitive_data"]
READS:      state["disease_name"], state["validated_target"] (if available)
WRITES:     state["competitive_data"] — {
                total_trials, active_trials, approved_drug_count,
                density_label, target_level_competition,
                existing_drugs_are_curative, white_space_narrative,
                top_sponsors
            }

APIS CALLED:
  - ClinicalTrials.gov API v2 (tools/clinicaltrials_client.py)
  - OpenFDA drug label API (tools/openfda_client.py)
  - Gemini — curative vs symptomatic assessment

RUNS IN PARALLEL with the science pipeline. Part of the market track (Agents 6-8).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

import config
from agents.base_agent import BaseAgent
from orchestrator.state import MolForgeState
from tools import clinicaltrials_client, openfda_client

logger = logging.getLogger(__name__)

# --- Curative vs symptomatic assessment prompt ---
CURATIVE_ASSESSMENT_PROMPT = """
You are a pharmaceutical analyst assessing the nature of existing treatments.

DISEASE: {disease_name}
APPROVED DRUGS:
{drugs_list}

Are the currently approved drugs for this disease curative or only symptomatic?
Consider:
- Do any drugs modify disease progression?
- Are treatments primarily managing symptoms?
- Is there a significant unmet need for disease-modifying therapies?

Return ONLY valid JSON. No markdown. No explanation.
Schema: {{"are_curative": bool, "assessment": "1-2 sentences", "disease_modifying_count": int}}
"""

# --- White space narrative prompt ---
WHITE_SPACE_PROMPT = """
You are a pharmaceutical competitive intelligence analyst.

DISEASE: {disease_name}
TOTAL CLINICAL TRIALS: {total_trials}
ACTIVE TRIALS: {active_trials}
APPROVED DRUGS: {approved_count}
COMPETITIVE DENSITY: {density}
TOP SPONSORS: {sponsors}

Write a single concise sentence (max 30 words) describing the competitive white space
opportunity for a new drug candidate in this indication.

Return ONLY the sentence, no quotes, no JSON.
"""


class CompetitiveScout(BaseAgent):
    name = "competitive_scout"

    async def run(self, state: MolForgeState) -> MolForgeState:
        disease = state["disease_name"]
        target = state.get("validated_target", {})
        target_gene = target.get("gene_symbol") or target.get("name")

        self.emit(state, f"Competitive Scout: starting — scanning trial landscape for {disease}...")

        # ------------------------------------------------------------------
        # Step 1: Fetch ClinicalTrials.gov data
        # ------------------------------------------------------------------
        self.emit(state, "Competitive Scout: querying ClinicalTrials.gov...")

        try:
            trials_data = await clinicaltrials_client.fetch_trials(
                disease_name=disease,
                target_name=target_gene,
            )
        except Exception as exc:
            state["errors"].append(f"Competitive Scout: ClinicalTrials.gov error: {exc}")
            trials_data = {
                "total_trials": 0, "active_trials": 0, "completed_trials": 0,
                "recruiting_trials": 0, "by_phase": {}, "top_sponsors": [],
                "target_trials": None,
            }

        total_trials = trials_data.get("total_trials", 0)
        active_trials = trials_data.get("active_trials", 0)
        target_trials = trials_data.get("target_trials")

        self.emit(state, f"Competitive Scout: found {total_trials} trials ({active_trials} active)")

        # ------------------------------------------------------------------
        # Step 2: Fetch approved drugs from OpenFDA
        # ------------------------------------------------------------------
        self.emit(state, "Competitive Scout: querying OpenFDA for approved drugs...")

        try:
            approved_drugs = await openfda_client.fetch_approved_drugs(disease)
        except Exception as exc:
            state["errors"].append(f"Competitive Scout: OpenFDA error: {exc}")
            approved_drugs = []

        approved_count = len(approved_drugs)
        self.emit(state, f"Competitive Scout: found {approved_count} approved drugs")

        # ------------------------------------------------------------------
        # Step 3: Assess competitive density
        # ------------------------------------------------------------------
        if approved_count < 3 and active_trials < 10:
            density_label = "WHITE_SPACE"
        elif approved_count > 8 or active_trials > 25:
            density_label = "CROWDED"
        else:
            density_label = "MODERATE"

        # ------------------------------------------------------------------
        # Step 4: Check target-level competition
        # ------------------------------------------------------------------
        target_level_competition = False
        if target_trials is not None and target_trials > 0:
            target_level_competition = True
            logger.info("Target %s: %d trials found", target_gene, target_trials)

        # ------------------------------------------------------------------
        # Step 5: Curative vs symptomatic assessment via Gemini
        # ------------------------------------------------------------------
        existing_drugs_are_curative = True  # Default conservative assumption
        curative_assessment = ""

        if config.GEMINI_API_KEY and approved_drugs:
            self.emit(state, "Competitive Scout: assessing curative vs symptomatic treatments...")

            drugs_text = "\n".join(
                f"- {d['drug_name']} ({d['generic_name']})"
                + (f": {d['mechanism_hint'][:100]}" if d.get("mechanism_hint") else "")
                for d in approved_drugs[:10]
            )

            try:
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=config.GEMINI_API_KEY,
                    temperature=0.1,
                )

                prompt = CURATIVE_ASSESSMENT_PROMPT.format(
                    disease_name=disease,
                    drugs_list=drugs_text,
                )
                response = await llm.ainvoke(prompt)
                raw = response.content if hasattr(response, "content") else str(response)
                parsed = self.parse_gemini_json(raw)

                if parsed and isinstance(parsed, dict):
                    existing_drugs_are_curative = parsed.get("are_curative", True)
                    curative_assessment = parsed.get("assessment", "")
                else:
                    state["errors"].append("Competitive Scout: Gemini curative assessment unparseable")
            except Exception as exc:
                state["errors"].append(f"Competitive Scout: Gemini curative check failed: {exc}")

        # ------------------------------------------------------------------
        # Step 6: White space narrative via Gemini
        # ------------------------------------------------------------------
        white_space_narrative = ""

        if config.GEMINI_API_KEY:
            try:
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=config.GEMINI_API_KEY,
                    temperature=0.3,
                )

                prompt = WHITE_SPACE_PROMPT.format(
                    disease_name=disease,
                    total_trials=total_trials,
                    active_trials=active_trials,
                    approved_count=approved_count,
                    density=density_label,
                    sponsors=", ".join(trials_data.get("top_sponsors", [])[:5]) or "N/A",
                )
                response = await llm.ainvoke(prompt)
                white_space_narrative = (response.content if hasattr(response, "content") else str(response)).strip()
            except Exception as exc:
                state["errors"].append(f"Competitive Scout: Gemini white space narrative failed: {exc}")
                white_space_narrative = f"{density_label} competitive landscape with {approved_count} approved drugs."

        if not white_space_narrative:
            white_space_narrative = f"{density_label} competitive landscape with {approved_count} approved drugs and {active_trials} active trials."

        # ------------------------------------------------------------------
        # Write to state
        # ------------------------------------------------------------------
        state["competitive_data"] = {
            "total_trials": total_trials,
            "active_trials": active_trials,
            "completed_trials": trials_data.get("completed_trials", 0),
            "recruiting_trials": trials_data.get("recruiting_trials", 0),
            "by_phase": trials_data.get("by_phase", {}),
            "approved_drug_count": approved_count,
            "approved_drugs": [
                {"name": d["drug_name"], "generic": d["generic_name"]}
                for d in approved_drugs[:10]
            ],
            "density_label": density_label,
            "target_level_competition": target_level_competition,
            "target_trials": target_trials,
            "existing_drugs_are_curative": existing_drugs_are_curative,
            "curative_assessment": curative_assessment,
            "white_space_narrative": white_space_narrative,
            "top_sponsors": trials_data.get("top_sponsors", [])[:10],
        }

        self.emit(
            state,
            f"Competitive Scout: done — {density_label}, "
            f"{total_trials} trials, {approved_count} approved drugs, "
            f"target competition={target_level_competition}",
        )

        return state
