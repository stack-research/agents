# Architecture Notes

## Why this layout

- `catalog/projects` allows independent evolution by domain or team.
- A strict per-agent file set makes docs and validation scriptable.
- Project-level READMEs keep local context close to agents.

## Planned Evolution

- Add JSON schema for `agent.yaml`.
- Add lint/check script for required files.
- Add benchmark/eval fixtures for each agent.
