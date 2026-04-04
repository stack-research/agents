# Runbook

## Input Contract

```json
{
  "system_name": "inference-gateway",
  "capabilities": {
    "throttle": "rate limiter on API gateway reduces throughput to 10%",
    "degrade": "read-only mode disables write endpoints",
    "isolate": "",
    "hard_stop": "container kill via orchestrator"
  },
  "last_tested": "2026-01-15"
}
```

## Steps

1. Validate system_name and capabilities are present.
2. Check each of the four kill path levels: throttle, degrade, isolate, hard_stop.
3. Count present levels (non-empty description) for coverage_score.
4. List missing or empty levels as gaps.
5. Parse `last_tested` as ISO date when present and flag missing or stale test evidence.
6. Determine escalation_readiness from coverage plus recency.
7. Generate recommended actions.
8. Return strict output JSON.

## Failure Modes

- Missing required fields: return validation error.
- Empty system_name: return validation error.
- capabilities not an object: return validation error.
- non-ISO or future `last_tested`: return validation error.
