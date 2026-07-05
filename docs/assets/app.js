const REPO = "jUXTAPOSITION1/V.A.P.E";
const RAW = `https://raw.githubusercontent.com/${REPO}/main`;
// The vape-x402 worker's base URL — backs the free Alchemy-powered
// /portfolio, /nfts, /network-status routes (more reliable + full token/NFT
// auto-discovery vs. the public mainnet.base.org RPC + curated token list)
// and the priced /scan/* x402 offerings. Deployed on Deno Deploy (see
// worker/README.md's "Alternative: Deno Deploy" section — the Cloudflare
// path hit an account-level workers.dev subdomain bug). Every caller below
// still falls back to its direct-API path if this ever returns an error, so
// the site keeps working even if the worker is down.
//
// IMPORTANT: this must be Deno Deploy's stable *production* URL (the one
// shown at the top of the project's Overview page), not an individual
// build's preview URL (e.g. "vape-8kje756vhqqy.deno.net") — preview URLs are
// frozen forever at whatever code was live for that one build and never
// receive later pushes, which is exactly what caused the x402 hire flow to
// keep failing with a stale CORS config after the fix had already shipped.
const WORKER_BASE = "https://vape.juxtaposition1.deno.net";
const fmtUsd = n => n==null ? "—" : (n>=1e9 ? "$"+(n/1e9).toFixed(2)+"B" : n>=1e6 ? "$"+(n/1e6).toFixed(1)+"M" : "$"+Number(n).toLocaleString());
const pct = n => (typeof n==="number") ? `<span class="${n>=0?'text-emerald-400':'text-rose-400'}">${n>=0?'+':''}${n.toFixed(2)}%</span>` : "";

// Every successful x402 hire gets saved here (browser localStorage, keyed by
// the paying wallet) so "Portfolio Intelligence" can show a persistent
// engagement history with no backend — same zero-cost, keyless philosophy as
// the rest of the site. Scope: this device/browser only, not synced across
// devices; that's an honest limitation of a no-backend design, not a bug.
const CaseHistory = {
    KEY: 'vape_case_history_v1',
    MAX_ENTRIES: 200,
    _all() {
        try { return JSON.parse(localStorage.getItem(this.KEY) || '[]'); } catch (e) { return []; }
    },
    save(record) {
        const all = this._all();
        all.unshift({ id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, timestamp: Date.now(), ...record });
        try { localStorage.setItem(this.KEY, JSON.stringify(all.slice(0, this.MAX_ENTRIES))); } catch (e) { /* storage full/unavailable — non-fatal */ }
    },
    forWallet(address) {
        if (!address) return [];
        const a = address.toLowerCase();
        return this._all().filter(c => (c.walletAddress || '').toLowerCase() === a);
    },
};
window.CaseHistory = CaseHistory;
// app.js is a classic script; wallet.js/profile.js are ES modules with their own
// top-level scope, so top-level const bindings here aren't visible to them
// unless explicitly published on window.
window.fmtUsd = fmtUsd;
window.pct = pct;
window.WORKER_BASE = WORKER_BASE;

