# regression-triage-agent runbook

1. Validate failure summary and optional changed component list.
2. Detect likely cause category using deterministic keywords and context.
3. Assign severity (sev1-sev4) based on impact language.
4. Produce 2-4 concise investigation actions.
5. Return JSON contract exactly.
