"""
orchestrator/runner.py — Async graph execution and job lifecycle management.

Handles:
  - Starting pipeline jobs (background asyncio tasks)
  - Tracking job status (pending / running / complete / failed)
  - Streaming status_updates via WebSocket as the graph runs
  - Persisting final results to backend/jobs/{job_id}/results.json
  - Tracking report path from report_generator node

Usage:
    job_id = await start_job(disease_name, websocket_manager)
    status = get_job_status(job_id)
    results = get_job_results(job_id)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from orchestrator.graph import compiled_graph
from orchestrator.state import create_initial_state, MolForgeState
from ws.manager import WebSocketManager

logger = logging.getLogger(__name__)

# In-memory job registry: job_id -> {"status": ..., "state": ..., "task": ...}
_jobs: dict[str, dict[str, Any]] = {}

JOBS_DIR = Path(__file__).parent.parent / "jobs"
JOBS_DIR.mkdir(exist_ok=True)


async def start_job(disease_name: str, ws_manager: WebSocketManager) -> str:
    """
    Create a new job, initialise state, and start the pipeline as a background task.

    Returns the job_id immediately so the API can return a ws_url to the client.
    """
    state = create_initial_state(disease_name)
    job_id = state["job_id"]

    # Create job subdirectory
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    _jobs[job_id] = {
        "status": "pending",
        "state": state,
        "task": None,
    }

    # Launch as a non-blocking background task
    task = asyncio.create_task(_run_pipeline(job_id, state, ws_manager))
    _jobs[job_id]["task"] = task

    logger.info("Job started: job_id=%s disease=%s", job_id, disease_name)
    return job_id


async def _run_pipeline(job_id: str, state: MolForgeState, ws_manager: WebSocketManager) -> None:
    """Internal: execute the compiled graph and stream updates via WebSocket."""
    _jobs[job_id]["status"] = "running"

    try:
        # Track last known status update count to only stream new ones
        last_update_idx = 0

        # astream yields state snapshots after each node completes
        async for chunk in compiled_graph.astream(state):
            # chunk is a dict: {node_name: updated_state_slice}
            for node_name, updated in chunk.items():
                if not isinstance(updated, dict):
                    continue

                # Merge partial state back into our tracking dict.
                # status_updates and errors use operator.add in LangGraph,
                # so the delta contains only NEW items — accumulate them.
                for key, val in updated.items():
                    if key in ("status_updates", "errors") and isinstance(val, list):
                        _jobs[job_id]["state"].setdefault(key, []).extend(val)
                    else:
                        _jobs[job_id]["state"][key] = val

            # Stream any new status_updates
            current_updates = _jobs[job_id]["state"].get("status_updates", [])
            new_updates = current_updates[last_update_idx:]
            for msg in new_updates:
                await ws_manager.send(job_id, {
                    "type": "agent_done" if "done" in msg.lower() else "agent_start",
                    "agent": list(chunk.keys())[0] if chunk else "unknown",
                    "message": msg,
                })
            last_update_idx = len(current_updates)

            # Send progress update
            total_nodes = 10  # 8 agents + scorer + report
            done_count = sum(1 for u in current_updates if "done" in u.lower())
            progress = min(int(done_count / total_nodes * 100), 99)
            await ws_manager.send(job_id, {"type": "progress", "pct": progress})

        # Pipeline complete
        final_state: MolForgeState = _jobs[job_id]["state"]
        _jobs[job_id]["status"] = "complete"

        go_count = sum(1 for c in final_state.get("final_candidates", []) if c.get("verdict") == "GO")
        completion_msg = f"Analysis complete. {go_count} GO candidate(s) found."

        await ws_manager.send(job_id, {"type": "complete", "message": completion_msg})
        await ws_manager.send(job_id, {"type": "progress", "pct": 100})

        # Persist results to disk
        _save_results(job_id, final_state)

    except Exception as exc:
        logger.exception("Pipeline failed for job_id=%s: %s", job_id, exc)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["state"]["errors"].append(str(exc))
        await ws_manager.send(job_id, {
            "type": "error",
            "agent": "orchestrator",
            "message": f"Pipeline failed: {exc}",
        })


def _save_results(job_id: str, state: MolForgeState) -> None:
    """Persist final state to jobs/{job_id}/results.json for later retrieval."""
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    path = job_dir / "results.json"
    try:
        with open(path, "w") as f:
            json.dump(dict(state), f, indent=2, default=str)
        logger.info("Results saved: %s", path)
    except Exception as exc:
        logger.error("Failed to save results for %s: %s", job_id, exc)

    # Also keep a flat file for backwards compat
    flat_path = JOBS_DIR / f"{job_id}.json"
    try:
        with open(flat_path, "w") as f:
            json.dump(dict(state), f, indent=2, default=str)
    except Exception:
        pass


def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Return status info for a job, or None if not found."""
    job = _jobs.get(job_id)
    if not job:
        return None

    state: MolForgeState = job["state"]
    total_nodes = 10  # 8 agents + scorer + report
    done_count = sum(1 for u in state.get("status_updates", []) if "done" in u.lower())
    progress_pct = min(int(done_count / total_nodes * 100), 99) if job["status"] == "running" else (
        100 if job["status"] == "complete" else 0
    )

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress_pct": progress_pct,
        "updates": state.get("status_updates", []),
    }


def get_job_results(job_id: str) -> dict[str, Any] | None:
    """Return full results for a completed job, or None if not found/not complete."""
    job = _jobs.get(job_id)
    if not job:
        # Try loading from disk (subdirectory first, then flat file)
        for path in [JOBS_DIR / job_id / "results.json", JOBS_DIR / f"{job_id}.json"]:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        return None

    if job["status"] != "complete":
        return None

    return dict(job["state"])
