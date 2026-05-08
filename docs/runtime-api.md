# Cognitive Council × Agent Runtime API

This document sketches the convergence path between the Cognitive Council scaffold and the local Agent Runtime Lab.

The Council currently runs as a local Python CLI: it loads a task fixture, evaluates eight cognitive slices, applies a profile, and returns one executive decision JSON object. The Runtime API shape below wraps that contract in a tiny local job interface so other local agents can submit work, inspect status, handle approvals, and keep receipts without turning the Council into an always-online service.

This is a design contract, not a deployed service. Do not expose it to the network until authentication, authorization, persistence, audit retention, and rate limits are explicitly designed.

## Goals

- Keep Cognitive Council's slice decision contract stable.
- Let Agent Runtime Lab own run lifecycle, approval gates, and receipts.
- Support deterministic no-network runs by default.
- Allow explicitly requested model-backed slices later without changing callers.
- Give future local agents such as Mercury and Leo a simple interface to call.

## Base URL

For local prototypes only:

```text
http://127.0.0.1:8765
```

Bind to loopback only. Do not bind `0.0.0.0` for this prototype.

## Current implementation note

`server.py` exposes the canonical local FastAPI wrapper with `POST /runs` and `GET /runs/{id}`. It returns and stores a full run record under `.runs/`: request, council result, approval object, and receipt. The service uses deterministic slices by default; a model-backed slice only runs when explicitly requested with `llmSlice`.

## POST /runs

Create a new Council run.

### Request

```json
{
  "task": {
    "id": "quick-send-001",
    "title": "Check whether a message should be sent",
    "user_message": "Send this to Sam: I can meet at 3pm.",
    "context": {
      "channel": "email",
      "external_side_effect": true,
      "known_contacts": ["Sam Rivera"]
    }
  },
  "profile": "balanced",
  "mode": "deterministic",
  "model_backed_slice": null,
  "caller": {
    "agent": "mercury",
    "purpose": "pre-send safety check"
  },
  "idempotency_key": "mercury-quick-send-001-v1"
}
```

### Fields

- `task` is the same fixture-like object used by `run_council.py`.
- `profile` is one of `balanced`, `operator`, `safety`, `strategist`, or another local profile file.
- `mode` is either `deterministic` or `model_backed`.
- `model_backed_slice` is `null` for deterministic mode, or exactly one slice name when model-backed mode is explicitly enabled.
- `caller` records which local agent requested the run and why.
- `idempotency_key` prevents duplicate work when a caller retries.

### Response: completed deterministic run

```json
{
  "run_id": "run_...",
  "status": "completed",
  "created_at": "2026-05-08T21:05:00Z",
  "updated_at": "2026-05-08T21:05:01Z",
  "mode": "deterministic",
  "profile": "balanced",
  "result": {
    "runtime": "cognitive-council.local.v0",
    "task_id": "quick-send-001",
    "decision": "confirm_then_send",
    "requires_confirmation": true,
    "confidence": 0.82,
    "flags": ["body_explicit", "external_send", "recipient_explicit"],
    "next_action": {
      "type": "ask_confirmation",
      "message": "Confirm the exact recipient/content before sending."
    }
  },
  "approval": {
    "required": true,
    "approval_id": "appr_run_20260508_210500_7f3a_send",
    "reason": "External side effect requires user confirmation before send.",
    "action": {
      "type": "external_send",
      "channel": "email",
      "recipient_status": "explicit",
      "body_status": "explicit"
    },
    "status": "pending"
  },
  "receipt": {
    "receipt_id": "receipt_run_...",
    "run_id": "run_...",
    "status": "completed",
    "decision": "confirm_then_send",
    "requires_confirmation": true,
    "approval": { "required": true, "kind": "confirmation", "status": "pending" },
    "result_summary": { "confidence": 0.85, "flags": ["external_send"], "top_influences": ["action"] }
  }
}
```

## GET /runs/{id}

Fetch the latest run state.

### Response: pending approval

```json
{
  "run_id": "run_20260508_210500_7f3a",
  "status": "waiting_for_approval",
  "created_at": "2026-05-08T21:05:00Z",
  "updated_at": "2026-05-08T21:05:01Z",
  "decision": {
    "decision": "confirm_then_send",
    "requires_confirmation": true,
    "flags": ["external_send", "recipient_explicit", "body_explicit"]
  },
  "approval": {
    "required": true,
    "approval_id": "appr_run_20260508_210500_7f3a_send",
    "status": "pending",
    "expires_at": "2026-05-08T22:05:00Z"
  },
  "receipt": {
    "receipt_id": "rcpt_run_20260508_210500_7f3a",
    "path": "logs/receipts/2026-05-08/run_20260508_210500_7f3a.json"
  }
}
```

### Response: completed without approval

```json
{
  "run_id": "run_20260508_211000_a91c",
  "status": "completed",
  "decision": {
    "decision": "present_tradeoff_plan",
    "requires_confirmation": false,
    "flags": ["planning_required", "recommendation_needed", "tradeoff_detected"]
  },
  "approval": {
    "required": false,
    "status": "not_required"
  },
  "receipt": {
    "receipt_id": "rcpt_run_20260508_211000_a91c",
    "path": "logs/receipts/2026-05-08/run_20260508_211000_a91c.json"
  }
}
```

## Approval objects

