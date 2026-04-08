"""
tools/pdb_client.py — RCSB PDB REST API client.

Fallback structure source for Agent 3 (StructureResolver) when AlphaFold
pLDDT is too low or entry is missing.

Search: https://search.rcsb.org/rcsbsearch/v2/query (POST, JSON query DSL)
Download: https://files.rcsb.org/download/{pdb_id}.pdb
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
                    logger.warning("pdb_client: HTTP %d, retry %d/%d in %ds", resp.status_code, attempt + 1, max_retries, wait)
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            wait = 2 ** attempt
            logger.warning("pdb_client: network error %s, retry %d/%d in %ds", exc, attempt + 1, max_retries, wait)
            await asyncio.sleep(wait)

    logger.error("pdb_client: all %d retries exhausted for %s", max_retries, url)
    return None


async def search_by_uniprot(uniprot_id: str) -> list[dict]:
    """
    Search RCSB PDB for experimental structures mapped to a UniProt ID.
    Returns list of {pdb_id, score} sorted by resolution (best first).
    """
    url = "https://search.rcsb.org/rcsbsearch/v2/query"
    query = {
        "query": {
            "type": "group",
            "logical_operator": "and",
            "nodes": [
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                        "operator": "exact_match",
                        "value": uniprot_id,
                    },
                },
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_name",
                        "operator": "exact_match",
                        "value": "UniProt",
                    },
                },
            ],
        },
        "return_type": "entry",
        "request_options": {
            "sort": [
                {
                    "sort_by": "rcsb_entry_info.resolution_combined",
                    "direction": "asc",
                }
            ],
            "results_content_type": ["experimental"],
            "paginate": {"start": 0, "rows": 10},
        },
    }

    data = await _fetch_with_retry(url, method="POST", json_body=query)
    if not data:
        return []

    results = []
    for hit in data.get("result_set", []):
        pdb_id = hit.get("identifier", "")
        score = hit.get("score", 0)
        results.append({"pdb_id": pdb_id, "score": score})

    return results


async def fetch_structure(uniprot_id: str) -> dict | None:
    """
    Search PDB for structures matching uniprot_id.
    Returns best structure (highest resolution, < 2.5A) or None.
    """
    hits = await search_by_uniprot(uniprot_id)
    if not hits:
        logger.info("PDB: no structures found for UniProt %s", uniprot_id)
        return None

    best = hits[0]
    pdb_id = best["pdb_id"]

    # Fetch entry metadata to get resolution
    meta_url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
    meta = await _fetch_with_retry(meta_url)

    resolution = None
    if meta:
        res_val = meta.get("rcsb_entry_info", {}).get("resolution_combined")
        if isinstance(res_val, list) and res_val:
            resolution = res_val[0]
        elif isinstance(res_val, (int, float)):
            resolution = res_val

    if resolution is not None and resolution > 2.5:
        logger.info("PDB: best structure %s has resolution %.2fA (> 2.5A), skipping", pdb_id, resolution)
        return None

    return {
        "pdb_id": pdb_id,
        "resolution": resolution,
        "source": "rcsb_pdb",
        "uniprot_id": uniprot_id,
    }


async def download_pdb(pdb_id: str) -> str | None:
    """Download PDB file content as string."""
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.error("PDB download failed for %s: %s", pdb_id, exc)
        return None
