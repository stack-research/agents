# workflow-ops

Workflow operations project for routing tasks and recording execution checkpoints.

## Agents

1. `router-agent`
   - Purpose: route incoming work to the most suitable agent.
   - Output: `target_agent`, `priority`, and `rationale`.
2. `checkpoint-agent`
   - Purpose: record workflow progress snapshots for traceability.
   - Output: `checkpoint_id`, `recorded`, and `summary`.

## Local Commands

- Run router example:
  `python3 scripts/run_agent.py --agent workflow-ops.router-agent --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json --pretty`
- Run checkpoint example:
  `python3 scripts/run_agent.py --agent workflow-ops.checkpoint-agent --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json --pretty`
- Run router in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent workflow-ops.router-agent --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json --pretty`
