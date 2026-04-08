"""
tools/alphafold_client.py — AlphaFold DB API client.

Used by Agent 3 (StructureResolver) to fetch predicted protein structures.

API: https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}
Returns a list — always take [0] for the primary prediction.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def _fetch_with_retry(
    url: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    max_retries: int = 3,
    timeout: float = 30.0,
) -> dict | list | None:
    """HTTP GET/POST with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "POST":
                    resp = await client.post(url, params=params, json=json_body)
                else:
                    resp = await client.get(url, params=params)

                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** attempt
                    logger.warning("alphafold_client: HTTP %d, retry %d/%d in %ds", resp.status_code, attempt + 1, max_retries, wait)
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            wait = 2 ** attempt
            logger.warning("alphafold_client: network error %s, retry %d/%d in %ds", exc, attempt + 1, max_retries, wait)
            await asyncio.sleep(wait)

    logger.error("alphafold_client: all %d retries exhausted for %s", max_retries, url)
    return None


async def fetch_structure(uniprot_id: str) -> dict | None:
    """
    Fetch AlphaFold predicted structure metadata for a UniProt ID.

    Returns dict with keys: pdb_url, cif_url, plddt_avg, uniprot_id, source
    or None if the entry is not found / API fails.
    """
    url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
    data = await _fetch_with_retry(url)

    if not data:
        logger.warning("AlphaFold: no response for %s", uniprot_id)
        return None

    # API returns a list — take [0]
    if isinstance(data, list):
        if len(data) == 0:
            logger.warning("AlphaFold: empty list for %s", uniprot_id)
            return None
        entry = data[0]
    else:
        entry = data

    pdb_url = entry.get("pdbUrl")
    cif_url = entry.get("cifUrl")

    if not pdb_url:
        logger.warning("AlphaFold: no pdbUrl for %s", uniprot_id)
        return None

    # Global confidence metric (pLDDT average)
    plddt_avg = entry.get("globalMetricValue")
    if plddt_avg is None:
        plddt_avg = entry.get("confidenceAvgLocalScore")

    return {
        "pdb_url": pdb_url,
        "cif_url": cif_url,
        "plddt_avg": plddt_avg,
        "uniprot_id": uniprot_id,
        "source": "alphafold_db",
        "model_version": entry.get("latestVersion", "unknown"),
    }


async def download_pdb(pdb_url: str) -> str | None:
    """Download PDB file content as string from a given URL."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(pdb_url)
            resp.raise_for_status()
            return resp.text
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.error("AlphaFold PDB download failed: %s", exc)
        return None