const App = {
    async refresh() {
        document.getElementById('live-label').textContent = 'SYNCING';
        await Promise.allSettled([this.metrics(), this.protocols(), this.bounties(), this.bountyCommand(), this.reports(), this.chart(this._days||30), this.reputation(), this.intel()]);
        document.getElementById('live-label').textContent = 'LIVE';
        document.getElementById('last-sync').textContent = 'synced ' + new Date().toLocaleTimeString();
    },

    // Bounty Command Center telemetry strip + VAPE's own audit track record.
    // opportunities.json is the same real feed bounties() renders cards from;
    // this just adds the aggregate counts and the separate poc-reports ledger.
    async bountyCommand() {
        try {
            const data = await (await fetch(`${RAW}/intel/bounty-radar/opportunities.json?t=`+Date.now())).json();
            const list = Array.isArray(data) ? data : [];
            const liveStatuses = new Set(['live','active']);
            const live = list.filter(o => liveStatuses.has((o.status||'').toLowerCase())).length;
            const platforms = new Set(list.map(o=>o.platform).filter(Boolean));
            this._set('bcc-total', list.length.toLocaleString());
            this._set('bcc-live', live.toLocaleString());
            this._set('bcc-platforms', platforms.size);
            document.getElementById('bcc-updated').textContent = 'radar synced ' + new Date().toLocaleTimeString();
        } catch(e) {
            document.getElementById('bcc-updated').textContent = 'radar telemetry unavailable';
        }

        const auditEl = document.getElementById('bcc-audit-list');
        try {
            const items = await (await fetch(`https://api.github.com/repos/${REPO}/contents/intel/audits/poc-reports`)).json();
            const files = (Array.isArray(items)?items:[]).filter(f=>f.name.endsWith('.md'))
                .map(f=>{
                    const stopped = /-STOPPED/.test(f.name);
                    const m = f.name.match(/(\d{4}-\d{2}-\d{2})/);
                    const base = f.name.replace(/\.md$/,'').replace(/-STOPPED/,'').replace(/^(audit|lead)-/,'').replace(/-\d{4}-\d{2}-\d{2}$/,'');
                    return { name: base.replace(/-/g,' '), stopped, date: m?m[1]:'', url: f.html_url, isAudit: f.name.startsWith('audit-') };
                })
                .sort((a,b)=>b.date.localeCompare(a.date));
            this._set('bcc-audits', files.filter(f=>f.isAudit).length);
            if (!files.length) throw 0;
            auditEl.innerHTML = files.map(f => `
                <a href="${f.url}" target="_blank" class="card-h glass rounded-xl p-4 block">
                    <div class="flex items-center justify-between gap-2 mb-1.5">
                        <i class="fa-solid ${f.stopped?'fa-ban text-zinc-500':'fa-file-shield text-emerald-500'}"></i>
                        <span class="text-[10px] px-2 py-0.5 rounded ${f.stopped?'bg-white/5 text-zinc-500':'bg-emerald-500/10 text-emerald-500'}">${f.stopped?'Lead stopped':'Audit filed'}</span>
                    </div>
                    <div class="font-semibold text-xs leading-snug capitalize">${this._esc(f.name)}</div>
                    <div class="text-[10px] text-zinc-500 mt-1">${f.date}</div>
                </a>`).join('');
        } catch(e) {
            auditEl.innerHTML = '<div class="sm:col-span-2 lg:col-span-4 text-zinc-500 text-sm">No audits filed yet — <a class="text-cyan-400" href="https://github.com/'+REPO+'/tree/main/intel/audits/poc-reports" target="_blank">browse the audit ledger</a>.</div>';
        }
    },

    _rep: null,
    async reputation() {
        try {
            if (!this._rep) this._rep = await (await fetch(`${RAW}/data/reputation.json?t=`+Date.now())).json();
            const r = this._rep, a = r.verifiable_activity||{}, c = r.capabilities||{}, id = r.identity||{};
            const set = (el,v)=>{const n=document.getElementById(el); if(n) n.textContent = (v==null?'—':Number(v).toLocaleString());};
            set('rep-reports', a.reports_published);
            set('rep-broadcasts', a.intel_broadcasts);
            set('rep-investigations', a.catalog_investigations);
            set('rep-tools', a.tools_verified);
            set('rep-tools-built', a.tools_built);
            set('rep-offerings', c.offerings_live);
            set('agent-status-offerings', c.offerings_live);
            set('rep-skills', a.skills_codified);
            this._renderWorkshop(a.tools_built_list || [], r.generated);
            const vlink = document.getElementById('rep-verify');
            if (vlink && id.verify_identity) vlink.href = id.verify_identity;
            const allOfferings = Array.isArray(c.offerings) ? c.offerings : [];
            const x402able = allOfferings.filter(o=>o.x402 ?? o.auto);
            const manual = allOfferings.filter(o=>!o.auto);
            const grid = document.getElementById('rep-offerings-grid');
            if (grid) {
                grid.innerHTML = x402able.map(o=>`
                    <button onclick="Hire.openX402('${o.name}', ${o.price_usd})" class="text-left bg-white/5 hover:bg-white/10 hover:ring-1 hover:ring-cyan-500/50 transition rounded-xl p-3 flex flex-col gap-1 cursor-pointer">
                      <div class="flex items-center justify-between gap-2">
                        <span class="font-mono text-xs text-zinc-200">${o.name}</span>
                        <span class="font-display text-cyan-400 text-sm whitespace-nowrap">$${o.price_usd}</span>
                      </div>
                      <div class="text-[11px] text-zinc-500 leading-snug">${o.summary}</div>
                      <span class="text-[9px] text-cyan-400/80 uppercase tracking-wider"><i class="fa-solid fa-bolt"></i> x402 · ${o.sla && o.sla!=='instant' ? this._esc(o.sla) : 'select to initiate'}</span>
                    </button>`).join('');
            }
            const acpGrid = document.getElementById('acp-offerings-grid');
            if (acpGrid) {
                acpGrid.innerHTML = manual.map(o=>`
                    <button onclick="Hire.openAcp('${o.name}')" class="text-left bg-white/5 hover:bg-white/10 hover:ring-1 hover:ring-amber-500/50 transition rounded-xl p-3 flex flex-col gap-1 cursor-pointer">
                      <div class="flex items-center justify-between gap-2">
                        <span class="font-mono text-xs text-zinc-200">${o.name}</span>
                        <span class="font-display text-amber-300 text-sm whitespace-nowrap">$${o.price_usd}</span>
                      </div>
                      <div class="text-[11px] text-zinc-500 leading-snug">${o.summary}</div>
                      <span class="text-[9px] text-brass-400 uppercase tracking-wider" style="color:var(--brass)"><i class="fa-solid fa-scale-balanced"></i> ACP · select to commission</span>
                    </button>`).join('');
            }
            const disc = document.getElementById('rep-disclaimer');
            if (disc) disc.textContent = (r.disclaimer||'') + (a.first_report?` · Active since ${a.first_report.replace(/(\d{4})(\d{2})(\d{2})/,'$1-$2-$3')}.`:'');
        } catch(e){
            const grid = document.getElementById('rep-offerings-grid');
            if (grid) grid.innerHTML = '<div class="text-amber-400 text-xs">Reputation feed unavailable (regenerating).</div>';
        }
    },

    // "The Workshop" — real PRs opened by VAPE's own build pipelines
    // (agents/build_request.py, agents/skillforge_build.py), pre-fetched and
    // filtered server-side in agents/publish_reputation.py::tool_builds() so
    // the browser never needs its own GitHub Search API call/rate limit.
    _renderWorkshop(builds, generatedAt) {
        const el = document.getElementById('workshop-body');
        if (!el) return;
        const upd = document.getElementById('workshop-updated');
        if (upd) upd.textContent = 'ledger ' + this._ago(generatedAt);
        if (!builds.length) {
            el.innerHTML = `<div class="md:col-span-2 text-center py-8 text-zinc-500 text-sm">
                <i class="fa-solid fa-drafting-compass text-2xl mb-3 opacity-50 block"></i>
                No open build proposals right now — the last cycle found no gap worth building against
                (tool registry clean, no fresh findings to ground a proposal in). Checks run 2x/day automatically.
            </div>`;
            return;
        }
        const statusStyle = { merged: ['#10b981','Merged'], open: ['#22d3ee','Open · awaiting review'], closed: ['#71717a','Closed'] };
        el.innerHTML = builds.map(b => {
            const [col, label] = statusStyle[b.status] || statusStyle.closed;
            const v = b.verification || {};
            const vBits = [];
            if (v.ok) vBits.push(`<span class="text-emerald-400">✅ ${v.ok}</span>`);
            if (v.warn) vBits.push(`<span class="text-amber-400">⚠️ ${v.warn}</span>`);
            if (v.fail) vBits.push(`<span class="text-rose-400">❌ ${v.fail}</span>`);
            return `
            <a href="${b.url}" target="_blank" rel="noopener" class="card-h glass rounded-xl p-4 block">
                <div class="flex items-start justify-between gap-2 mb-1.5">
                    <div class="font-semibold text-sm leading-snug min-w-0">${this._esc(b.title)}</div>
                    <span class="text-[10px] px-2 py-0.5 rounded shrink-0 whitespace-nowrap" style="color:${col};background:${col}1a">${label}</span>
                </div>
                <div class="text-xs text-zinc-500 flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span class="text-indigo-400">${b.kind==='self-directed'?'VAPE self-directed':'Human-requested'}</span>
                    <span>· #${b.number} · ${this._ago(b.created_at)}</span>
                    ${vBits.length?`<span>· verify: ${vBits.join(' ')}</span>`:''}
                </div>
            </a>`;
        }).join('');
    },

    _tvlHist: null, _chart: null,
    async chart(days=30) {
        try {
            if (!this._tvlHist) {
                const raw = await (await fetch('https://api.llama.fi/v2/historicalChainTvl/Base')).json();
                this._tvlHist = raw.map(p => ({ t: p.date*1000, v: p.tvl }));
            }
            const slice = this._tvlHist.slice(-days);
            const labels = slice.map(p => new Date(p.t).toLocaleDateString(undefined,{month:'short',day:'numeric'}));
            const data = slice.map(p => p.v);
            const ctx = document.getElementById('tvlChart');
            if (this._chart) this._chart.destroy();
            const g = ctx.getContext('2d').createLinearGradient(0,0,0,200);
            g.addColorStop(0,'rgba(34,211,238,0.35)'); g.addColorStop(1,'rgba(34,211,238,0)');
            this._chart = new Chart(ctx, {
                type:'line',
                data:{ labels, datasets:[{ data, borderColor:'#22d3ee', backgroundColor:g, fill:true, tension:0.25, pointRadius:0, borderWidth:2 }]},
                options:{ responsive:true, maintainAspectRatio:true, plugins:{legend:{display:false},
                    tooltip:{callbacks:{label:c=>'$'+(c.parsed.y/1e9).toFixed(3)+'B'}}},
                    scales:{ y:{ticks:{color:'#52525b',callback:v=>'$'+(v/1e9).toFixed(1)+'B'},grid:{color:'rgba(255,255,255,0.04)'}},
                             x:{ticks:{color:'#52525b',maxTicksLimit:8},grid:{display:false}} } }
            });
        } catch(e){ document.getElementById('tvlChart').insertAdjacentHTML('afterend','<div class="text-amber-400 text-sm mt-2">TVL history unavailable.</div>'); }
    },

    // Hard-reject GoPlus fields — same tier as honeypot, not just an advisory
    // flag. Real, documented GoPlus token_security fields, flat "0"/"1"
    // strings like their siblings (is_mintable etc.) below. Kept in its own
    // list so agents/token_scan.py / worker/src/scan.ts stay field-for-field
    // identical (see .github/workflows/scan-parity.yml for the CI half of
    // that guarantee — this browser path is the manually-reviewed third).
    _HARD_REJECT_FIELDS: ['is_blacklisted', 'selfdestruct', 'is_airdrop_scam'],

    renderScanResult(el, addr, chain, gp, liq, pairs) {
        pairs = pairs || [];
        const flags = [];
        if (gp.is_honeypot==='1') flags.push('HONEYPOT');
        if (parseFloat(gp.buy_tax)>0.1) flags.push('buy tax '+(gp.buy_tax*100).toFixed(0)+'%');
        if (parseFloat(gp.sell_tax)>0.1) flags.push('sell tax '+(gp.sell_tax*100).toFixed(0)+'%');
        if (gp.is_mintable==='1') flags.push('mintable');
        if (gp.owner_address && gp.owner_address!=='0x0000000000000000000000000000000000000000') flags.push('owner not renounced');
        if (liq>0 && liq<10000) flags.push('low liquidity');
        this._HARD_REJECT_FIELDS.forEach(field => { if (gp[field]==='1') flags.push(field.replace(/_/g,' ')); });
        const lpHolders = (gp.lp_holder_count!=null && gp.lp_holder_count!=='') ? parseInt(gp.lp_holder_count,10) : null;
        if (lpHolders!=null && !isNaN(lpHolders) && lpHolders<=1) flags.push('LP concentrated (1 holder)');
        const holders = (gp.holder_count!=null && gp.holder_count!=='') ? parseInt(gp.holder_count,10) : null;
        if (holders!=null && !isNaN(holders) && holders<50) flags.push('low holder count');
        const pairCreatedTimes = pairs.map(p=>p.pairCreatedAt).filter(Boolean);
        const pairCreatedMs = pairCreatedTimes.length ? Math.min(...pairCreatedTimes) : null;
        if (pairCreatedMs && (Date.now()-pairCreatedMs)/86400000 < 3) flags.push('fresh launch (<3 days)');
        const hasSocials = pairs.some(p => (p.info?.socials?.length>0) || (p.info?.websites?.length>0));
        if (!hasSocials) flags.push('no declared socials');
        const hardReject = gp.is_honeypot==='1' || this._HARD_REJECT_FIELDS.some(field => gp[field]==='1');
        const verdict = hardReject ? ['REJECT','#fb7185'] : (flags.length>=2 ? ['CAUTION','#fbbf24'] : ['PROCEED','#10b981']);
        const vc = verdict[1];
        const name = gp.token_name ? `${this._esc(gp.token_name)} (${this._esc(gp.token_symbol)})` : this._shortAddr(addr);
        el.innerHTML = `
            <div class="glass rounded-2xl p-5">
                <div class="flex items-center justify-between mb-3">
                    <a href="${this._explorerUrl(addr, chain)}" target="_blank" rel="noopener" class="flex items-center gap-2 min-w-0 hover:opacity-80">
                        ${this._iconImg(addr, chain, 28)}
                        <div class="font-semibold truncate">${name}</div>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-60 shrink-0"></i>
                    </a>
                    <span class="px-3 py-1 rounded-lg font-display shrink-0" style="color:${vc};background:${vc}1a">${verdict[0]}</span>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div><div class="text-zinc-500">Holders</div><div class="stat">${gp.holder_count?Number(gp.holder_count).toLocaleString():'—'}</div></div>
                    <div><div class="text-zinc-500">Liquidity</div><div class="stat">${liq?fmtUsd(liq):'—'}</div></div>
                    <div><div class="text-zinc-500">Honeypot</div><div class="${gp.is_honeypot==='1'?'text-rose-400':'text-emerald-500'}">${gp.is_honeypot==='1'?'YES':'no'}</div></div>
                    <div><div class="text-zinc-500">Buy/Sell tax</div><div>${gp.buy_tax!=null?(gp.buy_tax*100).toFixed(1):'?'}% / ${gp.sell_tax!=null?(gp.sell_tax*100).toFixed(1):'?'}%</div></div>
                </div>
                <div class="mt-3 text-xs">${flags.length?flags.map(f=>`<span class="inline-block rounded px-2 py-0.5 mr-1 mb-1" style="color:${vc};background:${vc}1a">${f}</span>`).join(''):'<span class="text-emerald-500">No risk flags from real on-chain scan.</span>'}</div>
                <div class="mt-2 text-[10px] text-zinc-600">Real data: GoPlus token_security + DexScreener liquidity. Not investment advice.</div>
            </div>`;
        return verdict[0];
    },

    async hunt() {
        const el = document.getElementById('hunt-result');
        const addr = (document.getElementById('hunt-target').value||'').trim();
        const chain = document.getElementById('hunt-chain').value;
        if (!/^0x[a-fA-F0-9]{40}$/.test(addr)) { el.innerHTML = '<span class="text-amber-400">Enter a valid 0x… 40-hex contract address.</span>'; return; }
        el.innerHTML = '<span class="text-cyan-400"><i class="fa-solid fa-spinner fa-spin"></i> Assessing real data (GoPlus + DexScreener)…</span>';
        try {
            const [gpR, dsR] = await Promise.allSettled([
                fetch(`https://api.gopluslabs.io/api/v1/token_security/${chain}?contract_addresses=${addr}`).then(r=>r.json()),
                fetch(`https://api.dexscreener.com/latest/dex/tokens/${addr}`).then(r=>r.json())
            ]);
            const gp = gpR.status==='fulfilled' ? (Object.values(gpR.value.result||{})[0]||{}) : {};
            const pairs = dsR.status==='fulfilled' ? (dsR.value.pairs||[]) : [];
            const liq = pairs.reduce((s,p)=>s+(p.liquidity?.usd||0),0);
            this.renderScanResult(el, addr, chain, gp, liq, pairs);
        } catch(e){ el.innerHTML = '<span class="text-amber-400">Scan failed (rate limit or unsupported token). Try again.</span>'; }
    },

    async metrics() {
        // DefiLlama TVL
        try {
            const chains = await (await fetch('https://api.llama.fi/v2/chains')).json();
            const base = chains.find(c => (c.name||'').toLowerCase()==='base');
            document.getElementById('m-tvl').classList.remove('skeleton');
            document.getElementById('m-tvl').textContent = base ? fmtUsd(base.tvl) : '—';
            this._tvl = base?.tvl;
        } catch(e){ this._set('m-tvl','—'); }

        // Base block + gas — prefer the Alchemy-backed worker endpoint (more
        // reliable, keyless from the browser's perspective) and fall back to
        // the public RPC directly if the worker isn't deployed/configured.
        try {
            let block, gasGwei;
            if (WORKER_BASE) {
                try {
                    const s = await (await fetch(`${WORKER_BASE}/network-status`)).json();
                    if (typeof s.blockNumber === 'number') { block = s.blockNumber; gasGwei = s.gasPriceGwei; }
                } catch (e) { /* fall through to public RPC */ }
            }
            if (block == null) {
                const rpc = (m,p=[]) => fetch('https://mainnet.base.org',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:m,params:p,id:1})}).then(r=>r.json());
                const [bn, gp] = await Promise.all([rpc('eth_blockNumber'), rpc('eth_gasPrice')]);
                block = parseInt(bn.result,16);
                gasGwei = parseInt(gp.result,16)/1e9;
            }
            this._set('m-block', block.toLocaleString());
            this._set('m-gas', gasGwei.toFixed(3));
        } catch(e){ this._set('m-block','—'); this._set('m-gas','—'); }

        // Prices
        try {
            const p = await (await fetch('https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin&vs_currencies=usd&include_24hr_change=true')).json();
            this._ethPrice = p.ethereum.usd;
            this._set('m-price', `$${Math.round(p.ethereum.usd).toLocaleString()} / $${Math.round(p.bitcoin.usd).toLocaleString()}`);
        } catch(e){ this._set('m-price','—'); }
    },

    async protocols() {
        const el = document.getElementById('protocols');
        try {
            const list = await (await fetch('https://api.llama.fi/protocols')).json();
            const base = list.filter(p => (p.chains||[]).includes('Base') && p.category!=='CEX' && (p.chainTvls?.Base>0))
                .map(p => ({name:p.name, slug:p.slug, tvl:p.chainTvls.Base, c1:p.change_1d, cat:p.category, logo:p.logo}))
                .sort((a,b)=>b.tvl-a.tvl).slice(0,8);
            el.innerHTML = base.map((p,i)=>`
                <div class="card-h glass rounded-xl px-3 sm:px-4 py-3 flex items-center gap-2 sm:gap-3">
                    <span class="text-zinc-600 text-sm w-4 sm:w-5 shrink-0">${i+1}</span>
                    ${p.logo?`<img src="${p.logo}" alt="" width="24" height="24" class="rounded-full bg-white/5 object-cover shrink-0 sm:w-7 sm:h-7" onerror="this.remove()">`:''}
                    <div class="min-w-0 flex-1">
                        <div class="font-semibold truncate">${p.name}</div>
                        <div class="text-xs text-zinc-500 truncate">${p.cat||''}</div>
                    </div>
                    <div class="spark shrink-0 hidden sm:block" data-slug="${p.slug||''}" style="width:72px;height:26px"></div>
                    <div class="text-right shrink-0 w-16 sm:w-24">
                        <div class="stat font-display text-sm sm:text-base">${fmtUsd(p.tvl)}</div>
                        <div class="text-xs">${pct(p.c1)}</div>
                    </div>
                </div>`).join('');
            this._sparklines();
            // anomaly flags (rule-based, client-side)
            const flags = [];
            if (typeof this._tvl==='number') {} // chain-level change not in v2/chains; protocol-level below
            base.forEach(p => { if (typeof p.c1==='number' && p.c1<=-20) flags.push(`${p.name} TVL ${p.c1.toFixed(1)}% in 24h — investigate`); });
            const an = document.getElementById('anomalies');
            an.querySelector('.skeleton')?.remove();
            an.innerHTML = flags.length ? flags.map(f=>`<div class="flex gap-2"><i class="fa-solid fa-triangle-exclamation text-amber-400 mt-0.5"></i><span>${f}</span></div>`).join('')
                : `<div class="flex gap-2 text-emerald-500"><i class="fa-solid fa-check"></i><span>No critical flags (rule-based pass)</span></div>`;
        } catch(e){ el.innerHTML = `<div class="text-amber-400 text-sm">Live protocol fetch unavailable.</div>`; }
    },

    _sparkCache: {},
    async _sparklines() {
        const nodes = [...document.querySelectorAll('.spark[data-slug]')].filter(n=>n.dataset.slug && !n._done);
        for (const n of nodes) {
            n._done = true;
            const slug = n.dataset.slug;
            try {
                let series = this._sparkCache[slug];
                if (!series) {
                    const d = await (await fetch(`https://api.llama.fi/protocol/${slug}`)).json();
                    const ct = d.chainTvls?.Base?.tvl || [];
                    series = ct.slice(-14).map(x=>x.totalLiquidityUSD||0);
                    this._sparkCache[slug] = series;
                }
                if (series.length < 2) continue;
                const min=Math.min(...series), max=Math.max(...series), W=72, H=26, pad=2, rng=(max-min)||1;
                const pts = series.map((v,i)=>{
                    const x = pad + i*(W-2*pad)/(series.length-1);
                    const y = H-pad - ((v-min)/rng)*(H-2*pad);
                    return `${x.toFixed(1)},${y.toFixed(1)}`;
                }).join(' ');
                const up = series[series.length-1] >= series[0];
                const col = up ? '#10b981' : '#fb7185';
                n.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><polyline fill="none" stroke="${col}" stroke-width="1.5" points="${pts}"/></svg>`;
                await new Promise(r=>setTimeout(r,120));
            } catch(e){ /* leave blank on failure */ }
        }
    },

    async bounties() {
        const el = document.getElementById('bounties');
        try {
            let data = await (await fetch(`${RAW}/intel/bounty-radar/opportunities.json?t=`+Date.now())).json();
            if (!Array.isArray(data)) data = [];
            data = data.sort((a,b)=>(b.prizeUsd||0)-(a.prizeUsd||0)).slice(0,6);
            if (!data.length) throw 0;
            el.innerHTML = data.map(b=>`
                <a href="${b.url||'#'}" target="_blank" class="card-h glass rounded-xl p-4 block">
                    <div class="flex items-start justify-between gap-2">
                        <div class="font-semibold text-sm leading-snug">${(b.name||'Unknown').replace(/</g,'&lt;')}</div>
                        <div class="text-cyan-400 font-display shrink-0">${b.prizeUsd?fmtUsd(b.prizeUsd):'—'}</div>
                    </div>
                    <div class="text-xs text-zinc-500 mt-2">${(b.platform||'')} ${b.status?'· '+b.status:''}</div>
                    ${(b.tags||[]).slice(0,4).map(t=>`<span class="inline-block text-[10px] bg-white/5 rounded px-1.5 py-0.5 mr-1 mt-2 text-zinc-400">${t}</span>`).join('')}
                </a>`).join('');
        } catch(e){
            el.innerHTML = `<div class="text-zinc-500 text-sm col-span-2">No live radar data yet — <a class="text-cyan-400" href="https://github.com/${REPO}/tree/main/intel/bounty-radar" target="_blank">browse intel</a>.</div>`;
        }
    },

    async reports() {
        const el = document.getElementById('reports');
        try {
            const items = await (await fetch(`https://api.github.com/repos/${REPO}/contents/reports`)).json();
            const md = (Array.isArray(items)?items:[]).filter(f=>f.name.endsWith('.md'))
                .map(f=>{ const m=f.name.match(/(\d{8})_(\d{6})/); f._ts=m?m[1]+m[2]:'0'; return f; })
                .sort((a,b)=>b._ts.localeCompare(a._ts)).slice(0,6);
            if (!md.length) throw 0;
            el.innerHTML = md.map(f=>`
                <a href="${f.html_url}" target="_blank" class="card-h glass rounded-lg px-4 py-2.5 flex items-center justify-between text-sm">
                    <span class="flex items-center gap-2 min-w-0"><i class="fa-solid fa-file-lines text-zinc-500"></i><span class="truncate">${f.name}</span></span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-zinc-600 text-xs shrink-0"></i>
                </a>`).join('');
        } catch(e){
            el.innerHTML = `<a href="https://github.com/${REPO}/tree/main/reports" target="_blank" class="text-cyan-400 text-sm">View all reports on GitHub →</a>`;
        }
    },

    // ── Intel index: investigation summary + explorer (from data/intel-index.json)
    _intel: null, _tab: 'investigations', _typeFilter: null,
    _verdictColor(v){
        v=(v||'').toUpperCase();
        if(/REJECT|CRITICAL|HIGH|BEARISH|RISK-OFF|FEAR/.test(v)) return '#fb7185';
        if(/CAUTION|MEDIUM|NEUTRAL/.test(v)) return '#fbbf24';
        if(/PROCEED|LOW|ALL CLEAR|BULLISH|RISK-ON|GREED/.test(v)) return '#10b981';
        return '#a1a1aa';
    },
    _pill(v){ if(!v) return ''; const c=this._verdictColor(v);
        return `<span class="px-2 py-0.5 rounded font-display text-[11px] whitespace-nowrap" style="color:${c};background:${c}1a">${v}</span>`; },
    _ago(iso){ if(!iso) return ''; const d=new Date(iso); if(isNaN(d)) return iso;
        const s=(Date.now()-d)/1e3; if(s<3600) return Math.floor(s/60)+'m ago';
        if(s<86400) return Math.floor(s/3600)+'h ago'; return Math.floor(s/86400)+'d ago'; },
    // Escapes quotes too, not just tag-relevant chars — several call sites
    // interpolate this into an HTML *attribute* value (e.g. title="${...}"),
    // and a target/name containing a bare `"` could otherwise break out of
    // the attribute and inject a new one (CodeQL: incomplete HTML attribute
    // sanitization). Real risk: on-chain token/contract names are attacker-
    // controlled data rendered here.
    _esc(t){ return (t||'').replace(/[<>&"']/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c])); },
    _shortAddr(a){ return (a && a.length>12) ? a.slice(0,6)+'…'+a.slice(-4) : (a||''); },
    _symFromTitle(t){ const m=(t||'').match(/Investigation\s*[—-]\s*(.+)$/); return m ? m[1].trim() : null; },
    _chainSlug(c){
        const s=String(c||'');
        if(/42161|arbitrum/i.test(s)) return 'arbitrum';
        if(/^1$|ethereum/i.test(s)) return 'ethereum';
        return 'base';
    },
    _tokenIcon(address, chain){
        if(!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) return null;
        return `https://dd.dexscreener.com/ds-data/tokens/${this._chainSlug(chain)}/${address.toLowerCase()}.png?size=lg`;
    },
    _explorerUrl(address, chain){
        if(!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) return null;
        const slug = this._chainSlug(chain);
        const host = slug==='arbitrum' ? 'arbiscan.io' : slug==='ethereum' ? 'etherscan.io' : 'basescan.org';
        return `https://${host}/address/${address}`;
    },
    _iconImg(address, chain, size=36, extra=''){
        const src = this._tokenIcon(address, chain);
        return src ? `<img src="${src}" alt="" width="${size}" height="${size}" class="rounded-full bg-white/5 object-cover shrink-0 ${extra}" onerror="this.remove()">` : '';
    },

    async intel(){
        try{
            if(!this._intel) this._intel = await (await fetch(`${RAW}/data/intel-index.json?t=`+Date.now())).json();
            const d=this._intel, c=d.counts||{};
            document.getElementById('inv-updated').textContent = 'index '+this._ago(d.generated);
            ['investigations','reports','broadcasts','tools'].forEach(k=>{
                const n=document.getElementById('c-'+k); if(n) n.textContent='('+((c[k])??0)+')';
            });
            // hero: latest investigation
            const inv=(d.latest_summary||{}).investigation;
            const iel=document.getElementById('inv-latest');
            if(inv){
                const sym = inv.symbol || this._symFromTitle(inv.title);
                const heading = sym || this._shortAddr(inv.target) || inv.title || 'target';
                const explorer = this._explorerUrl(inv.target, inv.chain);
                iel.innerHTML=`
                    <div class="flex items-center justify-between gap-2 mb-3">
                        <div class="text-[10px] uppercase tracking-widest text-zinc-500">Deep Investigation</div>
                        ${this._pill(inv.verdict)}
                    </div>
                    <a href="${explorer||'#'}" target="_blank" rel="noopener" class="flex items-center gap-3 mb-1 ${explorer?'hover:opacity-80':'pointer-events-none'}">
                        ${this._iconImg(inv.target, inv.chain, 40)}
                        <div class="min-w-0">
                            <div class="font-display text-lg leading-tight truncate">${this._esc(heading)}</div>
                            ${inv.target?`<div class="font-mono text-[11px] text-zinc-500 truncate" title="${this._esc(inv.target)}">${this._esc(this._shortAddr(inv.target))} ${explorer?'<i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-60"></i>':''}</div>`:''}
                        </div>
                    </a>
                    ${inv.score?`<div class="text-xs text-zinc-400 mt-2 mb-2">Safety score <span class="text-cyan-400 font-display">${inv.score}</span></div>`:''}
                    <div class="text-xs text-zinc-400 leading-relaxed break-words">${this._esc(inv.summary||inv.key_finding||'')}</div>
                    <a href="${inv.url}" target="_blank" class="inline-flex items-center gap-1.5 text-cyan-400 text-xs mt-3 hover:underline">Read full investigation <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i></a>`;
            } else { iel.innerHTML='<div class="text-zinc-500 text-sm">No investigation logged yet.</div>'; }
            // hero: latest report
            const rep=(d.latest_summary||{}).report;
            const rel=document.getElementById('inv-report');
            if(rep){
                rel.innerHTML=`
                    <div class="flex items-center justify-between gap-2 mb-2">
                        <div class="text-[10px] uppercase tracking-widest text-zinc-500">Latest Report · ${this._esc(rep.type||'')}</div>
                        ${this._pill(rep.threat)}
                    </div>
                    <div class="font-display text-lg leading-tight mb-1 break-words">${this._esc(rep.title||rep.file)}</div>
                    <div class="text-[11px] text-zinc-500 mb-2">${this._ago(rep.date)}</div>
                    <div class="text-xs text-zinc-400 leading-relaxed break-words">${this._esc((rep.summary||'').slice(0,260))}${(rep.summary||'').length>260?'…':''}</div>
                    <a href="${rep.url}" target="_blank" class="inline-flex items-center gap-1.5 text-cyan-400 text-xs mt-3 hover:underline">Open report <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i></a>`;
            } else { rel.innerHTML='<div class="text-zinc-500 text-sm">No report indexed.</div>'; }
            this._renderIntel();
        }catch(e){
            document.getElementById('intel-body').innerHTML='<div class="text-amber-400 text-sm">Intel index unavailable (regenerating next cycle).</div>';
        }
    },

    _renderIntel(){
        const d=this._intel; if(!d) return;
        const body=document.getElementById('intel-body');
        const fw=document.getElementById('intel-filter-wrap');
        const tab=this._tab;
        // type filter chips (reports only)
        if(tab==='reports'){
            const types=Object.keys(d.counts.reports_by_type||{}).sort((a,b)=>d.counts.reports_by_type[b]-d.counts.reports_by_type[a]);
            fw.classList.remove('hidden');
            document.getElementById('intel-filter').innerHTML=
                [['',' all']].concat(types.map(t=>[t,t])).map(([v,label])=>{
                    const on=(this._typeFilter||'')===v;
                    return `<button data-type="${v}" class="px-2 py-0.5 rounded ${on?'bg-cyan-600 text-black':'bg-white/5 hover:bg-white/10 text-zinc-300'}">${label}${v?` <span class="opacity-60">${d.counts.reports_by_type[v]}</span>`:''}</button>`;
                }).join('');
        } else { fw.classList.add('hidden'); }

        let rows='';
        if(tab==='investigations'){
            const items=d.investigations||[];
            rows=items.length?items.map(i=>{
                const sym = i.symbol || this._symFromTitle(i.title);
                const icon = this._iconImg(i.target, i.chain, 32, 'mt-0.5');
                return `
                <a href="${i.url}" target="_blank" class="card-h glass rounded-xl p-4 flex items-start gap-3">
                    ${icon || '<i class="fa-solid fa-magnifying-glass-chart text-cyan-400 mt-1"></i>'}
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center justify-between gap-2">
                            <span class="font-mono text-xs truncate min-w-0">${this._esc(sym || this._shortAddr(i.target) || i.title || 'target')}</span>
                            <span class="flex items-center gap-2 shrink-0">${i.score?`<span class="text-cyan-400 text-xs font-display">${i.score}</span>`:''}${this._pill(i.verdict)}</span>
                        </div>
                        <div class="text-xs text-zinc-500 mt-1 truncate">${i.target?`<span class="font-mono" title="${this._esc(i.target)}">${this._esc(this._shortAddr(i.target))}</span> · `:''}${this._esc(i.date||'')} · ${this._esc(i.offering||i.chain||'deep_investigation')}</div>
                        ${(i.summary||i.key_finding)?`<div class="text-[11px] text-zinc-400 mt-1 leading-snug break-words">${this._esc((i.summary||i.key_finding).slice(0,180))}</div>`:''}
                    </div>
                </a>`;
            }).join(''):'<div class="text-zinc-500 text-sm">No investigations logged yet.</div>';
        } else if(tab==='reports'){
            let items=d.reports||[];
            if(this._typeFilter) items=items.filter(r=>r.type===this._typeFilter);
            rows=items.slice(0,40).map(r=>`
                <a href="${r.url}" target="_blank" class="card-h glass rounded-xl p-4 flex items-start gap-3">
                    <i class="fa-solid fa-file-lines text-zinc-500 mt-1"></i>
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center justify-between gap-2">
                            <span class="font-semibold text-sm truncate min-w-0">${this._esc(r.title||r.file)}</span>
                            ${this._pill(r.threat)}
                        </div>
                        <div class="text-xs text-zinc-500 mt-1"><span class="text-indigo-400">${this._esc(r.type)}</span> · ${this._ago(r.date)}</div>
                        ${r.summary?`<div class="text-[11px] text-zinc-400 mt-1 leading-snug break-words">${this._esc(r.summary.slice(0,200))}${r.summary.length>200?'…':''}</div>`:''}
                    </div>
                </a>`).join('')||'<div class="text-zinc-500 text-sm">No reports for this filter.</div>';
        } else if(tab==='broadcasts'){
            const items=d.broadcasts||[];
            rows=items.length?items.map(b=>`
                <a href="${b.url}" target="_blank" class="card-h glass rounded-xl p-4 flex items-start gap-3">
                    <i class="fa-solid fa-tower-broadcast text-cyan-400 mt-1"></i>
                    <div class="min-w-0 flex-1">
                        <div class="font-semibold text-sm break-words">${this._esc(b.title||b.file)}</div>
                        <div class="text-xs text-zinc-500 mt-1">${this._ago(b.date)}</div>
                        ${b.summary?`<div class="text-[11px] text-zinc-400 mt-1 leading-snug break-words">${this._esc(b.summary.slice(0,200))}${b.summary.length>200?'…':''}</div>`:''}
                    </div>
                </a>`).join(''):'<div class="text-zinc-500 text-sm">No broadcasts yet.</div>';
        } else if(tab==='tools'){
            const items=d.tools||[];
            rows=items.length?items.map(t=>{
                const ok=t.status==='verified'; const lim=t.known_limitation;
                const col=ok?'#10b981':(lim?'#fbbf24':'#a1a1aa');
                return `<a href="${t.url||'#'}" target="_blank" class="card-h glass rounded-xl p-4 flex items-start gap-3">
                    <i class="fa-solid ${ok?'fa-circle-check':'fa-circle-dot'} mt-1" style="color:${col}"></i>
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center justify-between gap-2">
                            <span class="font-mono text-sm">${this._esc(t.name)}${t.version?`<span class="text-zinc-600"> v${this._esc(t.version)}</span>`:''}</span>
                            <span class="text-[11px] px-2 py-0.5 rounded" style="color:${col};background:${col}1a">${this._esc(t.status||'?')}</span>
                        </div>
                        <div class="text-xs text-zinc-500 mt-1"><span class="text-indigo-400">${this._esc(t.tier)}</span>${t.purpose?' · '+this._esc(t.purpose):''}</div>
                    </div>
                </a>`;
            }).join(''):'<div class="text-zinc-500 text-sm">No tools registered.</div>';
        }
        body.innerHTML=rows;
    },

    _set(id,v){ const e=document.getElementById(id); e.classList.remove('skeleton'); e.textContent=v; }
};
window.App = App;

// ── Scroll-reveal (plain IntersectionObserver, no library) ──────────────────
function initReveal() {
    const els = document.querySelectorAll('.reveal');
    if (!els.length) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        els.forEach(el => el.classList.add('in-view'));
        return;
    }
    const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) { e.target.classList.add('in-view'); io.unobserve(e.target); }
        });
    }, { threshold: 0.15 });
    els.forEach(el => io.observe(el));
}

