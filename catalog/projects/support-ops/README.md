# support-ops

Support operations project with agents that structure and prioritize inbound requests.

## Agents

1. `triage-agent`
   - Purpose: classify support messages into actionable triage fields.
   - Output: `priority`, `category`, and `next_action`.
2. `reply-drafter-agent`
   - Purpose: draft concise customer replies from structured triage details.
   - Output: `subject` and `reply`.
3. `summary-agent`
   - Purpose: summarize weekly support ticket trends and suggest follow-up actions.
   - Output: `ticket_count`, `priority_breakdown`, `top_categories`, `summary`, `recommended_actions`.

## Pipeline

- `scripts/run_support_pipeline.py` composes:
  1. `triage-agent`
  2. `reply-drafter-agent`

Input example:

- `catalog/projects/support-ops/examples/pipeline-input.json`

Run pipeline:

- `python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty`
- `AGENT_MODE=llm python3 scripts/run_support_pipeline.py --input catalog/projects/support-ops/examples/pipeline-input.json --pretty`

## Local Commands

- Run triage example:
  `python3 scripts/run_agent.py --agent support-ops.triage-agent --input catalog/projects/support-ops/agents/triage-agent/examples/example-input.json --pretty`
- Run reply drafter example:
  `python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty`
- Run reply drafter in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent support-ops.reply-drafter-agent --input catalog/projects/support-ops/agents/reply-drafter-agent/examples/example-input.json --pretty`
- Run weekly summary example:
  `python3 scripts/run_agent.py --agent support-ops.summary-agent --input catalog/projects/support-ops/agents/summary-agent/examples/example-input.json --pretty`
- Run weekly summary in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent support-ops.summary-agent --input catalog/projects/support-ops/agents/summary-agent/examples/example-input.json --pretty`
