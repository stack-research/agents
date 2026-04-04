# Runbook

## Input Contract

```json
{
  "trigger": "customer-payment-failed webhook received",
  "knowledge": "account has 3 prior failures this month; retry policy allows 5 max",
  "rules_applied": ["retry-if-under-limit", "notify-on-third-failure"],
  "alternatives_considered": ["escalate-to-human", "block-account"],
  "action_taken": "queued automatic retry and sent notification to billing team"
}
```

## Steps

1. Validate all five required fields are present and non-empty.
2. Sanitize all text inputs.
3. Generate deterministic lineage_id from normalized trigger and action_taken plus a short stable hash.
4. Assemble record object with all five fields.
5. Assess integrity: complete if all fields substantive, partial otherwise.
6. Return strict output JSON.

## Failure Modes

- Missing required fields: return validation error.
- Empty string fields: return validation error.
- Non-array rules_applied or alternatives_considered: return validation error.
