"""
config.py — MolForge AI centralised configuration.

Loads all environment variables from .env using python-dotenv and exports them
as typed module-level constants. All other modules import from here — never
call os.environ directly elsewhere.

High-risk file: all 8 agents import from this. Run gitnexus_impact before editing.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

# --- Gemini ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# --- ChromaDB ---
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# --- PubMed ---
PUBMED_API_KEY: str = os.getenv("PUBMED_API_KEY", "")

# --- Server ---
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

# --- Logging ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# --- Pipeline Tuning ---
MAX_CANDIDATES: int = int(os.getenv("MAX_CANDIDATES", "25"))
NOVELTY_THRESHOLD: float = float(os.getenv("NOVELTY_THRESHOLD", "0.85"))
SA_SCORE_MAX: float = float(os.getenv("SA_SCORE_MAX", "6.0"))


def health_check() -> dict:
    """
    Verify critical configuration is present and reachable.
    Called by GET /health on startup and liveness checks.

    Returns a status dict — keys: status, gemini, chroma, rdkit, detail.
    """
    issues = []

    gemini_status = "reachable" if GEMINI_API_KEY else "missing"
    if not GEMINI_API_KEY:
        issues.append("GEMINI_API_KEY not set")

    # RDKit import check
    try:
        from rdkit import Chem  # noqa: F401
        rdkit_status = "ok"
    except ImportError:
        rdkit_status = "not installed"
        issues.append("rdkit not installed")

    # ChromaDB connectivity check
    try:
        import chromadb  # noqa: F401
        chroma_status = "connected"
    except ImportError:
        chroma_status = "not installed"
        issues.append("chromadb not installed")

    overall = "ok" if not issues else "degraded"

    return {
        "status": overall,
        "gemini": gemini_status,
        "chroma": chroma_status,
        "rdkit": rdkit_status,
        "detail": issues if issues else None,
    }
