# Smoke: schema-compat-validator-agent

- Run example input and expect `compatibility_status` in `compatible|compatible_with_warnings|incompatible`.
- Remove a producer required field from consumer schema and expect `incompatible`.
- Use invalid `compat_mode` and expect deterministic validation error.
