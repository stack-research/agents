# observability-ops

Observability operations project focused on log analysis and SLO compliance reporting.

## Agents

1. `log-analyzer-agent`
   - Purpose: analyze log entries for patterns and anomalies.
   - Output: `patterns`, `anomalies`, and `severity`.
2. `slo-reporter-agent`
   - Purpose: generate SLO compliance reports from service metrics and targets.
   - Output: `compliance_status`, `findings`, and `recommended_actions`.

## Local Commands

- Run log analyzer example:
  `python3 scripts/run_agent.py --agent observability-ops.log-analyzer-agent --input catalog/projects/observability-ops/agents/log-analyzer-agent/examples/example-input.json --pretty`
- Run SLO reporter example:
  `python3 scripts/run_agent.py --agent observability-ops.slo-reporter-agent --input catalog/projects/observability-ops/agents/slo-reporter-agent/examples/example-input.json --pretty`
- Run log analyzer in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent observability-ops.log-analyzer-agent --input catalog/projects/observability-ops/agents/log-analyzer-agent/examples/example-input.json --pretty`
- Run SLO reporter in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent observability-ops.slo-reporter-agent --input catalog/projects/observability-ops/agents/slo-reporter-agent/examples/example-input.json --pretty`
