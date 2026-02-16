# qa-ops

Quality assurance operations project focused on test generation and regression triage.

## Agents

1. `test-case-generator-agent`
   - Purpose: generate bounded, practical test cases from feature specs.
   - Output: `test_cases` and `risk_focus`.
2. `regression-triage-agent`
   - Purpose: classify likely regression cause and propose follow-up actions.
   - Output: `probable_cause`, `severity`, and `recommended_actions`.

## Local Commands

- Run test-case generator example:
  `python3 scripts/run_agent.py --agent qa-ops.test-case-generator-agent --input catalog/projects/qa-ops/agents/test-case-generator-agent/examples/example-input.json --pretty`
- Run regression triage example:
  `python3 scripts/run_agent.py --agent qa-ops.regression-triage-agent --input catalog/projects/qa-ops/agents/regression-triage-agent/examples/example-input.json --pretty`
- Run test-case generator in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent qa-ops.test-case-generator-agent --input catalog/projects/qa-ops/agents/test-case-generator-agent/examples/example-input.json --pretty`
