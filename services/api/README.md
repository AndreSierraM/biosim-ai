# biosim-api

FastAPI service: `/health`, `POST /v1/specs/validate` against
`packages/experiment-schema`, run/job endpoints (`/v1/runs`, `/v1/engines`),
and constrained planning (`POST /v1/plan`).

## Run

```bash
cd services/api
uv venv .venv
uv pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --port 8123
```

## Try

```bash
curl localhost:8123/health
curl -X POST localhost:8123/v1/specs/validate \
  -H 'content-type: application/json' -d '{}'  # -> valid:false with errors
```
