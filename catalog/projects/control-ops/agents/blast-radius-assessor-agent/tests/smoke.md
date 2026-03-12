# Smoke Test

Input:

- `examples/example-input.json`

Expected:

- Output includes `risk_score`, `max_damage_potential`, `detection_latency`, `containment_time`, `findings`, and `recommended_controls`.
- `risk_score` is an integer between 0 and 100.
- `max_damage_potential` is one of `low`, `medium`, `high`, `critical`.
- `detection_latency` is one of `fast`, `moderate`, `slow`.
- `containment_time` is one of `fast`, `moderate`, `slow`.
- `findings` has 1 to 5 entries.
- `recommended_controls` has exactly 3 entries.
