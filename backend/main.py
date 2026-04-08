"""
main.py — MolForge AI FastAPI application entry point.

All routes are defined here. Import from models.py for request/response shapes.
Import from orchestrator/runner.py for job lifecycle management.

Run with: uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
from models import (
    DiscoverRequest,
    DiscoverResponse,
    ErrorResponse,
    HealthResponse,
    ResultsResponse,
    StatusResponse,
    CandidateCompound,
    AdmetDetail,
    MarketBrief,
    ValidatedTarget,
)
from orchestrator.runner import get_job_results, get_job_status, start_job
from ws.manager import manager as ws_manager

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MolForge AI backend starting up...")
    logger.info("CORS origins: %s", config.CORS_ORIGINS)
    logger.info("Max candidates: %d | Novelty threshold: %.2f", config.MAX_CANDIDATES, config.NOVELTY_THRESHOLD)

    health = config.health_check()
    if health["status"] == "degraded":
        logger.warning("Health check issues on startup: %s", health.get("detail"))
    else:
        logger.info("Health check OK — gemini=%s rdkit=%s chroma=%s", health["gemini"], health["rdkit"], health["chroma"])

    yield

    logger.info("MolForge AI backend shutting down...")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MolForge AI",
    description="End-to-end agentic drug discovery platform — From Disease to Drug Candidate, Autonomously",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health():
    """Liveness check — verifies Gemini key, RDKit, and ChromaDB are available."""
    return config.health_check()


@app.post("/api/discover", response_model=DiscoverResponse)
async def discover(request: DiscoverRequest):
    """
    Start a new drug discovery pipeline for the given disease.
    Returns a job_id and WebSocket URL immediately — pipeline runs in background.
    """
    job_id = await start_job(request.disease, ws_manager)
    ws_url = f"{config.CORS_ORIGINS[0].replace('http', 'ws').replace('https', 'wss').replace(':5173', ':8000').replace(':3000', ':8000')}/ws/{job_id}"
    # Simpler: construct from request base URL in production; hardcode ws base for now
    ws_url = f"ws://localhost:{config.BACKEND_PORT}/ws/{job_id}"
    return DiscoverResponse(job_id=job_id, status="started", ws_url=ws_url)


@app.get("/api/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """Poll job status and recent status_updates."""
    status = get_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return StatusResponse(**status)


@app.get("/api/results/{job_id}", response_model=ResultsResponse)
async def get_results(job_id: str):
    """Return final results for a completed job."""
    results = get_job_results(job_id)
    if results is None:
        status = get_job_status(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        raise HTTPException(status_code=202, detail=f"Job {job_id} is still {status['status']}")

    # Map raw state dict → ResultsResponse
    final_candidates = []
    for c in results.get("final_candidates", []):
        admet_raw = c.get("admet_detail", {})
        admet = AdmetDetail(**admet_raw) if admet_raw else None
        final_candidates.append(CandidateCompound(
            smiles=c.get("smiles", ""),
            name=c.get("name"),
            composite_score=c.get("composite_score", 0.0),
            binding_score=c.get("binding_score", 0.0),
            admet_score=c.get("admet_score", 0.0),
            literature_score=c.get("literature_score", 0.0),
            market_score=c.get("market_score", 0.0),
            verdict=c.get("verdict", "INVESTIGATE"),
            novelty_score=c.get("novelty_score", 0.0),
            admet_detail=admet,
            svg_url=f"/api/molecule/svg/{job_id}/{results['final_candidates'].index(c)}",
        ))

    target_raw = results.get("validated_target", {})
    # Target may use "name" or "gene_symbol" depending on agent output
    target_name = target_raw.get("name") or target_raw.get("gene_symbol")
    validated_target = ValidatedTarget(**{**target_raw, "name": target_name}) if target_name else None

    market_raw = results.get("market_data", {})
    opportunity_raw = results.get("opportunity_score", {})
    competitive_raw = results.get("competitive_data", {})
    market_brief = MarketBrief(
        patient_population=market_raw.get("patient_population"),
        market_size=market_raw.get("market_size_usd") or market_raw.get("market_size_usd_estimate"),
        opportunity_rating=opportunity_raw.get("rating"),
        unmet_need_score=opportunity_raw.get("score"),
        commercial_brief=opportunity_raw.get("commercial_brief"),
        competitive_density=competitive_raw.get("density_label") or competitive_raw.get("competitive_density"),
    ) if market_raw or opportunity_raw else None

    return ResultsResponse(
        job_id=job_id,
        disease=results.get("disease_name", ""),
        status="complete",
        validated_target=validated_target,
        final_candidates=final_candidates,
        market_brief=market_brief,
        report_url=f"/api/report/{job_id}",
    )


@app.get("/api/molecule/svg/{job_id}/{candidate_index}")
async def get_molecule_svg(job_id: str, candidate_index: int):
    """Return 2D SVG structure for a specific candidate compound."""
    from fastapi.responses import Response
    from chemistry.visualizer import smiles_to_svg

    results = get_job_results(job_id)
    if results is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    candidates = results.get("final_candidates", [])
    if candidate_index < 0 or candidate_index >= len(candidates):
        raise HTTPException(status_code=404, detail=f"Candidate index {candidate_index} out of range")

    smiles = candidates[candidate_index].get("smiles", "")
    if not smiles:
        raise HTTPException(status_code=404, detail="No SMILES for this candidate")

    # Check query param for dark mode
    svg = smiles_to_svg(smiles, width=350, height=250)
    if svg is None:
        # Return error SVG if rendering fails
        error_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="350" height="250">'
            '<rect width="350" height="250" fill="#f8f8f8"/>'
            '<text x="175" y="130" text-anchor="middle" fill="#888" font-family="monospace" font-size="12">'
            'Structure could not be rendered'
            '</text></svg>'
        )
        return Response(content=error_svg, media_type="image/svg+xml")

    return Response(content=svg, media_type="image/svg+xml")


@app.get("/api/candidate/{job_id}/{candidate_index}")
async def get_candidate_detail(job_id: str, candidate_index: int):
    """
    Return full research detail for a specific candidate compound.
    Includes all pipeline data: target info, docking, ADMET, synthesis, biologics.
    """
    results = get_job_results(job_id)
    if results is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    candidates = results.get("final_candidates", [])
    if candidate_index < 0 or candidate_index >= len(candidates):
        raise HTTPException(status_code=404, detail=f"Candidate index {candidate_index} out of range")

    candidate = candidates[candidate_index]
    smiles = candidate.get("smiles", "")

    # Gather all related data for this candidate
    docking_results = results.get("docking_results", [])
    docking = next((d for d in docking_results if d.get("smiles") == smiles), None)

    synthesis_routes = results.get("synthesis_routes", [])
    synthesis = next((s for s in synthesis_routes if s.get("smiles") == smiles), None)

    admet_results = results.get("admet_results", [])
    admet_full = next((a for a in admet_results if a.get("smiles") == smiles), None)

    return {
        "candidate": candidate,
        "candidate_index": candidate_index,
        "validated_target": results.get("validated_target", {}),
        "protein_structure": results.get("protein_structure", {}),
        "docking": docking,
        "synthesis": synthesis,
        "admet_full": admet_full,
        "biologics": results.get("biologics_data", {}),
        "market_data": results.get("market_data", {}),
        "competitive_data": results.get("competitive_data", {}),
        "opportunity_score": results.get("opportunity_score", {}),
        "disease": results.get("disease_name", ""),
        "svg_url": f"/api/molecule/svg/{job_id}/{candidate_index}",
    }


@app.get("/api/protein/pdb/{job_id}")
async def get_protein_pdb(job_id: str):
    """Return the PDB file for the protein structure of a job."""
    from fastapi.responses import Response
    from pathlib import Path

    results = get_job_results(job_id)
    if results is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    pdb_path = results.get("protein_structure", {}).get("pdb_file_path")
    if not pdb_path or not Path(pdb_path).exists():
        raise HTTPException(status_code=404, detail="No PDB file available for this job")

    pdb_content = Path(pdb_path).read_text()
    return Response(content=pdb_content, media_type="text/plain")


@app.get("/api/report/{job_id}")
async def get_report(job_id: str):
    """Return PDF report for a completed job."""
    from fastapi.responses import FileResponse
    from pathlib import Path

    jobs_dir = Path(__file__).parent / "jobs"
    report_path = jobs_dir / job_id / "report.pdf"

    if not report_path.exists():
        # Check if job exists but report not yet generated
        results = get_job_results(job_id)
        if results is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        raise HTTPException(status_code=404, detail=f"Report for job {job_id} not yet generated")

    return FileResponse(
        path=str(report_path),
        media_type="application/pdf",
        filename=f"molforge_{job_id}_report.pdf",
    )


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    Real-time agent status stream for a job.
    Client connects here after receiving ws_url from POST /api/discover.
    """
    await ws_manager.connect(job_id, websocket)
    try:
        # Keep connection alive — messages are pushed by the pipeline runner
        while True:
            # Wait for any client message (ping/pong keepalive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(job_id)
        logger.info("WebSocket client disconnected: job_id=%s", job_id)
