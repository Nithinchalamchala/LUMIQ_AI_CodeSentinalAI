"""FastAPI server with WebSocket support for the Code Review Agent Pipeline."""

from __future__ import annotations
import asyncio
import json
import logging
import os
import uuid
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BASE_DIR, FRONTEND_DIR
from backend.models import (
    ReviewRequest, PipelineResult, AgentEvent, PipelineStatus
)
from backend.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ── App Setup ──────────────────────────────────────────
app = FastAPI(
    title="AI Code Review Agent",
    description="Multi-agent autonomous code review and fix pipeline",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── State ──────────────────────────────────────────────
# In-memory storage for pipeline runs
pipeline_runs: Dict[str, PipelineResult] = {}
# WebSocket connections per job
ws_connections: Dict[str, list[WebSocket]] = {}


# ── WebSocket Event Broadcasting ───────────────────────
async def broadcast_event(job_id: str, event: AgentEvent):
    """Send an agent event to all WebSocket clients for a job."""
    if job_id in ws_connections:
        message = json.dumps({
            "type": "agent_event",
            "data": event.model_dump(mode="json")
        })
        disconnected = []
        for ws in ws_connections[job_id]:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            ws_connections[job_id].remove(ws)


async def broadcast_status(job_id: str, status: str, data: dict = None):
    """Send a status update to all WebSocket clients."""
    if job_id in ws_connections:
        message = json.dumps({
            "type": "status_update",
            "data": {"status": status, **(data or {})}
        })
        disconnected = []
        for ws in ws_connections[job_id]:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            ws_connections[job_id].remove(ws)


# ── API Routes ─────────────────────────────────────────

@app.post("/api/review")
async def start_review(request: ReviewRequest):
    """Start a new code review pipeline run."""
    job_id = str(uuid.uuid4())

    async def event_callback(event: AgentEvent):
        """Forward agent events to WebSocket clients."""
        if job_id in pipeline_runs:
            pipeline_runs[job_id].events.append(event)
        await broadcast_event(job_id, event)
        # Also broadcast status changes
        status_map = {
            "analyzer": "analyzing",
            "planner": "planning",
            "fixer": "fixing",
            "verifier": "verifying",
        }
        agent_status = status_map.get(event.agent.value, "")
        if agent_status and event.event_type == "started":
            await broadcast_status(job_id, agent_status)

    # Initialize the pipeline result
    result = PipelineResult(job_id=job_id, status=PipelineStatus.PENDING)
    pipeline_runs[job_id] = result

    # Run pipeline in background
    async def run_pipeline():
        try:
            orchestrator = Orchestrator(event_callback=event_callback)
            final_result = await orchestrator.run(
                target_path=request.target_path,
                repo_url=request.repo_url,
                demo=request.demo
            )
            final_result.job_id = job_id
            pipeline_runs[job_id] = final_result

            await broadcast_status(job_id, final_result.status.value, {
                "result": final_result.model_dump(mode="json")
            })
        except Exception as e:
            logger.exception(f"Pipeline error for job {job_id}")
            pipeline_runs[job_id].status = PipelineStatus.FAILED
            pipeline_runs[job_id].error = str(e)
            await broadcast_status(job_id, "failed", {"error": str(e)})

    asyncio.create_task(run_pipeline())

    return {"job_id": job_id, "status": "started"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get the current status of a pipeline run."""
    if job_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail="Job not found")
    result = pipeline_runs[job_id]
    return {
        "job_id": job_id,
        "status": result.status.value,
        "events_count": len(result.events),
        "error": result.error
    }


@app.get("/api/report/{job_id}")
async def get_report(job_id: str):
    """Get the full pipeline report."""
    if job_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail="Job not found")
    return pipeline_runs[job_id].model_dump(mode="json")


@app.get("/api/events/{job_id}")
async def get_events(job_id: str):
    """Get all events for a pipeline run."""
    if job_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "events": [e.model_dump(mode="json") for e in pipeline_runs[job_id].events]
    }


# ── WebSocket ──────────────────────────────────────────

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time pipeline events."""
    await websocket.accept()

    if job_id not in ws_connections:
        ws_connections[job_id] = []
    ws_connections[job_id].append(websocket)

    try:
        # Send existing events first
        if job_id in pipeline_runs:
            for event in pipeline_runs[job_id].events:
                await websocket.send_text(json.dumps({
                    "type": "agent_event",
                    "data": event.model_dump(mode="json")
                }))

        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_text(json.dumps({"type": "heartbeat"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if job_id in ws_connections:
            if websocket in ws_connections[job_id]:
                ws_connections[job_id].remove(websocket)


# ── Static Files (Frontend) ───────────────────────────

# Serve frontend files
frontend_path = str(FRONTEND_DIR)
if os.path.exists(frontend_path):
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")


@app.get("/")
async def serve_frontend():
    """Serve the main dashboard."""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Frontend not found. Place files in /frontend/</h1>")


# ── Health Check ───────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "demo_mode": True
    }
