# OpsPilot local integration

## Ports and environment

| Process | Bind / URL | Relevant environment |
|---|---|---|
| Demo `web` | `127.0.0.1:5001` | No API keys; chaos control is loopback-only |
| Demo `api` | `127.0.0.1:5002` | No API keys; chaos control is loopback-only |
| Demo `worker` | `127.0.0.1:5003` | No API keys; chaos control is loopback-only |
| FastAPI backend | `127.0.0.1:5000` | `DATABASE_URL`, `ALLOWED_ORIGINS`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`, provider key, `CHAOS_ENABLED`, `ZERO_TOUCH_DEFAULT`, `AUTH_ENABLED`, `API_KEY`, `MONITOR_ENABLED` |
| Vite frontend | `http://localhost:3000` | `VITE_API_BASE_URL=http://localhost:5000` (blank selects mock mode) |

Copy `.env.example` to `.env` to configure the backend. Provider keys belong only in the backend environment. The API key, if enabled, must not be placed in Vite variables because those are public in the browser bundle.

## Start order

From the repository root, run `./scripts/dev` on macOS/Linux or `.\scripts\dev.ps1` in PowerShell. The launcher starts the three loopback demo services, then Uvicorn, then Vite, and stops its launchers when interrupted. `CHAOS_ENABLED=true` is scoped to this local-development backend process; do not use the launcher or this setting on a public interface. Logs are written under `.dev-logs/`.

To start each process manually:

1. `python -m backend.demo_services.launcher`
2. `CHAOS_ENABLED=true uvicorn backend.main:app --host 127.0.0.1 --port 5000 --reload`
3. `npm run dev -- --host 127.0.0.1`

Wait for `/health` before using the UI. To exercise a self-healing CRASH in the integration test, set `zeroTouchEnabled` through the backend settings endpoint (the test does this temporarily) and keep the local demo supervisor running. After a target crashes, the supervisor waits 2.5 seconds before restarting that service so the monitor can observe and record the outage.

## Integration verification

With the stack running, execute:

```sh
.venv/bin/python scripts/integration_check.py
```

On Windows, use `.venv\Scripts\python.exe scripts\integration_check.py`. The test performs a real local CRASH against `api:5002`, so it must only be run against this allow-listed demo stack. It adds and deletes a temporary non-demo endpoint, temporarily enables zero-touch mode and restores settings, and deliberately retains the resulting incident as an integration record. For API-key authentication, supply `--api-key` (the value is never printed). `--failure-modes-only` runs backend-down, wrong-key, CORS, and SSE disconnect checks without injecting chaos.

The runner generates JSON Schema from backend Pydantic response models, validates response key shapes/values, and compares corresponding TypeScript interface field names. The pytest suite additionally exercises deterministic LLM failure and timeout handling with fake providers and no external network.

## API curl examples

Set shell variables first:

```sh
BASE=http://127.0.0.1:5000
# For AUTH_ENABLED=true, set KEY to the backend API key and append -H "X-API-Key: $KEY".
```

| Endpoint | Example |
|---|---|
| `GET /health` | `curl "$BASE/health"` |
| `GET /api/probe` | `curl -G "$BASE/api/probe" --data-urlencode 'url=http://127.0.0.1:5001/healthz'` |
| `POST /api/chaos/inject` | `curl -X POST "$BASE/api/chaos/inject" -H 'Content-Type: application/json' -d '{"service":"api","port":5002,"type":"CRASH"}'` |
| `POST /api/remediate` | `curl -X POST "$BASE/api/remediate" -H 'Content-Type: application/json' -d '{"service":"api","action":"restart"}'` |
| `POST /api/emergency/intake` | `curl -X POST "$BASE/api/emergency/intake" -H 'Content-Type: application/json' -d '{"incidentType":"service outage","location":"demo cluster","priority":"YELLOW","reportedBy":"operator","description":"API requests are failing"}'` |
| `POST /api/emergency/{caseId}/evidence` | `curl -X POST "$BASE/api/emergency/EMG-1234/evidence" -F 'file=@evidence.png;type=image/png'` |
| `POST /api/analyze` | `curl -X POST "$BASE/api/analyze" -H 'Content-Type: application/json' -d '{"metrics":{"service":"api","anomaly_type":"CRASH"},"logs":["connection refused"]}'` |
| Legacy `POST /analyze` | `curl -X POST "$BASE/analyze" -H 'Content-Type: application/json' -d '{"metrics":{"service":"api"},"logs":[]}'` |
| `GET /api/services/health` | `curl "$BASE/api/services/health"` |
| `GET /api/incidents` | `curl "$BASE/api/incidents?limit=50&offset=0"` |
| `GET /api/incidents/{id}` | `curl "$BASE/api/incidents/INC-105"` |
| `GET /api/incidents/export.md` | `curl "$BASE/api/incidents/export.md"` |
| `GET /api/kpis` | `curl "$BASE/api/kpis"` |
| `GET /api/endpoints` | `curl "$BASE/api/endpoints"` |
| `POST /api/endpoints` | `curl -X POST "$BASE/api/endpoints" -H 'Content-Type: application/json' -d '{"name":"sample","url":"http://127.0.0.1:5001/healthz","serviceKey":"sample","port":5001,"probeIntervalSeconds":2}'` |
| `PATCH /api/endpoints/{id}` | `curl -X PATCH "$BASE/api/endpoints/4" -H 'Content-Type: application/json' -d '{"probeIntervalSeconds":5,"enabled":true}'` |
| `DELETE /api/endpoints/{id}` | `curl -X DELETE "$BASE/api/endpoints/4"` |
| `GET /api/settings` | `curl "$BASE/api/settings"` |
| `PUT /api/settings` | `curl -X PUT "$BASE/api/settings" -H 'Content-Type: application/json' -d '{"llmProvider":"openai","p99LatencySlaMs":1500,"webhookUrl":null,"zeroTouchEnabled":false,"operatorName":"Local operator"}'` |
| `GET /api/stream/events` | `curl -N "$BASE/api/stream/events"` |
| `GET /api/db/tables` | `curl "$BASE/api/db/tables"` |
| `GET /api/db/tables/{name}` | `curl -G "$BASE/api/db/tables/incidents" --data-urlencode 'limit=50' --data-urlencode 'offset=0' --data-urlencode 'q=api'` |
| `GET /api/db/schema` | `curl "$BASE/api/db/schema"` |
| `GET /api/db/export` | `curl "$BASE/api/db/export"` |

