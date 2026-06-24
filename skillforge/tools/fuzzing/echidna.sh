#!/usr/bin/env bash
# SKILLFORGE tool: Echidna (crytic/echidna) — property-based SC fuzzer.
# Usage: echidna.sh <contract.sol> <ContractName> [--test-mode property|assertion]
set -uo pipefail
SOL="${1:?usage: echidna.sh <contract.sol> <ContractName> [mode]}"
NAME="${2:?contract name required}"
MODE="${3:---test-mode property}"

if ! command -v echidna >/dev/null 2>&1; then
  echo "[echidna.sh] installing latest release..." >&2
  mkdir -p "$HOME/.local/bin"
  TAG=$(curl -s https://api.github.com/repos/crytic/echidna/releases/latest | grep -m1 tag_name | cut -d'"' -f4)
  curl -fsSL "https://github.com/crytic/echidna/releases/download/${TAG}/echidna-${TAG}-x86_64-linux.tar.gz" \
    | tar xz -C "$HOME/.local/bin" 2>/dev/null
  export PATH="$HOME/.local/bin:$PATH"
fi
command -v echidna >/dev/null 2>&1 || { echo '{"error":"echidna install failed"}'; exit 1; }

echo "[echidna.sh] version: $(echidna --version 2>&1)" >&2
echidna "$SOL" --contract "$NAME" $MODE --format json 2>/dev/null || true
