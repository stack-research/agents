# data-validator-agent smoke checks

- Valid input returns `valid_count`, `invalid_count`, `violations`, and `verdict`.
- `verdict` stays in allowed enum values.
- `violations` length does not exceed 10.
- All-valid records return `verdict` of `pass`.
