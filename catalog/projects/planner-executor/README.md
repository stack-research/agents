# planner-executor

Project for a simple two-agent planning workflow.

## Agents

1. `planner-agent`
   - Purpose: convert a goal into a bounded execution plan.
   - Output: `plan_steps` and `risk_level`.
2. `executor-agent`
   - Purpose: summarize execution progress against planned steps.
   - Output: `status`, `completed_steps`, `blocked_steps`, and `summary`.

## Local Commands

- Run planner example:
  `python3 scripts/run_agent.py --agent planner-executor.planner-agent --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json --pretty`
- Run executor example:
  `python3 scripts/run_agent.py --agent planner-executor.executor-agent --input catalog/projects/planner-executor/agents/executor-agent/examples/example-input.json --pretty`
- Run planner in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent planner-executor.planner-agent --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json --pretty`
