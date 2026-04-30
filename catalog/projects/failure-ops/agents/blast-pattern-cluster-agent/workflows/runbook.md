# Runbook: blast-pattern-cluster-agent

## Steps

1. Validate `incident_id` and non-empty `failure_modes`.
2. Group failure modes by service overlap and impact severity.
3. Assign `blast_pattern` per cluster: localized, tier, cross-system, or global.
4. Emit bounded rationale and confidence per cluster.

## Failure handling

- Missing `failure_mode_id` on any input mode: validation error.
- Invalid impact/confidence values: coerce to safe defaults (`medium`) before scoring.
- Empty clusters after normalization: return one fallback localized cluster with note.
