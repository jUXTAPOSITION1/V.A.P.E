// CLI runner for scan-parity CI (.github/workflows/scan-parity.yml) — prints
// {verdict, flags} as JSON so it can be diffed against agents/token_scan.py's
// output for the same address. Not used by the deployed worker itself.
import { scan } from "../src/scan";

const [, , address, chainArg] = process.argv;
if (!address) {
  console.error("usage: tsx scripts/run-scan.ts <0x_address> [chain_id]");
  process.exit(2);
}

scan(address, chainArg ? Number(chainArg) : 8453).then((r) => {
  if (r.error) {
    console.error(JSON.stringify(r));
    process.exit(1);
  }
  console.log(JSON.stringify({ verdict: r.verdict, flags: [...r.flags].sort() }));
});
