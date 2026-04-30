# Smoke: artifact-inventory-agent

- Run example input; expect `inventory_status` `complete` and two `artifacts` with `content_sha256` set.
- Empty `artifacts` must error in deterministic mode.
- Invalid `role` must error.
