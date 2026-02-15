# Smoke Checks

## Case 1: healthy

Input age `10`, error `0.2` -> expect `ok`.

## Case 2: stale heartbeat

Input age `40`, error `0.2` -> expect `warn`.

## Case 3: escalation by errors

Input age `20`, error `6.1` -> expect `warn`.

## Case 4: critical stale + errors

Input age `100`, error `8.5` -> expect `critical`.
