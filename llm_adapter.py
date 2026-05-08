#!/usr/bin/env python3
"""Optional model-backed slice adapter for Cognitive Council.

This file is intentionally small and swappable. It preserves the same slice JSON
contract as the deterministic runtime and only runs when explicitly requested.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import request, error

ROOT = Path(__file__).parent
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.environ.get("COUNCIL_MODEL", "gpt-5.5")

REQUIRED_KEYS = {
    "slice",
    "recommendation",
    "decision_vote",
    "confidence",
    "evidence",
    "concerns",
}


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    return json.loads(text)


def _prompt_for_slice(slice_name: str) -> str:
    path = ROOT / "slices" / f"{slice_name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are the {slice_name} cognitive slice. Return compact JSON only."


def run_openai_slice(
    slice_name: str,
    task: dict[str, Any],
    base: dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Run one model-backed slice via OpenAI Responses API.

    Requires OPENAI_API_KEY. Raises a clear RuntimeError if unavailable.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot run model-backed slice")

    system = (
        _prompt_for_slice(slice_name)
        + "\n\nReturn JSON only with exactly these keys: "
        + ", ".join(sorted(REQUIRED_KEYS))
        + ". confidence must be a number from 0 to 1. decision_vote must be one of: "
        + "answer_directly, confirm_then_send, ask_clarifying_question, safety_hold, "
        + "ask_for_specific_feedback, present_tradeoff_plan."
    )
    user = {
        "task": task,
        "deterministic_base_analysis": base,
        "contract": sorted(REQUIRED_KEYS),
    }
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, sort_keys=True)},
        ],
        "text": {"format": {"type": "json_object"}},
    }
    req = request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI slice call failed: HTTP {exc.code}: {body[:500]}") from exc

    text = data.get("output_text")
    if not text:
        chunks: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    chunks.append(content.get("text", ""))
        text = "\n".join(chunks)
    parsed = _extract_json(text or "{}")
    return normalize_slice_output(slice_name, parsed, base)


def normalize_slice_output(slice_name: str, obj: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """Coerce model output into the runtime's slice-output contract."""
    out = {
        "slice": slice_name,
        "recommendation": str(obj.get("recommendation") or "model_slice_review"),
        "decision_vote": str(obj.get("decision_vote") or base.get("decision") or "answer_directly"),
        "confidence": float(obj.get("confidence", base.get("confidence", 0.5))),
        "evidence": obj.get("evidence") if isinstance(obj.get("evidence"), list) else [],
        "concerns": obj.get("concerns") if isinstance(obj.get("concerns"), list) else [],
        "adapter": "openai.responses",
    }
    out["confidence"] = round(max(0.05, min(0.99, out["confidence"])), 3)
    return out
