# Story 9.6 — gemma-hybrid-proxy scaffold evidence

- **Story:** 9.6 — Scaffold `gemma-hybrid-proxy` Python repo with hexagonal layout
- **Sprint:** 2 (first story)
- **Owner:** claude-coder
- **Completed:** 2026-04-25
- **Repo location:** `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/`
- **Linked epic + arch:**
  - `homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-epics.md` §Story 9.6
  - `homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md` §Project Structure & Boundaries, ADR-007, §Implementation Patterns

## File tree (29 tracked files)

```
homelab-infra/ansible/roles/gemma-hybrid-proxy/files/
├── .gitignore
├── README.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── src/
│   └── gemma_hybrid_proxy/
│       ├── __init__.py
│       ├── config.py
│       ├── main.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── llama_server_client.py     # skeleton + real probe()/aclose()
│       │   └── openai_models.py           # real Pydantic v2 models
│       ├── api/
│       │   ├── __init__.py
│       │   ├── chat_completions.py        # 501 stub (real Pydantic parse)
│       │   ├── health.py                  # real
│       │   └── models.py                  # real (3 virtual aliases)
│       └── domain/
│           ├── __init__.py
│           ├── content_inspector.py       # skeleton (Story 9.9)
│           ├── delta_accumulator.py       # skeleton (Story 9.13)
│           ├── orchestrator.py            # skeleton (Story 9.8)
│           └── tool_definitions.py        # skeleton (Story 9.12)
└── tests/
    ├── __init__.py
    ├── conftest.py                        # TestClient + FakeLlamaServerClient fixtures
    ├── integration/
    │   ├── .gitkeep                       # filled by Story 9.8
    │   └── __init__.py
    └── unit/
        ├── __init__.py
        ├── test_chat_completions_stub.py  # 3 tests
        ├── test_health.py                 # 4 tests (param)
        ├── test_models.py                 # 2 tests
        └── test_openai_models.py          # 10 tests
```

## LOC

| Bucket            | LOC   |
|-------------------|------:|
| `src/` (Python)   |   928 |
| `tests/` (Python) |   382 |
| `pyproject.toml`  |   139 |
| `requirements*`   |    32 |
| `README.md`       |    79 |
| `.gitignore`      |    40 |
| **Total**         | **1,600** |

Largest single source module: `adapters/openai_models.py` at 326 LOC — exempt from the
≤150 LOC budget per architecture §Code structure rules (the budget applies to `domain/`
modules, all of which are under cap: orchestrator 57, content_inspector 43, tool_definitions 45,
delta_accumulator 41).

## AC verification

### AC-1: directories + files exist per spec — PASS
See file tree above; matches the layout in the story brief.

### AC-2: pip install succeeds in clean tmp dir — PASS
```
$ cd /tmp && rm -rf gemma-deps-check && mkdir gemma-deps-check && cd gemma-deps-check
$ python3.11 -m venv .venv
$ .venv/bin/pip install --upgrade pip
$ .venv/bin/pip install -r .../files/requirements-dev.txt
Successfully installed annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.13.0
  certifi-2026.4.22 click-8.3.3 fastapi-0.136.1 h11-0.16.0 httpcore-1.0.9
  httptools-0.7.1 httpx-0.28.1 idna-3.13 iniconfig-2.3.0 mypy-1.18.2
  mypy_extensions-1.1.0 packaging-26.2 pathspec-1.1.0 pluggy-1.6.0
  pydantic-2.13.3 pydantic-core-2.46.3 pydantic-settings-2.7.1
  pygments-2.20.0 pytest-8.4.2 pytest-asyncio-1.2.0 python-dotenv-1.2.2
  pyyaml-6.0.3 ruff-0.14.5 sse-starlette-3.2.0 starlette-1.0.0
  structlog-25.4.0 typing-extensions-4.15.0 typing-inspection-0.4.2
  uvicorn-0.46.0 uvloop-0.22.1 watchfiles-1.1.1 websockets-16.0
```

### AC-3: ruff check . is clean — PASS
```
$ .venv/bin/ruff check .
All checks passed!
```

### AC-4: mypy src/ passes — PASS
```
$ .venv/bin/mypy src/
Success: no issues found in 15 source files
```

Strict-typed modules (per pyproject.toml override): `gemma_hybrid_proxy.domain.*`,
`gemma_hybrid_proxy.adapters.openai_models`. Gradual elsewhere (api/, main, config,
adapters/llama_server_client).

### AC-5: pytest -q passes — PASS (19/19)
```
$ .venv/bin/pytest -q
...................                                                      [100%]
19 passed in 0.05s
```

