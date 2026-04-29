1. Validate task and prerequisite arrays.
2. Compute missing prerequisites from required vs completed.
3. If missing, set `ready=false` and keep target as checkpoint handler.
4. If ready, route by task intent and available agents.
5. Emit concise rationale with priority.
