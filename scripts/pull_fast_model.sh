#!/usr/bin/env bash
set -euo pipefail

docker compose up -d ollama
docker compose exec ollama ollama pull llama3.2:3b
echo "Model ready: llama3.2:3b"
