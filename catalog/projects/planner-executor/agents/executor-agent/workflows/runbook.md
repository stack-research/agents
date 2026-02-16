# executor-agent runbook

1. Validate `plan_steps` exists and has at least one step.
2. Parse optional `context` string.
3. Derive bounded progress values (`completed_steps`, `blocked_steps`).
4. Build concise summary under 60 words.
5. Return JSON contract exactly.
