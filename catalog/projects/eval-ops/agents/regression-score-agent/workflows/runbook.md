# regression-score-agent runbook

1. Ensure both score maps use the same metric keys where comparison is intended.
2. Set `regression_threshold_percent` stricter for release gates (for example 2.0) and looser for exploratory runs (for example 10.0).
3. If `verdict` is `fail`, block promotion until metrics recover or the change is justified.
4. On missing numeric values, fix upstream telemetry before rerunning.
