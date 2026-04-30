# inter-ops

Validate producer and consumer schema contracts from payload snapshots to detect compatibility risks before integration.

## Agents

1. **`schema-compat-validator-agent`** — Compares producer and consumer schema objects, classifies compatibility, and emits bounded migration actions.

## Local commands

Deterministic:

```bash
python3 scripts/run_agent.py --agent inter-ops.schema-compat-validator-agent \
  --input catalog/projects/inter-ops/agents/schema-compat-validator-agent/examples/example-input.json --pretty
```

LLM mode:

```bash
AGENT_MODE=llm python3 scripts/run_agent.py --agent inter-ops.schema-compat-validator-agent \
  --input catalog/projects/inter-ops/agents/schema-compat-validator-agent/examples/example-input.json --pretty
```

Tests:

```bash
python3 -m unittest tests.test_inter_ops tests.test_inter_ops_llm -v
```
