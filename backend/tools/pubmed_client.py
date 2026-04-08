"""
tools/pubmed_client.py — PubMed Entrez API wrapper.

Fetches recent biomedical abstracts from PubMed for a given disease query.
Used by Agent 1 (DiseaseAnalyst) to build the literature corpus.

API: NCBI Entrez E-utilities (no auth required; PUBMED_API_KEY increases rate limit)
Base URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
Rate limit: 3 req/s without key, 10 req/s with key

Key endpoints:
  - esearch.fcgi — get list of PMIDs matching query
  - efetch.fcgi  — fetch abstracts for a list of PMIDs (retmode=xml)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from xml.etree import ElementTree

import httpx

import config

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


async def fetch_abstracts(
    disease_name: str,
    max_results: int = 30,
    max_retries: int = 3,
) -> list[dict]:
    """
    Fetch recent PubMed abstracts for a disease query.

    Two-step process:
      1. esearch → list of PMIDs
      2. efetch  → full abstract XML for those PMIDs

    Filters to papers published in the last 3 years.
    Returns list of {pmid, title, abstract, pub_date, authors}.
    """
    # Calculate mindate — 3 years ago
    three_years_ago = datetime.now() - timedelta(days=3 * 365)
    mindate = three_years_ago.strftime("%Y/%m/%d")
    today = datetime.now().strftime("%Y/%m/%d")

    # --- Step 1: esearch to get PMIDs ---
    search_params = {
        "db": "pubmed",
        "term": f"{disease_name} AND (protein target OR drug target OR therapeutic target)",
        "retmax": str(max_results),
        "retmode": "json",
        "sort": "relevance",
        "datetype": "pdat",
        "mindate": mindate,
        "maxdate": today,
    }
    if config.PUBMED_API_KEY:
        search_params["api_key"] = config.PUBMED_API_KEY

    pmids = await _esearch_with_retry(search_params, max_retries)
    if not pmids:
        logger.warning("PubMed esearch returned no PMIDs for '%s'", disease_name)
        return []

    logger.info("PubMed esearch: found %d PMIDs for '%s'", len(pmids), disease_name)

    # --- Step 2: efetch to get abstracts ---
    abstracts = await _efetch_with_retry(pmids, max_retries)
    logger.info("PubMed efetch: retrieved %d abstracts", len(abstracts))
    return abstracts


async def _esearch_with_retry(params: dict, max_retries: int) -> list[str]:
    """Run esearch with retry logic. Returns list of PMID strings."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(ESEARCH_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("esearchresult", {}).get("idlist", [])
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.error("PubMed esearch failed after %d retries: %s", max_retries, exc)
                return []
            wait = 2 ** attempt
            logger.warning("PubMed esearch attempt %d failed: %s, retrying in %ds", attempt + 1, exc, wait)
            await asyncio.sleep(wait)
    return []


async def _efetch_with_retry(pmids: list[str], max_retries: int) -> list[dict]:
    """Run efetch with retry logic. Returns list of parsed abstract dicts."""
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    if config.PUBMED_API_KEY:
        fetch_params["api_key"] = config.PUBMED_API_KEY

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(EFETCH_URL, params=fetch_params)
                resp.raise_for_status()
                return _parse_pubmed_xml(resp.text)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                logger.error("PubMed efetch failed after %d retries: %s", max_retries, exc)
                return []
            wait = 2 ** attempt
            logger.warning("PubMed efetch attempt %d failed: %s, retrying in %ds", attempt + 1, exc, wait)
            await asyncio.sleep(wait)
    return []


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    """Parse PubMed efetch XML into a list of abstract dicts."""
    results = []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        logger.error("Failed to parse PubMed XML: %s", exc)
        return []

    for article in root.findall(".//PubmedArticle"):
        try:
            medline = article.find("MedlineCitation")
            if medline is None:
                continue

            pmid_el = medline.find("PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            art = medline.find("Article")
            if art is None:
                continue

            # Title
            title_el = art.find("ArticleTitle")
            title = title_el.text if title_el is not None else ""

            # Abstract — may have multiple AbstractText sections
            abstract_parts = []
            abstract_el = art.find("Abstract")
            if abstract_el is not None:
                for text_el in abstract_el.findall("AbstractText"):
                    label = text_el.get("Label", "")
                    text = text_el.text or ""
                    # Some AbstractText elements have mixed content with sub-elements
                    if not text:
                        text = "".join(text_el.itertext())
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            abstract = " ".join(abstract_parts).strip()

            if not abstract:
                continue  # Skip entries without abstracts

            # Publication date
            pub_date = _extract_pub_date(art)

            # Authors
            authors = _extract_authors(art)

            results.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "pub_date": pub_date,
                "authors": authors,
            })
        except Exception as exc:
            logger.warning("Failed to parse one PubMed article: %s", exc)
            continue

    return results


def _extract_pub_date(article_el) -> str:
    """Extract publication date string from an Article element."""
    journal = article_el.find("Journal")
    if journal is not None:
        pub_date = journal.find(".//PubDate")
        if pub_date is not None:
            year = pub_date.findtext("Year", "")
            month = pub_date.findtext("Month", "")
            day = pub_date.findtext("Day", "")
            if year:
                parts = [year]
                if month:
                    parts.append(month)
                if day:
                    parts.append(day)
                return " ".join(parts)
            # MedlineDate fallback
            medline_date = pub_date.findtext("MedlineDate", "")
            if medline_date:
                return medline_date
    return ""


def _extract_authors(article_el) -> str:
    """Extract author names as a comma-separated string."""
    author_list = article_el.find("AuthorList")
    if author_list is None:
        return ""
    names = []
    for author in author_list.findall("Author"):
        last = author.findtext("LastName", "")
        initials = author.findtext("Initials", "")
        if last:
            names.append(f"{last} {initials}".strip())
    return ", ".join(names[:5])  # Cap at 5 authors for brevity
