#!/usr/bin/env python3
"""
Ad hoc, read-only diagnostic for agents/defillama.py — prints the real
result of calling one of its functions against a live slug/chain/address, for
verifying a fix (or reproducing a user-reported bug) against real upstream
data. Must run from GitHub Actions (workflow_dispatch); this repo's dev
sandbox has no egress to api.llama.fi/coins.llama.fi/coingecko.com.

Usage: python scripts/diag_defillama.py <function> <arg>
  e.g. python scripts/diag_defillama.py unlocks aptos
       python scripts/diag_defillama.py chain_overview Aptos
"""
import json
import sys

sys.path.insert(0, ".")
import agents.defillama as dl


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    fn_name, arg = sys.argv[1], sys.argv[2]
    fn = getattr(dl, fn_name, None)
    if fn is None or not callable(fn):
        print(f"no such function: {fn_name}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(fn(arg), indent=2, default=str))


if __name__ == "__main__":
    main()
