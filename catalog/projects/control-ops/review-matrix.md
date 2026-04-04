# Control-Ops Review Matrix

This file is the compact contract matrix used to keep `control-ops` aligned across metadata, runtime, tests, prompts, and pipelines.

| Agent | Required Inputs | Stable Outputs | Canonical Decision Rules | Downstream Consumers |
| --- | --- | --- | --- | --- |
| `lineage-recorder-agent` | `trigger`, `knowledge`, `rules_applied`, `alternatives_considered`, `action_taken` | `lineage_id`, `record`, `integrity_check` | Sanitize and bound all fields. `lineage_id` is a readable slug plus short stable hash. | governance pipeline |
| `scope-validator-agent` | `action_description`, `permissions_requested` | `verdict`, `findings`, `risk_level` | Score action destructiveness, scope boundedness, reversibility, permission sensitivity, and traceability. `review` and `fail` both stop execution. | governance pipeline, incident pipeline |
| `blast-radius-assessor-agent` | `service_name`, `permissions` | `risk_score`, `max_damage_potential`, `detection_latency`, `containment_time`, `findings`, `recommended_controls` | Weighted permission + dependency score minus resource-limit credit. Controls come from the same factor set. | resilience pipeline |
| `kill-path-auditor-agent` | `system_name`, `capabilities` | `coverage_score`, `gaps`, `escalation_readiness`, `recommended_actions` | `coverage_score` counts present kill-path levels. `last_tested` must be ISO date or empty; missing or stale test evidence adds gaps and can demote readiness. | resilience pipeline |

## Pipeline Status Matrix

### Governance pipeline

| Scope verdict | Target execution | `pipeline_status` | `target_output.status` |
| --- | --- | --- | --- |
| `pass` | execute target | `ok` | target payload output |
| `review` | skip target | `needs_review` | `needs_review` |
| `fail` | skip target | `blocked` | `blocked` |
| validation/runtime failure | skip target | `degraded` | `degraded` |

### Resilience pipeline

| Risk score | Kill-path coverage | `resilience_verdict` |
| --- | --- | --- |
| `>= 50` and `<= 1` | any | `inadequate` |
| `>= 60` and `<= 2` | any | `inadequate` |
| `>= 40` and `<= 2` | any | `at-risk` |
| `< 40` and `== 4` | any | `adequate` |
| otherwise | any | `partial` |
