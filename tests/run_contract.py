#!/usr/bin/env python3
"""No-dependency contract runner for Cognitive Council fixtures."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
RUNTIME = ROOT / "run_council.py"


def run_fixture(path: Path) -> dict:
    raw = subprocess.check_output([sys.executable, str(RUNTIME), str(path), "--profile", "balanced"], text=True)
    return json.loads(raw)


def main() -> int:
    failures = []
    for path in sorted(FIXTURES.glob("*.json")):
        fixture = json.loads(path.read_text())
        expected = fixture["expected"]
        result = run_fixture(path)
        flags = set(result["flags"])
        required = set(expected["required_flags"])
        forbidden = set(expected["forbidden_flags"])
        checks = [
            (result["decision"] == expected["decision"], f"decision {result['decision']} != {expected['decision']}"),
            (result["requires_confirmation"] is expected["requires_confirmation"], "confirmation mismatch"),
            (required.issubset(flags), f"missing flags {sorted(required - flags)}"),
            (flags.isdisjoint(forbidden), f"forbidden flags present {sorted(flags & forbidden)}"),
        ]
        bad = [msg for ok, msg in checks if not ok]
        if bad:
            failures.append((path.name, bad, result))
        else:
            print(f"PASS {path.stem}: {result['decision']} flags={','.join(result['flags'])}")
    if failures:
        print("\nFAILURES", file=sys.stderr)
        for name, bad, result in failures:
            print(f"- {name}: {'; '.join(bad)}", file=sys.stderr)
            print(json.dumps(result, indent=2), file=sys.stderr)
        return 1
    print("\nAll contract fixtures passed.")

    print("\nRunning local /runs service contract tests...")
    subprocess.check_call([sys.executable, str(ROOT / "tests" / "test_runs_service.py")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
