# planner-executor

Project for a simple two-agent planning workflow.

## Agents

1. `planner-agent`
   - Purpose: convert a goal into a bounded execution plan.
   - Output: `plan_steps` and `risk_level`.
2. `executor-agent`
   - Purpose: summarize execution progress against planned steps.
   - Output: `status`, `completed_steps`, `blocked_steps`, and `summary`.

## Pipeline

- `scripts/run_planner_executor_pipeline.py` composes:
  1. `planner-agent`
  2. `executor-agent`

Input example:

- `catalog/projects/planner-executor/examples/pipeline-input.json`

Run pipeline:

- `python3 scripts/run_planner_executor_pipeline.py --input catalog/projects/planner-executor/examples/pipeline-input.json --pretty`
- `AGENT_MODE=llm python3 scripts/run_planner_executor_pipeline.py --input catalog/projects/planner-executor/examples/pipeline-input.json --pretty`

## Local Commands

- Run planner example:
  `python3 scripts/run_agent.py --agent planner-executor.planner-agent --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json --pretty`
- Run executor example:
  `python3 scripts/run_agent.py --agent planner-executor.executor-agent --input catalog/projects/planner-executor/agents/executor-agent/examples/example-input.json --pretty`
- Run planner in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent planner-executor.planner-agent --input catalog/projects/planner-executor/agents/planner-agent/examples/example-input.json --pretty`
