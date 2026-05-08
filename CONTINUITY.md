# Cognitive Council — Continuity

## Working Name

**Cognitive Council**

Repo-friendly slug: `cognitive-council`

Runtime/API component: **Council Runtime**

## One-line Description

A modular meta-intelligence runtime where cognitive slice agents produce structured judgments and an executive/ego layer synthesizes them into decisions, approval gates, and receipts.

## Core Thesis

Methods are many; mechanisms are few.

Intelligent behavior can be usefully decomposed into recurring computational motifs:

1. Compression
2. Attention
3. Prediction
4. Simulation
5. Selection
6. Action
7. Explanation
8. Update

Different substrates can implement these motifs differently — biological cognition, LLMs, tool-using agents, teams — but the loop keeps reappearing.

## Architecture Shape

```text
Task / Context
  ↓
Cognitive slices
  - compression
  - attention
  - prediction
  - simulation
  - selection
  - action
  - explanation
  - update
  ↓
Executive / Ego synthesizer
  ↓
Decision + confidence + dissent + top influences
  ↓
Approval object when needed
  ↓
Receipt / run record
```

## Current Local Path

`/home/jimasaur/.openclaw/workspace-grumpy/projects/cognitive-council`

## Current State as of 2026-05-08

Implemented local deterministic prototype:

- `run_council.py` — CLI council runner
- `compare_profiles.py` — compare balanced/operator/safety/strategist profiles
- `llm_adapter.py` — optional one-slice OpenAI Responses adapter; not yet run locally because shell lacked `OPENAI_API_KEY`
- `server.py` — local FastAPI `/runs` API
- `runs_service.py` — filesystem-backed local run service
- `schemas.py` — stdlib validators for request/result/approval/receipt/run record
- `tests/run_contract.py` — no-dependency contract runner
- `tests/test_runs_service.py` — local service and FastAPI contract tests
- `docs/runtime-api.md` — API docs and future Mercury/Leo integration shape

The canonical `/runs` record now includes:

- `run_id`
- `status`
- `request`
- `result`
- `receipt`
- `receipt.approval`

## Tested Outcomes

Contract suite passes current fixtures:

- `adversarial_urgency` → `safety_hold`
- `draft_loop_regression` → `ask_for_specific_feedback`
- `email_ambiguity` → `ask_clarifying_question`
- `meta_intelligence_design` → `present_tradeoff_plan`
- `planning_tradeoff` → `present_tradeoff_plan`
- `quick_send` → `confirm_then_send`

FastAPI smoke test passed:

- `POST /runs` with `quick_send` + `operator`
- Result: `confirm_then_send`
- Approval: required, kind `confirmation`, status `pending`
- Top influences: `action`, `selection`, `compression`
- `GET /runs/{id}` returned stored record

## Key Design Rules

- Deterministic tests stay primary.
- Model-backed slices are opt-in and should replace only one slice at a time.
- Never let model slice output bypass approval gates.
- Approval/receipt contract wraps the council decision.
- External side effects require explicit approval unless a separate, tested policy grants a narrow exception.
- The first model-backed slice should be `simulation`, then `prediction`, then `explanation`, then `selection`.
- Avoid model-backed `action` until approval/receipt guarantees are mature.

## Repo Seed Recommendation

Suggested GitHub repo name:

`cognitive-council`

Suggested short README tagline:

> A tiny runtime for modular agentic cognition: slice judgments, executive synthesis, approval gates, and receipts.

## Next Step

After repo creation, copy this project into the repo, then:

1. Normalize package layout.
2. Add CI for `python3 tests/run_contract.py`.
3. Wire a model-backed `simulation` slice through OpenClaw runtime or an explicit provider adapter.
4. Compare deterministic vs model-backed slice outputs in receipts.
5. Add a fixture proving model-backed slice noise cannot alter approval requirements for external actions.
