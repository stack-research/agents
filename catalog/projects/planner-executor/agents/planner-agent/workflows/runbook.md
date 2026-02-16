# planner-agent runbook

1. Validate `goal` is present and non-empty.
2. Normalize and sanitize untrusted text.
3. Generate 3-6 bounded steps.
4. Assign risk level (low/medium/high) from goal context.
5. Return JSON contract exactly.
