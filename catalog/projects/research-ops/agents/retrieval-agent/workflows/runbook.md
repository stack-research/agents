# retrieval-agent runbook

1. Validate `query` and optional source list.
2. Sanitize source and query text.
3. Emit 1..max_points notes with concise wording.
4. Set confidence according to source coverage.
5. Return JSON contract exactly.
