# pr-summary-agent runbook

1. Validate title and changed_files inputs.
2. Sanitize untrusted text in all inputs.
3. Analyze file paths for sensitive areas (auth, config, infra, migrations).
4. Generate concise summary from title and file scope.
5. Identify risk areas from file paths and optional diff summary.
6. Assign review focus based on file count and sensitivity.
7. Return JSON contract exactly.
