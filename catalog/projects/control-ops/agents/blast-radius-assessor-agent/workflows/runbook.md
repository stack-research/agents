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
2. Score permissions with explicit weights for critical, destructive, sensitive, and read-like access.
3. Score dependency count and external exposure separately.
4. Apply resource-limit credit from rate, budget, concurrency, timeout, and compute limits.
5. Compute risk_score, max_damage_potential, detection_latency, and containment_time from the shared matrix.
6. Generate findings and recommended controls from the same factor set.
7. Return strict output JSON.

## Failure Modes

- Missing required fields: return validation error.
- Empty service_name: return validation error.
- Empty permissions array: return validation error.
