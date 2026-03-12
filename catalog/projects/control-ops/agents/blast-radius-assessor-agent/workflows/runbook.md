# Runbook

## Input Contract

```json
{
  "service_name": "payment-processor",
  "permissions": ["database-write", "external-api-call", "pii-read"],
  "dependencies": ["auth-service", "ledger-db", "notification-queue"],
  "resource_limits": {
    "rate_limit": "100 req/s",
    "budget_cap": "$500/day",
    "concurrency": 10
  }
}
```

## Steps

1. Validate service_name and permissions are present and non-empty.
2. Score permissions by sensitivity (write, admin, pii, external access).
3. Score dependency count and coupling risk.
4. Assess resource limits (present vs missing).
5. Compute risk_score, max_damage_potential, detection_latency, containment_time.
6. Generate findings and recommended controls.
7. Return strict output JSON.

## Failure Modes

- Missing required fields: return validation error.
- Empty service_name: return validation error.
- Empty permissions array: return validation error.
