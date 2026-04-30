# experiment-ops

Experiment operations: register hypotheses with clarity checks, generate bounded experiment plans, and adjudicate observed metrics against stated success criteria.

## Agents

1. **`hypothesis-registration-agent`** — Normalizes a hypothesis statement, assigns a stable id, and flags ambiguities when clarification is needed.
2. **`experiment-plan-agent`** — Produces control/treatment variants, metrics, guardrails, and next steps from a hypothesis (and optional constraints).
3. **`result-adjudication-agent`** — Maps `observed_metrics` plus optional `success_criteria` / `primary_metric` to a bounded verdict and follow-ups.

## Local commands

Deterministic:

```bash
python3 scripts/run_agent.py --agent experiment-ops.hypothesis-registration-agent \
  --input catalog/projects/experiment-ops/agents/hypothesis-registration-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent experiment-ops.experiment-plan-agent \
  --input catalog/projects/experiment-ops/agents/experiment-plan-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent experiment-ops.result-adjudication-agent \
  --input catalog/projects/experiment-ops/agents/result-adjudication-agent/examples/example-input.json --pretty
```

LLM mode:

```bash
AGENT_MODE=llm python3 scripts/run_agent.py --agent experiment-ops.hypothesis-registration-agent \
  --input catalog/projects/experiment-ops/agents/hypothesis-registration-agent/examples/example-input.json --pretty
```

Tests:

```bash
python3 -m unittest tests.test_experiment_ops tests.test_experiment_ops_llm -v
```
