# Runbook: cost-attribution-agent

1. Validate `run_id` and `stages[]`.
2. Compute token and runtime spend using observed stage prices, else fallback table.
3. Emit bounded stage costs, total cost, and dominant drivers.
