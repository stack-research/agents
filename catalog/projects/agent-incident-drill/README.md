# agent-incident-drill

A scenario project for measuring agent incident response with the existing agent catalog.

The drill composes support, workflow, and ControlOps agents around one controlled failure. It is not a production incident platform. It is a reproducible harness that shows whether a proposed agent action is scoped, recorded, contained, and recoverable.

## Scenario

The default scenario models a support-to-export incident. A customer-data export request attempts to cross from review into a write-capable path. The drill checks the action before execution, records lineage, assesses blast radius, audits kill paths, simulates rollback or compensation, and emits a scorecard.

## Pipeline

`scripts/run_agent_incident_drill.py` composes:

1. `workflow-ops.router-agent`
2. `support-ops.triage-agent`
3. `control-ops.scope-validator-agent`
4. `control-ops.lineage-recorder-agent`
5. `control-ops.blast-radius-assessor-agent`
6. `control-ops.kill-path-auditor-agent`
7. `workflow-ops.checkpoint-agent`

If scope validation returns `review` or `fail`, the unsafe action is not executed. The attempted action is still recorded as incident evidence.

## Output

The runner emits:

- `workflow_id`
- `scenario`
- `event_journal`
- `governance`
- `resilience`
- `lineage_query`
- `containment_timing`
- `rollback_or_compensation`
- `scorecard`
- `pipeline_status`

## Local Commands

- Run the deterministic drill:
`python3 scripts/run_agent_incident_drill.py --input catalog/projects/agent-incident-drill/examples/drill-input.json --pretty`
- Run the deterministic tests:
`python3 -m unittest tests.test_agent_incident_drill`