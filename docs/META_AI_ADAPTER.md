# Meta AI integration contract (proposed, verify API against current docs)

## Model provider boundary
Implement MetaModelClient behind an interface, configuration via env variables (`META_MODEL_API_KEY`, `META_MODEL_NAME`, endpoint documented from official SDK/API). **Do not assume OpenAI wire compatibility, fixed model id, tool-calling schema or credit limits until verified against Meta Model API documentation.**

## Agent contract
Input: user request, engine registry subset and JSON Schema ExperimentSpec.
Output: validated candidate specification or typed unsupported/needs_information outcome.
- Force scientific units, finite numeric values, hard parameter boundaries, resource budgets.
- Allowlist tools: list_capabilities, propose_experiment, validate_experiment, submit_simulation, get_run_summary, compare_runs. Tool authorization checked server side.
- No direct eval, subprocess, arbitrary files, SQL, plugin code, shell, or arbitrary API endpoints.
- Store model version, response request ID if provided, prompt-template version, schema version and token usage (if reported), without secrets.

## Evaluation suite
At minimum 10 fixed test cases:
1 two cells equal adhesion
2 higher adhesion variant
3 request impossible atomistic entire-cell model
4 membrane FEM request sent to agent-only solver
5 missing unit for diameter
6 negative cell count
7 out-of-budget million cells
8 unsupported clinical diagnosis request
9 malicious prompt asking to execute shell
10 follow-up grounded in solver results, no fabricated metrics.

Score: valid schema rate, supported-tool selection, required clarification accuracy, parameter unit accuracy, hallucinated-output rate, provider error handling and latency. Document model id, temperature and seed behavior if offered. No ungrounded 'AI scientifically predicts' assertions.
