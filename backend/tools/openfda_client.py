"""
tools/openfda_client.py — OpenFDA API client.

Used by Agent 7 (CompetitiveScout) to find approved drugs for a disease indication.

API: https://api.fda.gov/drug/label.json
Search: indications_and_usage:{disease_name}
Deduplicate by generic_name, max 20 results.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.fda.gov/drug/label.json"


async def _fetch_json(url: str, params: dict, max_retries: int = 3) -> dict | None:
    """Fetch JSON from OpenFDA API with retry logic."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                logger.debug("OpenFDA %s → %d", resp.url, resp.status_code)
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** attempt
                    logger.warning("OpenFDA HTTP %d, retrying in %ds", resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code == 404:
                    # No results found — not an error
                    return {"results": [], "meta": {"results": {"total": 0}}}
                resp.raise_for_status()
                return resp.json()
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            wait = 2 ** attempt
            logger.warning("OpenFDA network error: %s, retrying in %ds", exc, wait)
            await asyncio.sleep(wait)
    return None


async def fetch_approved_drugs(disease_name: str) -> list[dict[str, Any]]:
    """
    Fetch approved drugs from OpenFDA for a given disease indication.

    Returns list of:
        {
            drug_name: str,
            generic_name: str,
            approval_date: str | None,
            mechanism_hint: str | None
        }

    Deduplicated by generic_name, max 20 results.
    """
    # Clean disease name for OpenFDA search syntax
    # Remove special characters that break OpenFDA search
    clean_name = disease_name.replace("'", "").replace('"', "").replace("(", "").replace(")", "")

    params = {
        "search": f'indications_and_usage:"{clean_name}"',
        "limit": "50",
    }

    data = await _fetch_json(BASE_URL, params)
    if not data:
        logger.warning("OpenFDA: no response for '%s'", disease_name)
        return []

    results = data.get("results", [])
    total = data.get("meta", {}).get("results", {}).get("total", 0)
    logger.info("OpenFDA: %s → %d total labels, %d returned", disease_name, total, len(results))

    # Extract drug info and deduplicate
    seen_generics: set[str] = set()
    drugs: list[dict[str, Any]] = []

    for label in results:
        openfda = label.get("openfda", {})

        # Get generic name
        generic_names = openfda.get("generic_name", [])
        generic = generic_names[0].lower() if generic_names else ""
        if not generic:
            # Try substance_name as fallback
            substance = openfda.get("substance_name", [])
            generic = substance[0].lower() if substance else ""
        if not generic:
            continue

        # Deduplicate
        if generic in seen_generics:
            continue
        seen_generics.add(generic)

        # Get brand name
        brand_names = openfda.get("brand_name", [])
        brand = brand_names[0] if brand_names else generic.title()

        # Get mechanism hint from pharmacodynamics or mechanism_of_action
        mechanism = None
        moa_text = label.get("mechanism_of_action", [])
        if moa_text:
            # Take first 150 chars as hint
            mechanism = moa_text[0][:150] if moa_text[0] else None

        # Approval date from product_type or effective_time
        approval_date = label.get("effective_time", None)

        drugs.append({
            "drug_name": brand,
            "generic_name": generic,
            "approval_date": approval_date,
            "mechanism_hint": mechanism,
        })

        if len(drugs) >= 20:
            break

    logger.info("OpenFDA: %d unique approved drugs found for '%s'", len(drugs), disease_name)
    return drugs
