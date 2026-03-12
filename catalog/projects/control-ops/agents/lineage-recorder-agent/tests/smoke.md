# Smoke Test

Input:

- `examples/example-input.json`

Expected:

- Output includes `lineage_id`, `record`, and `integrity_check`.
- `record` contains exactly five keys: `trigger`, `knowledge`, `rules_applied`, `alternatives_considered`, `action_taken`.
- `integrity_check` is `complete` when all fields are substantive.
