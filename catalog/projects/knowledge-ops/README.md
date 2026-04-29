# knowledge-ops

Reusable knowledge, memory, and temporal agents for catalog-wide composition.

## Agents

1. `evidence-ranker-agent`
  - Purpose: score and rank candidate evidence for downstream decisions.
  - Output: `ranked_evidence` and `overall_confidence`.
2. `claim-trace-agent`
  - Purpose: map assertions to evidence support states.
  - Output: `assertion_map` and `coverage_score`.
3. `memory-curator-agent`
  - Purpose: distill run artifacts into compact, reusable memory entries.
  - Output: `memory_updates` and `expires_in_hours`.
4. `temporal-watch-agent`
  - Purpose: compare snapshots over time and detect drift.
  - Output: `temporal_signals`, `drift_level`, and `recommended_actions`.

## Local Commands

- `python3 scripts/run_agent.py --agent knowledge-ops.evidence-ranker-agent --input catalog/projects/knowledge-ops/agents/evidence-ranker-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent knowledge-ops.claim-trace-agent --input catalog/projects/knowledge-ops/agents/claim-trace-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent knowledge-ops.memory-curator-agent --input catalog/projects/knowledge-ops/agents/memory-curator-agent/examples/example-input.json --pretty`
- `python3 scripts/run_agent.py --agent knowledge-ops.temporal-watch-agent --input catalog/projects/knowledge-ops/agents/temporal-watch-agent/examples/example-input.json --pretty`