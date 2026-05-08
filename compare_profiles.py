#!/usr/bin/env python3
"""Run one fixture through multiple executive weighting profiles."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_council import DEFAULT_FIXTURE, executive, load_json, load_profiles


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", nargs="?", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--profiles", default="balanced,operator,safety,strategist")
    parser.add_argument("--llm-slice")
    parser.add_argument("--model")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    task = load_json(args.fixture)
    known = load_profiles()
    rows = []
    for profile in [p.strip() for p in args.profiles.split(",") if p.strip()]:
        if profile not in known:
            raise SystemExit(f"Unknown profile {profile}; known: {', '.join(sorted(known))}")
        result = executive(task, profile, llm_slice=args.llm_slice, model=args.model)
        rows.append(
            {
                "profile": profile,
                "decision": result["decision"],
                "requires_confirmation": result["requires_confirmation"],
                "confidence": result["confidence"],
                "flags": result["flags"],
                "top_influences": result["top_influences"],
                "next_action": result["next_action"],
                "dissent": result["dissent"],
            }
        )
    print(json.dumps({"fixture": task.get("id"), "comparisons": rows}, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
