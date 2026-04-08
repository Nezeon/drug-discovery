"""
tools/who_gho_client.py — WHO Global Health Observatory (GHO) API client.

Used by Agent 6 (MarketAnalyst) to fetch disease burden statistics.

API: https://ghoapi.azureedge.net/api/
Returns OData JSON format — parse the "value" array.
Rate limits are not documented but be conservative — asyncio.sleep(0.5) between calls.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://ghoapi.azureedge.net/api"

# Map common diseases to WHO GHO indicator keywords and codes.
# WHO codes are specific — we map disease names to the most relevant indicators.
_DISEASE_INDICATOR_MAP: dict[str, dict[str, Any]] = {
    "parkinson": {
        "keywords": ["neurological", "noncommunicable"],
        "indicator_codes": ["NCDMORT3070", "NCD_BMI_30A"],
        "category": "neurological",
    },
    "alzheimer": {
        "keywords": ["dementia", "neurological", "noncommunicable"],
        "indicator_codes": ["NCDMORT3070"],
        "category": "neurological",
    },
    "dementia": {
        "keywords": ["dementia", "neurological"],
        "indicator_codes": ["NCDMORT3070"],
        "category": "neurological",
    },
    "diabetes": {
        "keywords": ["diabetes", "glucose"],
        "indicator_codes": ["NCD_GLUC_04", "NCD_BMI_30A", "NCDMORT3070"],
        "category": "metabolic",
    },
    "cancer": {
        "keywords": ["cancer", "neoplasm", "malignant"],
        "indicator_codes": ["NCDMORT3070"],
        "category": "oncology",
    },
    "malaria": {
        "keywords": ["malaria"],
        "indicator_codes": ["MALARIA_EST_CASES", "MALARIA_EST_DEATHS"],
        "category": "infectious",
    },
    "tuberculosis": {
        "keywords": ["tuberculosis", "TB"],
        "indicator_codes": ["TB_e_inc_num", "TB_e_mort_exc_tbhiv_num"],
        "category": "infectious",
    },
    "hiv": {
        "keywords": ["HIV", "AIDS"],
        "indicator_codes": ["HIV_0000000001"],
        "category": "infectious",
    },
    "asthma": {
        "keywords": ["asthma", "respiratory"],
        "indicator_codes": ["NCDMORT3070"],
        "category": "respiratory",
    },
    "hypertension": {
        "keywords": ["hypertension", "blood pressure"],
        "indicator_codes": ["BP_04", "NCD_HYP_PREVALENCE_A"],
        "category": "cardiovascular",
    },
}

# Fallback prevalence estimates (millions globally) for common diseases.
# Used when WHO GHO API data is unavailable.
_FALLBACK_PREVALENCE: dict[str, dict[str, Any]] = {
    "parkinson": {"prevalence_global": "10M", "incidence_annual": "1.2M", "daly_total": 3_200_000, "mortality_annual": "330K"},
    "alzheimer": {"prevalence_global": "55M", "incidence_annual": "10M", "daly_total": 11_400_000, "mortality_annual": "1.8M"},
    "dementia": {"prevalence_global": "55M", "incidence_annual": "10M", "daly_total": 11_400_000, "mortality_annual": "1.8M"},
    "diabetes": {"prevalence_global": "537M", "incidence_annual": "50M", "daly_total": 70_000_000, "mortality_annual": "6.7M"},
    "cancer": {"prevalence_global": "50M", "incidence_annual": "20M", "daly_total": 250_000_000, "mortality_annual": "10M"},
    "malaria": {"prevalence_global": "250M", "incidence_annual": "250M", "daly_total": 46_000_000, "mortality_annual": "620K"},
    "tuberculosis": {"prevalence_global": "10M", "incidence_annual": "10M", "daly_total": 35_000_000, "mortality_annual": "1.3M"},
    "hiv": {"prevalence_global": "39M", "incidence_annual": "1.3M", "daly_total": 37_000_000, "mortality_annual": "630K"},
    "asthma": {"prevalence_global": "262M", "incidence_annual": "25M", "daly_total": 22_000_000, "mortality_annual": "455K"},
    "hypertension": {"prevalence_global": "1.3B", "incidence_annual": "100M", "daly_total": 218_000_000, "mortality_annual": "10.8M"},
}


async def _fetch_json(url: str, params: dict | None = None, max_retries: int = 3) -> dict | None:
    """Fetch JSON from WHO GHO API with retry logic."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                logger.debug("WHO GHO %s → %d", url, resp.status_code)
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** attempt
                    logger.warning("WHO GHO HTTP %d, retrying in %ds", resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            wait = 2 ** attempt
            logger.warning("WHO GHO network error: %s, retrying in %ds", exc, wait)
            await asyncio.sleep(wait)
    return None


def _match_disease(disease_name: str) -> str | None:
    """Find the best matching disease key from our indicator map."""
    disease_lower = disease_name.lower()
    for key in _DISEASE_INDICATOR_MAP:
        if key in disease_lower:
            return key
    return None


async def fetch_indicators(keyword: str) -> list[dict]:
    """
    Search WHO GHO for indicator codes matching a keyword.
    GET https://ghoapi.azureedge.net/api/Indicator?$filter=contains(IndicatorName,'{keyword}')
    """
    url = f"{BASE_URL}/Indicator"
    params = {"$filter": f"contains(IndicatorName,'{keyword}')"}
    data = await _fetch_json(url, params)
    if not data:
        return []
    return data.get("value", [])


async def fetch_indicator_data(indicator_code: str, spatial_dim: str = "GLOBAL") -> list[dict]:
    """
    Fetch data for a specific WHO GHO indicator.
    GET https://ghoapi.azureedge.net/api/{indicator_code}
    """
    url = f"{BASE_URL}/{indicator_code}"
    params = {}
    if spatial_dim:
        params["$filter"] = f"SpatialDim eq '{spatial_dim}'"
    data = await _fetch_json(url, params)
    if not data:
        return []
    return data.get("value", [])


async def fetch_disease_burden(disease_name: str) -> dict[str, Any]:
    """
    Fetch disease burden data from WHO GHO API.

    Returns:
        {
            prevalence_global: str,
            incidence_annual: str,
            mortality_annual: str,
            daly_total: int,
            data_source: str,
            indicator_data: list[dict]  # raw indicator values found
        }
    """
    result: dict[str, Any] = {
        "prevalence_global": None,
        "incidence_annual": None,
        "mortality_annual": None,
        "daly_total": 0,
        "data_source": "who_gho",
        "indicator_data": [],
    }

    disease_key = _match_disease(disease_name)
    if not disease_key:
        # Try searching WHO indicators directly
        logger.info("No preset mapping for '%s', searching WHO indicators...", disease_name)
        indicators = await fetch_indicators(disease_name.split()[0])
        if indicators:
            result["indicator_data"] = [
                {"code": ind.get("IndicatorCode"), "name": ind.get("IndicatorName")}
                for ind in indicators[:5]
            ]
            # Try fetching the first indicator's data
            for ind in indicators[:3]:
                code = ind.get("IndicatorCode")
                if code:
                    values = await fetch_indicator_data(code)
                    if values:
                        result["indicator_data"].append({"code": code, "values_count": len(values)})
                    await asyncio.sleep(0.5)  # Rate limit courtesy

        # Use generic fallback
        result["data_source"] = "who_gho_search"
        return result

    # Use our mapped indicators
    mapping = _DISEASE_INDICATOR_MAP[disease_key]
    all_values = []

    for code in mapping["indicator_codes"]:
        await asyncio.sleep(0.5)  # Rate limit courtesy
        values = await fetch_indicator_data(code)
        if values:
            # Get the most recent global value
            sorted_vals = sorted(values, key=lambda v: v.get("TimeDim", 0), reverse=True)
            if sorted_vals:
                latest = sorted_vals[0]
                all_values.append({
                    "code": code,
                    "year": latest.get("TimeDim"),
                    "value": latest.get("NumericValue"),
                    "display": latest.get("Value"),
                })

    result["indicator_data"] = all_values

    # Apply fallback prevalence data (WHO GHO does not always have prevalence directly)
    fallback = _FALLBACK_PREVALENCE.get(disease_key, {})
    if fallback:
        result["prevalence_global"] = fallback.get("prevalence_global")
        result["incidence_annual"] = fallback.get("incidence_annual")
        result["mortality_annual"] = fallback.get("mortality_annual")
        result["daly_total"] = fallback.get("daly_total", 0)
        # If WHO returned numeric data, try to use it
        for val in all_values:
            numeric = val.get("value")
            if numeric and isinstance(numeric, (int, float)):
                if "MORT" in val.get("code", "").upper():
                    result["mortality_annual"] = f"{int(numeric):,}"
                elif "DALY" in val.get("code", "").upper():
                    result["daly_total"] = int(numeric)
        result["data_source"] = "who_gho+reference"
    else:
        result["data_source"] = "who_gho_partial"

    logger.info("WHO GHO: %s → %d indicator values fetched", disease_name, len(all_values))
    return result
