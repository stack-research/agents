# benchmark-curator-agent runbook

1. Confirm `candidate_cases` each include `case_id` and `title`.
2. Run deterministic mode for repeatable curation; use LLM mode only when phrasing of gaps must be richer.
3. If `curation_verdict` is `sparse`, collect more cases before freezing a suite version.
4. On validation errors, fix payload shape and rerun.
