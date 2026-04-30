# Runbook: failure-library-agent

## Steps

1. Validate `incident_id` and non-empty `observations` (max 64 items).
2. Normalize each observation into a bounded failure mode shape.
3. Generate deterministic `failure_mode_id` values from canonicalized mode content.
4. Set `library_status` to `complete` when every observation produced at least one indicator and precondition, otherwise `partial`.

## Failure handling

- Missing required fields (`service`, `symptom`, `impact`): validation error.
- Non-object observations: validation error.
- Oversized arrays are truncated deterministically to bound output.
