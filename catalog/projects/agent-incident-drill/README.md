# agent-incident-drill

A scenario project for measuring agent incident response with the existing agent catalog.

The drill composes support, workflow, and ControlOps agents around one controlled failure. It is not a production incident platform. It is a reproducible harness that shows whether a proposed agent action is scoped, recorded, contained, and recoverable.

## Scenarios

Each scenario is a JSON input under `examples/`. The same pipeline runs for all; only the narrative and fields change.

| Scenario | File | What it models |
|----------|------|----------------|
| Support export boundary | `drill-input.json` | Urgent customer-data export toward an external workspace; checks that high-risk export stays gated. |
| Data corruption recovery | `drill-input-data-corruption.json` | Checksum / replication incident on a ledger shard; proposed restore and WAL replay with tight scope. |
| Auth lockout break-glass | `drill-input-auth-lockout.json` | Org-wide admin lockout after MFA policy change; proposed temporary MFA bypass and emergency policy push. |
| Supply chain compromise | `drill-input-supply-chain-compromise.json` | Compromised dependency in CI; proposed key rotation, token revocation, and publish block until clean rebuild. |

For every scenario, the drill checks the action before execution, records lineage, assesses blast radius, audits kill paths, records rollback or compensation, and emits a scorecard. If scope validation returns `review` or `fail`, the unsafe action is not executed; the attempt is still recorded as incident evidence.

## Pipeline

`scripts/run_agent_incident_drill.py` composes:

1. `workflow-ops.router-agent`
2. `support-ops.triage-agent`
3. `control-ops.scope-validator-agent`
4. `control-ops.lineage-recorder-agent`
5. `control-ops.blast-radius-assessor-agent`
6. `control-ops.kill-path-auditor-agent`
7. `workflow-ops.checkpoint-agent`

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

Run the deterministic drill (pick one input):

```bash
python3 scripts/run_agent_incident_drill.py \
  --input catalog/projects/agent-incident-drill/examples/drill-input.json --pretty
python3 scripts/run_agent_incident_drill.py \
  --input catalog/projects/agent-incident-drill/examples/drill-input-data-corruption.json --pretty
python3 scripts/run_agent_incident_drill.py \
  --input catalog/projects/agent-incident-drill/examples/drill-input-auth-lockout.json --pretty
python3 scripts/run_agent_incident_drill.py \
  --input catalog/projects/agent-incident-drill/examples/drill-input-supply-chain-compromise.json --pretty
```

Compare scorecards from two saved drill outputs (JSON files from runs above):

```bash
python3 scripts/compare_agent_incident_drill_scorecards.py \
  --baseline /path/to/run-a.json --current /path/to/run-b.json
```

Deterministic tests:

```bash
python3 -m unittest tests.test_agent_incident_drill
```