Approvals are runtime-level gates around side effects, not Council decisions by themselves. The Council says whether confirmation is required; Agent Runtime decides how to pause, present, resume, or cancel the run.

Suggested approval shape:

```json
{
  "required": true,
  "approval_id": "appr_run_...",
  "status": "pending",
  "reason": "External side effect requires user confirmation before send.",
  "requested_at": "2026-05-08T21:05:01Z",
  "expires_at": "2026-05-08T22:05:01Z",
  "action": {
    "type": "external_send",
    "summary": "Send drafted email to Sam Rivera",
    "risk_flags": ["external_send"]
  }
}
```

Allowed `status` values:

- `not_required`
- `pending`
- `approved`
- `denied`
- `expired`
- `cancelled`

Local-only prototype rule: a pending approval never executes the side effect. It only returns a structured pause state and writes a receipt.

## Receipts

Every run should write a local receipt before returning success.

Minimum receipt fields:

```json
{
  "receipt_id": "rcpt_run_...",
  "run_id": "run_...",
  "created_at": "2026-05-08T21:05:01Z",
  "caller": {"agent": "mercury", "purpose": "pre-send safety check"},
  "mode": "deterministic",
  "profile": "balanced",
  "task_id": "quick-send-001",
  "decision": "confirm_then_send",
  "requires_confirmation": true,
  "flags": ["external_send", "recipient_explicit", "body_explicit"],
  "approval_id": "appr_run_...",
  "approval_status": "pending",
  "slice_output_count": 8,
  "model_backed_slice": null
}
```

Receipts should stay local, avoid secrets, and prefer pointers over sensitive payloads. If task content includes private user data, store a minimized summary plus a local path pointer rather than duplicating the full content into broad logs.

## Deterministic vs model-backed slices

### Deterministic mode

- Default mode.
- Uses only local rule-based slice functions.
- No network calls.
- Best for contract tests, safety gates, CI, and local smoke checks.
- Equivalent to running:

```bash
python3 run_council.py tests/fixtures/quick_send.json --profile balanced --pretty
```

### Model-backed mode

- Opt-in only.
- Replaces exactly one slice with a model adapter while preserving the slice JSON contract.
- Requires an API key in the environment when using the current OpenAI adapter.
- Should be disabled in local-only Runtime API tests.
- Equivalent to running:

```bash
python3 run_council.py tests/fixtures/meta_intelligence_design.json \
  --profile strategist \
  --llm-slice simulation \
  --pretty
```

Runtime request example:

```json
{
  "task": {"id": "design-001", "title": "Design review", "objective": "Compare architecture options", "options": []},
  "profile": "strategist",
  "mode": "model_backed",
  "model_backed_slice": "simulation",
  "caller": {"agent": "leo", "purpose": "architecture tradeoff review"}
}
```

The Runtime should reject `mode: "model_backed"` unless the operator has explicitly enabled network/model access for that session.

## Curl examples

Start the current local API:

```bash
python3 -m pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8765
```

Create a deterministic run with the current v0 server shape:

```bash
curl -sS http://127.0.0.1:8765/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "task": {
      "id": "quick-send-001",
      "title": "Quick send check",
      "user_message": "Send this to Sam: I can meet at 3pm.",
      "context": {
        "channel": "email",
        "external_side_effect": true,
        "known_contacts": ["Sam Rivera"]
      }
    },
    "profile": "balanced"
  }'
```

Create a deterministic run from a fixture:

```bash
curl -sS http://127.0.0.1:8765/runs \
  -H 'Content-Type: application/json' \
  -d '{"fixture":"tests/fixtures/quick_send.json","profile":"balanced"}'
```

Fetch a run by the returned `id`:

```bash
curl -sS http://127.0.0.1:8765/runs/00000000-0000-0000-0000-000000000000
```

Submit a model-backed request only after explicit local enablement and with `OPENAI_API_KEY` available:

```bash
curl -sS http://127.0.0.1:8765/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "fixture": "tests/fixtures/meta_intelligence_design.json",
    "profile": "strategist",
    "llm_slice": "simulation"
  }'
```

Future Agent Runtime callers can wrap the same request with `mode`, `caller`, and `idempotency_key`; those fields are target-contract fields and should be added to `server.py` before callers depend on them.

## How Mercury and Leo could call it later

Mercury, as an operator-style agent, could call `POST /runs` before any outbound message, file write outside the workspace, or other user-visible side effect. It would use deterministic mode for fast safety gating, then inspect `approval.required` before proceeding.

Leo, as a design/review agent, could call `POST /runs` for planning and architecture tradeoffs. It would usually use the `strategist` profile and deterministic mode first. If explicitly allowed, Leo could request one model-backed slice such as `simulation` for richer scenario review while still receiving the same executive decision shape.

Both agents should treat Council output as advisory until Runtime approval state is resolved. A `decision` of `confirm_then_send` is not permission to send; only an approved Runtime approval object can unblock the caller.

## Local-only safety notes

- Bind to `127.0.0.1` only.
- Default to deterministic mode and no network.
- Do not execute external side effects from `POST /runs`.
- Never store API keys, tokens, full email bodies, or secret payloads in receipts.
- Require explicit user/operator enablement for model-backed slices.
- Allow at most one model-backed slice per run while the contract is still experimental.
- Prefer idempotency keys for callers that may retry.
- Keep approval state separate from Council slice votes.
- Run contract tests before changing response shapes:

```bash
python3 tests/run_contract.py
```
