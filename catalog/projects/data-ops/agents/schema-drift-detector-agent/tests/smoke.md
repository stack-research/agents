# schema-drift-detector-agent smoke checks

- Valid input returns `changes`, `drift_severity`, and `recommended_actions`.
- `drift_severity` stays in allowed enum values.
- `changes` entries contain `field`, `change_type`, and `detail`.
- Identical schemas return `drift_severity` of `none`.
