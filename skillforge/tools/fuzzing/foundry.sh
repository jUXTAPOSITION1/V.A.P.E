#!/usr/bin/env bash
# SKILLFORGE tool: Foundry (foundry-rs/foundry) — forge fuzz/invariant + anvil fork PoC.
# Usage: foundry.sh <project_dir> [fuzz-runs]
set -uo pipefail
PROJ="${1:?usage: foundry.sh <project_dir> [fuzz-runs]}"
RUNS="${2:-1024}"

if ! command -v forge >/dev/null 2>&1; then
  echo "[foundry.sh] installing prebuilt binary..." >&2
  mkdir -p "$HOME/.local/bin"
  TAG=$(curl -s https://api.github.com/repos/foundry-rs/foundry/releases/latest | grep -m1 tag_name | cut -d'"' -f4)
  curl -fsSL "https://github.com/foundry-rs/foundry/releases/download/${TAG}/foundry_${TAG}_linux_amd64.tar.gz" | tar xz -C "$HOME/.local/bin" 2>/dev/null
  export PATH="$HOME/.local/bin:$PATH"
fi
command -v forge >/dev/null 2>&1 || { echo '{"error":"foundry install failed"}'; exit 1; }

echo "[foundry.sh] version: $(forge --version 2>&1)" >&2
cd "$PROJ" || exit 1
forge test --fuzz-runs "$RUNS" --json 2>/dev/null || true