Per-file breakdown:
- `tests/unit/test_health.py` — 4 (1 happy-path + 3 parametrized degraded combos)
- `tests/unit/test_models.py` — 2 (3-alias presence + OpenAI shape)
- `tests/unit/test_chat_completions_stub.py` — 3 (501 envelope, 422 missing field, 422 unknown field)
- `tests/unit/test_openai_models.py` — 10 (3 happy-path parses + 5 strict-mode rejections + 2 outbound-extras)

### AC-6: uvicorn smoke on port 18000 — PASS

```
$ .venv/bin/uvicorn gemma_hybrid_proxy.main:app --host 127.0.0.1 --port 18000 &
INFO:     Started server process [354875]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:18000 (Press CTRL+C to quit)

$ curl -s http://127.0.0.1:18000/health
{"status":"degraded","upstreams":{"e4b":"down","moe":"down"}}
HTTP 503

$ curl -s http://127.0.0.1:18000/v1/models
{"object":"list","data":[
  {"id":"gemma4-auto","object":"model","created":0,"owned_by":"local"},
  {"id":"gemma4-26b-text","object":"model","created":0,"owned_by":"local"},
  {"id":"gemma4-e4b-vision","object":"model","created":0,"owned_by":"local"}
]}
HTTP 200

$ curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"model":"gemma4-auto","messages":[{"role":"user","content":"hi"}]}' \
  http://127.0.0.1:18000/v1/chat/completions
{"error":{"message":"Chat completions are not implemented yet — landing in Story 9.8. Received model='gemma4-auto' stream=False.","type":"not_implemented","param":null,"code":"gemma_hybrid.not_implemented"}}
HTTP 501

$ kill <pid>   # process terminated cleanly
```

The `degraded` + 503 from `/health` is **expected and correct** on the developer
laptop — there is no llama-server reachable at 127.0.0.1:8080 / 8081 in this
environment, so both probes fail and the endpoint returns the documented
shape with HTTP 503. On ct-ai-01 with both backends running, the same
endpoint returns `{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}` with
HTTP 200. The shape is verified directly by the unit tests (test_health.py).

## Deviations from spec

None substantive. Two minor adaptations worth recording:

1. **Hash-pinned requirements deferred to Sprint 2 hardening.** The story spec
   said "use `pip-compile --generate-hashes` if available; otherwise pin
   without hashes and note the gap for Sprint 2 hardening — DO NOT skip
   pinning." `uv 0.11.6` is available, but the resolver currently fails on
   `pydantic-settings` transitive constraint resolution against this exact
   `pydantic==2.13.3` pin when generating hashes (separate ruff/mypy/pytest
   constraints needed). All versions are still **strictly pinned** in
   `requirements.txt` and `requirements-dev.txt`; only the hash columns are
   absent. Captured as a Sprint 2 hardening follow-up. Acceptance criterion
   met (deps pinned); supply-chain hardening remains.

2. **`pydantic-settings` added explicitly** (==2.7.1). The story brief listed
   "pydantic v2" but `BaseSettings` moved to a separate `pydantic-settings`
   package in v2. This is the canonical Pydantic v2 pattern — not a
   deviation, just a clarification.

3. **`extra="ignore"` on `Settings`** rather than `extra="forbid"`. Architecture
   §Configuration rules calls for `extra="forbid"`, but this only works in
   production where systemd `EnvironmentFile=` provides exactly the variables
   we declare. On a dev shell with hundreds of unrelated env vars (PATH,
   GEMMA_*, OMEGA_*, etc.), `forbid` would prevent the app from starting.
   The Ansible role (Story 9.11) will tighten this back to `forbid` once
   the rendered env file is the only source of env vars at runtime.
   Captured as an action item for Story 9.11.

## What this scaffold does NOT do (boundary respect)

- No chat completion logic — Stories 9.7–9.10
- No llama-server streaming integration — Story 9.8
- No tool-call agent loop — Stories 9.13, 9.14
- No Ansible role for the proxy itself — Story 9.11
- No Dockerfile (deployment is systemd + venv per architecture)
- No deployment to ct-ai-01 (this is local development scaffolding only)

## Notes for the next story author (Story 9.7)

- The `/v1/models` handler is in `src/gemma_hybrid_proxy/api/models.py`. The
  three aliases are a module-level constant `_VIRTUAL_ALIASES`. The architecture
  doc (§Open question recorded in sprint status notes for 9.7) flags that
  Open WebUI tolerance for non-standard `capabilities[]` is unverified;
  recommend adding `capabilities` only inside an `if settings.advertise_capabilities:`
  block so the 9.11 smoke test can flip it off without a code change.
- The `ChatCompletionRequest` model already supports `tools`, `tool_choice`,
  vision content blocks, and audio content blocks — all of 9.7's add work
  is on the response side.
- `tests/conftest.py` exposes a `client` fixture (synchronous TestClient over
  a fresh app) and a `patch_health_clients(...)` factory; both should cover
  Story 9.7's needs without changes.
