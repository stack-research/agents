# Runbook: result-adjudication-agent

## Steps

1. Validate metrics object is non-empty and numeric values are comparable.
2. Resolve `primary_metric` when omitted (deterministic: first sorted key).
3. Parse explicit bounds from `success_criteria` when present; otherwise emit inconclusive guidance.

## Failure handling

- Non-numeric primary observation: validation error.
- Missing metrics: validation error.
