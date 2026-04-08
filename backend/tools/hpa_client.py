"""
tools/hpa_client.py — Human Protein Atlas (HPA) client.

Fetches tissue expression data for Agent 2 (TargetValidator).
Used to check if a protein target is expressed in the tissue
affected by the disease under study.

API: https://www.proteinatlas.org/api/
Note: HPA has limited public API. We use their search endpoint
and fall back to a curated gene expression knowledge base.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

HPA_SEARCH_URL = "https://www.proteinatlas.org/api/search_download.php"

# Disease → affected tissue mapping (common diseases)
# For unknown diseases, Agent 2 will use Gemini to map
DISEASE_TISSUE_MAP: dict[str, str] = {
    "parkinson": "brain",
    "parkinson's disease": "brain",
    "alzheimer": "brain",
    "alzheimer's disease": "brain",
    "huntington": "brain",
    "huntington's disease": "brain",
    "als": "brain",
    "amyotrophic lateral sclerosis": "brain",
    "multiple sclerosis": "brain",
    "epilepsy": "brain",
    "schizophrenia": "brain",
    "depression": "brain",
    "glioblastoma": "brain",
    "diabetes": "pancreas",
    "type 2 diabetes": "pancreas",
    "type 1 diabetes": "pancreas",
    "pancreatitis": "pancreas",
    "pancreatic cancer": "pancreas",
    "liver cancer": "liver",
    "hepatitis": "liver",
    "cirrhosis": "liver",
    "nafld": "liver",
    "lung cancer": "lung",
    "copd": "lung",
    "asthma": "lung",
    "pulmonary fibrosis": "lung",
    "breast cancer": "breast",
    "colorectal cancer": "colon",
    "prostate cancer": "prostate",
    "kidney disease": "kidney",
    "chronic kidney disease": "kidney",
    "renal cell carcinoma": "kidney",
    "heart failure": "heart",
    "cardiomyopathy": "heart",
    "atherosclerosis": "heart",
    "leukemia": "bone marrow",
    "lymphoma": "lymph node",
    "melanoma": "skin",
    "psoriasis": "skin",
    "rheumatoid arthritis": "synovial tissue",
    "osteoarthritis": "cartilage",
    "crohn's disease": "colon",
    "ulcerative colitis": "colon",
    "ovarian cancer": "ovary",
    "endometriosis": "uterus",
}

# Curated brain-expressed genes (HPA data for key neuro targets)
# These are known to be expressed in brain tissue based on HPA data
_BRAIN_EXPRESSED_GENES: set[str] = {
    "LRRK2", "SNCA", "PINK1", "PARK7", "GBA1", "PRKN", "MAOB", "COMT",
    "DDC", "TH", "SLC6A3", "DRD1", "DRD2", "DRD3", "DRD4", "DRD5",
    "APP", "PSEN1", "PSEN2", "MAPT", "BACE1", "TREM2", "APOE", "GSK3B",
    "ADAM10", "BIN1", "HTR2A", "OPRM1", "GRIN1", "GRIN2A", "GRIN2B",
    "GAD1", "GAD2", "SLC6A4", "GABRA1", "GABRG2", "CHRNA7", "CHAT",
    "ACHE", "SYP", "SNAP25", "VMAT2", "SLC18A2", "VPS13C", "USP25",
    "P2RX7", "RNASET2", "PKM",
}


async def fetch_tissue_expression(
    gene_symbol: str,
    target_tissue: str,
    max_retries: int = 3,
) -> dict:
    """
    Check if a protein is expressed in a given tissue.

    Tries HPA API first; falls back to curated gene lists.

    Returns {
        expressed_in_target_tissue: bool,
        expression_level: str (HIGH/MEDIUM/LOW/NOT_DETECTED),
        tissue_name: str
    }
    """
    # Try HPA API
    result = await _query_hpa(gene_symbol, target_tissue, max_retries)
    if result:
        # Cross-check: if API says NOT_DETECTED but curated list says expressed,
        # trust curated data (HPA search API can be unreliable for tissue queries)
        if not result["expressed_in_target_tissue"]:
            curated = _curated_expression(gene_symbol, target_tissue)
            if curated["expressed_in_target_tissue"] and curated["expression_level"] != "UNKNOWN":
                logger.info("HPA API says NOT_DETECTED for %s in %s, but curated data says expressed — using curated",
                            gene_symbol, target_tissue)
                return curated
        return result

    # Fallback: curated knowledge
    return _curated_expression(gene_symbol, target_tissue)


def get_tissue_for_disease(disease_name: str) -> str:
    """Map a disease name to its primary affected tissue."""
    disease_lower = disease_name.lower().strip()
    # Direct match
    if disease_lower in DISEASE_TISSUE_MAP:
        return DISEASE_TISSUE_MAP[disease_lower]
    # Partial match
    for key, tissue in DISEASE_TISSUE_MAP.items():
        if key in disease_lower or disease_lower in key:
            return tissue
    # Default: unknown
    return "unknown"


async def _query_hpa(
    gene_symbol: str, target_tissue: str, max_retries: int
) -> dict | None:
    """Query Human Protein Atlas API for tissue expression."""
    params = {
        "search": gene_symbol,
        "format": "json",
        "columns": "g,t,Level,Reliability",
        "compress": "no",
    }

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(HPA_SEARCH_URL, params=params)
                if resp.status_code in (404, 400):
                    return None
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    return None

                # Search for the target tissue in results
                tissue_lower = target_tissue.lower()
                for entry in data:
                    tissue = str(entry.get("Tissue", entry.get("t", ""))).lower()
                    if tissue_lower in tissue or tissue in tissue_lower:
                        level = entry.get("Level", entry.get("level", "NOT_DETECTED"))
                        return {
                            "expressed_in_target_tissue": level.upper() not in ("NOT DETECTED", "NOT_DETECTED", ""),
                            "expression_level": _normalize_level(level),
                            "tissue_name": target_tissue,
                        }

                # Tissue not found in results — check if gene exists at all
                return None

        except (httpx.HTTPError, httpx.TimeoutException, ValueError):
            if attempt == max_retries - 1:
                return None
            await asyncio.sleep(2 ** attempt)
    return None


def _curated_expression(gene_symbol: str, target_tissue: str) -> dict:
    """Fallback: use curated gene expression data."""
    gene_upper = gene_symbol.upper()
    tissue_lower = target_tissue.lower()

    if tissue_lower == "brain" and gene_upper in _BRAIN_EXPRESSED_GENES:
        return {
            "expressed_in_target_tissue": True,
            "expression_level": "MEDIUM",  # Conservative estimate
            "tissue_name": target_tissue,
        }

    # For unknown combinations, assume expressed (conservative — avoids false negatives)
    return {
        "expressed_in_target_tissue": True,
        "expression_level": "UNKNOWN",
        "tissue_name": target_tissue,
    }


def _normalize_level(level: str) -> str:
    """Normalize HPA expression level to HIGH/MEDIUM/LOW/NOT_DETECTED."""
    level_upper = str(level).upper().strip()
    if level_upper in ("HIGH",):
        return "HIGH"
    if level_upper in ("MEDIUM",):
        return "MEDIUM"
    if level_upper in ("LOW",):
        return "LOW"
    if level_upper in ("NOT DETECTED", "NOT_DETECTED", ""):
        return "NOT_DETECTED"
    return "MEDIUM"  # Default for ambiguous values
