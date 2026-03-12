# code-reviewer-agent smoke checks

- Valid input returns `findings`, `severity`, and `suggested_actions`.
- `severity` stays in allowed enum values.
- Clean diff returns `severity` of `clean` and empty `findings`.
- Security patterns in diff produce `critical` severity.
