# workflow-ops

Workflow operations project for routing tasks and recording execution checkpoints.

## Agents

1. `router-agent`
   - Purpose: route incoming work to the most suitable agent.
   - Output: `target_agent`, `priority`, and `rationale`.
2. `dependency-router-agent`
   - Purpose: route only when dependencies/prerequisites are satisfied.
   - Output: `target_agent`, `ready`, `missing_prerequisites`, `priority`, and `rationale`.
3. `retry-policy-agent`
   - Purpose: decide retry, backoff, escalation, or stop for failed stages.
   - Output: `decision`, `backoff_ms`, `reason_code`, and `next_step`.
4. `checkpoint-agent`
   - Purpose: record workflow progress snapshots for traceability.
   - Output: `checkpoint_id`, `recorded`, and `summary`.

## Pipeline

- `scripts/run_workflow_pipeline.py` composes:
  1. `router-agent`
  2. routed target agent
  3. `checkpoint-agent`
  - output includes `stage_timing` and `failure_taxonomy` fields

Input example:

- `catalog/projects/workflow-ops/examples/pipeline-input.json`

Run pipeline:

- `python3 scripts/run_workflow_pipeline.py --input catalog/projects/workflow-ops/examples/pipeline-input.json --pretty`
- `AGENT_MODE=llm python3 scripts/run_workflow_pipeline.py --input catalog/projects/workflow-ops/examples/pipeline-input.json --pretty`

## Local Commands

- Run router example:
  `python3 scripts/run_agent.py --agent workflow-ops.router-agent --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json --pretty`
- Run checkpoint example:
  `python3 scripts/run_agent.py --agent workflow-ops.checkpoint-agent --input catalog/projects/workflow-ops/agents/checkpoint-agent/examples/example-input.json --pretty`
- Run dependency router example:
  `python3 scripts/run_agent.py --agent workflow-ops.dependency-router-agent --input catalog/projects/workflow-ops/agents/dependency-router-agent/examples/example-input.json --pretty`
- Run retry policy example:
  `python3 scripts/run_agent.py --agent workflow-ops.retry-policy-agent --input catalog/projects/workflow-ops/agents/retry-policy-agent/examples/example-input.json --pretty`
- Run router in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent workflow-ops.router-agent --input catalog/projects/workflow-ops/agents/router-agent/examples/example-input.json --pretty`
