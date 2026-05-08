# Loose Ends / Resume Stubs

This is the parking lot for the next `/new` session. It is intentionally concrete.

## 1. Agent Memory write route

Status: unresolved.

What happened:

- Grumpy's secret file exists at `/home/jimasaur/.openclaw-grumpy/secrets/agent-memory.env`.
- It now contains both legacy `GRUMPY_MEMORY_TOKEN` and expected `AGENT_MEMORY_TOKEN` aliases.
- Permissions are `600`.
- Grumpy gateway was reloaded after the alias was added.
- Direct guessed HTTP write routes did not accept writes:
  - `/memories`
  - `/memory`
  - `/api/memories`
  - `/api/memory`

Next step:

- Discover the actual Agent Memory API route/helper instead of guessing.
- Search the local Agent Memory service/repo or inspect the running service on `AGENT_MEMORY_BASE_URL`.
- Do not print or commit the token.

## 2. Grumpy ↔ Skippy coordination

Status: foundations exist, not fully exercised.

Observed OpenClaw config on Grumpy:

- `tools.sessions.visibility = "all"`
- `tools.agentToAgent.enabled = true`
- `tools.agentToAgent.allow = ["main"]`

Current understanding:

- OpenClaw has session-to-session A2A behavior through `sessions_send` when sessions are visible and allowed.
- A first-class `agent_to_agent` tool was not exposed in Grumpy's current tool list.
- Treat this as privileged, audited local coordination — not a cryptographically secret channel.

Next step:

- Identify Skippy's visible session/agent target.
- Send a tiny safe ping through `sessions_send` only after confirming routing.
- Record the working pattern in local memory and, once fixed, Agent Memory.

## 3. Cognitive Council model-backed slice

Status: adapter exists, not exercised with a real key in this shell.

Files:

- `llm_adapter.py`
- `run_council.py --llm-slice <slice>`

Next step:

- Prefer an OpenClaw-backed adapter or explicitly sourced provider key.
- Run exactly one model-backed slice first: `simulation`.
- Compare deterministic vs model-backed receipts for:
  - `tests/fixtures/meta_intelligence_design.json`
  - `tests/fixtures/quick_send.json`
- Add a regression proving model noise cannot bypass approval gates.

## 4. Voice agent hardening backlog

Status: separate project, not part of this repo.

Local path:

- `/home/jimasaur/.openclaw/workspace-grumpy/projects/voice-agent-poc`

Important next hardening ideas:

- Immutable action receipts
- Payload hash-binding for approval prompts
- Audit dashboard for sent email/calendar changes
- Rate limiting on `/session`, `/tools/*`, and `/auth/*`
- Session idle and absolute timeout controls
- Encrypted token storage or AWS Secrets Manager/KMS for per-user Microsoft token caches

## 5. Repo hygiene

Status: good enough for initial handoff.

Done:

- `.gitignore` excludes `.runs/`, pycache, env/secrets, logs, and editor files.
- Tests are dependency-light and use stdlib `unittest` where possible.
- GitHub Actions workflow exists for contract tests.

Optional later:

- Convert to a package under `src/cognitive_council/` if imports grow.
- Add type checking only if it remains low-friction.
- Add a changelog once commits become more frequent.
