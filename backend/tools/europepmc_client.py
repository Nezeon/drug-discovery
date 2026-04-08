"""
tools/europepmc_client.py — Europe PMC REST API client.

Supplementary literature source for Agent 1 (DiseaseAnalyst).
Europe PMC has better coverage of preprints and EU-funded research.

API: https://www.ebi.ac.uk/europepmc/webservices/rest/
Key endpoint: /search?query=...&format=json&pageSize=25&resultType=core
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

EUROPEPMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


async def fetch_abstracts(
    disease_name: str,
    max_results: int = 20,
    max_retries: int = 3,
) -> list[dict]:
    """
    Fetch recent abstracts from Europe PMC for a disease query.

    Params: query={disease_name}, format=json, pageSize, sort=date
    Returns list of {pmid, title, abstract, pub_date}.
    """
    params = {
        "query": f"{disease_name} AND (protein target OR drug target OR therapeutic target)",
        "format": "json",
        "pageSize": str(max_results),
        "resultType": "core",
        "sort": "date",
    }

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(EUROPEPMC_SEARCH_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return _parse_results(data)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.error("Europe PMC search failed after %d retries: %s", max_retries, exc)
                return []
            wait = 2 ** attempt
            logger.warning("Europe PMC attempt %d failed: %s, retrying in %ds", attempt + 1, exc, wait)
            await asyncio.sleep(wait)
    return []


def _parse_results(data: dict) -> list[dict]:
    """Parse Europe PMC JSON search results into abstract dicts."""
    results = []
    result_list = data.get("resultList", {}).get("result", [])

    for item in result_list:
        abstract = item.get("abstractText", "")
        if not abstract:
            continue  # Skip entries without abstracts

        pmid = item.get("pmid", item.get("id", ""))
        title = item.get("title", "")
        pub_date = item.get("firstPublicationDate", item.get("pubYear", ""))
        authors = item.get("authorString", "")

        results.append({
            "pmid": str(pmid),
            "title": title,
            "abstract": abstract,
            "pub_date": pub_date,
            "authors": authors,
        })

    return results
