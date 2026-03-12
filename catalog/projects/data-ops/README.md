# data-ops

Data operations project focused on schema drift detection and data validation.

## Agents

1. `schema-drift-detector-agent`
   - Purpose: detect and classify schema changes between two schema versions.
   - Output: `changes`, `drift_severity`, and `recommended_actions`.
2. `data-validator-agent`
   - Purpose: validate data records against a set of rules and report violations.
   - Output: `valid_count`, `invalid_count`, `violations`, and `verdict`.

## Local Commands

- Run schema drift detector example:
  `python3 scripts/run_agent.py --agent data-ops.schema-drift-detector-agent --input catalog/projects/data-ops/agents/schema-drift-detector-agent/examples/example-input.json --pretty`
- Run data validator example:
  `python3 scripts/run_agent.py --agent data-ops.data-validator-agent --input catalog/projects/data-ops/agents/data-validator-agent/examples/example-input.json --pretty`
- Run schema drift detector in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent data-ops.schema-drift-detector-agent --input catalog/projects/data-ops/agents/schema-drift-detector-agent/examples/example-input.json --pretty`
- Run data validator in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent data-ops.data-validator-agent --input catalog/projects/data-ops/agents/data-validator-agent/examples/example-input.json --pretty`