window.addEventListener('load', () => {
    initReveal();
    App.refresh();
    setInterval(()=>App.refresh(), 300000);
    // chart range buttons
    document.getElementById('tvl-range').addEventListener('click', e => {
        const b = e.target.closest('button'); if (!b) return;
        App._days = +b.dataset.d;
        [...e.currentTarget.children].forEach(x=>{x.className='px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10';});
        b.className='px-2.5 py-1 rounded-lg bg-indigo-600';
        App.chart(App._days);
    });
    // Enter key launches hunt
    document.getElementById('hunt-target').addEventListener('keypress', e=>{ if(e.key==='Enter') App.hunt(); });
    // Intel Explorer tab switching
    document.getElementById('intel-tabs').addEventListener('click', e=>{
        const b=e.target.closest('button[data-tab]'); if(!b) return;
        App._tab=b.dataset.tab; App._typeFilter=null;
        [...e.currentTarget.querySelectorAll('button')].forEach(x=>x.className='px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10');
        b.className='px-3 py-1.5 rounded-lg bg-indigo-600';
        App._renderIntel();
    });
    // Report type filter
    document.getElementById('intel-filter').addEventListener('click', e=>{
        const b=e.target.closest('button[data-type]'); if(!b) return;
        App._typeFilter=b.dataset.type||null; App._renderIntel();
    });
});
