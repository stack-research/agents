# research-ops

Research operations project for converting source material into concise summaries and actions.

## Agents

1. `source-planner-agent`
   - Purpose: plan the next evidence collection steps from a query and existing evidence.
   - Output: `fetch_plan`, `priority_sources`, and `coverage_target`.
2. `retrieval-agent`
   - Purpose: extract bounded notes from a query and source list.
   - Output: `notes` and `confidence`.
3. `gap-detector-agent`
   - Purpose: detect unsupported assertions and recommend targeted collection actions.
   - Output: `gaps`, `risk_level`, and `next_collection_actions`.
4. `synthesis-agent`
   - Purpose: convert research notes into a brief/report summary and actions.
   - Output: `headline`, `summary`, and `next_actions`.

## Local Commands

- Run source planner example:
  `python3 scripts/run_agent.py --agent research-ops.source-planner-agent --input catalog/projects/research-ops/agents/source-planner-agent/examples/example-input.json --pretty`
- Run retrieval example:
  `python3 scripts/run_agent.py --agent research-ops.retrieval-agent --input catalog/projects/research-ops/agents/retrieval-agent/examples/example-input.json --pretty`
- Run gap detector example:
  `python3 scripts/run_agent.py --agent research-ops.gap-detector-agent --input catalog/projects/research-ops/agents/gap-detector-agent/examples/example-input.json --pretty`
- Run synthesis example:
  `python3 scripts/run_agent.py --agent research-ops.synthesis-agent --input catalog/projects/research-ops/agents/synthesis-agent/examples/example-input.json --pretty`
- Run research chain in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent research-ops.source-planner-agent --input catalog/projects/research-ops/agents/source-planner-agent/examples/example-input.json --pretty`
