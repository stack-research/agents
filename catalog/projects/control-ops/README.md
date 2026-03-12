# control-ops

Operational control agents for governance, lineage, blast radius assessment, and kill path auditing of autonomous systems.

## Agents

1. `lineage-recorder-agent`
   - Purpose: structure decision events into append-only lineage records for auditability.
   - Output: `lineage_id`, `record`, `integrity_check`.
2. `scope-validator-agent`
   - Purpose: validate proposed actions against governance requirements before execution.
   - Output: `verdict`, `findings`, `risk_level`.
3. `blast-radius-assessor-agent`
   - Purpose: estimate blast radius of a service from its permissions, dependencies, and resource limits.
   - Output: `risk_score`, `max_damage_potential`, `detection_latency`, `containment_time`, `findings`, `recommended_controls`.
4. `kill-path-auditor-agent`
   - Purpose: audit system shutdown capabilities against the four-level kill path spectrum.
   - Output: `coverage_score`, `gaps`, `escalation_readiness`, `recommended_actions`.

## Pipelines

### Governance Pipeline

`scripts/run_governance_pipeline.py` composes:

1. `scope-validator-agent` (governance gate)
2. configurable target agent (e.g. `planner-executor.planner-agent`)
3. `lineage-recorder-agent` (decision lineage)
4. `workflow-ops.checkpoint-agent` (checkpoint)

If scope validation returns `fail`, the pipeline short-circuits: it records lineage and a checkpoint but does not execute the target agent.

Run:

- `python3 scripts/run_governance_pipeline.py --input catalog/projects/control-ops/examples/governance-pipeline-input.json --pretty`
- `AGENT_MODE=llm python3 scripts/run_governance_pipeline.py --input catalog/projects/control-ops/examples/governance-pipeline-input.json --pretty`

### Resilience Pipeline

`scripts/run_resilience_pipeline.py` composes:

1. `blast-radius-assessor-agent`
2. `kill-path-auditor-agent`

Returns a combined `resilience_verdict` (adequate/partial/at-risk/inadequate) based on risk score vs kill path coverage.

Run:

- `python3 scripts/run_resilience_pipeline.py --input catalog/projects/control-ops/examples/resilience-pipeline-input.json --pretty`
- `AGENT_MODE=llm python3 scripts/run_resilience_pipeline.py --input catalog/projects/control-ops/examples/resilience-pipeline-input.json --pretty`

## Local Commands

- Run lineage-recorder example:
  `python3 scripts/run_agent.py --agent control-ops.lineage-recorder-agent --input catalog/projects/control-ops/agents/lineage-recorder-agent/examples/example-input.json --pretty`
- Run scope-validator example:
  `python3 scripts/run_agent.py --agent control-ops.scope-validator-agent --input catalog/projects/control-ops/agents/scope-validator-agent/examples/example-input.json --pretty`
- Run blast-radius-assessor example:
  `python3 scripts/run_agent.py --agent control-ops.blast-radius-assessor-agent --input catalog/projects/control-ops/agents/blast-radius-assessor-agent/examples/example-input.json --pretty`
- Run kill-path-auditor example:
  `python3 scripts/run_agent.py --agent control-ops.kill-path-auditor-agent --input catalog/projects/control-ops/agents/kill-path-auditor-agent/examples/example-input.json --pretty`
