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
2. Check whether action keywords suggest irreversible or high-impact operations.
3. Check whether reversibility_plan is present for destructive actions.
4. Check permission proportionality against scope boundary.
5. Determine verdict and risk_level.
6. Return strict output JSON.

## Failure Modes

- Missing required fields: return validation error.
- Empty action_description: return validation error.
- Empty permissions_requested array: return validation error.
