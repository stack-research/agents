# Runbook: hypothesis-registration-agent

## Steps

1. Validate `hypothesis_statement` is non-empty after trim.
2. Emit `hypothesis_id` and `normalized_statement` for traceability.
3. If hedging or missing measurability is detected, set `needs_clarification` and list `ambiguities`.

## Failure handling

- Empty input: return validation error upstream; do not invent hypothesis text.
- Overly long input: normalize to bounded length in deterministic mode.
