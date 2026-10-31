from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from src.agent.workflow import investigation_graph
from src.data import repository
from src.domain.models import IngestEventRequest, InvestigationRequest


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
UI_FILE = Path(__file__).parent / "ui" / "index.html"


@asynccontextmanager
async def lifespan(_: FastAPI):
    repository.initialize()
    yield


app = FastAPI(
    title="SecOps Investigation Copilot",
    description="Read-only, evidence-grounded security investigations across normalized event sources.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(UI_FILE)


@app.get("/api/health")
def health() -> dict[str, str]:
    import os

    hosted = os.getenv("USE_HOSTED_MODEL", "false").lower() == "true" and bool(os.getenv("OPENAI_API_KEY"))
    return {"status": "ok", "model_mode": "hosted" if hosted else "deterministic"}


@app.get("/api/events")
def list_events() -> list[dict[str, Any]]:
    return repository.get_events()


@app.post("/api/events", status_code=201)
def ingest_event(event: IngestEventRequest) -> dict[str, str]:
    try:
        repository.add_event(event)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not persist event") from exc
    return {"status": "accepted", "event_id": event.event_id}


@app.post("/api/investigations", status_code=201)
def investigate(request: InvestigationRequest) -> dict[str, Any]:
    try:
        result = investigation_graph.invoke({
            "question": request.question,
            "alert_id": request.alert_id,
            "time_window_hours": request.time_window_hours,
        })
        report = result["report"]
        return repository.save_investigation(request.question, request.alert_id, report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {type(exc).__name__}") from exc


@app.get("/api/investigations")
def list_investigations() -> list[dict[str, Any]]:
    return repository.get_investigations()
