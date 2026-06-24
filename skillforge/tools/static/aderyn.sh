#!/usr/bin/env bash
# SKILLFORGE tool: Aderyn (Cyfrin/aderyn) — Rust Solidity AST analyzer.
# Usage: aderyn.sh <project_dir>   (a Foundry/Hardhat project root)
set -uo pipefail
PROJ="${1:?usage: aderyn.sh <project_dir>}"

if ! command -v aderyn >/dev/null 2>&1; then
  echo "[aderyn.sh] installing via cyfrinup..." >&2
  curl -fsSL https://raw.githubusercontent.com/Cyfrin/aderyn/dev/cyfrinup/install | bash >/dev/null 2>&1
  export PATH="$HOME/.cyfrin/bin:$PATH"
  command -v cyfrinup >/dev/null 2>&1 && cyfrinup >/dev/null 2>&1
fi
command -v aderyn >/dev/null 2>&1 || { echo '{"error":"aderyn install failed"}'; exit 1; }

echo "[aderyn.sh] version: $(aderyn --version 2>&1)" >&2
aderyn "$PROJ" -o /dev/stdout 2>/dev/null || true
