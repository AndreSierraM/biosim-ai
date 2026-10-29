# biosim-web

Two-cell adhesion workbench: prompt → Meta AI plan → engine runs →
side-by-side 3D comparison with parameter edit, rerun and bundle export.
Plain Three.js inside React on purpose — small, explicit render loop.

## Run

Needs the API (planner + runs). Without a Meta key, boot the API with the
planner fixture for a fully working UI:

```bash
# terminal 1: API
cd services/api
BIOSIM_PLANNER_FIXTURE=tests/fixtures/acceptance.json \
  .venv/bin/python -m uvicorn app.main:app --port 8123

# terminal 2: web
cd apps/web && npm install && npm run dev   # -> http://localhost:5173
npm run build    # typecheck + production bundle
```

API base override: `VITE_API_URL=http://host:8123 npm run dev`.
