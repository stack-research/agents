1. Validate `run_id`, `artifacts`, and horizon parameters.
2. Normalize and truncate artifact text into memory facts.
3. Assign confidence per fact.
4. Emit `memory_updates` and `expires_in_hours`.
5. Reject empty artifacts and out-of-range horizons.