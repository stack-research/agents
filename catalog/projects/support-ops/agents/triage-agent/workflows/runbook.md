# Runbook

## Input Contract

```json
{
  "text": "Our production checkout is down for all users.",
  "customer_tier": "enterprise"
}
```

## Steps

1. Validate `text` as non-empty string.
2. Parse for urgency and issue type.
3. Assign category.
4. Assign base priority from impact.
5. Escalate one level for enterprise tier (up to `p1`).
6. Produce concise imperative next action.
7. Emit JSON output.

## Failure Modes

- Empty text: return validation error.
- Unknown customer_tier: treat as `free`.
- Ambiguous issue type: category `other`, conservative priority `p3`.
