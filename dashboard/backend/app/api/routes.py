from __future__ import annotations

import threading
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.loader import (
    DEFAULT_STAGE,
    STAGE_ORDER,
    group_standings,
    load_config,
    load_matches,
    load_metrics,
    load_predictions,
    load_rankings,
    refresh_pipeline,
)

router = APIRouter(prefix="/api")

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _validate_stage(stage: str) -> str:
    if stage not in STAGE_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage; use one of {', '.join(STAGE_ORDER)}",
        )
    return stage


class SimulationRequest(BaseModel):
    strength: str = "elo"
    stage: str = DEFAULT_STAGE
    simulations: int = Field(default=3000, ge=50, le=10000)


def _set_job(job_id: str, **updates: Any) -> None:
    with _jobs_lock:
        job = _jobs.setdefault(
            job_id,
            {
                "job_id": job_id,
                "status": "running",
                "progress": 0.0,
                "message": "",
                "result": None,
            },
        )
        job.update(updates)


def _run_simulation_job(job_id: str, strength: str, stage: str, simulations: int) -> None:
    _set_job(
        job_id,
        status="running",
        progress=0.0,
        message="Running Monte Carlo simulations…",
    )

    def on_progress(done: int, total: int) -> None:
        _set_job(
            job_id,
            progress=done / total if total else 0.0,
            message=f"Simulated {done}/{total}",
        )

    try:
        result = load_rankings(
            strength=strength,
            stage=stage,
            resimulate=True,
            simulations=simulations,
            on_progress=on_progress,
        )
        _set_job(
            job_id,
            status="done",
            progress=1.0,
            message="Complete",
            result=result,
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="error",
            message=str(exc),
            progress=0.0,
        )


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/config")
def config() -> dict:
    return load_config()


@router.get("/teams/rankings")
def rankings(
    strength: str = Query(default="elo"),
    stage: str = Query(default=DEFAULT_STAGE),
    resimulate: bool = Query(default=False),
) -> dict:
    if strength not in {"elo", "fifa"}:
        raise HTTPException(status_code=400, detail="Invalid strength; use elo or fifa")
    stage = _validate_stage(stage)
    return load_rankings(strength=strength, stage=stage, resimulate=resimulate)


@router.post("/simulations")
def start_simulation(body: SimulationRequest) -> dict:
    if body.strength not in {"elo", "fifa"}:
        raise HTTPException(status_code=400, detail="Invalid strength; use elo or fifa")
    stage = _validate_stage(body.stage)
    job_id = uuid.uuid4().hex
    _set_job(job_id, status="running", progress=0.0, message="Queued")
    thread = threading.Thread(
        target=_run_simulation_job,
        args=(job_id, body.strength, stage, body.simulations),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@router.get("/simulations/{job_id}")
def simulation_status(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Unknown job")
        return dict(job)


@router.get("/predictions/worldcup")
def worldcup_predictions(
    strength: str = Query(default="elo"),
    stage: str = Query(default=DEFAULT_STAGE),
    resimulate: bool = Query(default=False),
) -> dict:
    if strength not in {"elo", "fifa"}:
        raise HTTPException(status_code=400, detail="Invalid strength; use elo or fifa")
    stage = _validate_stage(stage)
    if resimulate:
        payload = load_rankings(strength=strength, stage=stage, resimulate=True)
        return {
            "strength": strength,
            "stage": stage,
            "teams": payload.get("teams", []),
            "resimulated": payload.get("resimulated", True),
        }
    return load_predictions(strength, stage)


@router.get("/matches")
def matches(
    year: int | None = Query(default=2026),
    played: bool | None = Query(default=None),
) -> dict:
    return {"matches": load_matches(year=year, played=played)}


@router.get("/groups/{group}")
def group(group: str, year: int = Query(default=2026)) -> dict:
    groups = group_standings(year=year)
    key = group if group in groups else f"Group {group.upper()}"
    if key not in groups:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"group": key, "standings": groups[key]}


@router.get("/groups")
def all_groups(year: int = Query(default=2026)) -> dict:
    return {"groups": group_standings(year=year)}


@router.get("/metrics")
def metrics() -> dict:
    return {"metrics": load_metrics()}


@router.post("/refresh-data")
def refresh_data() -> dict:
    try:
        return refresh_pipeline()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
