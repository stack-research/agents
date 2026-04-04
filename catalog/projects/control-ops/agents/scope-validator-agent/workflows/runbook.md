# Runbook

## Input Contract

```json
{
  "action_description": "delete all inactive user accounts older than 90 days",
  "permissions_requested": ["database-write", "user-admin", "audit-log-write"],
  "reversibility_plan": "soft-delete with 30-day recovery window",
  "scope_boundary": "inactive accounts in us-east region only"
}
```

## Steps

1. Validate action_description and permissions_requested are present and non-empty.
2. Classify the action as read-only, mutating, or destructive.
3. Score scope boundedness from the `scope_boundary` text.
4. Score reversibility from the `reversibility_plan` text.
5. Score permission sensitivity and traceability from `permissions_requested`.
6. Determine `pass`, `review`, or `fail` from the shared threshold matrix.
7. Return strict output JSON.

## Failure Modes

- Missing required fields: return validation error.
- Empty action_description: return validation error.
- Empty permissions_requested array: return validation error.
