"""
tools/disgenet_client.py — DisGeNET REST API client.

Fetches gene-disease associations for Agent 1 (DiseaseAnalyst).
DisGeNET provides scored associations between genes and diseases.

API: https://www.disgenet.org/api/
Note: DisGeNET requires a free API key for full access. If the API is
unavailable or rate-limited, we fall back to OpenTargets for gene-disease
associations.

Fallback strategy: If DisGeNET returns 401/403/429 or times out, we use
OpenTargets Platform API to get disease-associated targets instead.
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

DISGENET_BASE = "https://www.disgenet.org/api"
OPENTARGETS_GQL = "https://api.platform.opentargets.org/api/v4/graphql"

# DisGeNET API key (optional — free tier available at disgenet.org)
DISGENET_API_KEY = os.getenv("DISGENET_API_KEY", "")


async def fetch_gene_associations(
    disease_name: str,
    max_results: int = 20,
    max_retries: int = 3,
) -> list[dict]:
    """
    Fetch gene-disease associations for a disease.

    Tries DisGeNET first; falls back to OpenTargets if unavailable.
    Returns list of {gene_symbol, gene_name, score, pmids_count}, sorted by score desc.
    """
    # Try DisGeNET first
    results = await _fetch_disgenet(disease_name, max_results, max_retries)
    if results:
        return results

    # Fallback: OpenTargets
    logger.info("DisGeNET unavailable, falling back to OpenTargets for gene associations")
    return await _fetch_opentargets_fallback(disease_name, max_results, max_retries)


async def _fetch_disgenet(
    disease_name: str, max_results: int, max_retries: int
) -> list[dict]:
    """Try to fetch from DisGeNET REST API."""
    if not DISGENET_API_KEY:
        logger.info("No DISGENET_API_KEY set, skipping DisGeNET")
        return []

    headers = {"Authorization": f"Bearer {DISGENET_API_KEY}"}

    # Step 1: Map disease name to UMLS CUI
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{DISGENET_BASE}/disease/search",
                    params={"query": disease_name, "limit": 1},
                    headers=headers,
                )
                if resp.status_code in (401, 403):
                    logger.warning("DisGeNET auth failed (HTTP %d)", resp.status_code)
                    return []
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                diseases = resp.json()
                if not diseases:
                    return []
                disease_id = diseases[0].get("diseaseId", "")
                break
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.warning("DisGeNET disease search failed: %s", exc)
                return []
            await asyncio.sleep(2 ** attempt)
    else:
        return []

    if not disease_id:
        return []

    # Step 2: Fetch gene-disease associations
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{DISGENET_BASE}/gda/disease/{disease_id}",
                    params={"limit": max_results},
                    headers=headers,
                )
                if resp.status_code in (401, 403, 429):
                    return []
                resp.raise_for_status()
                data = resp.json()
                return _parse_disgenet_results(data)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.warning("DisGeNET GDA fetch failed: %s", exc)
                return []
            await asyncio.sleep(2 ** attempt)
    return []


def _parse_disgenet_results(data: list | dict) -> list[dict]:
    """Parse DisGeNET gene-disease association response."""
    if isinstance(data, dict):
        data = data.get("results", data.get("payload", []))
    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        results.append({
            "gene_symbol": item.get("gene_symbol", item.get("geneSymbol", "")),
            "gene_name": item.get("gene_name", item.get("geneName", "")),
            "score": float(item.get("score", item.get("ei", 0))),
            "pmids_count": int(item.get("pmid_count", item.get("nOfPmids", 0))),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:20]


async def _fetch_opentargets_fallback(
    disease_name: str, max_results: int, max_retries: int
) -> list[dict]:
    """
    Fallback: use OpenTargets to get disease-associated targets.

    Step 1: Search for disease EFO ID
    Step 2: Query associated targets
    """
    # Step 1: Search disease
    efo_id = await _search_opentargets_disease(disease_name, max_retries)
    if not efo_id:
        logger.warning("OpenTargets fallback: could not find EFO ID for '%s'", disease_name)
        return []

    # Step 2: Query associated targets
    query = """
    query AssociatedTargets($efoId: String!, $size: Int!) {
      disease(efoId: $efoId) {
        associatedTargets(page: {size: $size, index: 0}) {
          rows {
            target {
              approvedSymbol
              approvedName
            }
            score
            datasourceScores {
              componentId: id
              score
            }
          }
        }
      }
    }
    """
    variables = {"efoId": efo_id, "size": max_results}

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    OPENTARGETS_GQL,
                    json={"query": query, "variables": variables},
                )
                resp.raise_for_status()
                data = resp.json()

                rows = (
                    data.get("data", {})
                    .get("disease", {})
                    .get("associatedTargets", {})
                    .get("rows", [])
                )

                results = []
                for row in rows:
                    target = row.get("target", {})
                    # Count literature evidence as proxy for pmids_count
                    lit_score = 0
                    for ds in row.get("datasourceScores", []):
                        if "literature" in ds.get("componentId", "").lower():
                            lit_score = ds.get("score", 0)
                            break

                    results.append({
                        "gene_symbol": target.get("approvedSymbol", ""),
                        "gene_name": target.get("approvedName", ""),
                        "score": float(row.get("score", 0)),
                        "pmids_count": int(lit_score * 100),  # Approximate
                    })

                results.sort(key=lambda x: x["score"], reverse=True)
                return results

        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.error("OpenTargets fallback failed: %s", exc)
                return []
            await asyncio.sleep(2 ** attempt)
    return []


async def _search_opentargets_disease(disease_name: str, max_retries: int) -> str:
    """Search OpenTargets for a disease EFO ID."""
    query = """
    query SearchDisease($queryString: String!) {
      search(queryString: $queryString, entityNames: ["disease"], page: {size: 1, index: 0}) {
        hits {
          id
          name
        }
      }
    }
    """
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    OPENTARGETS_GQL,
                    json={"query": query, "variables": {"queryString": disease_name}},
                )
                resp.raise_for_status()
                data = resp.json()
                hits = data.get("data", {}).get("search", {}).get("hits", [])
                if hits:
                    return hits[0].get("id", "")
                return ""
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.warning("OpenTargets disease search failed: %s", exc)
                return ""
            await asyncio.sleep(2 ** attempt)
    return ""
