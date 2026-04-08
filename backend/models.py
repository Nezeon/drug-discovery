"""
models.py — MolForge AI Pydantic request/response models.

All FastAPI endpoint shapes are defined here. Import from this module in main.py
and any other module that needs to serialise/deserialise API data.

Never define inline Pydantic models inside route handlers — always define them here.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# POST /api/discover
# ---------------------------------------------------------------------------

class DiscoverRequest(BaseModel):
    disease: str = Field(..., min_length=2, max_length=200, description="Disease name to analyse")


class DiscoverResponse(BaseModel):
    job_id: str
    status: Literal["started"] = "started"
    ws_url: str


# ---------------------------------------------------------------------------
# GET /api/status/{job_id}
# ---------------------------------------------------------------------------

class StatusResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "complete", "failed"]
    current_agent: Optional[str] = None
    progress_pct: int = Field(0, ge=0, le=100)
    updates: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# GET /api/results/{job_id} — nested models first
# ---------------------------------------------------------------------------

class AdmetDetail(BaseModel):
    absorption: Literal["PASS", "WARN", "FAIL"] = "WARN"
    distribution: Literal["PASS", "WARN", "FAIL"] = "WARN"
    metabolism: Literal["PASS", "WARN", "FAIL"] = "WARN"
    excretion: Literal["PASS", "WARN", "FAIL"] = "WARN"
    toxicity: Literal["PASS", "WARN", "FAIL"] = "WARN"
    herg: Optional[Literal["PASS", "WARN", "FAIL"]] = None
    hepatotoxicity: Optional[Literal["PASS", "WARN", "FAIL"]] = None


class CandidateCompound(BaseModel):
    smiles: str
    name: Optional[str] = None
    composite_score: float = Field(..., ge=0.0, le=1.0)
    binding_score: float = Field(..., ge=0.0, le=1.0)
    admet_score: float = Field(..., ge=0.0, le=1.0)
    literature_score: float = Field(..., ge=0.0, le=1.0)
    market_score: float = Field(..., ge=0.0, le=1.0)
    verdict: Literal["GO", "INVESTIGATE", "NO-GO"]
    novelty_score: float = Field(..., ge=0.0, le=1.0)
    admet_detail: Optional[AdmetDetail] = None
    svg_url: Optional[str] = None


class MarketBrief(BaseModel):
    patient_population: Optional[str] = None
    market_size: Optional[str] = None
    opportunity_rating: Optional[str] = None
    unmet_need_score: Optional[float] = None
    commercial_brief: Optional[str] = None
    competitive_density: Optional[str] = None


class ValidatedTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    protein_name: Optional[str] = None
    uniprot_id: Optional[str] = None
    druggability_score: Optional[float] = None
    evidence: Optional[str] = None


class ResultsResponse(BaseModel):
    job_id: str
    disease: str
    status: Literal["complete", "failed"]
    validated_target: Optional[ValidatedTarget] = None
    final_candidates: list[CandidateCompound] = Field(default_factory=list)
    market_brief: Optional[MarketBrief] = None
    report_url: Optional[str] = None


# ---------------------------------------------------------------------------
# WebSocket message shapes — /ws/{job_id}
# ---------------------------------------------------------------------------

class WebSocketMessage(BaseModel):
    type: Literal["agent_start", "agent_done", "progress", "complete", "error"]
    agent: Optional[str] = None
    message: Optional[str] = None
    pct: Optional[int] = Field(None, ge=0, le=100)
    data: Optional[Any] = None


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    gemini: str
    chroma: str
    rdkit: str
    detail: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Error shape (used by all endpoints on failure)
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    detail: str
    agent: Optional[str] = None
