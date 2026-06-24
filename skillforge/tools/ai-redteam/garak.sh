#!/usr/bin/env bash
# SKILLFORGE tool: garak (NVIDIA/garak) — LLM vulnerability scanner.
# Usage: garak.sh <model_type> <model_name> [probes]
#   e.g. garak.sh openai gpt-4o-mini encoding,dan,promptinject
# Real output only. Writes garak JSONL report path to stdout.
set -uo pipefail
MTYPE="${1:?usage: garak.sh <model_type> <model_name> [probes]}"
MNAME="${2:?model_name required}"
PROBES="${3:-}"

if ! python -m garak --version >/dev/null 2>&1; then
  echo "[garak.sh] installing (heavy: torch/transformers)..." >&2
  pip install --quiet garak >/dev/null 2>&1
fi
python -m garak --version >/dev/null 2>&1 || { echo '{"error":"garak install failed"}'; exit 1; }

echo "[garak.sh] $(python -m garak --version 2>&1 | head -1)" >&2
ARGS="--model_type $MTYPE --model_name $MNAME"
[ -n "$PROBES" ] && ARGS="$ARGS --probes $PROBES"
python -m garak $ARGS 2>&1 || true
