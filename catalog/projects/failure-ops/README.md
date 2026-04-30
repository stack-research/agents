# failure-ops

Model incident failure behavior: normalize failure modes, cluster blast patterns, and generate rollback playbooks with safety checks.

## Agents

1. **`failure-library-agent`** — Normalizes incident observations into stable failure mode records with indicators, preconditions, and confidence.
2. **`blast-pattern-cluster-agent`** — Clusters failure modes into blast patterns (`localized|tier|cross-system|global`) with rationale and confidence.
3. **`rollback-playbook-agent`** — Produces ordered rollback playbook steps with prerequisites, abort conditions, verification checks, and escalation triggers.

## Local commands

Deterministic:

```bash
python3 scripts/run_agent.py --agent failure-ops.failure-library-agent \
  --input catalog/projects/failure-ops/agents/failure-library-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent failure-ops.blast-pattern-cluster-agent \
  --input catalog/projects/failure-ops/agents/blast-pattern-cluster-agent/examples/example-input.json --pretty
python3 scripts/run_agent.py --agent failure-ops.rollback-playbook-agent \
  --input catalog/projects/failure-ops/agents/rollback-playbook-agent/examples/example-input.json --pretty
```

LLM mode:

```bash
AGENT_MODE=llm python3 scripts/run_agent.py --agent failure-ops.failure-library-agent \
  --input catalog/projects/failure-ops/agents/failure-library-agent/examples/example-input.json --pretty
```

Tests:

```bash
python3 -m unittest tests.test_failure_ops tests.test_failure_ops_llm -v
```
