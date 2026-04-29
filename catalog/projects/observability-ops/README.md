# observability-ops

Observability operations project focused on log analysis, SLO compliance reporting, and incident/change signal correlation.

## Agents

1. `log-analyzer-agent`
   - Purpose: analyze log entries for patterns and anomalies.
   - Output: `patterns`, `anomalies`, and `severity`.
2. `slo-reporter-agent`
   - Purpose: generate SLO compliance reports from service metrics and targets.
   - Output: `compliance_status`, `findings`, and `recommended_actions`.
3. `change-correlation-agent`
   - Purpose: map metric/log signal shifts to nearby deploy and config events.
   - Output: `correlated_events`, `incident_signals`, `confidence`, and `summary`.
4. `alert-tuner-agent`
   - Purpose: suggest threshold tuning from noisy alert patterns and miss labels.
   - Output: `tuning_recommendations`, `incident_signals`, `noise_score`, and `rationale`.

## Shared Schema

- `schemas/incident-signal.json` defines a reusable incident signal object for cross-agent and pipeline consumption.

## Local Commands

- Run log analyzer example:
  `python3 scripts/run_agent.py --agent observability-ops.log-analyzer-agent --input catalog/projects/observability-ops/agents/log-analyzer-agent/examples/example-input.json --pretty`
- Run SLO reporter example:
  `python3 scripts/run_agent.py --agent observability-ops.slo-reporter-agent --input catalog/projects/observability-ops/agents/slo-reporter-agent/examples/example-input.json --pretty`
- Run log analyzer in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent observability-ops.log-analyzer-agent --input catalog/projects/observability-ops/agents/log-analyzer-agent/examples/example-input.json --pretty`
- Run SLO reporter in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent observability-ops.slo-reporter-agent --input catalog/projects/observability-ops/agents/slo-reporter-agent/examples/example-input.json --pretty`
- Run change correlation example:
  `python3 scripts/run_agent.py --agent observability-ops.change-correlation-agent --input catalog/projects/observability-ops/agents/change-correlation-agent/examples/example-input.json --pretty`
- Run alert tuner example:
  `python3 scripts/run_agent.py --agent observability-ops.alert-tuner-agent --input catalog/projects/observability-ops/agents/alert-tuner-agent/examples/example-input.json --pretty`
