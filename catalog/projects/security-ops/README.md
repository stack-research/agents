# security-ops

Security-focused project containing agents that assess and harden agentic workflows.

## Agents

1. `agentic-security-scanner-agent`
   - Purpose: scan catalog projects for baseline OWASP Agentic AI control coverage.
   - Output: summary, risk score, and actionable findings.

## Local Commands

- Run scanner:
  `python3 scripts/run_security_scan.py --target-path . --pretty`
- Run scanner via generic runner:
  `python3 scripts/run_agent.py --agent security-ops.agentic-security-scanner-agent --input catalog/projects/security-ops/agents/agentic-security-scanner-agent/examples/example-input.json --pretty`
