# Runbook: schema-compat-validator-agent

## Steps

1. Validate `contract_name`, `producer_schema`, and `consumer_schema`.
2. Normalize field maps from each schema payload.
3. Compare field presence, requiredness, and primitive type compatibility.
4. Classify compatibility for `compat_mode` (`backward`, `forward`, or `full`).
5. Emit bounded change lists and migration-oriented recommendations.

## Failure handling

- Missing required top-level inputs: validation error.
- Unsupported schema shapes: validation error with bounded guidance.
- Unknown compat mode: validation error.
