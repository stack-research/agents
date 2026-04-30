# cost-ops

Estimate and control pipeline spend using payload metrics: attribute token/runtime cost, enforce budget guardrails, and recommend safe optimization actions.

## Agents

1. **`cost-attribution-agent`** — Computes stage and total spend from observed metrics with optional fallback price tables.
2. **`budget-guardrail-agent`** — Evaluates attributed spend against run/stage/daily limits and emits guardrail status.
3. **`pipeline-optimizer-agent`** — Produces bounded optimization suggestions ranked by estimated savings and risk.

## Local commands

Deterministic:

```bash
python3 scripts/run_agent.py --agent cost-ops.cost-attribution-agent \
  --input catalog/projects/cost-ops/agents/cost-attribution-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent cost-ops.budget-guardrail-agent \
  --input catalog/projects/cost-ops/agents/budget-guardrail-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent cost-ops.pipeline-optimizer-agent \
  --input catalog/projects/cost-ops/agents/pipeline-optimizer-agent/examples/example-input.json --pretty
```

LLM mode:

```bash
AGENT_MODE=llm python3 scripts/run_agent.py --agent cost-ops.cost-attribution-agent \
  --input catalog/projects/cost-ops/agents/cost-attribution-agent/examples/example-input.json --pretty
```

Tests:

```bash
python3 -m unittest tests.test_cost_ops tests.test_cost_ops_llm -v
```
