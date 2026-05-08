# Cognitive Council — Continuity

## Name

**Cognitive Council**

Repo slug: `cognitive-council`

Runtime/API component: **Council Runtime**

GitHub repo: <https://github.com/Jimasaur/cognitive-council>

Local path: `/home/jimasaur/.openclaw/workspace-grumpy/projects/cognitive-council`

## One-line description

A modular meta-intelligence runtime where cognitive slice agents produce structured judgments and an executive/ego layer synthesizes them into decisions, approval gates, and receipts.

## Thesis

> Methods are many; mechanisms are few.

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

## Architecture

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

## Current state as of 2026-05-08 closeout

The project is bundled and safe to put down.

Implemented:

- `run_council.py` — deterministic CLI council runner
- `compare_profiles.py` — compare balanced/operator/safety/strategist profiles
- `llm_adapter.py` — optional one-slice OpenAI Responses adapter; not yet exercised in this shell with a real key
- `server.py` — canonical local FastAPI `/runs` API
- `runs_service.py` — filesystem-backed local run service
- `schemas.py` — stdlib validators for request/result/approval/receipt/run record
- `schemas/*.json` — schema-style contract docs
- `tests/run_contract.py` — no-dependency deterministic contract runner
- `tests/test_runs_service.py` — local service and FastAPI contract tests
- `tests/test_mock_runtime_contract.py` — stdlib unittest fixture contract smoke
- `.github/workflows/tests.yml` — GitHub Actions contract/unit/compile checks
- `docs/runtime-api.md` — API docs and future Mercury/Leo integration shape
- `docs/handoff.md` — quick resume guide
- `docs/loose-ends.md` — parked stubs for the next `/new`
- `ROADMAP.md` — small staged roadmap

Canonical `/runs` record includes:

- `run_id`
- `status`
- `request`
- `result`
- `receipt`
- `receipt.approval`

## Tested outcomes

Contract suite passes current fixtures:

- `adversarial_urgency` → `safety_hold`
- `draft_loop_regression` → `ask_for_specific_feedback`
- `email_ambiguity` → `ask_clarifying_question`
- `meta_intelligence_design` → `present_tradeoff_plan`
- `planning_tradeoff` → `present_tradeoff_plan`
- `quick_send` → `confirm_then_send`

FastAPI smoke previously passed:

- `POST /runs` with `quick_send` + `operator`
- Result: `confirm_then_send`
- Approval: required, kind `confirmation`, status `pending`
- Top influences: `action`, `selection`, `compression`
- `GET /runs/{id}` returned stored record

## Design rules to preserve

- Deterministic tests stay primary.
- Model-backed slices are opt-in and should replace only one slice at a time.
- Never let model slice output bypass approval gates.
- Approval/receipt contract wraps the council decision.
- External side effects require explicit approval unless a separate, tested policy grants a narrow exception.
- The first model-backed slice should be `simulation`, then `prediction`, then `explanation`, then `selection`.
- Avoid model-backed `action` until approval/receipt guarantees are mature.
- Keep this prototype loopback/local unless auth, authorization, persistence, audit retention, and rate limits are explicitly designed.

## Resume pointer

For the next fresh session, start with:

1. `docs/handoff.md`
2. `docs/loose-ends.md`
3. `ROADMAP.md`
4. `python3 tests/run_contract.py`
5. `python3 -m unittest tests.test_runs_service tests.test_mock_runtime_contract`
