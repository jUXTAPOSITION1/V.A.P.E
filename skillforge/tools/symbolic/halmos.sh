#!/usr/bin/env bash
# SKILLFORGE tool: Halmos (a16z/halmos) — symbolic testing for Foundry projects.
# Reuses the project's own Solidity test suite as the spec: any function named
# check_<name>_<behavior>(...) is symbolically executed (bounded, Z3-backed)
# instead of fuzzed, proving no assertion violation exists in that bound
# rather than sampling random inputs. No separate spec language (unlike
# Certora's CVL) — write the property as a normal Foundry test function.
# Usage: halmos.sh <project_dir>   (a Foundry project root, forge already built)
set -uo pipefail
PROJ="${1:?usage: halmos.sh <project_dir>}"

if ! command -v halmos >/dev/null 2>&1; then
  echo "[halmos.sh] installing..." >&2
  pip install --quiet halmos >/dev/null 2>&1
fi
command -v halmos >/dev/null 2>&1 || { echo '{"error":"halmos install failed"}'; exit 1; }
command -v forge >/dev/null 2>&1 || { echo '{"error":"halmos needs a Foundry project (forge not found)"}'; exit 1; }

echo "[halmos.sh] version: $(halmos --version 2>&1)" >&2
cd "$PROJ" || exit 1
halmos 2>&1 || true
