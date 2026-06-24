#!/usr/bin/env bash
# SKILLFORGE tool: deepteam (confident-ai/deepteam) — LLM/agent red-teaming framework.
# deepteam is a Python library, not a CLI scanner. This wrapper runs a campaign script.
# Usage: deepteam.sh <campaign.py>   (a python file that builds + runs red_team())
#        deepteam.sh --check         (verify import + version only)
set -uo pipefail
ARG="${1:?usage: deepteam.sh <campaign.py | --check>}"

if ! python -c "import deepteam" >/dev/null 2>&1; then
  echo "[deepteam.sh] installing..." >&2
  pip install --quiet deepteam >/dev/null 2>&1
fi
python -c "import deepteam" >/dev/null 2>&1 || { echo '{"error":"deepteam install failed"}'; exit 1; }

VER=$(python -c "import importlib.metadata as m; print(m.version('deepteam'))" 2>/dev/null)
echo "[deepteam.sh] deepteam $VER" >&2

if [ "$ARG" = "--check" ]; then
  echo "{\"tool\":\"deepteam\",\"version\":\"$VER\",\"status\":\"importable\"}"
  exit 0
fi
[ -f "$ARG" ] || { echo "{\"error\":\"campaign file not found: $ARG\"}"; exit 1; }
python "$ARG" 2>&1 || true
