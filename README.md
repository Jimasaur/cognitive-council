# Cognitive Council

A tiny runtime for modular agentic cognition: slice judgments, executive synthesis, approval gates, and receipts.

## Core idea

**Methods are many; mechanisms are few.**

Cognitive Council explores whether useful agent behavior can be decomposed into a small set of recurring motifs:

1. compression
2. attention
3. prediction
4. simulation
5. selection
6. action
7. explanation
8. update

Each motif is represented as a cognitive slice. The executive layer weighs slice outputs through a profile and returns one structured decision with confidence, flags, top influences, approval state, and a receipt.

## Current status

This repo is a local, deterministic v0 prototype.

It currently includes:

- `run_council.py` — CLI council runner
- `compare_profiles.py` — profile comparison helper
- `server.py` — local FastAPI `/runs` wrapper
- `runs_service.py` — filesystem-backed local run service
- `schemas.py` + `schemas/*.json` — validation and contract docs
- `llm_adapter.py` — optional one-slice OpenAI Responses adapter
- `tests/fixtures/*.json` — deterministic regression fixtures
- `docs/runtime-api.md` — canonical local runtime API contract
- `docs/handoff.md` — quick resume guide
- `docs/loose-ends.md` — parked work for the next session
- `ROADMAP.md` — short forward path
- `CONTINUITY.md` — project continuity notes

By default it makes **no network calls** and uses deterministic local slice logic.

## Install

The core CLI uses only the Python standard library. The local API/tests use FastAPI/TestClient dependencies from `requirements.txt`.

```bash
python3 -m pip install -r requirements.txt
```

## Run the council

Default sample fixture:

```bash
python3 run_council.py --pretty
```

Specific fixture and profile:

```bash
python3 run_council.py tests/fixtures/planning_tradeoff.json --profile strategist --pretty
```

Compare profiles:

```bash
python3 compare_profiles.py tests/fixtures/meta_intelligence_design.json --pretty
```

## Run tests

Deterministic contract fixtures:

```bash
python3 tests/run_contract.py
```

Service/API tests:

```bash
python3 -m unittest tests.test_runs_service tests.test_mock_runtime_contract
```

Compile check:

```bash
python3 -m py_compile run_council.py compare_profiles.py llm_adapter.py runs_service.py schemas.py server.py
```

## Local `/runs` API

Run the local API on loopback only:

```bash
uvicorn server:app --host 127.0.0.1 --port 8765
```

Health check:

```bash
curl -s http://127.0.0.1:8765/health
```

Create a deterministic run from a fixture:

```bash
curl -s http://127.0.0.1:8765/runs \
  -H 'content-type: application/json' \
  -d '{"fixture":"tests/fixtures/quick_send.json","profile":"operator"}'
```

Fetch a run:

```bash
curl -s http://127.0.0.1:8765/runs/<run_id>
```

Runs are stored locally under `.runs/`, which is gitignored.

Canonical run records include:

- `run_id`
- `status`
- `request`
- `result`
- `receipt`
- `receipt.approval`

## Optional model-backed slice

A model-backed slice is opt-in and should replace exactly one slice at a time.

Example, if `OPENAI_API_KEY` is available:

```bash
python3 run_council.py tests/fixtures/meta_intelligence_design.json \
  --profile strategist \
  --llm-slice simulation \
  --pretty
```

Recommended model-backed order:

```text
simulation → prediction → explanation → selection
```

Avoid model-backed `action` until approval and receipt guarantees are much more mature.

## Safety rules

- Deterministic tests stay primary.
- Model-backed slices are opt-in.
- Model output must not bypass approval gates.
- External side effects require explicit approval unless a separate, narrow, tested policy says otherwise.
- This prototype should bind to `127.0.0.1` only.
- Receipts should avoid secrets and broad duplication of private payloads.

## Fixture outcomes

Current deterministic fixtures are expected to resolve as follows:

| Fixture | Decision |
| --- | --- |
| `adversarial_urgency` | `safety_hold` |
| `draft_loop_regression` | `ask_for_specific_feedback` |
| `email_ambiguity` | `ask_clarifying_question` |
| `meta_intelligence_design` | `present_tradeoff_plan` |
| `planning_tradeoff` | `present_tradeoff_plan` |
| `quick_send` | `confirm_then_send` |

## Docs

- [Runtime API](docs/runtime-api.md)
- [Handoff](docs/handoff.md)
- [Loose Ends](docs/loose-ends.md)
- [Roadmap](ROADMAP.md)
- [Continuity](CONTINUITY.md)
