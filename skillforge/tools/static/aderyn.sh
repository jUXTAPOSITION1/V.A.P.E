#!/usr/bin/env bash
# SKILLFORGE tool: Aderyn (Cyfrin/aderyn) — Rust Solidity AST analyzer.
# Usage: aderyn.sh <project_dir>   (a Foundry/Hardhat project root)
set -uo pipefail
PROJ="${1:?usage: aderyn.sh <project_dir>}"

if ! command -v aderyn >/dev/null 2>&1; then
  # See skillforge/tools/install_all.sh's matching comment: the old
  # Cyfrin/aderyn/dev/cyfrinup/install URL 404s (confirmed) — this is
  # Cyfrin's real aderyn-installer.sh release asset, one step, no Rust
  # toolchain, no intermediate cyfrinup tool.
  echo "[aderyn.sh] installing prebuilt binary..." >&2
  mkdir -p "$HOME/.cyfrin/bin"
  ADERYN_INSTALLER=$(mktemp)
  if curl --proto '=https' --tlsv1.2 -fsSL -o "$ADERYN_INSTALLER" https://github.com/cyfrin/aderyn/releases/latest/download/aderyn-installer.sh 2>/dev/null; then
    bash "$ADERYN_INSTALLER" >/dev/null 2>&1
  fi
  rm -f "$ADERYN_INSTALLER"
fi
command -v aderyn >/dev/null 2>&1 || { echo '{"error":"aderyn install failed"}'; exit 1; }

echo "[aderyn.sh] version: $(aderyn --version 2>&1)" >&2
aderyn "$PROJ" -o /dev/stdout 2>/dev/null || true
