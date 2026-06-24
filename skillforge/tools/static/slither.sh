#!/usr/bin/env bash
# SKILLFORGE tool: Slither (crytic/slither) — Solidity static analysis.
# Usage: slither.sh <target>            target = path, or 0xADDR:CHAIN (etherscan/basescan)
# Real output only. Emits JSON to stdout. Exit 0 even with findings (findings != error).
set -uo pipefail
TARGET="${1:?usage: slither.sh <path|0xADDR>}"

if ! command -v slither >/dev/null 2>&1; then
  echo "[slither.sh] installing..." >&2
  pipx install slither-analyzer >/dev/null 2>&1 || pip install --quiet slither-analyzer >/dev/null 2>&1
fi
command -v slither >/dev/null 2>&1 || { echo '{"error":"slither install failed"}'; exit 1; }

echo "[slither.sh] version: $(slither --version 2>&1)" >&2
# JSON to stdout (- ). Slither returns nonzero when issues found; that is expected.
slither "$TARGET" --json - 2>/dev/null || true
