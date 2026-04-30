# Runbook: rollback-playbook-agent

## Steps

1. Validate `incident_id` and non-empty `clusters`.
2. Compute rollback severity class from blast pattern and confidence.
3. Emit ordered rollback steps, then attach prerequisites, abort conditions, and verification checks.
4. Add escalation points for human approval and safety break-glass events.

## Failure handling

- Empty `clusters`: validation error.
- Missing critical safety signals (for example no backup and no approval) forces `rollback_class=critical` and includes explicit abort condition.
- If no actionable cluster details exist, emit conservative minimal playbook with escalation.
