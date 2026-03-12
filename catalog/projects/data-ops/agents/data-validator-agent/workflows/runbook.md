# data-validator-agent runbook

1. Validate records is a non-empty array of objects.
2. Validate rules is a non-empty array of strings.
3. Sanitize all untrusted text in rules and record values.
4. Check each record against each rule using keyword matching.
5. Collect violations up to the limit of 10.
6. Compute verdict based on violation ratio.
7. Return JSON contract exactly.
