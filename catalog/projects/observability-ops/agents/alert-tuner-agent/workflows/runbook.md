# alert-tuner-agent runbook

1. Validate alert_history as a non-empty array of objects.
2. Normalize incident_labels to empty array when absent.
3. Compute noise ratio from non-actionable alerts.
4. Detect noisy metrics and missed incidents by threshold band.
5. Propose bounded threshold adjustments with expected impact hints.
6. Return tuning recommendations, noise score, and concise rationale.
