#!/usr/bin/env python3
"""Cognitive Council Runtime v0.

Default mode is deterministic/local: 8 cognitive slice agents produce structured
JSON, then an executive applies a weighting profile and emits a decision. An
optional --llm-slice flag can replace exactly one slice with a model-backed
adapter while preserving the same JSON contract.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "quick_send.json"
SLICE_NAMES = [
    "compression",
    "attention",
    "prediction",
    "simulation",
    "selection",
    "action",
    "explanation",
    "update",
]

DEFAULT_PROFILES: dict[str, dict[str, float]] = {
    "balanced": {name: 1.0 for name in SLICE_NAMES},
    "operator": {"compression": 0.8, "attention": 1.1, "prediction": 0.8, "simulation": 0.6, "selection": 1.0, "action": 1.8, "explanation": 0.6, "update": 0.7},
    "safety": {"compression": 1.0, "attention": 1.6, "prediction": 1.3, "simulation": 1.1, "selection": 1.5, "action": 0.5, "explanation": 1.2, "update": 1.1},
    "strategist": {"compression": 1.0, "attention": 1.1, "prediction": 1.7, "simulation": 1.8, "selection": 1.2, "action": 0.7, "explanation": 1.0, "update": 1.3},
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_profiles() -> dict[str, dict[str, float]]:
    profiles = dict(DEFAULT_PROFILES)
    profile_dir = ROOT / "profiles"
    for path in profile_dir.glob("*.json"):
        try:
            data = load_json(path)
            # Accept {slice: weight}, {"weights": {...}}, or the richer
            # prompt-asset profile shape {"slice_weights": {...}}.
            weights = data.get("slice_weights") or data.get("weights") or data
            if isinstance(weights, dict):
                profiles[path.stem] = {name: float(weights.get(name, DEFAULT_PROFILES["balanced"][name])) for name in SLICE_NAMES}
        except Exception:
            continue
    return profiles


def context_text(task: dict[str, Any]) -> str:
    parts = [
        task.get("title", ""),
        task.get("user_message", ""),
        task.get("objective", ""),
        json.dumps(task.get("context", {}), sort_keys=True),
        " ".join(task.get("constraints", [])),
    ]
    return " ".join(str(p) for p in parts).lower()


def base_analysis(task: dict[str, Any]) -> dict[str, Any]:
    text = context_text(task)
    ctx = task.get("context", {})
    flags: set[str] = set()
    decision = "answer_directly"
    requires_confirmation = False
    confidence = 0.72

    if ctx.get("external_side_effect") or ctx.get("channel") in {"email", "slack", "sms"}:
        flags.add("external_send")
    if ctx.get("financial_action") or "wire instructions" in text:
        flags.add("financial_risk")
    if any(term in text for term in ["urgent", "bypass", "do not ask"]):
        flags.add("adversarial_urgency")
        if "bypass" in text:
            flags.add("bypass_request")
        decision = "safety_hold"
        requires_confirmation = True
        confidence = 0.86
    elif ctx.get("channel") in {"email", "slack", "sms"}:
        contacts = ctx.get("known_contacts", [])
        first_names = [str(c).split()[0].lower() for c in contacts]
        if len(first_names) != len(set(first_names)):
            flags.update({"recipient_ambiguous", "missing_exact_recipient"})
            decision = "ask_clarifying_question"
            confidence = 0.82
        else:
            flags.update({"recipient_explicit", "body_explicit"})
            decision = "confirm_then_send"
            requires_confirmation = True
            confidence = 0.78
    if ctx.get("task_type") == "draft_revision" and int(ctx.get("prior_draft_attempts", 0)) >= 3:
        flags.update({"draft_loop_risk", "low_specificity_feedback", "needs_user_direction"})
        decision = "ask_for_specific_feedback"
        requires_confirmation = False
        confidence = 0.84
    if ctx.get("task_type") == "planning" or "whether we should" in text:
        flags.update({"planning_required", "tradeoff_detected", "recommendation_needed"})
        decision = "present_tradeoff_plan"
        requires_confirmation = False
        confidence = 0.8

    return {"decision": decision, "requires_confirmation": requires_confirmation, "flags": sorted(flags), "confidence": confidence}


def slice_output(name: str, task: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    flags = set(base["flags"])
    decision = base["decision"]
    confidence = base["confidence"]
    concerns = []
    evidence = []

    if name == "compression":
        recommendation = "preserve_core_facts"
        evidence = [task.get("user_message", "")[:160]]
        concerns = ["missing exact recipient"] if "missing_exact_recipient" in flags else []
    elif name == "attention":
        recommendation = "focus_on_risks" if flags else "focus_on_user_goal"
        evidence = sorted(flags)[:5]
        concerns = sorted(flags)
        confidence += 0.03 if flags else 0
    elif name == "prediction":
        recommendation = "expect_failure_without_clarification" if "recipient_ambiguous" in flags else "outcome_likely_stable"
        evidence = ["external action can create persistent side effects"] if "external_send" in flags else []
    elif name == "simulation":
        recommendation = "compare_best_likely_bad_cases"
        evidence = ["bad case: wrong recipient or duplicate loop"] if flags & {"recipient_ambiguous", "draft_loop_risk"} else ["low downside in current fixture"]
    elif name == "selection":
        recommendation = decision
        evidence = ["decision follows policy flags"]
        confidence += 0.04
    elif name == "action":
        recommendation = "execute_with_confirmation" if base["requires_confirmation"] else "execute_or_respond"
        evidence = ["confirmation required"] if base["requires_confirmation"] else ["no confirmation required"]
    elif name == "explanation":
        recommendation = "explain_decision_and_dissent"
        evidence = ["user should know why action is gated"] if base["requires_confirmation"] else []
    elif name == "update":
        recommendation = "record_policy_learning" if flags else "no_memory_update"
        evidence = sorted(flags)
    else:
        recommendation = decision

    return {
        "slice": name,
        "recommendation": recommendation,
        "decision_vote": decision,
        "confidence": round(max(0.05, min(0.99, confidence)), 3),
        "evidence": evidence,
        "concerns": concerns,
    }


def executive(task: dict[str, Any], profile_name: str, llm_slice: str | None = None, model: str | None = None) -> dict[str, Any]:
    profiles = load_profiles()
    if profile_name not in profiles:
        raise SystemExit(f"Unknown profile {profile_name}. Known: {', '.join(sorted(profiles))}")
    weights = profiles[profile_name]
    base = base_analysis(task)
    slices = []
    for name in SLICE_NAMES:
        if llm_slice == name:
            from llm_adapter import DEFAULT_MODEL, run_openai_slice

            slices.append(run_openai_slice(name, task, base, model or DEFAULT_MODEL))
        else:
            slices.append(slice_output(name, task, base))

    risk_weight = sum(weights[s] for s in ["attention", "prediction", "selection"])
    action_weight = weights["action"]
    effective_confidence = base["confidence"]
    if base["requires_confirmation"] and risk_weight > action_weight:
        effective_confidence += 0.04
    if profile_name == "operator" and base["decision"] == "confirm_then_send":
        effective_confidence += 0.03

    dissent = []
    if profile_name == "operator" and base["requires_confirmation"]:
        dissent.append({"slice": "action", "concern": "operator profile would prefer faster execution if policy allows"})
    if "recipient_ambiguous" in base["flags"]:
        dissent.append({"slice": "attention", "concern": "recipient ambiguity blocks safe execution"})

    slice_influence = sorted(
        [
            {
                "slice": s["slice"],
                "weight": weights[s["slice"]],
                "confidence": s["confidence"],
                "influence": round(weights[s["slice"]] * s["confidence"], 4),
            }
            for s in slices
        ],
        key=lambda row: row["influence"],
        reverse=True,
    )
    top_influences = [row["slice"] for row in slice_influence[:3]]

    return {
        "runtime": "cognitive-council.local.v0",
        "task_id": task.get("id"),
        "profile": profile_name,
        "decision": base["decision"],
        "requires_confirmation": base["requires_confirmation"],
        "confidence": round(max(0.05, min(0.99, effective_confidence)), 3),
        "flags": base["flags"],
        "weights": weights,
        "top_influences": top_influences,
        "slice_influence": slice_influence,
        "dissent": dissent,
        "slice_outputs": slices,
        "next_action": next_action(base),
    }


def next_action(base: dict[str, Any]) -> dict[str, str]:
    d = base["decision"]
    if d == "confirm_then_send":
        return {"type": "ask_confirmation", "message": "Confirm the exact recipient/content before sending."}
    if d == "ask_clarifying_question":
        return {"type": "ask_user", "message": "Which exact recipient did you mean?"}
    if d == "safety_hold":
        return {"type": "hold", "message": "Pause and verify because urgency/bypass/financial risk was detected."}
    if d == "ask_for_specific_feedback":
        return {"type": "ask_user", "message": "Ask for specific edits instead of looping drafts."}
    if d == "present_tradeoff_plan":
        return {"type": "respond", "message": "Present tradeoffs and a recommendation."}
    return {"type": "respond", "message": "Answer directly."}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", nargs="?", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--profile", default="balanced")
    parser.add_argument("--llm-slice", choices=SLICE_NAMES, help="replace one deterministic slice with a model-backed OpenAI slice")
    parser.add_argument("--model", help="model for --llm-slice; default COUNCIL_MODEL or adapter default")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = executive(load_json(args.fixture), args.profile, llm_slice=args.llm_slice, model=args.model)
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
