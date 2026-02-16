# Runbook

## Input Contract

```json
{
  "period_start": "2026-02-09",
  "period_end": "2026-02-15",
  "tickets": [
    {"id": "t1", "priority": "p2", "category": "access"},
    {"id": "t2", "priority": "p3", "category": "billing"}
  ],
  "top_n_actions": 3
}
```

## Steps

1. Validate required fields and ticket structure.
2. Count ticket totals by priority and category.
3. Select top categories (max three).
4. Write concise period summary.
5. Emit recommended follow-up actions.
6. Return strict output JSON.

## Failure Modes

- Missing required fields: return validation error.
- Invalid priority/category values: return validation error.
- `top_n_actions` outside range 2..4: return validation error.
