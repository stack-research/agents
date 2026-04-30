# Runbook: budget-guardrail-agent

1. Validate attribution payload and budget limits.
2. Compare total/stage costs to run and stage limits.
3. Emit `within|warning|breach` plus guardrails and mitigations.
