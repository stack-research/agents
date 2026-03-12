# slo-reporter-agent runbook

1. Validate service_name, metrics, and slo_targets inputs.
2. Sanitize untrusted text in service_name.
3. Compare each metric value against its SLO target.
4. Determine compliance status from comparison results.
5. Generate findings describing each metric's status.
6. Produce recommended actions for at-risk or breached metrics.
7. Return JSON contract exactly.
