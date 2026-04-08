"""
tools/string_client.py — STRING protein interaction database client.

Fetches protein-protein interaction data for Agent 2 (TargetValidator).
STRING provides functional protein associations with confidence scores.

API: https://string-db.org/api/
No authentication required.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

STRING_NETWORK_URL = "https://string-db.org/api/json/network"


async def fetch_interaction_score(
    gene_symbol: str,
    max_retries: int = 3,
) -> dict:
    """
    Fetch protein interaction data from STRING-DB.

    GET /api/json/network?identifiers={gene_symbol}&species=9606

    Returns {
        interaction_count: int,
        avg_score: float,
        is_hub_protein: bool  (True if interaction_count > 20)
    }
    """
    params = {
        "identifiers": gene_symbol,
        "species": "9606",  # Homo sapiens
        "limit": "50",
        "required_score": "400",  # Medium confidence (0-1000 scale)
    }

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(STRING_NETWORK_URL, params=params)
                if resp.status_code == 404:
                    return {"interaction_count": 0, "avg_score": 0.0, "is_hub_protein": False}
                resp.raise_for_status()
                data = resp.json()
                return _parse_network(data)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.error("STRING-DB query failed for %s: %s", gene_symbol, exc)
                return {"interaction_count": 0, "avg_score": 0.0, "is_hub_protein": False}
            await asyncio.sleep(2 ** attempt)
    return {"interaction_count": 0, "avg_score": 0.0, "is_hub_protein": False}


def _parse_network(data: list) -> dict:
    """Parse STRING network JSON into interaction summary."""
    if not data:
        return {"interaction_count": 0, "avg_score": 0.0, "is_hub_protein": False}

    # Each entry is an edge (interaction between two proteins)
    # Count unique interaction partners
    partners = set()
    scores = []
    for edge in data:
        partners.add(edge.get("preferredName_A", ""))
        partners.add(edge.get("preferredName_B", ""))
        score = edge.get("score", 0)
        scores.append(float(score))

    # Subtract 1 for the query protein itself
    interaction_count = max(0, len(partners) - 1)
    avg_score = sum(scores) / len(scores) if scores else 0.0

    return {
        "interaction_count": interaction_count,
        "avg_score": round(avg_score, 3),
        "is_hub_protein": interaction_count > 20,
    }
