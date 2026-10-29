# worker

Job execution. Filesystem store + background threads (hackathon
simplification; PostgreSQL/Redis are post-competition in #2).

- `worker/jobs.py` — job store (states: queued → running → completed/failed)
- `worker/engines.py` — engine registry (reference + PhysiCell)
- `worker/runner.py` — `execute(store, job_id)`; records failures, never crashes
- `engines/physicell/` — PhysiCell adapter, model sources and build

## Tests

```bash
python3 services/worker/tests/test_jobs.py
python3 services/worker/tests/test_runner.py
```
