# quality-drift-reporter-agent runbook

1. Supply at least three `windows` for meaningful volatility detection.
2. Align `metric_name` with the semantics of `score` (higher better vs lower better).
3. Investigate any window listed in `windows_flagged` before closing a quality review.
4. If validation fails on window shape, normalize scores upstream and rerun.
