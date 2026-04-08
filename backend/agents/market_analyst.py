"""
agents/market_analyst.py — Agent 6: Market Analyst

OWNS:       state["market_data"]
READS:      state["disease_name"]
WRITES:     state["market_data"] — {
                patient_population, prevalence_global, daly_total,
                market_size_usd_estimate, market_size_reasoning,
                orphan_flag, data_sources
            }

APIS CALLED:
  - WHO GHO API (tools/who_gho_client.py) — DALY burden, prevalence data
  - Wikidata SPARQL (tools/wikidata_client.py) — epidemiology supplement/fallback
  - Gemini — TAM estimation from prevalence + disease type

RUNS IN PARALLEL with the science pipeline (Agents 1-5).
Both pipelines start from START and converge at scorer_ranker.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

import config
from agents.base_agent import BaseAgent
from orchestrator.state import MolForgeState
from tools import who_gho_client, wikidata_client

logger = logging.getLogger(__name__)

# --- TAM estimation prompt ---
MARKET_SIZE_PROMPT = """
You are a pharmaceutical market analyst estimating the total addressable market
for a new drug candidate.

DISEASE: {disease_name}
PATIENT POPULATION: {patient_population}
ANNUAL PREVALENCE: {prevalence}
ANNUAL DALYs: {daly_total}

Using your knowledge of comparable approved drug prices and treatment costs:
1. Estimate the annual drug market size for this disease in USD
2. Consider both developed and developing market pricing
3. Factor in treatment duration (chronic vs acute)

Return ONLY valid JSON. No markdown. No explanation.
Schema: {{"market_size_usd": "string (e.g. '$6.1B')", "reasoning": "2-3 sentences explaining the estimate", "treatment_type": "chronic|acute|episodic"}}
"""


class MarketAnalyst(BaseAgent):
    name = "market_analyst"

    async def run(self, state: MolForgeState) -> MolForgeState:
        disease = state["disease_name"]
        self.emit(state, f"Market Analyst: starting — estimating disease burden for {disease}...")

        data_sources: list[str] = []

        # ------------------------------------------------------------------
        # Step 1: Fetch WHO GHO data
        # ------------------------------------------------------------------
        self.emit(state, "Market Analyst: querying WHO Global Health Observatory...")

        try:
            who_data = await who_gho_client.fetch_disease_burden(disease)
        except Exception as exc:
            state["errors"].append(f"Market Analyst: WHO GHO error: {exc}")
            who_data = {}

        if who_data and who_data.get("prevalence_global"):
            data_sources.append(f"WHO GHO ({who_data.get('data_source', 'api')})")
            logger.info("WHO GHO: prevalence=%s, DALYs=%s",
                        who_data.get("prevalence_global"), who_data.get("daly_total"))

        # ------------------------------------------------------------------
        # Step 2: Fetch Wikidata epidemiology as supplement/fallback
        # ------------------------------------------------------------------
        self.emit(state, "Market Analyst: querying Wikidata for epidemiology...")

        try:
            wiki_data = wikidata_client.fetch_epidemiology(disease)
        except Exception as exc:
            state["errors"].append(f"Market Analyst: Wikidata error: {exc}")
            wiki_data = {}

        if wiki_data and wiki_data.get("wikidata_entity"):
            data_sources.append("Wikidata")

        # Combine WHO + Wikidata — WHO is authoritative, Wikidata supplements
        prevalence = who_data.get("prevalence_global") or wiki_data.get("prevalence_rate")
        patient_pop = who_data.get("prevalence_global") or wiki_data.get("patient_population_estimate")
        daly_total = who_data.get("daly_total", 0)
        incidence = who_data.get("incidence_annual")
        mortality = who_data.get("mortality_annual")

        if not prevalence and not patient_pop:
            state["errors"].append("Market Analyst: no prevalence data from WHO or Wikidata")
            prevalence = "Unknown"
            patient_pop = "Unknown"

        self.emit(state, f"Market Analyst: prevalence={prevalence}, DALYs={daly_total:,}")

        # ------------------------------------------------------------------
        # Step 3: Estimate TAM using Gemini
        # ------------------------------------------------------------------
        market_size_estimate = "Unknown"
        market_reasoning = ""

        if config.GEMINI_API_KEY:
            self.emit(state, "Market Analyst: estimating total addressable market via Gemini...")

            prompt = MARKET_SIZE_PROMPT.format(
                disease_name=disease,
                patient_population=patient_pop or "Unknown",
                prevalence=prevalence or "Unknown",
                daly_total=f"{daly_total:,}" if daly_total else "Unknown",
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
                    market_size_estimate = parsed.get("market_size_usd", "Unknown")
                    market_reasoning = parsed.get("reasoning", "")
                    data_sources.append("Gemini (market estimation)")
                else:
                    state["errors"].append("Market Analyst: Gemini returned unparseable market estimate")
            except Exception as exc:
                state["errors"].append(f"Market Analyst: Gemini TAM estimation failed: {exc}")
        else:
            state["errors"].append("Market Analyst: GEMINI_API_KEY not set, skipping TAM estimation")

        # ------------------------------------------------------------------
        # Step 4: Orphan disease flag
        # ------------------------------------------------------------------
        orphan_flag = False
        orphan_note = ""

        # Parse patient population to check orphan threshold
        pop_str = str(patient_pop or "0")
        try:
            # Try to parse numeric population from strings like "10M", "200K"
            pop_numeric = _parse_population(pop_str)
            if pop_numeric and pop_numeric < 200_000:
                orphan_flag = True
                orphan_note = f"Qualifies for orphan drug designation ({pop_str} patients globally < 200K threshold)"
        except Exception:
            pass

        if not data_sources:
            data_sources.append("fallback_estimates")

        # ------------------------------------------------------------------
        # Write to state
        # ------------------------------------------------------------------
        state["market_data"] = {
            "patient_population": str(patient_pop) if patient_pop else "Unknown",
            "prevalence_global": str(prevalence) if prevalence else "Unknown",
            "incidence_annual": str(incidence) if incidence else "Unknown",
            "mortality_annual": str(mortality) if mortality else "Unknown",
            "daly_total": daly_total,
            "market_size_usd_estimate": market_size_estimate,
            "market_size_reasoning": market_reasoning,
            "orphan_flag": orphan_flag,
            "orphan_note": orphan_note,
            "data_sources": data_sources,
        }

        self.emit(
            state,
            f"Market Analyst: done — {patient_pop} patients, "
            f"market ~{market_size_estimate}, "
            f"orphan={orphan_flag}",
        )

        return state


def _parse_population(pop_str: str) -> int | None:
    """Parse population strings like '10M', '200K', '1.3B', '537M' to integers."""
    pop_str = pop_str.strip().upper().replace(",", "")

    # Direct numeric
    try:
        return int(float(pop_str))
    except ValueError:
        pass

    # Handle suffixes
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if pop_str.endswith(suffix):
            try:
                return int(float(pop_str[:-1]) * mult)
            except ValueError:
                pass

    return None
