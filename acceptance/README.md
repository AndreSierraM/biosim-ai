# Acceptance pipeline

Executable contract for `features/*/spec.md` (ATDD). Each handler in
`scenarios.py` maps 1:1 to a spec scenario and drives the system through
its HTTP boundary only.

```bash
./run-acceptance-tests.sh            # full suite, reference engine
./run-acceptance-tests.sh 001        # only the 001 spec
BIOSIM_ACCEPT_ENGINE=physicell ./run-acceptance-tests.sh 001
```

The runner boots its own API on :8123 with a throwaway runs directory,
so scenarios never touch dev state. UI visibility ("seen together")
is covered by the demo recording, not by these handlers.
