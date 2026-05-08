# Cognitive Council Runtime Scaffold

A tiny local scaffold for a future Cognitive Council Runtime.

The convergence path with the local Agent Runtime Lab is documented in [`docs/runtime-api.md`](docs/runtime-api.md). It sketches `POST /runs`, `GET /runs/{id}`, approval objects, receipts, deterministic vs model-backed slices, and future Mercury/Leo caller patterns.

Current behavior:

- Loads a JSON task fixture.
- Runs deterministic mock slice agents for the eight cognitive slices: compression, attention, prediction, simulation, selection, action, explanation, update.
- Applies profile weights.
- Emits an executive JSON decision.
- Provides a synchronous, file-backed local `/runs` service contract (`runs_service.py`) that creates completed run records and receipts without starting a server.
- Documents and validates run request, run record, council result, and receipt shapes with stdlib validators plus schema-like JSON docs under `schemas/`.
- Makes no network calls by default and uses only the Python standard library.
- Optionally replaces one slice with an OpenAI Responses API call via `--llm-slice`, preserving the same JSON contract.

## Run

```bash
python3 run_council.py --pretty
```

Use a specific fixture and profile:

```bash
python3 run_council.py tests/fixtures/planning_tradeoff.json --profile strategist --pretty
```

Compare profiles:

```bash
python3 compare_profiles.py tests/fixtures/meta_intelligence_design.json --pretty
```

Run one real model-backed slice, if `OPENAI_API_KEY` is available:

```bash
python3 run_council.py tests/fixtures/meta_intelligence_design.json --profile strategist --llm-slice simulation --pretty
```

Built-in / local profiles are `balanced`, `operator`, `safety`, and `strategist`.

Run no-dependency contract tests, including local `/runs` create/get/receipt checks:

```bash
python3 tests/run_contract.py
```

Run only the `/runs` service tests:

```bash
python3 tests/test_runs_service.py
```

## Local API

Install the small API dependencies, then run the service bound to localhost:

```bash
python3 -m pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8765
```

Create a deterministic local run from a fixture:

```bash
curl -s http://127.0.0.1:8765/runs \
  -H 'content-type: application/json' \
  -d '{"fixture":"tests/fixtures/quick_send.json","profile":"balanced"}'
```

Or pass inline task JSON with `task`. Runs are stored as JSON under `.runs/` and can be fetched with `GET /runs/{id}`. No model call is made unless `llm_slice` is explicitly provided.

## Fixture shape

Required keys:

- `id`
- `title`
- `objective`
- `options` with each option containing `id` and `label`

Optional keys:

- `constraints`
- `risk_flags`
- `profiles`

## Local `/runs` contract

`runs_service.LocalRunsService` is the no-network contract target for a future HTTP endpoint:

- `create_run(request)` accepts `{fixture, profile, requested_by?, metadata?}`.
- It runs the deterministic local council synchronously.
- It persists and returns a completed run record with `result` and `receipt`.
- `get_run(run_id)` retrieves and validates the stored record.
- Receipt `approval` objects always have `{required, kind, status, reason, action}`.

## Next obvious extensions

- Move slice agents into separate modules once behavior grows.
- Add schema docs for fixture inputs if the fixture contract expands.
- Replace mock slice agents with real agent adapters only after the contract is stable.
