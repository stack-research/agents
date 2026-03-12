# log-analyzer-agent smoke checks

- Valid input returns `patterns`, `anomalies`, and `severity`.
- `severity` stays in allowed enum values.
- `patterns` length is between 1 and 5.
- `anomalies` length does not exceed 5.
- Clean logs return `severity` of `normal`.
