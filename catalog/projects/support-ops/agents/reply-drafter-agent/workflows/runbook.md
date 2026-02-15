# Runbook

## Input Contract

```json
{
  "customer_name": "Alex",
  "priority": "p2",
  "category": "access",
  "issue_summary": "Users cannot sign in after password reset."
}
```

## Steps

1. Validate required fields (`priority`, `category`, `issue_summary`).
2. Choose subject template by category and urgency.
3. Draft a response that acknowledges issue, states next step, and timeline.
4. Keep reply concise and professional.
5. Emit JSON output.

## Failure Modes

- Missing required fields: return validation error.
- Unknown priority/category: return validation error.
- Empty issue summary: return validation error.
