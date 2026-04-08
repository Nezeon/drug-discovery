"""
tools/pubchem_client.py — PubChem REST API client.

Used by Agent 4 (CompoundDiscovery) for novelty cross-referencing.

API: https://pubchem.ncbi.nlm.nih.gov/rest/pug/
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


async def _fetch_json(url: str, params: dict[str, Any] | None = None, max_retries: int = 3) -> dict | None:
    """GET with retry."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
        except (httpx.RequestError, httpx.TimeoutException):
            await asyncio.sleep(2 ** attempt)
    return None


async def fetch_smiles(chembl_id: str) -> str | None:
    """
    Look up a compound in PubChem by name (ChEMBL ID) and return canonical SMILES.
    Returns None if not found.
    """
    url = f"{PUBCHEM_BASE}/compound/name/{chembl_id}/property/CanonicalSMILES/JSON"
    data = await _fetch_json(url)
    if not data:
        return None

    props = data.get("PropertyTable", {}).get("Properties", [])
    if props:
        return props[0].get("CanonicalSMILES")
    return None


async def similarity_search(smiles: str, threshold: int = 85, max_results: int = 5) -> list[str]:
    """
    Run 2D similarity search in PubChem.
    Returns list of SMILES for similar compounds found.
    """
    # URL-encode the SMILES
    import urllib.parse
    encoded = urllib.parse.quote(smiles, safe="")
    url = f"{PUBCHEM_BASE}/compound/fastsimilarity_2d/smiles/{encoded}/property/CanonicalSMILES/JSON"
    params = {"Threshold": threshold, "MaxRecords": max_results}

    data = await _fetch_json(url, params=params)
    if not data:
        return []

    props = data.get("PropertyTable", {}).get("Properties", [])
    return [p["CanonicalSMILES"] for p in props if p.get("CanonicalSMILES")]
