# code-ops

Code operations project focused on automated code review and PR summarization.

## Agents

1. `code-reviewer-agent`
   - Purpose: review code diffs for security, correctness, and style issues.
   - Output: `findings`, `severity`, and `suggested_actions`.
2. `pr-summary-agent`
   - Purpose: summarize pull request changes for reviewers with risk assessment.
   - Output: `summary`, `risk_areas`, and `review_focus`.

## Local Commands

- Run code reviewer example:
  `python3 scripts/run_agent.py --agent code-ops.code-reviewer-agent --input catalog/projects/code-ops/agents/code-reviewer-agent/examples/example-input.json --pretty`
- Run PR summary example:
  `python3 scripts/run_agent.py --agent code-ops.pr-summary-agent --input catalog/projects/code-ops/agents/pr-summary-agent/examples/example-input.json --pretty`
- Run code reviewer in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent code-ops.code-reviewer-agent --input catalog/projects/code-ops/agents/code-reviewer-agent/examples/example-input.json --pretty`
- Run PR summary in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent code-ops.pr-summary-agent --input catalog/projects/code-ops/agents/pr-summary-agent/examples/example-input.json --pretty`
