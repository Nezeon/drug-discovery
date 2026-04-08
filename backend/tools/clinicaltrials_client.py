"""
tools/clinicaltrials_client.py — ClinicalTrials.gov API v2 client.

Used by Agent 7 (CompetitiveScout) to count and categorize active trials for a disease.

API: https://clinicaltrials.gov/api/v2/studies
Documentation: https://clinicaltrials.gov/data-api/api

Query params:
  query.cond={disease}
  filter.overallStatus=RECRUITING,ACTIVE_NOT_RECRUITING
  countTotal=true
  pageSize=50
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


async def _fetch_json(url: str, params: dict, max_retries: int = 3) -> dict | None:
    """Fetch JSON from ClinicalTrials.gov with retry logic."""
    headers = {
        "User-Agent": "MolForgeAI/1.0 (Drug Discovery Platform)",
        "Accept": "application/json",
    }
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                resp = await client.get(url, params=params)
                logger.debug("ClinicalTrials.gov %s → %d", resp.url, resp.status_code)
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** attempt
                    logger.warning("ClinicalTrials.gov HTTP %d, retrying in %ds", resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            wait = 2 ** attempt
            logger.warning("ClinicalTrials.gov network error: %s, retrying in %ds", exc, wait)
            await asyncio.sleep(wait)
    return None


async def fetch_trials(disease_name: str, target_name: str | None = None) -> dict[str, Any]:
    """
    Fetch clinical trial data for a disease (and optionally a specific target).

    Returns:
        {
            total_trials: int,
            by_phase: {Phase1: int, Phase2: int, Phase3: int, Phase4: int},
            active_trials: int,
            completed_trials: int,
            recruiting_trials: int,
            top_sponsors: list[str],
            target_trials: int | None  (if target_name provided)
        }
    """
    result: dict[str, Any] = {
        "total_trials": 0,
        "by_phase": {"Phase1": 0, "Phase2": 0, "Phase3": 0, "Phase4": 0},
        "active_trials": 0,
        "completed_trials": 0,
        "recruiting_trials": 0,
        "top_sponsors": [],
        "target_trials": None,
    }

    # --- Query 1: All interventional drug trials for the disease ---
    params = {
        "query.cond": disease_name,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED,ENROLLING_BY_INVITATION",
        "filter.studyType": "INTERVENTIONAL",
        "countTotal": "true",
        "pageSize": "50",
        "fields": "NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName,InterventionType",
    }

    data = await _fetch_json(BASE_URL, params)
    if not data:
        logger.warning("ClinicalTrials.gov: no data for '%s'", disease_name)
        return result

    total = data.get("totalCount", 0)
    result["total_trials"] = total
    studies = data.get("studies", [])

    # Parse studies for phase breakdown and sponsors
    sponsor_counts: dict[str, int] = {}

    for study in studies:
        protocol = study.get("protocolSection", {})
        status_module = protocol.get("statusModule", {})
        design_module = protocol.get("designModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        interventions = protocol.get("armsInterventionsModule", {})

        # Only count drug interventions
        has_drug = False
        intervention_list = interventions.get("interventions", [])
        for interv in intervention_list:
            if interv.get("type", "").upper() in ("DRUG", "BIOLOGICAL"):
                has_drug = True
                break
        if not has_drug and intervention_list:
            continue

        # Count by status
        status = status_module.get("overallStatus", "")
        if status in ("RECRUITING", "ENROLLING_BY_INVITATION"):
            result["recruiting_trials"] += 1
            result["active_trials"] += 1
        elif status == "ACTIVE_NOT_RECRUITING":
            result["active_trials"] += 1
        elif status == "COMPLETED":
            result["completed_trials"] += 1

        # Count by phase
        phases = design_module.get("phases", [])
        for phase in phases:
            if "PHASE1" in phase.upper():
                result["by_phase"]["Phase1"] += 1
            elif "PHASE2" in phase.upper():
                result["by_phase"]["Phase2"] += 1
            elif "PHASE3" in phase.upper():
                result["by_phase"]["Phase3"] += 1
            elif "PHASE4" in phase.upper():
                result["by_phase"]["Phase4"] += 1

        # Count sponsors
        lead = sponsor_module.get("leadSponsor", {}).get("name", "")
        if lead:
            sponsor_counts[lead] = sponsor_counts.get(lead, 0) + 1

    # Top sponsors
    sorted_sponsors = sorted(sponsor_counts.items(), key=lambda x: x[1], reverse=True)
    result["top_sponsors"] = [s[0] for s in sorted_sponsors[:10]]

    # --- Query 2: Target-specific trials (if target provided) ---
    if target_name:
        await asyncio.sleep(0.5)  # Rate limit courtesy
        target_params = {
            "query.cond": disease_name,
            "query.intr": target_name,
            "filter.studyType": "INTERVENTIONAL",
            "countTotal": "true",
            "pageSize": "1",
        }
        target_data = await _fetch_json(BASE_URL, target_params)
        if target_data:
            result["target_trials"] = target_data.get("totalCount", 0)

    logger.info(
        "ClinicalTrials.gov: %s → %d total trials, %d active, %d completed",
        disease_name, total, result["active_trials"], result["completed_trials"],
    )
    return result
