# slo-reporter-agent smoke checks

- Valid input returns `compliance_status`, `findings`, and `recommended_actions`.
- `compliance_status` stays in allowed enum values.
- All-met metrics return `compliance_status` of `met`.
- Breached metric triggers `breached` status.
