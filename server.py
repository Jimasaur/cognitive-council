#!/usr/bin/env python3
"""Tiny local FastAPI service for Cognitive Council runs.

Canonical runtime contract:
- POST /runs accepts an inline task or local fixture path.
- It executes the Council synchronously and stores a completed run record under .runs/.
- Responses include result + approval + receipt using the same shape as tests.

Local-only prototype. Bind to 127.0.0.1; do not expose externally.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from run_council import ROOT, SLICE_NAMES, load_json
from runs_service import LocalRunsService, request_from_fixture
from schemas import ValidationError, validate_run_record

RUNS_DIR = ROOT / ".runs"

app = FastAPI(
    title="Cognitive Council Local Runtime",
    version="0.2.0",
    description="Local-only /runs wrapper around the Cognitive Council runtime.",
)


class RunRequest(BaseModel):
    """Request body for POST /runs.

    Provide exactly one of:
    - task: inline task/fixture JSON object
    - fixture / fixturePath: local fixture path, relative to this project unless absolute
    """

    task: dict[str, Any] | None = None
    fixture: str | None = None
    fixture_path: str | None = Field(default=None, alias="fixturePath")
    profile: str = "balanced"
    llm_slice: str | None = Field(default=None, alias="llmSlice")
    model: str | None = None
    requested_by: str = Field(default="local-http", alias="requestedBy")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_input(self) -> "RunRequest":
        path = self.fixture or self.fixture_path
        if self.task is None and not path:
            raise ValueError("Provide either 'task' or local fixture path via 'fixture'.")
        if self.task is not None and path:
            raise ValueError("Provide only one of 'task' or 'fixture'.")
        if self.llm_slice is not None and self.llm_slice not in SLICE_NAMES:
            raise ValueError(f"llm_slice must be one of: {', '.join(SLICE_NAMES)}")
        return self

    @property
    def requested_fixture(self) -> str | None:
        return self.fixture or self.fixture_path


def resolve_fixture(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def load_task(req: RunRequest) -> tuple[dict[str, Any], str]:
    if req.task is not None:
        return req.task, "inline"
    assert req.requested_fixture is not None
    path = resolve_fixture(req.requested_fixture)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Fixture not found: {req.requested_fixture}")
    try:
        return load_json(path), str(path)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Fixture is not valid JSON: {exc}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "runtime": "cognitive-council.local.v0"}


@app.post("/runs")
def create_run(req: RunRequest) -> dict[str, Any]:
    task, source = load_task(req)
    service = LocalRunsService(RUNS_DIR)
    local_request = request_from_fixture(
        task,
        profile=req.profile,
        requested_by=req.requested_by,
        llm_slice=req.llm_slice,
        model=req.model,
    )
    local_request["metadata"] = {**local_request.get("metadata", {}), **req.metadata, "task_source": source}
    try:
        record = service.create_run(local_request)
        validate_run_record(record)
        return record
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail=f"Run contract validation failed: {exc}") from exc
    except SystemExit as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Model-backed slice failures, unknown profile errors, etc. remain local and inspectable.
        raise HTTPException(status_code=500, detail=f"Run failed: {exc}") from exc


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    try:
        record = LocalRunsService(RUNS_DIR).get_run(run_id)
        validate_run_record(record)
        return record
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail=f"Stored run contract validation failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8765, reload=False)
