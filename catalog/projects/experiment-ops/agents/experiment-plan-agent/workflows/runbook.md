# Runbook: experiment-plan-agent

## Steps

1. Confirm hypothesis text is present and sanitized.
2. Emit control/treatment variants within `max_variants` when provided.
3. List metrics, guardrails, and execution risks before `next_steps`.

## Failure handling

- Missing hypothesis: validation error.
- Invalid `max_variants`: coerce to allowed range in deterministic mode.
