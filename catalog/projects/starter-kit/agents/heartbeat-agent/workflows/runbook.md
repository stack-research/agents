# Runbook

## Input Contract

Expected input payload:

```json
{
  "service_name": "billing-api",
  "heartbeat_age_seconds": 42,
  "error_rate_percent": 1.8
}
```

## Steps

1. Validate all required fields and numeric types.
2. Compute base status from heartbeat age.
3. Escalate status by error-rate rule.
4. Generate short report with service name, age, error rate, and final status.
5. Emit JSON output.

## Failure Modes

- Missing field: return validation error.
- Non-numeric metric: return validation error.
- Negative values: clamp to zero and note this in report.
