# executor-agent smoke checks

- Input with `plan_steps` should return execution summary fields.
- `status` should be `done` or `partial`.
- `completed_steps + blocked_steps` should not exceed plan size.
