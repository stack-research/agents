# starter-kit

Starter project containing simple, composable agents.

## Agents

1. `heartbeat-agent`
   - Purpose: summarize heartbeat signals from services.
   - Output: one status (`ok`, `warn`, `critical`) and a short rationale.
2. `classifier-agent`
   - Purpose: classify short text into one label.
   - Output: `label`, `confidence`, and a short rationale.

## Local Commands

- Run heartbeat example:
  `python3 scripts/run_agent.py --agent starter-kit.heartbeat-agent --input catalog/projects/starter-kit/agents/heartbeat-agent/examples/example-input.json --pretty`
- Run classifier example:
  `python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty`
- Run classifier in LLM mode:
  `AGENT_MODE=llm python3 scripts/run_agent.py --agent starter-kit.classifier-agent --input catalog/projects/starter-kit/agents/classifier-agent/examples/example-input.json --pretty`
- Run tests:
  `python3 -m unittest discover -s tests -v`
