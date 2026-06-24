#!/usr/bin/env bash
# SKILLFORGE tool: Mythril (Consensys/mythril) — symbolic execution on EVM bytecode.
# Usage: mythril.sh <target.sol | -a 0xADDR>   ( -a for on-chain address via RPC )
set -uo pipefail
[ $# -ge 1 ] || { echo "usage: mythril.sh <target.sol|-a 0xADDR>"; exit 2; }

if ! command -v myth >/dev/null 2>&1; then
  echo "[mythril.sh] installing..." >&2
  pip install --quiet mythril >/dev/null 2>&1
fi
command -v myth >/dev/null 2>&1 || { echo '{"error":"mythril install failed"}'; exit 1; }

echo "[mythril.sh] version: $(myth version 2>&1)" >&2
myth analyze "$@" -o json 2>/dev/null || true
