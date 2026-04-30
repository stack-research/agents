# eval-ops

Evaluation operations: curate benchmark suites, score regressions between eval runs, and report quality drift over time windows.

## Agents

1. **`benchmark-curator-agent`** — Deduplicates candidate eval cases, surfaces coverage gaps, and assigns a curation verdict.
2. **`regression-score-agent`** — Compares baseline vs current metric scores with configurable sensitivity.
3. **`quality-drift-reporter-agent`** — Interprets ordered metric windows for trend and drift severity.

## Local commands

Deterministic:

```bash
python3 scripts/run_agent.py --agent eval-ops.benchmark-curator-agent \
  --input catalog/projects/eval-ops/agents/benchmark-curator-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent eval-ops.regression-score-agent \
  --input catalog/projects/eval-ops/agents/regression-score-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent eval-ops.quality-drift-reporter-agent \
  --input catalog/projects/eval-ops/agents/quality-drift-reporter-agent/examples/example-input.json --pretty
```

LLM mode:

```bash
AGENT_MODE=llm python3 scripts/run_agent.py --agent eval-ops.benchmark-curator-agent \
  --input catalog/projects/eval-ops/agents/benchmark-curator-agent/examples/example-input.json --pretty
```

Tests:

```bash
python3 -m unittest tests.test_eval_ops tests.test_eval_ops_llm -v
```
