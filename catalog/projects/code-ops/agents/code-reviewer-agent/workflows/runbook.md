# code-reviewer-agent runbook

1. Validate diff input is a non-empty string.
2. Sanitize untrusted text in diff and optional context.
3. Scan for security patterns (injection, hardcoded secrets, unsafe eval).
4. Scan for correctness patterns (null checks, error handling, resource leaks).
5. Assign severity based on worst finding category.
6. Generate suggested actions for detected issues.
7. Return JSON contract exactly.
