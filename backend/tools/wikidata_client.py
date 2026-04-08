"""
tools/wikidata_client.py — Wikidata SPARQL client for epidemiology data.

Used by Agent 6 (MarketAnalyst) as a supplement/fallback for WHO GHO data.
Queries Wikidata SPARQL endpoint for disease prevalence and affected populations.

API: https://query.wikidata.org/sparql
Uses SPARQLWrapper Python library.
"""

from __future__ import annotations

import logging
from typing import Any

from SPARQLWrapper import SPARQLWrapper, JSON

logger = logging.getLogger(__name__)

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL query to find a disease entity and its epidemiological properties
_DISEASE_QUERY = """
SELECT ?disease ?diseaseLabel ?prevalence ?incidence ?deaths WHERE {{
  ?disease wdt:P31/wdt:P279* wd:Q112193867 .
  ?disease rdfs:label ?label .
  FILTER(LANG(?label) = "en")
  FILTER(CONTAINS(LCASE(?label), LCASE("{disease_name}")))
  OPTIONAL {{ ?disease wdt:P1193 ?prevalence . }}
  OPTIONAL {{ ?disease wdt:P3457 ?incidence . }}
  OPTIONAL {{ ?disease wdt:P1120 ?deaths . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT 5
"""

# Simpler fallback query: search by label match
_SIMPLE_QUERY = """
SELECT ?disease ?diseaseLabel WHERE {{
  ?disease wdt:P31 wd:Q12136 .
  ?disease rdfs:label ?label .
  FILTER(LANG(?label) = "en")
  FILTER(CONTAINS(LCASE(?label), LCASE("{disease_name}")))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT 5
"""


def _run_sparql(query: str) -> list[dict] | None:
    """Execute a SPARQL query against Wikidata and return results."""
    try:
        sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        sparql.addCustomHttpHeader("User-Agent", "MolForgeAI/1.0 (Drug Discovery Platform)")
        results = sparql.query().convert()
        bindings = results.get("results", {}).get("bindings", [])
        return bindings
    except Exception as exc:
        logger.error("Wikidata SPARQL query failed: %s", exc)
        return None


def fetch_epidemiology(disease_name: str) -> dict[str, Any]:
    """
    Query Wikidata for epidemiological data about a disease.

    Returns:
        {
            patient_population_estimate: str | None,
            prevalence_rate: str | None,
            wikidata_entity: str | None,
            source_url: str
        }
    """
    result: dict[str, Any] = {
        "patient_population_estimate": None,
        "prevalence_rate": None,
        "wikidata_entity": None,
        "source_url": "https://www.wikidata.org",
    }

    # Try the detailed epidemiology query first
    query = _DISEASE_QUERY.format(disease_name=disease_name.replace('"', '\\"'))
    bindings = _run_sparql(query)

    if bindings:
        for b in bindings:
            entity = b.get("disease", {}).get("value", "")
            label = b.get("diseaseLabel", {}).get("value", "")
            prevalence = b.get("prevalence", {}).get("value")
            incidence = b.get("incidence", {}).get("value")

            result["wikidata_entity"] = entity
            result["source_url"] = entity
            if prevalence:
                result["prevalence_rate"] = prevalence
            if incidence:
                result["patient_population_estimate"] = incidence

            logger.info("Wikidata: found %s (%s)", label, entity)
            break  # Use first match
    else:
        # Try simpler query just to find the entity
        query = _SIMPLE_QUERY.format(disease_name=disease_name.replace('"', '\\"'))
        bindings = _run_sparql(query)
        if bindings:
            entity = bindings[0].get("disease", {}).get("value", "")
            result["wikidata_entity"] = entity
            result["source_url"] = entity
            logger.info("Wikidata: found entity %s (no epi data)", entity)
        else:
            logger.warning("Wikidata: no results for '%s'", disease_name)

    return result
