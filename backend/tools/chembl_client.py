"""
tools/chembl_client.py — ChEMBL REST API client.

Used by Agent 4 (CompoundDiscovery) to fetch known actives for a target.

API: https://www.ebi.ac.uk/chembl/api/data/
Rate limit: 5 req/s — asyncio.sleep(0.2) between calls.

IMPORTANT:
  - Always filter standard_type to IC50, Ki, or Kd
  - ChEMBL SMILES are canonical — no need to re-canonicalise
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"


async def _fetch_json(url: str, params: dict[str, Any] | None = None, max_retries: int = 3) -> dict | None:
    """GET with retry and rate-limit sleep."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params, headers={"Accept": "application/json"})
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** attempt
                    logger.warning("chembl_client: HTTP %d, retry %d/%d", resp.status_code, attempt + 1, max_retries)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                await asyncio.sleep(0.2)  # Rate limit: 5 req/s
                return resp.json()
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning("chembl_client: error %s, retry %d/%d", exc, attempt + 1, max_retries)
            await asyncio.sleep(2 ** attempt)
    return None


async def _resolve_target_chembl_id(uniprot_id: str) -> str | None:
    """Map UniProt ID → ChEMBL target_chembl_id via target component search."""
    url = f"{CHEMBL_BASE}/target/search.json"
    data = await _fetch_json(url, params={"q": uniprot_id, "limit": 5})
    if not data:
        return None

    targets = data.get("targets", [])
    for t in targets:
        # Look for the target whose component has this uniprot accession
        components = t.get("target_components", [])
        for comp in components:
            accession = comp.get("accession", "")
            if accession.upper() == uniprot_id.upper():
                return t.get("target_chembl_id")

    # Fallback: return first single-protein target
    for t in targets:
        if t.get("target_type") == "SINGLE PROTEIN":
            return t.get("target_chembl_id")

    return targets[0].get("target_chembl_id") if targets else None


async def fetch_actives(uniprot_id: str, max_results: int = 50) -> list[dict]:
    """
    Fetch binding actives from ChEMBL for a target identified by UniProt ID.

    Returns list of {smiles, chembl_id, standard_value, standard_type}.
    Filters: IC50/Ki/Kd only, standard_value < 1000 nM.
    """
    target_id = await _resolve_target_chembl_id(uniprot_id)
    if not target_id:
        logger.warning("ChEMBL: could not resolve target for UniProt %s", uniprot_id)
        return []

    logger.info("ChEMBL: resolved %s → %s", uniprot_id, target_id)

    # Fetch activities
    url = f"{CHEMBL_BASE}/activity.json"
    params = {
        "target_chembl_id": target_id,
        "standard_type__in": "IC50,Ki,Kd",
        "standard_value__lte": 1000,
        "standard_units": "nM",
        "limit": max_results,
    }

    data = await _fetch_json(url, params=params)
    if not data:
        return []

    results = []
    seen_smiles = set()
    for act in data.get("activities", []):
        smiles = act.get("canonical_smiles")
        if not smiles or smiles in seen_smiles:
            continue
        seen_smiles.add(smiles)

        results.append({
            "smiles": smiles,
            "chembl_id": act.get("molecule_chembl_id", ""),
            "standard_value": act.get("standard_value"),
            "standard_type": act.get("standard_type", ""),
        })

    logger.info("ChEMBL: fetched %d unique actives for %s", len(results), target_id)
    return results
