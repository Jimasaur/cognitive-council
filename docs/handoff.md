# Handoff: Cognitive Council

## Repo

<https://github.com/Jimasaur/cognitive-council>

## Local path

`/home/jimasaur/.openclaw/workspace-grumpy/projects/cognitive-council`

## What this is

A tiny runtime for modular agentic cognition:

- cognitive slice judgments
- profile-weighted executive synthesis
- approval gates
- receipts
- local `/runs` contract

## What this is not yet

- Not a production service
- Not exposed to the network
- Not a side-effect executor
- Not a replacement for Mercury, Leo, or OpenClaw
- Not a model-orchestration framework yet

## Safe resume commands

Run deterministic contract fixtures:

```bash
python3 tests/run_contract.py
```

Run service/API tests:

```bash
python3 -m unittest tests.test_runs_service tests.test_mock_runtime_contract
```

Run a local API smoke:

```bash
uvicorn server:app --host 127.0.0.1 --port 8765
curl -s http://127.0.0.1:8765/health
```

Create a run:

```bash
curl -s http://127.0.0.1:8765/runs \
  -H 'content-type: application/json' \
  -d '{"fixture":"tests/fixtures/quick_send.json","profile":"operator"}'
```

## Current known-good behavior

- `quick_send` → `confirm_then_send`; approval pending
- `email_ambiguity` → `ask_clarifying_question`
- `adversarial_urgency` → `safety_hold`
- `draft_loop_regression` → `ask_for_specific_feedback`
- `planning_tradeoff` → `present_tradeoff_plan`
- `meta_intelligence_design` → `present_tradeoff_plan`

## Design constraints to preserve

- Deterministic tests are primary.
- Model-backed slices are opt-in.
- Replace only one slice at a time.
- External side effects require approval unless a narrow, tested policy says otherwise.
- Approval and receipt shape should be stable for future Mercury/Leo/OpenClaw callers.
- Receipts should avoid secrets and broad duplication of private payloads.
