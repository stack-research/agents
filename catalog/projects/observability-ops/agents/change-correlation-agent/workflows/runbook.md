# change-correlation-agent runbook

1. Validate incident_signals as a non-empty array of objects.
2. Normalize deploy_events and config_events to empty arrays when absent.
3. Identify high-severity or high-delta incident signals.
4. Match nearby change events within window_minutes (default 90).
5. Score matches by temporal distance, blast hint, and ownership overlap.
6. Return top correlated events, confidence, and concise summary.
