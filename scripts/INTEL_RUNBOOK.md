# VAPE Intel Sync Runbook (cron-driven)

Triggered by OpenClaw cron `vape-intel-sweep`. One consolidated agent turn per cycle.
First commandment: **max efficiency, lowest compute.** Do the whole sweep in ONE turn, write files, push once.

## Repo (persistent volume — survives container restarts)
`/home/node/.openclaw/repos/vape`  (git remote: jUXTAPOSITION1/V.A.P.E, branch main)

## Each cycle, produce these into `intel/reports/` using `intel/templates/`:
Naming: `<type>-YYYY-MM-DD-HH.md` (UTC hour, 2-digit).

1. **security-** — blockchain security sweep (exploits, incidents). web_search recent hacks/Immunefi/rekt.
2. **sentiment-** — X/narrative sentiment (use xurl/web_search on @based_vape lane + Base/Ethereum).
3. **base-** — Base chain health (TVL via DeFiLlama, gas, ecosystem). Include VAPE wallet line.
4. **macro-** — every other cycle only (macro & micro news, regulatory).
5. **broadcast-** — `intel/broadcasts/broadcast-YYYY-MM-DD-HH.md` consolidating the above.

(The **virtuals-** sweep type and ACP job/audit tracking were sunset 2026-07-31 — VAPE
refocused on Base/all-EVM/Ethereum with x402 as its sole commerce rail. Don't produce a
`virtuals-*.md` report or check for ACP activity in this runbook anymore.)

## Data sources (free, no LLM): 
- DeFiLlama: api.llama.fi/protocols , /v2/chains
- CoinGecko: api.coingecko.com/api/v3
- DexScreener, Basescan, GoPlusLabs
- web_search for incidents/news. xurl for X sentiment.

## SKILLFORGE pass (do this BEFORE persisting)
The deep work GitHub runners can't do. Each cycle:
1. Read `skillforge/memory/INDEX.md` + tail `findings.jsonl` (last 30) for current state.
2. **Mirror rule:** if you used ANY tool/API/analysis this cycle that is NOT in
   `skillforge/memory/tools-registry.json`, write a runnable wrapper under
   `skillforge/tools/<tier>/<name>.sh` and add a registry entry (status: untested).
3. Correlate the cycle's intel findings into `skillforge/memory/findings.jsonl`
   (real data only — actual incidents/CVEs/audit results, with refs).
4. If you learned a repeatable technique, append to `skillforge/memory/skills.jsonl`
   and (optionally) draft a `skillforge/skills/*.md` playbook.
5. Append one honest scorecard line to `skillforge/memory/lessons.jsonl`
   (what worked, what wasted compute, any bounty $ landed).
Keep it tight — this is one turn. `git add skillforge/` is included by intel_sync.sh.

## Persist (ALWAYS last step):
```
/home/node/.openclaw/repos/vape/scripts/intel_sync.sh "VAPE intel sync <stamp>"
```
This pulls, commits intel/ AND skillforge/, pushes. Pure git, zero LLM cost. Auto-syncs to HF.

## Efficiency rules
- ONE turn per cycle. Batch all web calls. Keep each report tight (template-sized).
- Skip a vertical if no signal — write "ALL CLEAR" briefly, don't pad.
- macro only on even cycles (00,08,16) to save compute.
- Never re-run a vertical mid-cycle.
