# Smoke Test

Input:

- `examples/example-input.json`

Expected:

- Output includes `ticket_count`, `priority_breakdown`, `top_categories`, `summary`, and `recommended_actions`.
- `priority_breakdown` contains `p1`, `p2`, `p3`, `p4` integer values.
- `recommended_actions` length equals `top_n_actions` input.
