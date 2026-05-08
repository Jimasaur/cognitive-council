"""Local no-network /runs service for Cognitive Council.

The service is deliberately filesystem-backed and synchronous: creating a run
executes the deterministic local council, writes a completed run record, and
returns it. It is the contract target for a future HTTP /runs endpoint without
starting a server or calling external APIs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from run_council import executive
from schemas import validate_run_record, validate_run_request


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class LocalRunsService:
    """Tiny file-backed service implementing create/get for local /runs."""

    def __init__(self, store_dir: Path):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        request = dict(validate_run_request(request))
        created_at = utc_now()
        run_id = f"run_{uuid4().hex}"
        result = executive(
            request["fixture"],
            request["profile"],
            llm_slice=request.get("llm_slice"),
            model=request.get("model"),
        )
        completed_at = utc_now()
        record = {
            "run_id": run_id,
            "status": "completed",
            "created_at": created_at,
            "updated_at": completed_at,
            "request": request,
            "result": result,
            "receipt": build_receipt(run_id, created_at, completed_at, result),
            "error": None,
        }
        validate_run_record(record)
        self._write(record)
        return record

    def get_run(self, run_id: str) -> dict[str, Any]:
        path = self._path(run_id)
        if not path.exists():
            raise KeyError(f"run not found: {run_id}")
        record = json.loads(path.read_text(encoding="utf-8"))
        validate_run_record(record)
        return record

    def _path(self, run_id: str) -> Path:
        if "/" in run_id or ".." in run_id:
            raise ValueError("invalid run_id")
        return self.store_dir / f"{run_id}.json"

    def _write(self, record: dict[str, Any]) -> None:
        tmp = self._path(record["run_id"]).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self._path(record["run_id"]))


def build_receipt(run_id: str, created_at: str, completed_at: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "receipt_id": f"receipt_{run_id}",
        "run_id": run_id,
        "runtime": result["runtime"],
        "created_at": created_at,
        "completed_at": completed_at,
        "status": "completed",
        "task_id": result["task_id"],
        "profile": result["profile"],
        "decision": result["decision"],
        "requires_confirmation": result["requires_confirmation"],
        "approval": approval_for_result(result),
        "result_summary": {
            "confidence": result["confidence"],
            "flags": result["flags"],
            "top_influences": result.get("top_influences", []),
            "next_action_type": result["next_action"]["type"],
            "slice_output_count": len(result.get("slice_outputs", [])),
        },
    }


def approval_for_result(result: dict[str, Any]) -> dict[str, Any]:
    action = result["next_action"]
    if not result.get("requires_confirmation"):
        return {
            "required": False,
            "kind": "none",
            "status": "not_required",
            "reason": "Council result does not require user approval before proceeding.",
            "action": action,
        }
    kind = "confirmation" if action.get("type") == "ask_confirmation" else "action"
    return {
        "required": True,
        "kind": kind,
        "status": "pending",
        "reason": action.get("message", "Approval required before proceeding."),
        "action": action,
    }


def request_from_fixture(
    fixture: dict[str, Any],
    profile: str = "balanced",
    requested_by: str = "local-test",
    llm_slice: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return {
        "fixture": fixture,
        "profile": profile,
        "llm_slice": llm_slice,
        "model": model,
        "requested_by": requested_by,
        "metadata": {"source": "fixture"},
    }
