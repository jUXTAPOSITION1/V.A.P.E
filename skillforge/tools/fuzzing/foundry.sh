#!/usr/bin/env bash
# SKILLFORGE tool: Foundry (foundry-rs/foundry) — forge fuzz/invariant + anvil fork PoC.
# Usage: foundry.sh <project_dir> [fuzz-runs]
set -uo pipefail
PROJ="${1:?usage: foundry.sh <project_dir> [fuzz-runs]}"
RUNS="${2:-1024}"

if ! command -v forge >/dev/null 2>&1; then
  echo "[foundry.sh] installing via foundryup..." >&2
  curl -fsSL https://foundry.paradigm.xyz | bash >/dev/null 2>&1
  export PATH="$HOME/.foundry/bin:$PATH"
  command -v foundryup >/dev/null 2>&1 && foundryup >/dev/null 2>&1
fi
command -v forge >/dev/null 2>&1 || { echo '{"error":"foundry install failed"}'; exit 1; }

echo "[foundry.sh] version: $(forge --version 2>&1)" >&2
cd "$PROJ" || exit 1
forge test --fuzz-runs "$RUNS" --json 2>/dev/null || true
