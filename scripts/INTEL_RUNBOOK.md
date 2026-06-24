# VAPE Intel Sync Runbook (cron-driven)

Triggered by OpenClaw cron `vape-intel-sweep`. One consolidated agent turn per cycle.
First commandment: **max efficiency, lowest compute.** Do the whole sweep in ONE turn, write files, push once.

## Repo (persistent volume — survives container restarts)
`/home/node/.openclaw/repos/vape`  (git remote: jUXTAPOSITION1/V.A.P.E, branch main)

## Each cycle, produce these into `intel/reports/` using `intel/templates/`:
Naming: `<type>-YYYY-MM-DD-HH.md` (UTC hour, 2-digit).

1. **security-** — blockchain security sweep (exploits, incidents). web_search recent hacks/Immunefi/rekt.
2. **sentiment-** — X/narrative sentiment (use xurl/web_search on @based_vape lane + Base/Virtuals).
3. **base-** — Base chain health (TVL via DeFiLlama, gas, ecosystem). Include VAPE wallet line.
4. **virtuals-** — Virtuals Protocol & ACP (VIRTUAL price, new agents, ACP marketplace).
5. **macro-** — every other cycle only (macro & micro news, regulatory).
6. **broadcast-** — `intel/broadcasts/broadcast-YYYY-MM-DD-HH.md` consolidating the above.

Optionally update `intel/catalog/investigation-catalog.md` if a new ACP audit/job ran.

## Data sources (free, no LLM): 
- DeFiLlama: api.llama.fi/protocols , /v2/chains
- CoinGecko: api.coingecko.com/api/v3
- DexScreener, Basescan, GoPlusLabs
- web_search for incidents/news. xurl for X sentiment.

## Persist (ALWAYS last step):
```
/home/node/.openclaw/repos/vape/scripts/intel_sync.sh "VAPE intel sync <stamp>"
```
This pulls, commits intel/, pushes. Pure git, zero LLM cost. Auto-syncs to HF via GitHub Action.

## Efficiency rules
- ONE turn per cycle. Batch all web calls. Keep each report tight (template-sized).
- Skip a vertical if no signal — write "ALL CLEAR" briefly, don't pad.
- macro only on even cycles (00,08,16) to save compute.
- Never re-run a vertical mid-cycle.
