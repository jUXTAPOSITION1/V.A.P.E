#!/usr/bin/env bash
# SKILLFORGE tool: promptfoo (promptfoo/promptfoo) — prompt/agent/RAG red-team + eval.
# Usage: promptfoo.sh <command...>   e.g. promptfoo.sh redteam run -c redteam.yaml
#        promptfoo.sh redteam init   (scaffold an adversarial config)
set -uo pipefail
[ $# -ge 1 ] || { echo "usage: promptfoo.sh <command...>"; exit 2; }

if ! command -v promptfoo >/dev/null 2>&1; then
  echo "[promptfoo.sh] installing globally via npm..." >&2
  npm install -g promptfoo >/dev/null 2>&1
fi
command -v promptfoo >/dev/null 2>&1 || { echo '{"error":"promptfoo install failed"}'; exit 1; }

echo "[promptfoo.sh] version: $(promptfoo --version 2>&1 | head -1)" >&2
promptfoo "$@" 2>&1 || true
