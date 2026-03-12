# log-analyzer-agent runbook

1. Validate log_entries is a non-empty array of strings.
2. Sanitize untrusted text in all log entries.
3. Scan entries for error, warning, and info patterns.
4. Detect anomalies (error spikes, timeouts, auth failures).
5. Classify severity based on anomaly types.
6. Return JSON contract exactly.
