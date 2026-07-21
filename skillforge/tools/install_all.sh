#!/usr/bin/env bash
# SKILLFORGE tool: install every static/symbolic-analysis tool VAPE's deep-dive
# audit pipeline needs (Slither, Mythril, Halmos, Foundry, Aderyn), idempotently.
#
# Each wrapper script under skillforge/tools/{static,symbolic,fuzzing}/*.sh
# already does "install if missing, else no-op" as its own first step before
# running the tool — but calling one bare (with no target) fails on its own
# required-arg check before it ever reaches that install line. This script
# extracts just the install logic (same exact commands) so a CI job can
# provision every tool up front with a single, argument-free call, before
# ever needing a real target to run against.
#
# Usage: install_all.sh   (no args — installs only, runs nothing)
set -uo pipefail

echo "[install_all] slither..." >&2
command -v slither >/dev/null 2>&1 || {
  pipx install slither-analyzer >/dev/null 2>&1 || pip install --quiet slither-analyzer >/dev/null 2>&1
}

echo "[install_all] mythril..." >&2
command -v myth >/dev/null 2>&1 || pip install --quiet mythril >/dev/null 2>&1

echo "[install_all] halmos..." >&2
command -v halmos >/dev/null 2>&1 || pip install --quiet halmos >/dev/null 2>&1

echo "[install_all] foundry (forge)..." >&2
if ! command -v forge >/dev/null 2>&1; then
  mkdir -p "$HOME/.local/bin"
  TAG=$(curl -s https://api.github.com/repos/foundry-rs/foundry/releases/latest | grep -m1 tag_name | cut -d'"' -f4)
  curl -fsSL "https://github.com/foundry-rs/foundry/releases/download/${TAG}/foundry_${TAG}_linux_amd64.tar.gz" \
    | tar xz -C "$HOME/.local/bin" 2>/dev/null
fi
export PATH="$HOME/.local/bin:$PATH"

echo "[install_all] aderyn..." >&2
if ! command -v aderyn >/dev/null 2>&1; then
  # Confirmed broken: the old Cyfrin/aderyn/dev/cyfrinup/install URL 404s
  # (verified directly — Cyfrin's real cyfrinup lives in the separate
  # Cyfrin/up repo, not a branch of Cyfrin/aderyn), which silently no-opped
  # this install on every single run. Cyfrin's own aderyn-installer.sh
  # release asset (what cyfrinup's dynamic_script calls internally anyway)
  # installs the prebuilt binary directly — one step, no Rust toolchain,
  # no intermediate cyfrinup tool needed at all.
  mkdir -p "$HOME/.cyfrin/bin"
  ADERYN_INSTALLER=$(mktemp)
  if curl --proto '=https' --tlsv1.2 -fsSL -o "$ADERYN_INSTALLER" https://github.com/cyfrin/aderyn/releases/latest/download/aderyn-installer.sh 2>/dev/null; then
    bash "$ADERYN_INSTALLER" >/dev/null 2>&1
  fi
  rm -f "$ADERYN_INSTALLER"
fi
export PATH="$HOME/.cyfrin/bin:$PATH"

echo "[install_all] versions:" >&2
command -v slither >/dev/null 2>&1 && echo "  slither: $(slither --version 2>&1)" >&2 || echo "  slither: MISSING" >&2
command -v myth >/dev/null 2>&1 && echo "  mythril: $(myth version 2>&1 | head -1)" >&2 || echo "  mythril: MISSING" >&2
command -v halmos >/dev/null 2>&1 && echo "  halmos: $(halmos --version 2>&1)" >&2 || echo "  halmos: MISSING" >&2
command -v forge >/dev/null 2>&1 && echo "  forge: $(forge --version 2>&1)" >&2 || echo "  forge: MISSING" >&2
command -v aderyn >/dev/null 2>&1 && echo "  aderyn: $(aderyn --version 2>&1)" >&2 || echo "  aderyn: MISSING" >&2