Evidence retrieval, when configured with an authenticated API key, is `GET /api/emergency/{caseId}/evidence`; the response is an attachment and requires the same `X-API-Key` header.

## Failure-mode results and checks

| Failure mode | Expected behavior | Verification |
|---|---|---|
| Backend down | Frontend remains usable in simulated mode; API client reports a network error | The integration runner checks a connection-refused backend address; browser fallback remains a UI behavior rather than a headless HTTP assertion |
| Wrong API key | `401 UNAUTHORIZED` with the standard error shape when auth is enabled | `--failure-modes-only`; this check is reported as skipped if auth is disabled |
| LLM key missing | Rule-based action is used, and the self-healing path is independent of LLM success | Run the full integration runner with the selected provider key absent. It reports whether an LLM fallback log was observed |
| LLM timeout | Deterministic diagnosis fallback; the pipeline remains available | Covered with fake-provider timeout tests in `tests/test_pytest_pipeline_llm.py` and `tests/test_llm_service.py` |
| Disallowed CORS origin | No `Access-Control-Allow-Origin` is returned to the disallowed origin | `--failure-modes-only` checks allowed and denied preflight requests |
| SSE disconnect | Stream closes cleanly and can reconnect | `--failure-modes-only` closes an SSE response and opens a second stream |

## Troubleshooting

| Symptom | Check / remedy |
|---|---|
| CORS error in browser | Ensure the frontend origin (normally `http://localhost:3000`) is an exact entry in backend `ALLOWED_ORIGINS`; restart the backend after changing it |
| Wrong API base URL | Set frontend `VITE_API_BASE_URL=http://localhost:5000`; restart Vite after editing its environment |
| `502 LLM_UNAVAILABLE` / `LLM_AUTH_FAILED` | Confirm `LLM_PROVIDER`, backend-only provider key, quota, and provider configuration. Incident remediation still uses the deterministic fallback |
| `504 LLM_TIMEOUT` | Check provider latency and `LLM_TIMEOUT_SECONDS`; timeout should not delay the independent deterministic fix path |
| Port conflict | Free ports `3000` and `5000`-`5003`; check `.opspilot-demo-pids.json` and process ownership before stopping anything |
| `CHAOS_DISABLED` | Use only the local dev launcher or set `CHAOS_ENABLED=true` in a trusted local backend process; never expose chaos control publicly |
| CRASH target does not recover | Ensure the demo launcher is running and owns the api process so it can restart it; confirm `api:5002` is registered and zero-touch is enabled for the automatic path |

## Frontend README contract notes

The implementation preserves the core dashboard and mock-mode contracts, but several README descriptions are illustrative rather than guaranteed by the real backend:

* The README's exact sample incidents and benchmark numbers are mock/demo content. Backend KPIs are calculated from persisted timestamps and can differ or show `n/a` when data is absent.
* Arbitrary external endpoints are subject to backend SSRF protections; loopback/private targets are rejected unless registered as allowed demo targets. The frontend does not guarantee that every host/port is probeable.
* Evidence upload stores and reports evidence through the authenticated backend route; the browser UI currently previews the selected image before submission but does not retrieve/display the stored image after upload.
* The LLM is configurable from backend provider settings and environment keys; model display names in the README are not hard-coded promises. Missing credentials or provider errors produce fallback diagnosis rather than blocking remediation.
* Starting the app with no `VITE_API_BASE_URL` intentionally selects mock simulation, not live backend telemetry. The old README's Streamlit/Flask descriptions refer to the project concept/history; the current backend is FastAPI with three FastAPI demo targets.
