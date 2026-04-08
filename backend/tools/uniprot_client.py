"""
tools/uniprot_client.py — UniProt REST API client.

Used by Agent 2 (TargetValidator) to fetch protein metadata:
  - UniProt accession ID
  - Protein name and function
  - Known binding/active site annotations
  - Cross-references to PDB structures
  - Subcellular location

API: https://rest.uniprot.org/uniprotkb/search
No authentication required.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"


async def fetch_protein_info(
    gene_symbol: str,
    max_retries: int = 3,
) -> dict:
    """
    Fetch protein information from UniProt for a human gene symbol.

    Query: gene:{gene_symbol} AND organism_id:9606 (Homo sapiens)

    Returns {
        uniprot_id, protein_name, function_description,
        has_binding_site, known_inhibitor_count, pdb_structures_count,
        subcellular_location
    }
    """
    params = {
        "query": f"gene:{gene_symbol} AND organism_id:9606 AND reviewed:true",
        "format": "json",
        "size": "1",
        "fields": "accession,protein_name,gene_names,cc_function,ft_binding,ft_act_site,xref_pdb,cc_subcellular_location,cc_interaction",
    }

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(UNIPROT_SEARCH, params=params)
                resp.raise_for_status()
                data = resp.json()
                return _parse_uniprot_result(data, gene_symbol)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.error("UniProt search failed for %s: %s", gene_symbol, exc)
                return {}
            await asyncio.sleep(2 ** attempt)
    return {}


def _parse_uniprot_result(data: dict, gene_symbol: str) -> dict:
    """Parse UniProt JSON response into a structured dict."""
    results = data.get("results", [])
    if not results:
        logger.warning("UniProt: no results for gene %s", gene_symbol)
        return {}

    entry = results[0]

    # UniProt accession
    uniprot_id = entry.get("primaryAccession", "")

    # Protein name
    protein_name = ""
    prot_desc = entry.get("proteinDescription", {})
    rec_name = prot_desc.get("recommendedName", {})
    if rec_name:
        full_name = rec_name.get("fullName", {})
        protein_name = full_name.get("value", "") if isinstance(full_name, dict) else str(full_name)
    if not protein_name:
        sub_names = prot_desc.get("submittedName", [])
        if sub_names:
            protein_name = sub_names[0].get("fullName", {}).get("value", "")

    # Function description
    function_desc = ""
    comments = entry.get("comments", [])
    for comment in comments:
        if comment.get("commentType") == "FUNCTION":
            texts = comment.get("texts", [])
            if texts:
                function_desc = texts[0].get("value", "")
                break

    # Binding sites and active sites from features
    features = entry.get("features", [])
    binding_count = sum(1 for f in features if f.get("type") in ("Binding site", "Active site"))
    has_binding_site = binding_count > 0

    # PDB cross-references
    xrefs = entry.get("uniProtKBCrossReferences", [])
    pdb_refs = [x for x in xrefs if x.get("database") == "PDB"]
    pdb_count = len(pdb_refs)

    # Subcellular location
    subcellular = ""
    for comment in comments:
        if comment.get("commentType") == "SUBCELLULAR LOCATION":
            locations = comment.get("subcellularLocations", [])
            if locations:
                loc = locations[0].get("location", {})
                subcellular = loc.get("value", "") if isinstance(loc, dict) else str(loc)
                break

    return {
        "uniprot_id": uniprot_id,
        "protein_name": protein_name,
        "function_description": function_desc[:500] if function_desc else "",
        "has_binding_site": has_binding_site,
        "binding_site_count": binding_count,
        "pdb_structures_count": pdb_count,
        "subcellular_location": subcellular,
    }
