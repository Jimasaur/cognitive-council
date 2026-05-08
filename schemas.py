"""Stdlib validators for Cognitive Council local /runs records.

These validators intentionally cover the stable contract fields instead of
requiring a third-party JSON Schema dependency at runtime. The matching
schema-like docs live in ./schemas/*.schema.json.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

RUN_STATUSES = {"queued", "running", "completed", "failed"}
APPROVAL_KINDS = {"none", "confirmation", "action"}
APPROVAL_STATUSES = {"not_required", "pending"}


class ValidationError(ValueError):
    """Raised when a local /runs object violates the contract."""


def _require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    return value


def _require_str(obj: dict[str, Any], key: str, path: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{path}.{key} must be a non-empty string")
    return value


def _require_bool(obj: dict[str, Any], key: str, path: str) -> bool:
    value = obj.get(key)
    if not isinstance(value, bool):
        raise ValidationError(f"{path}.{key} must be a boolean")
    return value


def _require_datetime(obj: dict[str, Any], key: str, path: str) -> None:
    value = _require_str(obj, key, path)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{path}.{key} must be an ISO-8601 datetime") from exc


def validate_run_request(value: Any) -> dict[str, Any]:
    request = _require_mapping(value, "run_request")
    fixture = _require_mapping(request.get("fixture"), "run_request.fixture")
    for key in ("id", "title", "user_message"):
        _require_str(fixture, key, "run_request.fixture")
    _require_str(request, "profile", "run_request")
    if request.get("llm_slice") is not None and not isinstance(request.get("llm_slice"), str):
        raise ValidationError("run_request.llm_slice must be a string or null when present")
    if request.get("model") is not None and not isinstance(request.get("model"), str):
        raise ValidationError("run_request.model must be a string or null when present")
    if "requested_by" in request and not isinstance(request["requested_by"], str):
        raise ValidationError("run_request.requested_by must be a string when present")
    if "metadata" in request and not isinstance(request["metadata"], dict):
        raise ValidationError("run_request.metadata must be an object when present")
    return request


def validate_council_result(value: Any) -> dict[str, Any]:
    result = _require_mapping(value, "council_result")
    for key in ("runtime", "task_id", "profile", "decision"):
        _require_str(result, key, "council_result")
    _require_bool(result, "requires_confirmation", "council_result")
    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValidationError("council_result.confidence must be a number between 0 and 1")
    if not isinstance(result.get("flags"), list) or not all(isinstance(f, str) for f in result["flags"]):
        raise ValidationError("council_result.flags must be a list of strings")
    if not isinstance(result.get("slice_outputs"), list):
        raise ValidationError("council_result.slice_outputs must be a list")
    action = _require_mapping(result.get("next_action"), "council_result.next_action")
    _require_str(action, "type", "council_result.next_action")
    _require_str(action, "message", "council_result.next_action")
    return result


def validate_approval(value: Any, path: str = "approval") -> dict[str, Any]:
    approval = _require_mapping(value, path)
    required = _require_bool(approval, "required", path)
    kind = _require_str(approval, "kind", path)
    status = _require_str(approval, "status", path)
    if kind not in APPROVAL_KINDS:
        raise ValidationError(f"{path}.kind must be one of {sorted(APPROVAL_KINDS)}")
    if status not in APPROVAL_STATUSES:
        raise ValidationError(f"{path}.status must be one of {sorted(APPROVAL_STATUSES)}")
    if required and status != "pending":
        raise ValidationError(f"{path}.status must be pending when approval is required")
    if not required and (kind != "none" or status != "not_required"):
        raise ValidationError(f"{path} must be kind=none/status=not_required when approval is not required")
    _require_str(approval, "reason", path)
    action = _require_mapping(approval.get("action"), f"{path}.action")
    _require_str(action, "type", f"{path}.action")
    _require_str(action, "message", f"{path}.action")
    return approval


def validate_receipt(value: Any) -> dict[str, Any]:
    receipt = _require_mapping(value, "receipt")
    for key in ("receipt_id", "run_id", "runtime", "task_id", "profile", "decision"):
        _require_str(receipt, key, "receipt")
    _require_datetime(receipt, "created_at", "receipt")
    _require_datetime(receipt, "completed_at", "receipt")
    if receipt.get("status") not in {"completed", "failed"}:
        raise ValidationError("receipt.status must be completed or failed")
    _require_bool(receipt, "requires_confirmation", "receipt")
    validate_approval(receipt.get("approval"), "receipt.approval")
    _require_mapping(receipt.get("result_summary"), "receipt.result_summary")
    return receipt


def validate_run_record(value: Any) -> dict[str, Any]:
    record = _require_mapping(value, "run_record")
    _require_str(record, "run_id", "run_record")
    if record.get("status") not in RUN_STATUSES:
        raise ValidationError(f"run_record.status must be one of {sorted(RUN_STATUSES)}")
    _require_datetime(record, "created_at", "run_record")
    _require_datetime(record, "updated_at", "run_record")
    validate_run_request(record.get("request"))
    validate_council_result(record.get("result"))
    validate_receipt(record.get("receipt"))
    if record["receipt"]["run_id"] != record["run_id"]:
        raise ValidationError("receipt.run_id must match run_record.run_id")
    if record["receipt"]["status"] != record["status"]:
        raise ValidationError("receipt.status must match run_record.status")
    return record
