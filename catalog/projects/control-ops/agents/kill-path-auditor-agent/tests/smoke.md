# Smoke Test

Input:

- `examples/example-input.json`

Expected:

- Output includes `coverage_score`, `gaps`, `escalation_readiness`, and `recommended_actions`.
- `coverage_score` is an integer between 0 and 4.
- `escalation_readiness` is one of `ready`, `partial`, `unprepared`.
- `recommended_actions` has exactly 3 entries.
