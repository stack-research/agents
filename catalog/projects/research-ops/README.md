# research-ops

Research operations project for converting source material into concise summaries and actions.

## Agents

1. `retrieval-agent`
   - Purpose: extract bounded notes from a query and source list.
   - Output: `notes` and `confidence`.
2. `synthesis-agent`
   - Purpose: convert research notes into a brief/report summary and actions.
   - Output: `headline`, `summary`, and `next_actions`.

## Local Commands

- Run retrieval example:
  `python3 scripts/run_agent.py --agent research-ops.retrieval-agent --input catalog/projects/research-ops/agents/retrieval-agent/examples/example-input.json --pretty`
- Run synthesis example:
  `python3 scripts/run_agent.py --agent research-ops.synthesis-agent --input catalog/projects/research-ops/agents/synthesis-agent/examples/example-input.json --pretty`
- Run retrieval in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent research-ops.retrieval-agent --input catalog/projects/research-ops/agents/retrieval-agent/examples/example-input.json --pretty`
