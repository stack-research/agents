# Smoke: bundle-seal-agent

- Run example input; expect `seal_status` `sealed` when lineage_ids are present.
- Omit lineage_records; expect `sealed_with_gaps`.
- Invalid `bundle_root_sha256` must error.
