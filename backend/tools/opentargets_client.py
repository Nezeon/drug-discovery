"""
tools/opentargets_client.py — OpenTargets GraphQL API client.

Used by Agent 2 (TargetValidator) to get quantitative disease-target association scores.

API: https://api.platform.opentargets.org/api/v4/graphql
Uses GraphQL POST requests — no API key required.

Also uses Ensembl REST to map gene symbols to Ensembl IDs.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

OPENTARGETS_GQL = "https://api.platform.opentargets.org/api/v4/graphql"
ENSEMBL_XREFS = "https://rest.ensembl.org/xrefs/symbol/homo_sapiens"


async def fetch_associations(
    disease_name: str,
    gene_symbol: str,
    max_retries: int = 3,
) -> dict:
    """
    Fetch OpenTargets association between a gene and a disease.

    Steps:
      1. Map gene_symbol → Ensembl gene ID via Ensembl REST
      2. Map disease_name → EFO ID via OpenTargets search
      3. Query OpenTargets for association score

    Returns {association_score, genetic_evidence, clinical_evidence, literature_evidence}
    or empty dict on failure.
    """
    # Step 1: Map gene symbol → Ensembl ID
    ensembl_id = await _get_ensembl_id(gene_symbol, max_retries)
    if not ensembl_id:
        logger.warning("Could not resolve Ensembl ID for %s", gene_symbol)
        return {}

    # Step 2: Map disease name → EFO ID
    efo_id = await _search_disease_efo(disease_name, max_retries)
    if not efo_id:
        logger.warning("Could not resolve EFO ID for '%s'", disease_name)
        return {}

    # Step 3: Query association
    return await _query_association(ensembl_id, efo_id, max_retries)


async def fetch_target_info(gene_symbol: str, max_retries: int = 3) -> dict:
    """
    Fetch target-level info from OpenTargets (druggability, tractability, safety).

    Returns {tractability_smallmolecule, tractability_antibody, safety_liabilities}.
    """
    ensembl_id = await _get_ensembl_id(gene_symbol, max_retries)
    if not ensembl_id:
        return {}

    query = """
    query TargetInfo($ensemblId: String!) {
      target(ensemblId: $ensemblId) {
        approvedSymbol
        approvedName
        tractability {
          label
          modality
          value
        }
        safetyLiabilities {
          event
          effects {
            direction
            dosing
          }
        }
      }
    }
    """
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    OPENTARGETS_GQL,
                    json={"query": query, "variables": {"ensemblId": ensembl_id}},
                )
                resp.raise_for_status()
                data = resp.json()

                target = data.get("data", {}).get("target", {})
                if not target:
                    return {}

                # Parse tractability
                tractability = target.get("tractability", []) or []
                sm_tractable = any(
                    t.get("modality") == "SM" and t.get("value", False)
                    for t in tractability
                )
                ab_tractable = any(
                    t.get("modality") == "AB" and t.get("value", False)
                    for t in tractability
                )

                safety = target.get("safetyLiabilities", []) or []

                return {
                    "tractability_smallmolecule": sm_tractable,
                    "tractability_antibody": ab_tractable,
                    "safety_liability_count": len(safety),
                }
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.error("OpenTargets target info failed: %s", exc)
                return {}
            await asyncio.sleep(2 ** attempt)
    return {}


async def _get_ensembl_id(gene_symbol: str, max_retries: int) -> str:
    """Map gene symbol to Ensembl gene ID via Ensembl REST xrefs."""
    url = f"{ENSEMBL_XREFS}/{gene_symbol}"
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    return ""
                resp.raise_for_status()
                data = resp.json()
                # Find the Ensembl gene ID
                for entry in data:
                    eid = entry.get("id", "")
                    if eid.startswith("ENSG"):
                        return eid
                return ""
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.warning("Ensembl xrefs failed for %s: %s", gene_symbol, exc)
                return ""
            await asyncio.sleep(2 ** attempt)
    return ""


async def _search_disease_efo(disease_name: str, max_retries: int) -> str:
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
            async with httpx.AsyncClient(timeout=20.0) as client:
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


async def _query_association(
    ensembl_id: str, efo_id: str, max_retries: int
) -> dict:
    """Query OpenTargets for target-disease association score."""
    query = """
    query Association($efoId: String!) {
      disease(efoId: $efoId) {
        associatedTargets(
          page: {size: 500, index: 0}
        ) {
          rows {
            target {
              id
              approvedSymbol
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
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    OPENTARGETS_GQL,
                    json={
                        "query": query,
                        "variables": {"efoId": efo_id},
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                rows = (
                    data.get("data", {})
                    .get("disease", {})
                    .get("associatedTargets", {})
                    .get("rows", [])
                )

                # Find our target in the results
                for row in rows:
                    target_id = row.get("target", {}).get("id", "")
                    if target_id == ensembl_id:
                        ds_scores = row.get("datasourceScores", [])
                        genetic = 0.0
                        clinical = 0.0
                        literature = 0.0
                        for ds in ds_scores:
                            cid = ds.get("componentId", "").lower()
                            s = ds.get("score", 0)
                            if "genetic" in cid or "gwas" in cid or "eva" in cid:
                                genetic = max(genetic, s)
                            elif "clinical" in cid or "chembl" in cid:
                                clinical = max(clinical, s)
                            elif "literature" in cid or "europepmc" in cid:
                                literature = max(literature, s)

                        return {
                            "association_score": float(row.get("score", 0)),
                            "genetic_evidence": genetic,
                            "clinical_evidence": clinical,
                            "literature_evidence": literature,
                        }

                # Target not found in top 500 — likely low association
                return {"association_score": 0.0, "genetic_evidence": 0.0,
                        "clinical_evidence": 0.0, "literature_evidence": 0.0}

        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.error("OpenTargets association query failed: %s", exc)
                return {}
            await asyncio.sleep(2 ** attempt)
    return {}
