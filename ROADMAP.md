# Cognitive Council Roadmap

This repo is intentionally small. The current goal is not to build a giant framework; it is to preserve a stable, testable contract for modular agentic cognition.

## Current milestone: v0 local runtime

Status: complete enough to put down and resume later.

- Deterministic local council runner
- Eight cognitive slices
- Profile-weighted executive synthesis
- Fixture-driven regression tests
- Local `/runs` FastAPI wrapper
- Approval and receipt objects in the canonical run record
- Optional one-slice model adapter stub through `llm_adapter.py`

## Next milestone: v0.1 packaging and CI

- Keep GitHub Actions running the deterministic contract suite.
- Normalize package layout only when imports become painful.
- Avoid adding dependencies unless they buy a clear test/runtime improvement.

## Next milestone: model-backed slice experiments

Start with exactly one model-backed slice:

1. `simulation`
2. `prediction`
3. `explanation`
4. `selection`

Avoid model-backed `action` until approval and receipt guarantees are mature.

Required guardrail before model-backed slices become more than an experiment:

- A regression fixture proving model output cannot remove or bypass approval requirements for external side effects.

## Next milestone: approval hardening

- Add immutable action receipts.
- Bind approval prompts to a payload hash.
- Make approval status transitions explicit and replay-safe.
- Keep side effects out of this repo until a caller/runtime owns execution safely.

## Next milestone: OpenClaw / Mercury / Leo integration

Likely shape:

- Mercury or Leo submits a local `POST /runs` request.
- Council returns a decision, flags, approval object, and receipt.
- Mercury/Leo remains responsible for user presentation and side-effect execution.
- OpenClaw remains the heavy-duty operator/runtime harness, not the default customer-bot substrate.
