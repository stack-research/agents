# pr-summary-agent smoke checks

- Valid input returns `summary`, `risk_areas`, and `review_focus`.
- `review_focus` stays in allowed enum values.
- `risk_areas` length is between 1 and 4.
- Summary is under 80 words.
