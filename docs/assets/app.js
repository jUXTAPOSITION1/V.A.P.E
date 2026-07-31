const REPO = "jUXTAPOSITION1/V.A.P.E";
const RAW = `https://raw.githubusercontent.com/${REPO}/main`;
// The vape-x402 worker's base URL — backs the free Alchemy-powered
// /portfolio, /nfts, /network-status routes (more reliable + full token/NFT
// auto-discovery vs. the public mainnet.base.org RPC + curated token list)
// and the priced /scan/* x402 offerings. Every caller below still falls back
// to its direct-API path if this ever returns an error, so the site keeps
// working even if the worker is down.
//
// Cloudflare Workers is the primary deploy target (.github/workflows/
// deploy-worker.yml, which also runs a post-deploy smoke test against this
// exact URL on every deploy). worker/deno/ mirrors the identical src/index.ts
// on Deno Deploy as a documented fallback — switch this back to
// "https://vape.juxtaposition1.deno.net" with zero code changes if this
// Cloudflare account ever re-hits the workers.dev subdomain-registration bug
// described in worker/README.md's "Cloudflare + Deno Deploy" section.
//
// IMPORTANT: whichever URL this points to, it must be that platform's
// stable *production* URL, not an individual build's preview URL (e.g.
// Deno's "vape-8kje756vhqqy.deno.net") — preview URLs are frozen forever at
// whatever code was live for that one build and never receive later pushes,
// which is exactly what caused the x402 hire flow to keep failing with a
// stale CORS config after the fix had already shipped.
const WORKER_BASE = "https://vape-x402.vapex402.workers.dev";
const fmtUsd = n => n==null ? "—" : (n>=1e9 ? "$"+(n/1e9).toFixed(2)+"B" : n>=1e6 ? "$"+(n/1e6).toFixed(1)+"M" : "$"+Number(n).toLocaleString());
const pct = n => (typeof n==="number") ? `<span class="${n>=0?'text-emerald-400':'text-rose-400'}">${n>=0?'+':''}${n.toFixed(2)}%</span>` : "";

// Shared chart-range map — one source of truth for every range selector on
// the site (the chain-wide TVL chart and each per-protocol detail chart).
// '24h' uses the last 2 points since DefiLlama's chain/protocol TVL history
// is daily granularity, not intraday — this is an honest 2-point "latest
// day vs the one before," not a real-time reading. 'all' needs no special
// case: JS's Array.slice(-Infinity) already returns the whole array.
const RANGE_DAYS = { '24h': 2, '7d': 7, '30d': 30, '90d': 90, '1y': 365, 'all': Infinity };

// Contextual icons for each x402 service offering — paired by subject/purpose
// (security audit → audit icon, market data → chart icon, etc.). Every class
// here is a long-established Font Awesome Free solid icon (no FA6/7 additions
// this couldn't verify from the sandbox) — a handful of earlier guesses
// (fa-vault, fa-link-chain, fa-circles, fa-crystal-ball) turned out to be
// invalid/uncertain class names, which render nothing rather than a fallback
// glyph. Also covers 4 offerings (agents/publish_reputation.py::OFFERINGS)
// that were missing here entirely and silently fell back to the generic dot.
const OFFERING_ICONS = {
    // scan/* security offerings
    'exploit_check': 'fa-shield-halved',
    'token_safety_check': 'fa-shield',
    'rug_pull_alert': 'fa-triangle-exclamation',
    'dossier_check': 'fa-magnifying-glass',
    'tx_decode': 'fa-link',
    'community_intel_broadcast': 'fa-bullhorn',
    'liquidity_check': 'fa-chart-line',
    'market_intel': 'fa-chart-pie',
    'bulk_safety_bundle': 'fa-box',
    'website_review': 'fa-globe',
    'partner_referral': 'fa-handshake',
    'wallet_recon': 'fa-user-secret',
    'whale_watch': 'fa-eye',
    // bounty offerings
    'bounty_deep_dive': 'fa-microscope',
    'deep_contract_audit': 'fa-file-contract',
    'forensics_deep': 'fa-magnifying-glass-chart',
    // data/* market-data offerings
    'wallet_pnl_deepdive': 'fa-wallet',
    'token_intel': 'fa-coins',
    'token_chart': 'fa-chart-area',
    'protocol': 'fa-cube',
    'protocol_fees': 'fa-dollar-sign',
    'unlocks': 'fa-lock-open',
    'treasury': 'fa-building-columns',
    'chain_protocols': 'fa-sitemap',
    'chain_overview': 'fa-globe',
    'chain_fees': 'fa-coins',
    'dex_volumes': 'fa-chart-bar',
    'yields': 'fa-arrow-trend-up',
    'stablecoins': 'fa-sack-dollar',
    'bridges': 'fa-right-left',
    'prediction_market_odds': 'fa-dice'
};

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
        this._intelPromise = null; // force a fresh intel-index fetch this cycle, shared by reports() + intel()
        // this.virtuals() sunset 2026-07-31 (VAPE is refocusing on Base/all-EVM/
        // Ethereum + x402, not the Virtuals ecosystem specifically) -- the
        // function and its #virtuals-stats/#virtuals-sparkline render targets
        // are left in place, just no longer invoked here.
        await Promise.allSettled([this.metrics(), this.sentiment(), this.protocols(), this.baseMovers(), this.predictionMarkets(), this.bounties(), this.bountyCommand(), this.reports(), this.chart(this._chartRange||'30d'), this.reputation(), this.intel()]);
        document.getElementById('live-label').textContent = 'LIVE';
        document.getElementById('last-sync').textContent = 'synced ' + new Date().toLocaleTimeString();
    },

    // Shared, memoized-per-cycle intel-index fetch — reports() and intel()
    // both want it and run concurrently in refresh()'s allSettled, so this
    // avoids a duplicate fetch and the race of reports() reading `this._intel`
    // before intel() has populated it.
    _intelPromise: null,
    async _loadIntel() {
        if (!this._intelPromise) {
            this._intelPromise = fetch(`${RAW}/data/intel-index.json?t=` + Date.now()).then(r => r.json()).catch(() => null);
        }
        return this._intelPromise;
    },

    // Bounty Command Center telemetry strip + VAPE's own audit track record.
    // opportunities.json is the same real feed bounties() renders cards from;
    // this just adds the aggregate counts and the separate hack-sweep-reports
    // ledger (VAPE's own proactive research — never a paid buyer's PoC, which
    // is delivered privately and never committed to this public repo).
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

        // Live task feed — real recent automated commits + one OCI-Grok
        // synthesis line (agents/task_feed.py, data/task-feed.json). A
        // separate try/catch from the telemetry/audit-list fetches above —
        // this feed being unavailable shouldn't blank out either of those.
        const taskFeedEl = document.getElementById('bcc-task-feed');
        const synthesisEl = document.getElementById('bcc-task-synthesis');
        const KIND_META = {
            investigation: ['fa-magnifying-glass-chart', '#60a5fa'],
            'bounty-radar': ['fa-satellite-dish', '#60a5fa'],
            audit: ['fa-file-shield', '#60a5fa'],
            broadcast: ['fa-tower-broadcast', '#a1a1aa'],
            reputation: ['fa-chart-line', '#a1a1aa'],
            sweep: ['fa-broom', '#a1a1aa'],
            'data-agent': ['fa-database', '#a1a1aa'],
            build: ['fa-code-merge', '#a1a1aa'],
            automation: ['fa-gears', '#a1a1aa'],
        };
        try {
            const feed = await (await fetch(`${RAW}/data/task-feed.json?t=`+Date.now())).json();
            const tasks = Array.isArray(feed.tasks) ? feed.tasks : [];
            this._set('bcc-tasks', tasks.length);
            if (synthesisEl) synthesisEl.textContent = feed.synthesis || '';
            if (!tasks.length) throw 0;
            this._taskFeedItems = tasks;
            this._taskFeedKindMeta = KIND_META;
            this._wireTaskFeedControls();
            this._renderTaskFeed();
        } catch(e) {
            if (taskFeedEl) taskFeedEl.innerHTML = '<div class="text-zinc-500 text-sm">No recent automated activity recorded.</div>';
            this._set('bcc-tasks', 0);
        }

        // intel/audits/hack-sweep-reports/ — VAPE's own proactive daily HACK
        // sweep, never a specific buyer's paid engagement — deliberately NOT
        // intel/audits/poc-reports/, which used to live here. Real privacy
        // gap this fixes: a paid buyer's PoC report may be the exact
        // technical detail they still need to submit to a bounty program
        // themselves; publicly listing it here (and it being committed to
        // this public repo at all — see deep-dive-bounty.yml's matching
        // fix) could let the audited project or another researcher see it
        // before the buyer submits. Paid engagement reports no longer land
        // in a publicly-committed directory at all as of that fix, so this
        // widget now only ever shows VAPE's own non-buyer-specific work.
        const auditEl = document.getElementById('bcc-audit-list');
        try {
            const items = await (await fetch(`https://api.github.com/repos/${REPO}/contents/intel/audits/hack-sweep-reports`)).json();
            const files = (Array.isArray(items)?items:[]).filter(f=>f.name.endsWith('.md'))
                .map(f=>{
                    const stopped = /-STOPPED/.test(f.name);
                    const m = f.name.match(/(\d{4}-\d{2}-\d{2})/);
                    const base = f.name.replace(/\.md$/,'').replace(/-STOPPED/,'').replace(/^(audit|lead|hack-sweep)-/,'').replace(/-\d{4}-\d{2}-\d{2}$/,'');
                    return { name: base.replace(/-/g,' '), stopped, date: m?m[1]:'', url: f.html_url, isAudit: !stopped };
                })
                .sort((a,b)=>b.date.localeCompare(a.date));
            this._set('bcc-audits', files.filter(f=>f.isAudit).length);
            if (!files.length) throw 0;
            this._auditFiles = files;
            this._wireAuditListControls();
            this._renderAuditList();
        } catch(e) {
            auditEl.innerHTML = '<div class="text-zinc-500 text-sm">No audits filed yet — <a class="text-zinc-400 hover:underline" href="https://github.com/'+REPO+'/tree/main/intel/audits/hack-sweep-reports" target="_blank">browse the audit ledger</a>.</div>';
        }
    },

    // Live Automation Feed — search + pagination over the already-fetched
    // task-feed.json entries.
    _taskFeedItems: [], _taskFeedKindMeta: {}, _taskFeedQuery: '',
    _wireTaskFeedControls() {
        if (this._taskFeedWired) return;
        this._taskFeedWired = true;
        const search = document.getElementById('bcc-task-search');
        if (search) search.addEventListener('input', () => {
            this._taskFeedQuery = search.value.trim().toLowerCase();
            this._pgReset('bcc-task-pg');
            this._renderTaskFeed();
        });
        this._pgWire('bcc-task-pg', 8, () => this._renderTaskFeed());
    },
    _renderTaskFeed() {
        const taskFeedEl = document.getElementById('bcc-task-feed');
        if (!taskFeedEl) return;
        let tasks = this._taskFeedItems;
        if (this._taskFeedQuery) tasks = tasks.filter(t => (t.message||'').toLowerCase().includes(this._taskFeedQuery) || (t.kind||'').toLowerCase().includes(this._taskFeedQuery));
        const items = this._pgSlice('bcc-task-pg', tasks, 8);
        taskFeedEl.innerHTML = items.length ? items.map(t => {
            const [icon, col] = this._taskFeedKindMeta[t.kind] || this._taskFeedKindMeta.automation || ['fa-gears', '#a1a1aa'];
            return `
            <a href="${t.url||'#'}" target="_blank" rel="noopener" class="card-h diff-row flex items-center gap-3">
                <i class="fa-solid ${icon} w-4 text-center shrink-0" style="color:${col}"></i>
                <div class="min-w-0 flex-1 text-xs text-zinc-300 truncate">${this._esc(t.message||'')}</div>
                <div class="text-[10px] text-zinc-500 shrink-0">${this._ago(t.date)}</div>
            </a>`;
        }).join('') : '<div class="text-zinc-500 text-sm">No automated activity matches this filter.</div>';
    },

    _rep: null,
    // Audit Track Record — search + pagination over the already-fetched
    // hack-sweep-reports directory listing.
    _auditFiles: [], _auditQuery: '',
    _wireAuditListControls() {
        if (this._auditWired) return;
        this._auditWired = true;
        const search = document.getElementById('bcc-audit-search');
        if (search) search.addEventListener('input', () => {
            this._auditQuery = search.value.trim().toLowerCase();
            this._pgReset('bcc-audit-pg');
            this._renderAuditList();
        });
        this._pgWire('bcc-audit-pg', 8, () => this._renderAuditList());
    },
    _renderAuditList() {
        const auditEl = document.getElementById('bcc-audit-list');
        if (!auditEl) return;
        let files = this._auditFiles;
        if (this._auditQuery) files = files.filter(f => f.name.includes(this._auditQuery));
        const items = this._pgSlice('bcc-audit-pg', files, 8);
        auditEl.innerHTML = items.length ? items.map(f => `
                <a href="${f.url}" target="_blank" class="card-h diff-row block">
                    <div class="flex items-center justify-between gap-2 mb-1.5">
                        <i class="fa-solid ${f.stopped?'fa-ban text-zinc-500':'fa-file-shield text-[#60a5fa]'}"></i>
                        <span class="text-[10px] ${f.stopped?'text-zinc-500':'text-[#60a5fa]'}">${f.stopped?'Lead stopped':'Audit filed'}</span>
                    </div>
                    <div class="text-xs leading-snug capitalize">${this._esc(f.name)}</div>
                    <div class="text-[10px] text-zinc-500 mt-1">${f.date}</div>
                </a>`).join('') : '<div class="text-zinc-500 text-sm">No audits match this filter.</div>';
    },

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
            const manual = allOfferings.filter(o=>!(o.x402 ?? o.auto));
            const grid = document.getElementById('rep-offerings-grid');
            if (grid) {
                const card = o=>{
                    const icon = OFFERING_ICONS[o.name] || 'fa-circle-dot';
                    return `
                    <div class="relative group">
                    <button onclick="Hire.openX402('${o.name}', ${o.price_usd})" class="offering-card w-full text-left panel-sm hover:border-white/30 transition flex flex-col gap-2 cursor-pointer" data-offering="${o.name}">
                      <div class="flex items-center gap-2">
                        <i class="fa-solid ${icon} offering-card-icon text-sm shrink-0"></i>
                        <div class="flex-1 flex items-center justify-between gap-2 min-w-0">
                          <span class="text-xs text-zinc-200 truncate">${o.name}</span>
                          <span class="text-zinc-100 text-sm whitespace-nowrap">$${o.price_usd}</span>
                        </div>
                      </div>
                      <div class="text-[11px] text-zinc-500 leading-snug">${o.summary}</div>
                      <span class="text-[9px] text-zinc-500 uppercase tracking-wider"><i class="fa-solid fa-bolt"></i> x402 · ${o.sla && o.sla!=='instant' ? this._esc(o.sla) : 'select to initiate'}</span>
                    </button>
                    ${o.directory_url ? `<a href="${o.directory_url}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="View on 402 Index" class="absolute top-2.5 right-2.5 text-zinc-600 hover:text-zinc-200 transition text-[10px] opacity-0 group-hover:opacity-100"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>` : ''}
                    </div>`;
                };
                grid.innerHTML = x402able.map(card).join('');
            }
            const acpGrid = document.getElementById('acp-offerings-grid');
            if (acpGrid) {
                acpGrid.innerHTML = manual.map(o=>{
                    const icon = OFFERING_ICONS[o.name] || 'fa-circle-dot';
                    return `
                    <button onclick="Hire.openAcp('${o.name}')" class="offering-card text-left panel-sm hover:border-white/30 transition flex flex-col gap-2 cursor-pointer" data-offering="${o.name}">
                      <div class="flex items-center gap-2">
                        <i class="fa-solid ${icon} offering-card-icon text-sm shrink-0"></i>
                        <div class="flex-1 flex items-center justify-between gap-2 min-w-0">
                          <span class="text-xs text-zinc-200 truncate">${o.name}</span>
                          <span class="text-zinc-100 text-sm whitespace-nowrap">$${o.price_usd}</span>
                        </div>
                      </div>
                      <div class="text-[11px] text-zinc-500 leading-snug">${o.summary}</div>
                      <span class="text-[9px] text-zinc-500 uppercase tracking-wider"><i class="fa-solid fa-scale-balanced"></i> ACP · select to commission</span>
                    </button>`;
                }).join('');
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
    // Client-side search/status-filter/sort/pagination over that already-
    // fetched list — the full array's already in memory, no extra fetch.
    WORKSHOP_PAGE_SIZE: 8,
    _workshop: { builds: [], q: '', status: '', sort: 'created_desc', page: 0 },

    _renderWorkshop(builds, generatedAt) {
        this._workshop.builds = builds || [];
        this._workshop.generatedAt = generatedAt;
        this._wireWorkshopControls();
        this._renderWorkshopBody();
    },

    _wireWorkshopControls() {
        if (this._workshopWired) return;
        this._workshopWired = true;
        const search = document.getElementById('workshop-search');
        const status = document.getElementById('workshop-status');
        const sort = document.getElementById('workshop-sort');
        const prev = document.getElementById('workshop-prev');
        const next = document.getElementById('workshop-next');
        if (search) {
            search.addEventListener('input', () => {
                this._workshop.q = search.value.trim().toLowerCase();
                this._workshop.page = 0;
                this._renderWorkshopBody();
            });
        }
        if (status) {
            status.addEventListener('change', () => {
                this._workshop.status = status.value;
                this._workshop.page = 0;
                this._renderWorkshopBody();
            });
        }
        if (sort) {
            sort.addEventListener('change', () => {
                this._workshop.sort = sort.value;
                this._workshop.page = 0;
                this._renderWorkshopBody();
            });
        }
        if (prev) {
            prev.addEventListener('click', () => {
                this._workshop.page = Math.max(0, this._workshop.page - 1);
                this._renderWorkshopBody();
            });
        }
        if (next) {
            next.addEventListener('click', () => {
                this._workshop.page += 1;
                this._renderWorkshopBody();
            });
        }
    },

    _filteredSortedWorkshop() {
        let list = this._workshop.builds;
        const { q, status, sort } = this._workshop;
        if (q) {
            list = list.filter(b => (b.title || '').toLowerCase().includes(q) || String(b.number).includes(q));
        }
        if (status) {
            list = list.filter(b => (b.status || 'closed') === status);
        }
        list = [...list].sort((a, b) => sort === 'created_asc'
            ? new Date(a.created_at) - new Date(b.created_at)
            : new Date(b.created_at) - new Date(a.created_at));
        return list;
    },

    _renderWorkshopBody() {
        const el = document.getElementById('workshop-body');
        if (!el) return;
        const upd = document.getElementById('workshop-updated');
        if (upd) upd.textContent = 'ledger ' + this._ago(this._workshop.generatedAt);

        if (!this._workshop.builds.length) {
            el.innerHTML = `<div class="md:col-span-2 text-center py-8 text-zinc-500 text-sm">
                No open build proposals right now — the last cycle found no gap worth building against
                (tool registry clean, no fresh findings to ground a proposal in). Checks run 2x/day automatically.
            </div>`;
            this._renderWorkshopPagination(0);
            return;
        }

        const filtered = this._filteredSortedWorkshop();
        const page = this._workshop.page;
        const pageItems = filtered.slice(page * this.WORKSHOP_PAGE_SIZE, (page + 1) * this.WORKSHOP_PAGE_SIZE);

        if (!filtered.length) {
            el.innerHTML = `<div class="md:col-span-2 text-center py-8 text-zinc-500 text-sm">No builds match this filter.</div>`;
            this._renderWorkshopPagination(0);
            return;
        }

        const statusStyle = { merged: ['#4ade80','Merged'], open: ['#a1a1aa','Open · awaiting review'], closed: ['#52525b','Closed'] };
        el.innerHTML = pageItems.map(b => {
            const [col, label] = statusStyle[b.status] || statusStyle.closed;
            const v = b.verification || {};
            const vBits = [];
            if (v.ok) vBits.push(`<span class="text-emerald-400">[OK] ${v.ok}</span>`);
            if (v.warn) vBits.push(`<span class="text-amber-400">[WARN] ${v.warn}</span>`);
            if (v.fail) vBits.push(`<span class="text-rose-400">[FAIL] ${v.fail}</span>`);
            return `
            <a href="${b.url}" target="_blank" rel="noopener" class="card-h diff-row block">
                <div class="flex items-start justify-between gap-2 mb-1.5">
                    <div class="text-sm leading-snug min-w-0">${this._esc(b.title)}</div>
                    <span class="text-[10px] shrink-0 whitespace-nowrap" style="color:${col}">${label}</span>
                </div>
                <div class="text-xs text-zinc-500 flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span>${b.kind==='self-directed'?'VAPE self-directed':'Human-requested'}</span>
                    <span>· #${b.number} · ${this._ago(b.created_at)}</span>
                    ${vBits.length?`<span>· verify: ${vBits.join(' ')}</span>`:''}
                </div>
            </a>`;
        }).join('');
        this._renderWorkshopPagination(filtered.length);
    },

    _renderWorkshopPagination(total) {
        const countEl = document.getElementById('workshop-count');
        const pageEl = document.getElementById('workshop-page');
        const prev = document.getElementById('workshop-prev');
        const next = document.getElementById('workshop-next');
        const page = this._workshop.page;
        const pages = Math.max(1, Math.ceil(total / this.WORKSHOP_PAGE_SIZE));
        if (countEl) {
            countEl.textContent = total
                ? `Showing ${page * this.WORKSHOP_PAGE_SIZE + 1}–${Math.min(total, (page + 1) * this.WORKSHOP_PAGE_SIZE)} of ${total}`
                : 'No builds match this filter.';
        }
        if (pageEl) pageEl.textContent = `Page ${page + 1} of ${pages}`;
        if (prev) prev.disabled = page <= 0;
        if (next) next.disabled = page + 1 >= pages;
    },

    _tvlHist: null, _chart: null,
    async chart(range='30d') {
        try {
            if (!this._tvlHist) {
                const raw = await (await fetch('https://api.llama.fi/v2/historicalChainTvl/Base')).json();
                this._tvlHist = raw.map(p => ({ t: p.date*1000, v: p.tvl }));
            }
            const slice = this._tvlHist.slice(-(RANGE_DAYS[range] || RANGE_DAYS['30d']));
            const labels = slice.map(p => new Date(p.t).toLocaleDateString(undefined,{month:'short',day:'numeric'}));
            const data = slice.map(p => p.v);
            const ctx = document.getElementById('tvlChart');
            if (this._chart) this._chart.destroy();
            const g = ctx.getContext('2d').createLinearGradient(0,0,0,200);
            g.addColorStop(0,'rgba(74,222,128,0.30)'); g.addColorStop(1,'rgba(74,222,128,0)');
            this._chart = new Chart(ctx, {
                type:'line',
                data:{ labels, datasets:[{ data, borderColor:'#4ade80', backgroundColor:g, fill:true, tension:0.25, pointRadius:0, borderWidth:2 }]},
                options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},
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

    // Addresses whose held balance is permanently removed from circulation —
    // excluded from concentration math or a healthy burn/deflationary
    // mechanism would flag as a whale-risk false positive. Mirrors
    // agents/token_scan.py::BURN_ADDRESSES / worker/src/scan.ts's
    // BURN_ADDRESSES — keep in sync.
    _BURN_ADDRESSES: ['0x0000000000000000000000000000000000000000', '0x000000000000000000000000000000000000dead'],

    // Real top-holder concentration + LP-lock status from GoPlus's own
    // per-holder "holders"/"lp_holders" arrays — already inside the SAME
    // `gp` object this scan already fetches (keyless, no new API call), but
    // never read; only the scalar holder_count/lp_holder_count were. Mirrors
    // agents/token_scan.py::_top_holder_concentration_pct()/_lp_locked_pct()
    // — see those functions' docstrings for the full context.
    _topHolderConcentrationPct(gp) {
        const holders = gp && gp.holders;
        if (!Array.isArray(holders) || holders.length===0) return null;
        let total=0, counted=0;
        for (const h of holders.slice(0,10)) {
            if (!h || typeof h!=='object') continue;
            const addr = String(h.address||'').toLowerCase();
            if (this._BURN_ADDRESSES.includes(addr)) continue;
            const tag = String(h.tag||'').toLowerCase();
            if (tag.includes('lp') || tag.includes('pool') || tag.includes('burn')) continue;
            let pct = parseFloat(h.percent);
            if (isNaN(pct)) continue;
            if (pct>1) pct/=100;
            total+=pct; counted++;
        }
        return counted===0 ? null : total*100;
    },
    _lpLockedPct(gp) {
        const lpHolders = gp && gp.lp_holders;
        if (!Array.isArray(lpHolders) || lpHolders.length===0) return null;
        let total=0, locked=0, counted=0;
        for (const h of lpHolders) {
            if (!h || typeof h!=='object') continue;
            let pct = parseFloat(h.percent);
            if (isNaN(pct)) continue;
            if (pct>1) pct/=100;
            total+=pct;
            if (String(h.is_locked)==='1') locked+=pct;
            counted++;
        }
        return (counted===0 || total<=0) ? null : (locked/total)*100;
    },

    // DexScreener fronts its API through Cloudflare, and its anti-bot layer
    // occasionally rate-limits datacenter/browser-proxy egress with an HTML
    // block page (Cloudflare "error code: 1015") instead of a clean 429 —
    // reading that as JSON throws a raw parser exception. Retry once, then
    // fall back to GeckoTerminal for liquidity so a transient DexScreener
    // block doesn't misreport real liquidity as $0. Mirrors
    // agents/token_scan.py::_get()/_fetch_liquidity_fallback() and
    // worker/src/scan.ts::safeGet()/fetchLiquidityFallback() — keep in sync.
    _GECKOTERMINAL_NETWORK: {'8453':'base','1':'eth','42161':'arbitrum'},
    async _safeFetchJson(url, retries=1) {
        for (let attempt=0; ; attempt++) {
            try {
                const r = await fetch(url);
                if (!r.ok) {
                    if (attempt<retries && (r.status===429||r.status===403||r.status>=500)) {
                        await new Promise(res=>setTimeout(res,400*(attempt+1))); continue;
                    }
                    return {_error:`upstream returned HTTP ${r.status}`};
                }
                return await r.json();
            } catch(e) {
                if (attempt<retries) { await new Promise(res=>setTimeout(res,400*(attempt+1))); continue; }
                return {_error:'upstream request failed or returned invalid data'};
            }
        }
    },
    async _fetchLiquidityFallback(addr, chain) {
        const network = this._GECKOTERMINAL_NETWORK[String(chain)];
        if (!network) return null;
        const data = await this._safeFetchJson(`https://api.geckoterminal.com/api/v2/networks/${network}/tokens/${addr}/pools`, 0);
        const pools = Array.isArray(data?.data) ? data.data : [];
        if (!pools.length) return null;
        const liquidity_usd = pools.reduce((s,p)=>s+(parseFloat(p?.attributes?.reserve_in_usd)||0),0);
        return { liquidity_usd, top_pair_dex: pools[0]?.relationships?.dex?.data?.id || null, source: 'geckoterminal' };
    },

    renderScanResult(el, addr, chain, gp, liq, pairs, note) {
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
        const topHolderPct = this._topHolderConcentrationPct(gp);
        if (topHolderPct!=null && topHolderPct>=70) flags.push(`concentrated holders (${topHolderPct.toFixed(0)}%)`);
        const lpLockedPct = this._lpLockedPct(gp);
        if (lpLockedPct!=null && lpLockedPct<50) flags.push(`LP mostly unlocked (${lpLockedPct.toFixed(0)}%)`);
        const hardReject = gp.is_honeypot==='1' || this._HARD_REJECT_FIELDS.some(field => gp[field]==='1');
        const verdict = hardReject ? ['REJECT','#fb7185'] : (flags.length>=2 ? ['CAUTION','#fbbf24'] : ['PROCEED','#10b981']);
        const vc = verdict[1];
        const name = gp.token_name ? `${this._esc(gp.token_name)} (${this._esc(gp.token_symbol)})` : this._shortAddr(addr);
        el.innerHTML = `
            <div class="panel-sm">
                <div class="flex items-center justify-between mb-3">
                    <a href="${this._explorerUrl(addr, chain)}" target="_blank" rel="noopener" class="flex items-center gap-2 min-w-0 hover:opacity-80">
                        ${this._iconImg(addr, chain, 28)}
                        <div class="truncate">${name}</div>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-60 shrink-0"></i>
                    </a>
                    <span class="px-3 py-1 border shrink-0" style="color:${vc};border-color:${vc}">${verdict[0]}</span>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div><div class="text-zinc-500">Holders</div><div class="stat">${gp.holder_count?Number(gp.holder_count).toLocaleString():'—'}</div></div>
                    <div><div class="text-zinc-500">Liquidity</div><div class="stat">${liq?fmtUsd(liq):'—'}</div></div>
                    <div><div class="text-zinc-500">Honeypot</div><div class="${gp.is_honeypot==='1'?'text-rose-400':'text-emerald-500'}">${gp.is_honeypot==='1'?'YES':'no'}</div></div>
                    <div><div class="text-zinc-500">Buy/Sell tax</div><div>${gp.buy_tax!=null?(gp.buy_tax*100).toFixed(1):'?'}% / ${gp.sell_tax!=null?(gp.sell_tax*100).toFixed(1):'?'}%</div></div>
                </div>
                <div class="mt-3 text-xs">${flags.length?flags.map(f=>`<span class="inline-block border px-2 py-0.5 mr-1 mb-1" style="color:${vc};border-color:${vc}">${f}</span>`).join(''):'<span class="text-emerald-500">No risk flags from real on-chain scan.</span>'}</div>
                ${note?`<div class="mt-2 text-[10px] text-amber-400">${this._esc(note)}</div>`:''}
                <div class="mt-2 text-[10px] text-zinc-600">Real on-chain token-safety and liquidity data. Not investment advice.</div>
            </div>`;
        return verdict[0];
    },

    async hunt() {
        const el = document.getElementById('hunt-result');
        const addr = (document.getElementById('hunt-target').value||'').trim();
        const chain = document.getElementById('hunt-chain').value;
        if (!/^0x[a-fA-F0-9]{40}$/.test(addr)) { el.innerHTML = '<span class="text-amber-400">Enter a valid 0x… 40-hex contract address.</span>'; return; }
        el.innerHTML = '<span class="text-zinc-400"><i class="fa-solid fa-spinner fa-spin"></i> Assessing real on-chain data…</span>';
        try {
            const [gpRaw, dsRaw] = await Promise.all([
                this._safeFetchJson(`https://api.gopluslabs.io/api/v1/token_security/${chain}?contract_addresses=${addr}`),
                this._safeFetchJson(`https://api.dexscreener.com/latest/dex/tokens/${addr}`)
            ]);
            if (gpRaw?._error) { el.innerHTML = `<span class="text-amber-400">Token security data unavailable (${this._esc(gpRaw._error)}). Try again shortly.</span>`; return; }
            const gp = Object.values(gpRaw.result||{})[0] || {};
            let pairs = dsRaw?.pairs || [];
            let liq = pairs.reduce((s,p)=>s+(p.liquidity?.usd||0),0);
            let note = null;
            // DexScreener failed outright (not just "no pairs found") — reporting
            // $0 liquidity for a token that may have plenty is misleading, not
            // just incomplete. Fall back to GeckoTerminal, same as the paid
            // offerings and agents/token_scan.py.
            if (dsRaw?._error && !pairs.length) {
                const fallback = await this._fetchLiquidityFallback(addr, chain);
                if (fallback) {
                    liq = fallback.liquidity_usd;
                    note = `Liquidity from an alternate source (primary market-data source temporarily unavailable: ${dsRaw._error}).`;
                } else {
                    note = `Market data unavailable (${dsRaw._error}) — liquidity may be understated.`;
                }
            }
            this.renderScanResult(el, addr, chain, gp, liq, pairs, note);
        } catch(e){ el.innerHTML = '<span class="text-amber-400">Scan failed unexpectedly. Try again.</span>'; }
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

    // Broader-market context alongside the Base-specific tiles above — both
    // sources are free, unauthenticated, and already stable public APIs used
    // industry-wide for exactly this (alternative.me's Fear & Greed Index,
    // CoinGecko's /global). One call each per five-minute refresh cycle, well
    // inside either service's rate limit.
    async sentiment() {
        try {
            const fng = await (await fetch('https://api.alternative.me/fng/?limit=1')).json();
            const d = (fng?.data || [])[0];
            const v = d ? parseInt(d.value, 10) : null;
            const el = document.getElementById('m-feargreed');
            el.classList.remove('skeleton');
            el.innerHTML = (v != null && !isNaN(v)) ? `${v} <span class="text-xs text-zinc-500 font-sans">${this._esc(d.value_classification || '')}</span>` : '—';
            const fill = document.getElementById('m-feargreed-fill');
            if (fill && v != null && !isNaN(v)) {
                fill.style.width = `${v}%`;
                fill.style.background = v <= 24 ? '#fb7185' : v <= 44 ? '#fbbf24' : v <= 55 ? '#a1a1aa' : v <= 75 ? '#84cc16' : '#10b981';
            }
        } catch (e) { this._set('m-feargreed', '—'); }

        try {
            const g = await (await fetch('https://api.coingecko.com/api/v3/global')).json();
            const mc = g?.data?.total_market_cap?.usd;
            const chg = g?.data?.market_cap_change_percentage_24h_usd;
            const el = document.getElementById('m-mcap');
            el.classList.remove('skeleton');
            el.innerHTML = mc != null ? `${fmtUsd(mc)}${typeof chg === 'number' ? ` <span class="text-xs font-sans">${pct(chg)}</span>` : ''}` : '—';
        } catch (e) { this._set('m-mcap', '—'); }
    },

    // "Base Movers" — real data source, tried in order:
    //   1. CoinGecko's "Base Ecosystem" category (curated, real Base tokens
    //      with reliable logo/symbol/name/price data in one keyless,
    //      CORS-friendly call).
    //   2. DexScreener's boosted-token feed as a fallback — kept because it
    //      was the only source before, but demoted: it's a paid-promotion
    //      signal (projects actively boosting a listing), not organic
    //      movers, and was observed going empty/unavailable often enough in
    //      practice that this section stopped populating entirely.
    // Gainers/Losers/Volume just re-sort whichever set loaded, client-side —
    // no extra requests per tab switch.
    _movers: null,
    _moversTab: 'trending',
    async baseMovers() {
        const el = document.getElementById('base-movers');
        if (!el) return;
        try {
            await this._moversFromCoinGecko();
        } catch (e) {
            console.error('[baseMovers] CoinGecko unavailable, falling back to DexScreener boosts:', e.message || e);
            try {
                await this._moversFromDexScreenerBoosts();
            } catch (e2) {
                console.error('[baseMovers] Base Movers unavailable:', e2.message || e2);
                el.innerHTML = `<div class="text-amber-400 text-sm">Live trending data unavailable — retries next cycle.</div>`;
            }
        }
    },
    async _moversFromCoinGecko() {
        // Real bug fixed here (caught by review): CoinGecko's /coins/markets
        // `order` param only accepts market_cap_desc/asc, volume_desc/asc, or
        // id_desc/asc — price_change_percentage_24h_desc isn't a real value
        // and was silently falling back to the default (market_cap_desc), so
        // the "trending" tab was actually just market-cap-ranked, not movers
        // at all. Fetch by market cap (a legitimate, broad pool of real Base
        // ecosystem tokens), then sort by absolute 24h change client-side —
        // same "biggest movers" definition already used server-side in
        // agents/data_fetchers.py::get_evm_movers().
        const res = await fetch('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=base-ecosystem&order=market_cap_desc&per_page=30&page=1&sparkline=false&price_change_percentage=24h');
        if (!res.ok) throw new Error(`coingecko coins/markets -> HTTP ${res.status}`);
        const coins = await res.json();
        if (!Array.isArray(coins) || !coins.length) throw new Error('coingecko returned no base-ecosystem coins');
        coins.sort((a, b) => Math.abs(b.price_change_percentage_24h ?? 0) - Math.abs(a.price_change_percentage_24h ?? 0));
        // Normalized into the exact shape _renderMovers() already expects
        // (priceUsd / priceChange.h24 / volume.h24 / baseToken.symbol+name /
        // info.imageUrl / url) so that function needs zero changes regardless
        // of which source actually supplied the data this cycle.
        this._movers = coins.map(c => ({
            url: `https://www.coingecko.com/en/coins/${c.id}`,
            baseToken: { symbol: (c.symbol || '').toUpperCase(), name: c.name, address: null },
            priceUsd: c.current_price,
            priceChange: { h24: c.price_change_percentage_24h },
            volume: { h24: c.total_volume },
            info: { imageUrl: c.image },
            // VAPE Score inputs _moverScore() reads — CoinGecko has no direct
            // liquidity/pair-age field, left null so that function skips them
            // rather than penalizing a source-side gap.
            marketCapRank: c.market_cap_rank ?? null,
            liquidityUsd: null,
            pairCreatedMs: null,
        }));
        this._renderMovers();
    },
    async _moversFromDexScreenerBoosts() {
        // DexScreener occasionally 403s or rate-limits this endpoint —
        // fetch() only rejects on a network-level failure, not on a non-2xx
        // response, so an unchecked `.json()` on a 403's (often non-JSON)
        // body was throwing an opaque parse error that told a browser
        // console nothing about the real cause. Check status explicitly so
        // the actual reason is visible for debugging instead of a silent
        // "Live data unavailable."
        const boostsRes = await fetch('https://api.dexscreener.com/token-boosts/top/v1');
        if (!boostsRes.ok) throw new Error(`token-boosts/top/v1 -> HTTP ${boostsRes.status}`);
        const boosts = await boostsRes.json();
        const addrs = [...new Set((Array.isArray(boosts) ? boosts : [])
            .filter(b => b.chainId === 'base' && b.tokenAddress)
            .map(b => b.tokenAddress.toLowerCase()))].slice(0, 30);
        if (!addrs.length) throw new Error('no boosted Base tokens right now');
        const pairsRes = await fetch(`https://api.dexscreener.com/latest/dex/tokens/${addrs.join(',')}`);
        if (!pairsRes.ok) throw new Error(`latest/dex/tokens -> HTTP ${pairsRes.status}`);
        const data = await pairsRes.json();
        const byToken = new Map();
        (data.pairs || []).forEach(p => {
            if (p.chainId !== 'base') return;
            const addr = (p.baseToken?.address || '').toLowerCase();
            if (!addr) return;
            const existing = byToken.get(addr);
            if (!existing || (p.liquidity?.usd || 0) > (existing.liquidity?.usd || 0)) byToken.set(addr, p);
        });
        // Preserve the boost feed's own ranking for the "trending" tab —
        // the tokens/{addrs} lookup above returns pairs in its own order,
        // not the boost ranking, so rebuild from `addrs`.
        // DexScreener's own pair schema already matches what _renderMovers()
        // expects (baseToken/priceUsd/priceChange.h24/volume.h24/url/info) —
        // spread the raw pair through unchanged, just add the VAPE Score
        // inputs _moverScore() reads that CoinGecko's path can't supply
        // (real liquidity depth, real pair age) but this source can.
        this._movers = addrs.map(a => byToken.get(a)).filter(Boolean).map(p => ({
            ...p, marketCapRank: null, liquidityUsd: p.liquidity?.usd ?? null, pairCreatedMs: p.pairCreatedAt ?? null,
        }));
        if (!this._movers.length) throw new Error('boosted addresses returned no matching Base pairs');
        this._renderMovers();
    },

    // VAPE Score for a Base mover — same 0-100/neutral-50/skip-on-missing
    // shape as _protocolScore(), but deliberately measuring market QUALITY,
    // not momentum: the tabs already rank by price change/volume, so this
    // score would just double up on that signal if it rewarded big moves.
    // Instead it rewards a real, established, liquid market and flags thin
    // or brand-new pairs as risk — the same "quality/trust" meaning "VAPE
    // Score"/"Safety score" carries everywhere else on the site.
    _moverScore(p) {
        let score = 50;
        if (typeof p.marketCapRank === 'number' && p.marketCapRank > 0) score += 15;
        const liq = p.liquidityUsd ?? p.volume?.h24;
        if (typeof liq === 'number') {
            if (liq >= 50000) score += 10;
            else if (liq < 5000) score -= 15;
        }
        const chg = p.priceChange?.h24;
        if (typeof chg === 'number' && Math.abs(chg) >= 50) score -= 10;
        if (typeof p.pairCreatedMs === 'number' && (Date.now() - p.pairCreatedMs) < 86400000) score -= 10;
        return Math.max(0, Math.min(100, Math.round(score)));
    },

    // ── Generic client-side pagination — same "Showing X–Y of Z / Page N of
    // M / Prev/Next" footer as Recent Jobs, reused across every data list on
    // the site that has its own search/sort/filter logic already (this only
    // owns the page-slice + footer, not the filtering). One state bag keyed
    // by an arbitrary string id so unrelated lists don't collide.
    _pg: {},
    _pgWire(key, pageSize, onChange) {
        if (this._pg[key]) return; // wire the buttons once per key
        this._pg[key] = { page: 0, pageSize, onChange };
        const prev = document.getElementById(key + '-prev');
        const next = document.getElementById(key + '-next');
        if (prev) prev.addEventListener('click', () => {
            const st = this._pg[key];
            st.page = Math.max(0, st.page - 1);
            st.onChange();
        });
        if (next) next.addEventListener('click', () => {
            const st = this._pg[key];
            st.page += 1;
            st.onChange();
        });
    },
    _pgPage(key) { return this._pg[key] ? this._pg[key].page : 0; },
    _pgReset(key) { if (this._pg[key]) this._pg[key].page = 0; },
    // Slices `items` to the current page for `key` and updates that key's
    // count/page/prev/next footer elements (ids: `${key}-count/-page/-prev/-next`).
    _pgSlice(key, items, pageSize) {
        const st = this._pg[key];
        const size = pageSize || (st && st.pageSize) || 10;
        const total = items.length;
        const pages = Math.max(1, Math.ceil(total / size));
        let page = st ? st.page : 0;
        if (page > pages - 1) { page = pages - 1; if (st) st.page = page; }
        const countEl = document.getElementById(key + '-count');
        const pageEl = document.getElementById(key + '-page');
        const prev = document.getElementById(key + '-prev');
        const next = document.getElementById(key + '-next');
        if (countEl) countEl.textContent = total ? `Showing ${page*size+1}–${Math.min(total,(page+1)*size)} of ${total}` : 'No entries match this filter.';
        if (pageEl) pageEl.textContent = `Page ${page+1} of ${pages}`;
        if (prev) prev.disabled = page <= 0;
        if (next) next.disabled = page + 1 >= pages;
        return items.slice(page * size, (page + 1) * size);
    },

    _renderMovers() {
        const el = document.getElementById('base-movers');
        if (!el || !this._movers) return;
        let items = this._movers.slice();
        if (this._moversTab === 'gainers') items.sort((a,b) => (b.priceChange?.h24 ?? -Infinity) - (a.priceChange?.h24 ?? -Infinity));
        else if (this._moversTab === 'losers') items.sort((a,b) => (a.priceChange?.h24 ?? Infinity) - (b.priceChange?.h24 ?? Infinity));
        else if (this._moversTab === 'volume') items.sort((a,b) => (b.volume?.h24 || 0) - (a.volume?.h24 || 0));
        const term = this._searchTerms.movers;
        const filtered = items.filter(p => this._matchesTokenSearch(p.baseToken?.symbol, p.baseToken?.name, term));
        this._pgWire('movers-pg', 10, () => this._renderMovers());
        const moversOffset = this._pgPage('movers-pg') * 10;
        items = this._pgSlice('movers-pg', filtered, 10);
        el.innerHTML = items.length ? items.map((p,i) => {
            const chg = p.priceChange?.h24;
            const icon = p.info?.imageUrl || this._tokenIcon(p.baseToken?.address, 'base');
            const priceUsd = p.priceUsd != null ? Number(p.priceUsd) : null;
            return `
            <a href="${p.url}" target="_blank" rel="noopener" class="card-h diff-row flex items-center gap-2 sm:gap-3 overflow-hidden">
                <span class="text-zinc-600 text-sm w-4 shrink-0">${moversOffset+i+1}</span>
                ${icon?`<img src="${icon}" alt="" width="28" height="28" class="rounded-full bg-white/5 object-cover shrink-0" onerror="this.remove()">`:''}
                <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2 min-w-0">
                        <span class="truncate">${this._esc(p.baseToken?.symbol||'?')}</span>
                    </div>
                    <div class="text-xs text-zinc-500 truncate">${this._esc(p.baseToken?.name||'')}</div>
                </div>
                <div class="text-right shrink-0 min-w-[4rem] sm:min-w-[6rem]">
                    <div class="stat text-sm sm:text-base">${priceUsd!=null?'$'+priceUsd.toLocaleString(undefined,{maximumSignificantDigits:6}):'—'}</div>
                    <div class="text-xs">${typeof chg==='number'?pct(chg):'—'}</div>
                </div>
                <div class="text-right shrink-0 hidden sm:block w-20">
                    <div class="text-[10px] text-zinc-500 uppercase tracking-wider">Vol 24h</div>
                    <div class="text-xs text-zinc-300">${fmtUsd(p.volume?.h24)}</div>
                </div>
            </a>`;
        }).join('') : (this._movers.length
            ? '<div class="text-zinc-500 text-sm">No tokens match your search.</div>'
            : '<div class="text-zinc-500 text-sm">No trending Base pairs right now.</div>');
    },

    // ── Virtuals Protocol — VIRTUAL token stats + trending/new Base tokens ──
    // Sourced entirely from Codex.io via the worker's /virtuals-snapshot,
    // /trending-base, and /new-launches routes (worker/src/lib/codex.ts, a
    // TS port of agents/codex_data.py) — Codex needs a bearer key that can't
    // ship to the browser, so unlike protocols()/chart()/baseMovers() this
    // can't be a direct client-side fetch. Intentionally no protocol TVL
    // here: Codex is a token-market-data platform, not a DeFi-TVL
    // aggregator, so this panel doesn't reach for DefiLlama to fill that
    // gap — everything shown is real Codex data or nothing.
    _trendingBase: [],
    _newLaunches: [],
    async virtuals() {
        if (!WORKER_BASE) return;
        try {
            const [snapRes, trendRes, launchRes] = await Promise.allSettled([
                fetch(`${WORKER_BASE}/virtuals-snapshot`).then(r=>r.json()),
                // 30, not 12 — the worker route is edge-cached per exact query
                // string (max-age=300), so a higher limit here doesn't cost any
                // extra Codex requests, just gives the new search box (below)
                // more rows to actually search across.
                fetch(`${WORKER_BASE}/trending-base?limit=30`).then(r=>r.json()),
                fetch(`${WORKER_BASE}/new-launches?limit=30`).then(r=>r.json()),
            ]);
            const snap = snapRes.status==='fulfilled' ? snapRes.value : null;
            if (snap && !snap.error) this._renderVirtualsStats(snap);
            else this._renderVirtualsUnavailable();
            const trend = trendRes.status==='fulfilled' ? trendRes.value : null;
            if (trend && !trend.error && Array.isArray(trend.tokens)) {
                this._trendingBase = trend.tokens;
                this._renderTrendingBase();
            } else {
                const el = document.getElementById('trending-base');
                if (el) el.innerHTML = '<div class="text-zinc-500 text-sm">Trending data unavailable right now.</div>';
            }
            const launch = launchRes.status==='fulfilled' ? launchRes.value : null;
            if (launch && !launch.error && Array.isArray(launch.tokens)) {
                this._newLaunches = launch.tokens;
                this._renderNewLaunches();
            } else {
                const el = document.getElementById('new-launches');
                if (el) el.innerHTML = '<div class="text-zinc-500 text-sm">New-launches data unavailable right now.</div>';
            }
        } catch(e) {
            this._renderVirtualsUnavailable();
            const trendEl = document.getElementById('trending-base');
            if (trendEl) trendEl.innerHTML = '<div class="text-zinc-500 text-sm">Trending data unavailable right now.</div>';
            const launchEl = document.getElementById('new-launches');
            if (launchEl) launchEl.innerHTML = '<div class="text-zinc-500 text-sm">New-launches data unavailable right now.</div>';
        }
    },

    // Swaps the four skeleton stat spans for an honest "unavailable" line —
    // this panel has no keyless fallback (Codex needs a worker-side key), so
    // an error here should read as "not available", not sit as a permanent
    // skeleton that looks like it's still loading.
    _renderVirtualsUnavailable() {
        const el = document.getElementById('virtuals-stats');
        if (el) el.innerHTML = '<span class="text-zinc-500 text-sm">Unavailable right now.</span>';
    },

    // 0-100, neutral start 50 — VIRTUAL's health from Codex-native signals:
    // 24h price change (small weight, noisy on its own) and top-10-holder
    // concentration (medium weight — a widely-held token is harder to
    // manipulate than one a handful of wallets control). No TVL trend input
    // here — see virtuals() above for why. Either factor is simply skipped
    // (not defaulted to neutral/zero) if Codex didn't return it this cycle.
    _virtualsScore(detail, holders) {
        let score = 50;
        const chg = detail && typeof detail.change24 === 'number' ? detail.change24 : null;
        if (chg != null) {
            if (chg >= 5) score += 10; else if (chg > 0) score += 5;
            else if (chg <= -10) score -= 10; else if (chg < 0) score -= 5;
        }
        const top10 = holders && typeof holders.top10HoldersPercent === 'number' ? holders.top10HoldersPercent : null;
        if (top10 != null) {
            if (top10 <= 20) score += 20; else if (top10 <= 35) score += 10;
            else if (top10 >= 70) score -= 20; else if (top10 >= 50) score -= 10;
        }
        return Math.max(0, Math.min(100, Math.round(score)));
    },

    _renderVirtualsStats(snap) {
        const detail = snap.detail || {};
        const holders = snap.holders || {};
        this._set('v-price', detail.priceUSD!=null ? '$'+Number(detail.priceUSD).toLocaleString(undefined,{maximumSignificantDigits:6}) : '—');
        this._set('v-mcap', fmtUsd(detail.marketCap));
        this._set('v-vol', fmtUsd(detail.volume24));
        const chgEl = document.getElementById('v-chg');
        if (chgEl) chgEl.innerHTML = pct(detail.change24);
        const holdEl = document.getElementById('v-holders');
        if (holdEl) holdEl.innerHTML = `${holders.count!=null?Number(holders.count).toLocaleString():'—'} holders <span class="text-xs">${holders.top10HoldersPercent!=null?'top10 '+holders.top10HoldersPercent.toFixed(1)+'%':''}</span>`;
        this._renderVirtualsSparkline(snap.bars);
    },

    // Real 30-day daily OHLCV close-price sparkline for VIRTUAL, from the
    // same /virtuals-snapshot call above (worker/src/lib/codex.ts::tokenBars,
    // Codex's getBars) — a minimal Chart.js line, no axes/gridlines, since
    // this is a glance-value sparkline, not a full chart like the protocol
    // detail modal's. Real data or nothing: skipped entirely on error/empty.
    // Wrapped in try/catch (unlike the other Chart.js call sites on this
    // page, which run standalone) because this one runs inside virtuals()'s
    // shared try block alongside Trending on Base and New Launches — a
    // blocked/failed Chart.js CDN load must not take those down with it.
    _renderVirtualsSparkline(bars) {
        try {
            const canvas = document.getElementById('virtuals-sparkline');
            if (!canvas || typeof Chart === 'undefined') return;
            const points = (bars && !bars.error && Array.isArray(bars.points)) ? bars.points : [];
            if (this._virtualsSparkChart) { this._virtualsSparkChart.destroy(); this._virtualsSparkChart = null; }
            if (!points.length) return;
            const data = points.map(p => p.c);
            const up = data[data.length-1] >= data[0];
            this._virtualsSparkChart = new Chart(canvas, {
                type: 'line',
                data: { labels: points.map(p => p.t), datasets: [{ data, borderColor: up?'#4ade80':'#fb7185',
                    fill: false, tension: 0.25, pointRadius: 0, borderWidth: 1.5 }] },
                options: { responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                    scales: { x: { display: false }, y: { display: false } } },
            });
        } catch (e) { /* non-fatal — the rest of the Virtuals panel still stands */ }
    },

    // Crypto/Base-relevant prediction-market odds from Polymarket + Kalshi
    // (both free, keyless) via the worker's /prediction-markets route
    // (worker/src/lib/predictionMarkets.ts) — same free-display + paid-x402
    // dual pattern as everything else on this panel.
    _predictionMarkets: [], _predictionQuery: '',
    _wirePredictionControls() {
        if (this._predictionWired) return;
        this._predictionWired = true;
        const search = document.getElementById('prediction-search');
        if (search) search.addEventListener('input', () => {
            this._predictionQuery = search.value.trim().toLowerCase();
            this._pgReset('prediction-pg');
            this._renderPredictionMarkets();
        });
        this._pgWire('prediction-pg', 8, () => this._renderPredictionMarkets());
    },
    async predictionMarkets() {
        const el = document.getElementById('prediction-markets');
        if (!el) return;
        if (!WORKER_BASE) { el.innerHTML = '<div class="text-zinc-500 text-sm">Prediction-market data unavailable right now.</div>'; return; }
        try {
            const res = await fetch(`${WORKER_BASE}/prediction-markets?limit=25`).then(r => r.json());
            if (!res || res.error || !Array.isArray(res.markets)) {
                el.innerHTML = '<div class="text-zinc-500 text-sm">Prediction-market data unavailable right now.</div>';
                return;
            }
            this._predictionMarkets = res.markets;
            this._wirePredictionControls();
            this._renderPredictionMarkets();
        } catch (e) {
            el.innerHTML = '<div class="text-zinc-500 text-sm">Prediction-market data unavailable right now.</div>';
        }
    },
    _renderPredictionMarkets() {
        const el = document.getElementById('prediction-markets');
        if (!el) return;
        let markets = this._predictionMarkets;
        if (this._predictionQuery) markets = markets.filter(m => (m.question||'').toLowerCase().includes(this._predictionQuery));
        const items = this._pgSlice('prediction-pg', markets, 8);
        el.innerHTML = items.length ? items.map((m) => {
            const yesPrice = Array.isArray(m.prices) && m.prices.length ? m.prices[0]
                : (typeof m.yes_bid_cents === 'number' ? m.yes_bid_cents / 100 : null);
            const yesPct = yesPrice != null ? Math.round(yesPrice * 100) : null;
            const pctLabel = yesPct != null ? yesPct + '% Yes' : '—';
            // Probability-read color, not a VAPE Score — a quick "which way is
            // the market leaning" glance, same band language as the rest of
            // the site (green/amber/rose) but scoped to this one number.
            const pctColor = yesPct == null ? '#a1a1aa' : yesPct >= 65 ? '#4ade80' : yesPct <= 35 ? '#fb7185' : '#fbbf24';
            const isPoly = m.platform === 'polymarket';
            const platformLabel = isPoly ? 'Polymarket' : 'Kalshi';
            const platformColor = isPoly ? '#818cf8' : '#34d399';
            // Real link or nothing — never a dead "#" href.
            const tag = m.url ? 'a' : 'div';
            const linkAttrs = m.url ? `href="${this._esc(m.url)}" target="_blank" rel="noopener"` : '';
            return `
            <${tag} ${linkAttrs} class="card-h diff-row flex items-center gap-2 sm:gap-3 overflow-hidden">
                <span class="text-[10px] px-1.5 py-0.5 border shrink-0 whitespace-nowrap" style="color:${platformColor};border-color:${platformColor}44">${platformLabel}</span>
                <div class="min-w-0 flex-1 text-xs sm:text-sm truncate">${this._esc(m.question || '')}</div>
                <div class="text-right shrink-0 min-w-[4.5rem]">
                    <div class="stat text-sm" style="color:${pctColor}">${pctLabel}</div>
                    <div class="text-[10px] text-zinc-500">${fmtUsd(m.volume)} vol</div>
                </div>
            </${tag}>`;
        }).join('') : '<div class="text-zinc-500 text-sm">No crypto-relevant prediction markets match this filter.</div>';
    },

    // VAPE Score for a trending Base token — same 0-100/neutral-50/skip-on-
    // missing shape as _moverScore(), and for the same reason: this list is
    // already ranked by Codex's own volume/liquidity signal, so the score
    // measures market QUALITY (a real, liquid, established pair) rather than
    // rewarding the momentum the ranking already captures. isVirtuals is
    // informational (which ecosystem launched it), not a quality signal, so
    // it isn't scored either way.
    _trendingTokenScore(t) {
        let score = 50;
        if (typeof t.liquidity === 'number') {
            if (t.liquidity >= 50000) score += 15;
            else if (t.liquidity < 5000) score -= 20;
        }
        if (typeof t.marketCap === 'number' && t.marketCap >= 1000000) score += 10;
        if (typeof t.change24 === 'number' && Math.abs(t.change24) >= 50) score -= 10;
        return Math.max(0, Math.min(100, Math.round(score)));
    },

    // Client-side search state for the three Codex-backed token lists —
    // filters the already-fetched array, no extra network requests (the
    // worker route is fetched once at a higher limit; see virtuals()).
    _searchTerms: { trending: '', launches: '', movers: '' },
    _setSearch(panel, term) {
        this._searchTerms[panel] = (term || '').trim().toLowerCase();
        if (panel === 'trending') this._renderTrendingBase();
        else if (panel === 'launches') this._renderNewLaunches();
        else if (panel === 'movers') this._renderMovers();
    },
    // Matches a token's symbol or name against the search term — substring,
    // case-insensitive. Empty term matches everything.
    _matchesTokenSearch(symbol, name, term) {
        if (!term) return true;
        return (symbol || '').toLowerCase().includes(term) || (name || '').toLowerCase().includes(term);
    },

    // Sorts one of the already-fetched Codex token arrays in place by a
    // numeric field, descending, nulls/missing last — shared by Trending on
    // Base and New Launches so both re-sort their existing 30-row fetch
    // client-side (see virtuals() above for why limit=30 was chosen) rather
    // than making a second network request per sort click.
    _sortTokensBy(items, field) {
        return [...items].sort((a, b) => {
            const av = a[field], bv = b[field];
            const an = typeof av === 'number' ? av : -Infinity;
            const bn = typeof bv === 'number' ? bv : -Infinity;
            return bn - an;
        });
    },

    _trendingSort: 'volume24',
    _renderTrendingBase() {
        const el = document.getElementById('trending-base');
        if (!el) return;
        const term = this._searchTerms.trending;
        const sorted = this._sortTokensBy(this._trendingBase, this._trendingSort);
        const filtered = sorted.filter(t => this._matchesTokenSearch(t.token?.symbol, t.token?.name, term));
        this._pgWire('trending-pg', 10, () => this._renderTrendingBase());
        const trendingOffset = this._pgPage('trending-pg') * 10;
        const items = this._pgSlice('trending-pg', filtered, 10);
        el.innerHTML = items.length ? items.map((t,i) => {
            const tok = t.token || {};
            const icon = this._tokenIcon(tok.address, 'base');
            return `
            <a href="https://dexscreener.com/base/${this._esc(tok.address||'')}" target="_blank" rel="noopener" class="card-h diff-row flex items-center gap-2 sm:gap-3 overflow-hidden">
                <span class="text-zinc-600 text-sm w-4 shrink-0">${trendingOffset+i+1}</span>
                ${icon?`<img src="${icon}" alt="" width="28" height="28" class="rounded-full bg-white/5 object-cover shrink-0" onerror="this.remove()">`:''}
                <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2 min-w-0">
                        <span class="truncate">${this._esc(tok.symbol||'?')}</span>
                        ${t.isVirtuals?'<span class="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30 shrink-0">Virtuals</span>':''}
                    </div>
                    <div class="text-xs text-zinc-500 truncate">${this._esc(tok.name||'')}</div>
                    <div class="text-[10px] text-zinc-500 sm:hidden truncate">Vol ${fmtUsd(t.volume24)} · MCap ${fmtUsd(t.marketCap)}</div>
                </div>
                <div class="text-right shrink-0 min-w-[4rem] sm:min-w-[6rem]">
                    <div class="stat text-sm sm:text-base">${t.priceUSD!=null?'$'+Number(t.priceUSD).toLocaleString(undefined,{maximumSignificantDigits:6}):'—'}</div>
                    <div class="text-xs">${typeof t.change24==='number'?pct(t.change24):'—'}</div>
                </div>
                <div class="text-right shrink-0 hidden sm:block w-20">
                    <div class="text-[10px] text-zinc-500 uppercase tracking-wider">Vol 24h</div>
                    <div class="text-xs text-zinc-300">${fmtUsd(t.volume24)}</div>
                </div>
                <div class="text-right shrink-0 hidden md:block w-20">
                    <div class="text-[10px] text-zinc-500 uppercase tracking-wider">Mkt cap</div>
                    <div class="text-xs text-zinc-300">${fmtUsd(t.marketCap)}</div>
                </div>
            </a>`;
        }).join('') : (this._trendingBase.length
            ? '<div class="text-zinc-500 text-sm">No tokens match your search.</div>'
            : '<div class="text-zinc-500 text-sm">Trending data unavailable right now.</div>');
    },

    // Human-readable "launched Xh ago" from a unix-seconds createdAt. Real
    // Codex data or nothing — returns '—' rather than a fabricated guess.
    _launchAge(createdAt) {
        if (typeof createdAt !== 'number') return '—';
        const mins = Math.floor((Date.now()/1000 - createdAt) / 60);
        if (mins < 60) return `${Math.max(mins,0)}m ago`;
        if (mins < 1440) return `${Math.floor(mins/60)}h ago`;
        return `${Math.floor(mins/1440)}d ago`;
    },

    // Newest tokens on Base by creation time (worker's /new-launches route,
    // see worker/src/lib/codex.ts::newLaunches) — the real, poll-friendly
    // launchpad feed that replaced the honest placeholder in
    // agents/codex_data.py::new_launchpad_tokens(). Reuses
    // _trendingTokenScore() as-is: brand-new tokens naturally read as
    // neutral "Fair" (liquidity/marketCap too new to score, not penalized)
    // unless something's already gone thin or wildly volatile.
    _launchesSort: 'createdAt',
    _renderNewLaunches() {
        const el = document.getElementById('new-launches');
        if (!el) return;
        const term = this._searchTerms.launches;
        const sorted = this._sortTokensBy(this._newLaunches, this._launchesSort);
        const filtered = sorted.filter(t => this._matchesTokenSearch(t.token?.symbol, t.token?.name, term));
        this._pgWire('launches-pg', 10, () => this._renderNewLaunches());
        const launchesOffset = this._pgPage('launches-pg') * 10;
        const items = this._pgSlice('launches-pg', filtered, 10);
        el.innerHTML = items.length ? items.map((t,i) => {
            const tok = t.token || {};
            const icon = this._tokenIcon(tok.address, 'base');
            return `
            <a href="https://dexscreener.com/base/${this._esc(tok.address||'')}" target="_blank" rel="noopener" class="card-h diff-row flex items-center gap-2 sm:gap-3 overflow-hidden">
                <span class="text-zinc-600 text-sm w-4 shrink-0">${launchesOffset+i+1}</span>
                ${icon?`<img src="${icon}" alt="" width="28" height="28" class="rounded-full bg-white/5 object-cover shrink-0" onerror="this.remove()">`:''}
                <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2 min-w-0">
                        <span class="truncate">${this._esc(tok.symbol||'?')}</span>
                        ${t.isVirtuals?'<span class="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30 shrink-0">Virtuals</span>':''}
                    </div>
                    <div class="text-xs text-zinc-500 truncate">${this._esc(tok.name||'')}</div>
                    <div class="text-[10px] text-zinc-500 sm:hidden truncate">Vol ${fmtUsd(t.volume24)} · MCap ${fmtUsd(t.marketCap)}</div>
                </div>
                <div class="text-right shrink-0 min-w-[4rem] sm:min-w-[6rem]">
                    <div class="stat text-sm sm:text-base">${t.priceUSD!=null?'$'+Number(t.priceUSD).toLocaleString(undefined,{maximumSignificantDigits:6}):'—'}</div>
                    <div class="text-xs text-zinc-500">${this._launchAge(t.createdAt)}</div>
                </div>
                <div class="text-right shrink-0 hidden sm:block w-20">
                    <div class="text-[10px] text-zinc-500 uppercase tracking-wider">Vol 24h</div>
                    <div class="text-xs text-zinc-300">${fmtUsd(t.volume24)}</div>
                </div>
                <div class="text-right shrink-0 hidden md:block w-20">
                    <div class="text-[10px] text-zinc-500 uppercase tracking-wider">Mkt cap</div>
                    <div class="text-xs text-zinc-300">${fmtUsd(t.marketCap)}</div>
                </div>
            </a>`;
        }).join('') : (this._newLaunches.length
            ? '<div class="text-zinc-500 text-sm">No tokens match your search.</div>'
            : '<div class="text-zinc-500 text-sm">No new launches right now.</div>');
    },

    _protoSort: 'tvl',
    async protocols() {
        const el = document.getElementById('protocols');
        try {
            const list = await (await fetch('https://api.llama.fi/protocols')).json();
            const base = list.filter(p => (p.chains||[]).includes('Base') && p.category!=='CEX' && (p.chainTvls?.Base>0))
                .map(p => ({name:p.name, slug:p.slug, tvl:p.chainTvls.Base, c1:p.change_1d, c7:p.change_7d, c30:p.change_1m, cat:p.category, logo:p.logo}))
                .sort((a,b)=>b.tvl-a.tvl).slice(0,8);
            // Kept for openProtocolReport() and _renderProtocolRows() to read
            // basic fields (tvl/c1/c7/c30/cat/logo) without a second /protocols
            // list fetch — the 8-protocol universe stays fixed (top by TVL);
            // #proto-sort only reorders this same set, it doesn't refetch.
            this._protoList = base;
            this._renderProtocolRows();
            this._enrichProtocols();
        } catch(e){ el.innerHTML = `<div class="text-amber-400 text-sm">Live protocol fetch unavailable.</div>`; }
    },

    // All-time TVL % change for a protocol — DefiLlama's list endpoint has
    // no "since inception" field, so this is derived from the full cached
    // history _enrichProtocols()/_ensureProtoDetail() populates. Returns
    // null (not zero) until that history has actually loaded for this slug.
    _allTimeChange(slug) {
        const hist = this._protoDetail[slug]?.tvlHistory;
        if (!hist || hist.length < 2 || !hist[0].v) return null;
        return ((hist[hist.length-1].v - hist[0].v) / hist[0].v) * 100;
    },

    // The % shown in each row's right-hand column tracks whichever range
    // #proto-sort currently has selected, so the visible number always
    // matches what the list is actually sorted by.
    _protoRangeVal(p) {
        const s = this._protoSort || 'tvl';
        if (s === '24h') return p.c1;
        if (s === '7d') return p.c7;
        if (s === '30d') return p.c30;
        if (s === 'all') return this._allTimeChange(p.slug);
        return p.c1; // 'tvl' — same 1d change shown before sorting existed
    },
    _protoRangeLabel() {
        const s = this._protoSort || 'tvl';
        return s === 'tvl' ? '24h' : s === 'all' ? 'all-time' : s;
    },

    // Re-sorts and redraws the already-fetched 8-protocol list in place —
    // no new network request (mirrors _renderMovers()'s tab-switch pattern).
    // Re-rendered nodes lose their spark/score/.proto-fees fill (fresh DOM),
    // so protocols()/the #proto-sort click handler both call
    // _enrichProtocols() right after — cache hits for already-known slugs
    // make that redraw effectively free.
    _renderProtocolRows() {
        const el = document.getElementById('protocols');
        const list = [...(this._protoList||[])];
        const s = this._protoSort || 'tvl';
        if (s === '24h') list.sort((a,b)=>(b.c1??-Infinity)-(a.c1??-Infinity));
        else if (s === '7d') list.sort((a,b)=>(b.c7??-Infinity)-(a.c7??-Infinity));
        else if (s === '30d') list.sort((a,b)=>(b.c30??-Infinity)-(a.c30??-Infinity));
        else if (s === 'all') list.sort((a,b)=>(this._allTimeChange(b.slug)??-Infinity)-(this._allTimeChange(a.slug)??-Infinity));
        else list.sort((a,b)=>b.tvl-a.tvl);
        const rangeLabel = this._protoRangeLabel();
        el.innerHTML = list.map((p,i)=>`
                <button onclick="App.openProtocolReport('${p.slug||''}')" class="card-h diff-row flex items-center gap-2 sm:gap-3">
                    <span class="text-zinc-600 text-sm w-4 sm:w-5 shrink-0">${i+1}</span>
                    ${p.logo?`<img src="${this._esc(p.logo)}" alt="" width="24" height="24" class="rounded-full bg-white/5 object-cover shrink-0 sm:w-7 sm:h-7" onerror="this.remove()">`:''}
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2 min-w-0">
                            <span class="truncate">${this._esc(p.name)}</span>
                        </div>
                        <div class="text-xs text-zinc-500 truncate">${this._esc(p.cat||'')}</div>
                        <div class="text-[11px] text-zinc-600 proto-fees">Fees 24h …</div>
                    </div>
                    <div class="spark shrink-0 hidden sm:block" data-slug="${this._esc(p.slug||'')}" style="width:72px;height:26px"></div>
                    <div class="text-right shrink-0 min-w-[4rem] sm:min-w-[6rem]">
                        <div class="stat text-sm sm:text-base">${fmtUsd(p.tvl)}</div>
                        <div class="text-[10px] text-zinc-600">${rangeLabel}</div>
                        <div class="text-xs">${pct(this._protoRangeVal(p))}</div>
                    </div>
                </button>`).join('');
    },

    // Combined per-protocol cache: full TVL history (not just a 14-day
    // slice — reused by the detail modal's range-selectable chart) + fees
    // 24h. Same 120ms-staggered fetch loop _sparklines() used to run alone;
    // now does one extra parallel request (fees) per protocol, still capped
    // at the 8 rows protocols() renders. Revenue/7d/30d fees and treasury
    // are deliberately NOT fetched here (kept lazy, per-slug, on modal open
    // in openProtocolReport()) to avoid ~3x the background requests on every
    // page load for numbers most visitors will never look at.
    _protoDetail: {},
    async _enrichProtocols() {
        const nodes = [...document.querySelectorAll('.spark[data-slug]')].filter(n=>n.dataset.slug && !n._done);
        for (const n of nodes) {
            n._done = true;
            const slug = n.dataset.slug;
            const row = n.closest('button.diff-row');
            try {
                let detail = this._protoDetail[slug];
                let fetchedFresh = false;
                if (!detail) {
                    fetchedFresh = true;
                    const [protoRes, feesRes] = await Promise.allSettled([
                        fetch(`https://api.llama.fi/protocol/${slug}`).then(r=>r.json()),
                        fetch(`https://api.llama.fi/summary/fees/${slug}?dataType=dailyFees`).then(r=>r.json()),
                    ]);
                    const d = protoRes.status==='fulfilled' ? protoRes.value : {};
                    const f = feesRes.status==='fulfilled' ? feesRes.value : {};
                    detail = {
                        // Full history, oldest→newest — _sparklines' own 14-day cap
                        // used to be applied here; now it's applied only at render
                        // time (both for this 14-day mini-chart and, unsliced, for
                        // the detail modal's 24h/7d/30d/90d/1y/all range selector).
                        tvlHistory: (d.chainTvls?.Base?.tvl || []).map(x=>({t:x.date*1000, v:x.totalLiquidityUSD||0})),
                        category: d.category, url: d.url, audits: d.audits, auditLinks: d.audit_links,
                        description: d.description, chains: d.chains, name: d.name, logo: d.logo,
                        fees24h: (f && !f.error) ? f.total24h : null,
                    };
                    this._protoDetail[slug] = detail;
                }
                const series = detail.tvlHistory.slice(-14).map(p=>p.v);
                if (series.length >= 2) {
                    const min=Math.min(...series), max=Math.max(...series), W=72, H=26, pad=2, rng=(max-min)||1;
                    const pts = series.map((v,i)=>{
                        const x = pad + i*(W-2*pad)/(series.length-1);
                        const y = H-pad - ((v-min)/rng)*(H-2*pad);
                        return `${x.toFixed(1)},${y.toFixed(1)}`;
                    }).join(' ');
                    const up = series[series.length-1] >= series[0];
                    n.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><polyline fill="none" stroke="${up?'#10b981':'#fb7185'}" stroke-width="1.5" points="${pts}"/></svg>`;
                }
                const feesEl = row?.querySelector('.proto-fees');
                if (feesEl) feesEl.textContent = `Fees 24h ${detail.fees24h!=null ? fmtUsd(detail.fees24h) : '—'}`;
                // Only the 8→9 real network requests need the courtesy
                // stagger to the free public API — a cache hit (from a
                // #proto-sort re-render, e.g.) fills instantly.
                if (fetchedFresh) await new Promise(r=>setTimeout(r,120));
            } catch(e){ /* leave blank on failure */ }
        }
    },

    // ── VAPE Score — quality/trust indicator, not a momentum signal ────────
    // 0-100, neutral start at 50, weighted additive factors generalizing
    // agents/virtuals_sweep.py::compute_health_score()'s pattern (deterministic,
    // never LLM-guessed) from one specific token to any Base protocol. Any
    // factor whose real data is missing this cycle is skipped — never
    // defaulted to a penalty — so a single flaky/untracked field only costs
    // precision, never direction (same rule that module documents).
    _protocolScore(p) {
        let score = 50;
        if (typeof p.c7 === 'number') {
            if (p.c7 >= 10) score += 20; else if (p.c7 > 0) score += 10;
            else if (p.c7 <= -20) score -= 20; else if (p.c7 < 0) score -= 10;
        }
        if (typeof p.c1 === 'number') {
            if (p.c1 >= 5) score += 10; else if (p.c1 > 0) score += 5;
            else if (p.c1 <= -10) score -= 10; else if (p.c1 < 0) score -= 5;
        }
        if (typeof p.fees24h === 'number' && p.fees24h > 0 && p.tvl > 0) {
            const feeYield = p.fees24h / p.tvl; // daily fee yield — real usage vs parked capital
            if (feeYield >= 0.001) score += 15; else if (feeYield >= 0.0002) score += 8; else score += 3;
        }
        if (p.audits && Number(p.audits) > 0) score += 7;
        return Math.max(0, Math.min(100, Math.round(score)));
    },

    // VAPE Score pill rendering is disabled site-wide for now — scores were
    // reading wildly wrong for some tokens. _scorePill()/_scoreBand() and
    // every *Score() function below are kept defined, just uncalled, pending
    // an accuracy fix; nothing currently invokes _scorePill().
    _scoreBand(score) {
        if (score >= 70) return { label: 'Strong', color: '#10b981' };
        if (score >= 40) return { label: 'Fair', color: '#fbbf24' };
        return { label: 'Weak', color: '#fb7185' };
    },
    _scorePill(score) {
        if (typeof score !== 'number') return '';
        const b = this._scoreBand(score);
        return `<span class="px-1.5 py-0.5 border text-[10px] whitespace-nowrap" style="color:${b.color};border-color:${b.color}" title="VAPE Score: ${b.label}">VAPE ${score}</span>`;
    },

    // One-line, human-readable list of which VAPE Score factors actually
    // fired for this protocol, so the modal doesn't just show a bare number.
    _scoreBreakdown(p) {
        const parts = [];
        if (typeof p.c7 === 'number') parts.push(p.c7 > 0 ? 'TVL 7d ↑' : p.c7 < 0 ? 'TVL 7d ↓' : 'TVL 7d flat');
        if (typeof p.fees24h === 'number' && p.fees24h > 0 && p.tvl > 0) {
            const y = p.fees24h / p.tvl;
            parts.push(y >= 0.001 ? 'fees/TVL strong' : y >= 0.0002 ? 'fees/TVL moderate' : 'fees/TVL thin');
        }
        if (p.audits && Number(p.audits) > 0) parts.push('audited');
        return parts.length ? parts.join(' · ') : 'insufficient data for a full breakdown';
    },

    // Ensures _protoDetail[slug] exists even if the user clicks a protocol
    // row before _enrichProtocols()'s staggered loop has reached it yet —
    // same fetch/shape as that loop, just triggered on demand instead of
    // waiting a turn.
    async _ensureProtoDetail(slug) {
        if (this._protoDetail[slug]) return this._protoDetail[slug];
        const [protoRes, feesRes] = await Promise.allSettled([
            fetch(`https://api.llama.fi/protocol/${slug}`).then(r=>r.json()),
            fetch(`https://api.llama.fi/summary/fees/${slug}?dataType=dailyFees`).then(r=>r.json()),
        ]);
        const d = protoRes.status==='fulfilled' ? protoRes.value : {};
        const f = feesRes.status==='fulfilled' ? feesRes.value : {};
        const detail = {
            tvlHistory: (d.chainTvls?.Base?.tvl || []).map(x=>({t:x.date*1000, v:x.totalLiquidityUSD||0})),
            category: d.category, url: d.url, audits: d.audits, auditLinks: d.audit_links,
            description: d.description, chains: d.chains, name: d.name, logo: d.logo,
            fees24h: (f && !f.error) ? f.total24h : null,
        };
        this._protoDetail[slug] = detail;
        return detail;
    },

    // Lazy, once-per-slug fetch of the heavier numbers most visitors never
    // look at (7d/30d fees, revenue, treasury) — only pulled when a user
    // actually opens this protocol's detail modal, cached on the same
    // _protoDetail[slug] record so reopening is instant.
    async _ensureProtoExtras(slug) {
        const detail = this._protoDetail[slug];
        if (!detail || detail.extrasFetchedAt) return detail;
        const [feesRes, revRes, treasuryRes] = await Promise.allSettled([
            fetch(`https://api.llama.fi/summary/fees/${slug}?dataType=dailyFees`).then(r=>r.json()),
            fetch(`https://api.llama.fi/summary/fees/${slug}?dataType=dailyRevenue`).then(r=>r.json()),
            fetch(`https://api.llama.fi/treasury/${slug}`).then(r=>r.json()),
        ]);
        const f = feesRes.status==='fulfilled' ? feesRes.value : {};
        if (f && !f.error) { detail.fees7d = f.total7d; detail.fees30d = f.total30d; detail.fees1y = f.total1y; detail.feesAllTime = f.totalAllTime; }
        const rev = revRes.status==='fulfilled' ? revRes.value : {};
        if (rev && !rev.error) { detail.revenue24h = rev.total24h; detail.revenue7d = rev.total7d; detail.revenue30d = rev.total30d; }
        const t = treasuryRes.status==='fulfilled' ? treasuryRes.value : {};
        if (t && !t.error) {
            // Mirrors agents/defillama.py::treasury()'s exact math: sum only
            // plain per-chain totals, excluding the "OwnTokens"/"<chain>-OwnTokens"
            // breakdown keys already folded into those totals (summing both
            // would double-count and inflate treasury_usd / skew own_token_share).
            const tvls = t.currentChainTvls || {};
            const own = tvls.OwnTokens || tvls.ownTokens || 0;
            const total = Object.entries(tvls).reduce((sum,[k,v]) =>
                (typeof v === 'number' && k !== 'OwnTokens' && k !== 'ownTokens' && !k.endsWith('-OwnTokens')) ? sum+v : sum, 0);
            if (total) detail.treasuryUsd = total, detail.ownTokenShare = own/total;
        }
        detail.extrasFetchedAt = Date.now();
        return detail;
    },

    _protoModal: null, _protoModalChart: null,
    _closeProtocolModal() {
        if (this._protoModalChart) { this._protoModalChart.destroy(); this._protoModalChart = null; }
        if (this._protoModal) { this._protoModal.remove(); this._protoModal = null; }
    },

    _renderProtoChart(slug, range) {
        const detail = this._protoDetail[slug];
        const canvas = document.getElementById('proto-report-chart');
        if (!detail || !canvas || !detail.tvlHistory.length) return;
        const slice = detail.tvlHistory.slice(-(RANGE_DAYS[range] || RANGE_DAYS['30d']));
        const labels = slice.map(p => new Date(p.t).toLocaleDateString(undefined,{month:'short',day:'numeric'}));
        const data = slice.map(p => p.v);
        if (this._protoModalChart) this._protoModalChart.destroy();
        const g = canvas.getContext('2d').createLinearGradient(0,0,0,200);
        g.addColorStop(0,'rgba(74,222,128,0.30)'); g.addColorStop(1,'rgba(74,222,128,0)');
        this._protoModalChart = new Chart(canvas, {
            type:'line',
            data:{ labels, datasets:[{ data, borderColor:'#4ade80', backgroundColor:g, fill:true, tension:0.25, pointRadius:0, borderWidth:2 }]},
            options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},
                tooltip:{callbacks:{label:c=>fmtUsd(c.parsed.y)}}},
                scales:{ y:{ticks:{color:'#52525b',callback:v=>fmtUsd(v)},grid:{color:'rgba(255,255,255,0.04)'}},
                         x:{ticks:{color:'#52525b',maxTicksLimit:8},grid:{display:false}} } }
        });
    },

    // Read-only protocol detail report — same .popover-over-backdrop modal
    // shell docs/assets/hire.js established for commerce flows, reused here
    // for a free, no-wallet, no-payment informational view.
    async openProtocolReport(slug) {
        this._closeProtocolModal();
        const base = (this._protoList || []).find(x => x.slug === slug) || { slug };
        const modal = document.createElement('div');
        modal.id = 'protocol-report-modal';
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" data-close></div>
            <div class="relative popover p-6 w-full max-w-lg max-h-[85vh] overflow-y-auto">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg flex items-center gap-2">
                        ${base.logo?`<img src="${this._esc(base.logo)}" alt="" width="24" height="24" class="rounded-full bg-white/5 object-cover" onerror="this.remove()">`:''}
                        ${this._esc(base.name || slug)}
                    </h3>
                    <button data-close class="text-zinc-500 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div id="proto-report-body" class="text-sm text-zinc-400">Loading…</div>
            </div>`;
        document.body.appendChild(modal);
        this._protoModal = modal;
        modal.querySelectorAll('[data-close]').forEach(el => el.onclick = () => this._closeProtocolModal());

        const body = document.getElementById('proto-report-body');
        try {
            const detail = await this._ensureProtoDetail(slug);
            body.innerHTML = `
                <div class="stat-line mb-5 pb-5 border-b border-white/10">
                    <span class="stat-pair"><span class="stat-label">tvl</span><span class="stat-value">${fmtUsd(base.tvl)}</span></span>
                    <span class="stat-pair"><span class="stat-label">fees 24h</span><span id="proto-fees24" class="stat-value">${detail.fees24h!=null?fmtUsd(detail.fees24h):'—'}</span></span>
                    <span class="stat-pair"><span class="stat-label">fees 7d</span><span id="proto-fees7" class="stat-value">…</span></span>
                    <span class="stat-pair"><span class="stat-label">fees 30d</span><span id="proto-fees30" class="stat-value">…</span></span>
                    <span class="stat-pair"><span class="stat-label">fees 1y</span><span id="proto-fees1y" class="stat-value">…</span></span>
                    <span class="stat-pair"><span class="stat-label">fees all-time</span><span id="proto-fees-all" class="stat-value">…</span></span>
                    <span class="stat-pair"><span class="stat-label">audits</span><span class="stat-value">${detail.audits?this._esc(String(detail.audits)):'—'}</span></span>
                </div>
                <div id="proto-treasury" class="text-xs text-zinc-500 mb-5"></div>
                <div class="flex items-center justify-between mb-3">
                    <h4 class="text-xs text-zinc-500 uppercase tracking-wider">TVL trend</h4>
                    <div class="flex gap-1 text-[11px]" id="proto-report-range">
                        <button data-d="24h" class="term-btn term-btn-sm">24h</button>
                        <button data-d="7d" class="term-btn term-btn-sm">7d</button>
                        <button data-d="30d" class="term-btn term-btn-sm term-btn-active">30d</button>
                        <button data-d="90d" class="term-btn term-btn-sm">90d</button>
                        <button data-d="1y" class="term-btn term-btn-sm">1y</button>
                        <button data-d="all" class="term-btn term-btn-sm">All</button>
                    </div>
                </div>
                <div class="chart-shell-sm mb-5"><canvas id="proto-report-chart"></canvas></div>
                ${detail.description?`<p class="text-xs text-zinc-500 mb-4 leading-relaxed">${this._esc(detail.description)}</p>`:''}
                <div class="flex gap-2 flex-wrap text-xs">
                    ${detail.url?`<a href="${this._esc(detail.url)}" target="_blank" rel="noopener" class="term-btn term-btn-sm"><i class="fa-solid fa-arrow-up-right-from-square"></i> Website</a>`:''}
                    <a href="https://defillama.com/protocol/${slug}" target="_blank" rel="noopener" class="term-btn term-btn-sm"><i class="fa-solid fa-arrow-up-right-from-square"></i> DefiLlama</a>
                    ${(detail.auditLinks||[]).slice(0,2).map(u=>`<a href="${this._esc(u)}" target="_blank" rel="noopener" class="term-btn term-btn-sm"><i class="fa-solid fa-shield-halved"></i> Audit</a>`).join('')}
                </div>`;
            this._renderProtoChart(slug, '30d');
            document.getElementById('proto-report-range').addEventListener('click', e => {
                const b = e.target.closest('button'); if (!b) return;
                [...e.currentTarget.children].forEach(x=>{x.className='term-btn term-btn-sm';});
                b.className='term-btn term-btn-sm term-btn-active';
                this._renderProtoChart(slug, b.dataset.d);
            });

            // Lazy extras (7d/30d fees, revenue, treasury) — fetched after the
            // core view above is already visible, so a slow/failed extra
            // fetch never blocks or breaks the rest of the modal.
            this._ensureProtoExtras(slug).then(d => {
                const f7 = document.getElementById('proto-fees7'); if (f7) f7.textContent = d.fees7d!=null?fmtUsd(d.fees7d):'—';
                const f30 = document.getElementById('proto-fees30'); if (f30) f30.textContent = d.fees30d!=null?fmtUsd(d.fees30d):'—';
                const f1y = document.getElementById('proto-fees1y'); if (f1y) f1y.textContent = d.fees1y!=null?fmtUsd(d.fees1y):'—';
                const fAll = document.getElementById('proto-fees-all'); if (fAll) fAll.textContent = d.feesAllTime!=null?fmtUsd(d.feesAllTime):'—';
                const tEl = document.getElementById('proto-treasury');
                if (tEl && d.treasuryUsd) {
                    tEl.textContent = `Treasury ${fmtUsd(d.treasuryUsd)}` + (d.ownTokenShare!=null ? ` · ${(d.ownTokenShare*100).toFixed(0)}% own-token` : '');
                }
            }).catch(()=>{});
        } catch(e) {
            body.innerHTML = '<div class="text-amber-400 text-sm">Protocol detail unavailable right now.</div>';
        }
    },

    // Bounty Ops (Task #197): real, checklist-tracked programs written by
    // agents/bounty_ops.py to intel/bounty-radar/bounty-ops/*.json. Keyed
    // by the same slug the backend generates (slugified program name) so a
    // card can show live checklist progress + a link to VAPE's own report
    // the moment one exists. Best-effort — a card renders fine with no
    // bounty-ops record at all (not every VAPE-fit program is tracked yet).
    _bountyOpsPromise: null,
    async _loadBountyOps() {
        if (this._bountyOpsPromise) return this._bountyOpsPromise;
        this._bountyOpsPromise = (async () => {
            try {
                const items = await (await fetch(`https://api.github.com/repos/${REPO}/contents/intel/bounty-radar/bounty-ops`)).json();
                const files = (Array.isArray(items) ? items : []).filter(f => f.name.endsWith('.json') && f.name !== 'INDEX.json');
                const entries = await Promise.all(files.map(f =>
                    fetch(`${RAW}/intel/bounty-radar/bounty-ops/${f.name}?t=`+Date.now()).then(r => r.json()).catch(() => null)
                ));
                const map = {};
                entries.filter(Boolean).forEach(e => {
                    const slug = (e.name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
                    map[slug] = e;
                });
                return map;
            } catch (e) { return {}; }
        })();
        return this._bountyOpsPromise;
    },

    _bountyOpsData: [], _bountyOpsMap: {},
    async bounties() {
        const el = document.getElementById('bounties');
        const searchEl = document.getElementById('bounty-ops-search');
        try {
            let data = await (await fetch(`${RAW}/intel/bounty-radar/opportunities.json?t=`+Date.now())).json();
            if (!Array.isArray(data)) data = [];
            // Task #196 fix: only real, VAPE-fit LIVE BOUNTY PROGRAMS here —
            // never a historical incident (track==="incident", already shown
            // in the Threat Ledger) and never a program whose scope doesn't
            // actually match VAPE's own tooling, regardless of headline $.
            data = data.filter(b => b.track === 'bounty' && b.vapeFit === true)
                       .sort((a,b)=>(b.bountyFitScore||0)-(a.bountyFitScore||0)).slice(0,30);
            if (!data.length) throw 0;
            const opsMap = await this._loadBountyOps();
            this._bountyOpsData = data;
            this._bountyOpsMap = opsMap;
            // Keyed lookup so docs/assets/hire.js::openBountyOps() can read back
            // full program context (name/platform/prize/vapeFitReason/tags) by
            // slug without stuffing a JSON blob into an inline onclick string.
            this._bountyOpsList = {};
            data.forEach(b => {
                const slug = (b.name||'').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
                this._bountyOpsList[slug] = b;
            });
            if (searchEl) {
                searchEl.classList.remove('hidden');
                searchEl.oninput = () => {
                    this._bountyOpsQuery = searchEl.value.trim().toLowerCase();
                    this._pgReset('bounty-ops-pg');
                    this._renderBounties();
                };
            }
            this._pgWire('bounty-ops-pg', 6, () => this._renderBounties());
            this._renderBounties();
        } catch(e){
            el.innerHTML = `<div class="text-zinc-500 text-sm">No VAPE-fit live bounty program currently tracked — <a class="text-zinc-400 hover:underline" href="https://github.com/${REPO}/tree/main/intel/bounty-radar" target="_blank">browse intel</a>.</div>`;
            if (searchEl) searchEl.classList.add('hidden');
        }
    },
    _bountyOpsQuery: '',
    _renderBounties() {
        const el = document.getElementById('bounties');
        if (!el) return;
        const opsMap = this._bountyOpsMap;
        let data = this._bountyOpsData;
        if (this._bountyOpsQuery) {
            const q = this._bountyOpsQuery;
            data = data.filter(b => `${b.name||''} ${b.platform||''} ${(b.tags||[]).join(' ')}`.toLowerCase().includes(q));
        }
        const items = this._pgSlice('bounty-ops-pg', data, 6);
        el.innerHTML = items.length ? items.map(b=>{
            const slug = (b.name||'').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
            const ops = opsMap[slug];
            const done = ops ? (ops.checklist||[]).filter(i=>i.done).length : 0;
            const total = ops ? (ops.checklist||[]).length : 0;
            return `
            <div class="diff-row">
                <div class="flex items-start justify-between gap-2">
                    <div class="text-sm leading-snug">${this._esc(b.name||'Unknown')}</div>
                    <div class="text-zinc-100 shrink-0">${b.prizeUsd?fmtUsd(b.prizeUsd):'—'}</div>
                </div>
                <div class="text-xs text-zinc-500 mt-2">${this._esc(b.platform||'')} ${b.status?'· '+this._esc(b.status):''}</div>
                ${b.vapeFitReason?`<div class="text-[10px] text-[#60a5fa]/80 mt-1.5"><i class="fa-solid fa-check-circle"></i> ${this._esc(b.vapeFitReason)}</div>`:''}
                ${(b.tags||[]).slice(0,4).map(t=>`<span class="inline-block text-[10px] mr-2 mt-2 text-zinc-500">${this._esc(t)}</span>`).join('')}
                ${ops?`<div class="mt-2 pt-2 border-t border-white/5 flex items-center justify-between text-[10px] text-zinc-500">
                    <span><i class="fa-solid fa-list-check"></i> Bounty Ops tracked${total?` · ${done}/${total} checklist`:''}</span>
                    ${ops.vapeReportUrl?`<span><i class="fa-solid fa-file-shield"></i> VAPE report</span>`:''}
                </div>`:''}
                <div class="mt-2.5 pt-2.5 border-t border-white/5 flex items-center gap-3">
                    <a href="${b.url||'#'}" target="_blank" class="text-[11px] text-zinc-500 hover:underline"><i class="fa-solid fa-arrow-up-right-from-square"></i> View program</a>
                    <button onclick="Hire.openBountyOps('${slug}')" class="text-[11px] text-[#60a5fa]/90 hover:underline"><i class="fa-solid fa-bolt"></i> Hire VAPE for this bounty</button>
                </div>
            </div>`;
        }).join('') : '<div class="text-zinc-500 text-sm">No bounty programs match this filter.</div>';
    },

    // Prefers the generated intel index (real title/type/verdict/summary per
    // report, same source the Archive's Reports tab uses) over a bare GitHub
    // directory listing — falls back to filenames-only if the index isn't
    // reachable for any reason, since that's still real, live data.
    async reports() {
        const el = document.getElementById('reports');
        try {
            const d = await this._loadIntel();
            if (!d) throw new Error('intel index unavailable');
            const items = (d.reports||[]).slice().sort((a,b)=>(b.date||'').localeCompare(a.date||'')).slice(0,6);
            if (!items.length) throw new Error('no reports in index');
            el.innerHTML = items.map(r=>`
                <a href="${r.url}" target="_blank" class="card-h diff-row flex items-start gap-3">
                    <i class="fa-solid fa-file-lines text-zinc-500 mt-1 shrink-0"></i>
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center justify-between gap-2">
                            <span class="text-sm truncate min-w-0">${this._esc(r.title||r.file)}</span>
                            ${this._pill(r.threat)}
                        </div>
                        <div class="text-xs text-zinc-500 mt-1 truncate">${this._esc(r.type||'report')} · ${this._ago(r.date)}</div>
                        ${r.summary?`<div class="text-[11px] text-zinc-400 mt-1 leading-snug truncate">${this._esc(r.summary)}</div>`:''}
                    </div>
                    <i class="fa-solid fa-arrow-up-right-from-square text-zinc-600 text-[10px] shrink-0 mt-1.5"></i>
                </a>`).join('');
        } catch(e) {
            try {
                const items = await (await fetch(`https://api.github.com/repos/${REPO}/contents/reports`)).json();
                const md = (Array.isArray(items)?items:[]).filter(f=>f.name.endsWith('.md'))
                    .map(f=>{ const m=f.name.match(/(\d{8})_(\d{6})/); f._ts=m?m[1]+m[2]:'0'; return f; })
                    .sort((a,b)=>b._ts.localeCompare(a._ts)).slice(0,6);
                if (!md.length) throw 0;
                el.innerHTML = md.map(f=>`
                    <a href="${f.html_url}" target="_blank" class="card-h diff-row flex items-center justify-between text-sm">
                        <span class="flex items-center gap-2 min-w-0"><i class="fa-solid fa-file-lines text-zinc-500"></i><span class="truncate">${f.name}</span></span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-zinc-600 text-xs shrink-0"></i>
                    </a>`).join('');
            } catch (e2) {
                el.innerHTML = `<a href="https://github.com/${REPO}/tree/main/reports" target="_blank" class="text-zinc-400 hover:underline text-sm">View all reports on GitHub →</a>`;
            }
        }
    },

    // ── Intel index: investigation summary + explorer (from data/intel-index.json)
    _intel: null, _tab: 'investigations', _typeFilter: null,
    INTEL_PAGE_SIZE: 10,
    _intelQuery: '', _intelSort: 'date_desc', _intelPage: 0,
    _verdictColor(v){
        v=(v||'').toUpperCase();
        if(/REJECT|CRITICAL|HIGH|BEARISH|RISK-OFF|FEAR/.test(v)) return '#fb7185';
        if(/CAUTION|MEDIUM|NEUTRAL/.test(v)) return '#fbbf24';
        if(/PROCEED|LOW|ALL CLEAR|BULLISH|RISK-ON|GREED/.test(v)) return '#10b981';
        return '#a1a1aa';
    },
    _pill(v){ if(!v) return ''; const c=this._verdictColor(v);
        return `<span class="px-2 py-0.5 border text-[11px] whitespace-nowrap" style="color:${c};border-color:${c}">${v}</span>`; },
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
    // Real bug fixed here: investigations are now genuinely multi-chain
    // (agents/investigate.py rotates auto-target across 7 EVM chains), but
    // this used to only distinguish arbitrum/ethereum/base — anything else
    // (Optimism/Polygon/BNB Chain/Avalanche) silently fell through to 'base',
    // giving a wrong-chain token-icon CDN path and a wrong explorer link.
    // Extracts the leading chain-id number from whatever format the
    // "Chain:" field is in (e.g. "42161 (Arbitrum)") and maps it directly —
    // robust to the exact display text wrapping around it.
    _CHAIN_ID_MAP: {'1':'ethereum','8453':'base','42161':'arbitrum','10':'optimism','137':'polygon','56':'bsc','43114':'avalanche'},
    _chainSlug(c){
        const m = String(c||'').match(/\d+/);
        return (m && this._CHAIN_ID_MAP[m[0]]) || 'base';
    },
    _tokenIcon(address, chain){
        if(!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) return null;
        return `https://dd.dexscreener.com/ds-data/tokens/${this._chainSlug(chain)}/${address.toLowerCase()}.png?size=lg`;
    },
    _explorerUrl(address, chain){
        if(!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) return null;
        const slug = this._chainSlug(chain);
        const hosts = {arbitrum:'arbiscan.io', ethereum:'etherscan.io', optimism:'optimistic.etherscan.io',
                       polygon:'polygonscan.com', bsc:'bscscan.com', avalanche:'snowtrace.io', base:'basescan.org'};
        return `https://${hosts[slug]||'basescan.org'}/address/${address}`;
    },
    // Archive/report-card meta line: small wrapping chips instead of a single
    // "·"-joined text string — a long joined line (long address, long offering
    // name) has nowhere to shrink and can push a narrow card wider than its
    // container; chips wrap onto a new line instead, so a card's width is
    // always bounded by its own layout, never by its content.
    _metaChips(parts){
        const items = parts.filter(Boolean);
        if(!items.length) return '';
        return `<div class="flex flex-wrap items-center gap-1.5 mt-1.5">${items.map(p=>`<span class="text-[10px] px-2 py-0.5 rounded bg-white/5 text-zinc-500 whitespace-nowrap max-w-full truncate">${p}</span>`).join('')}</div>`;
    },
    _iconChip(inner, colorClass=''){
        return `<div class="w-9 h-9 border border-white/10 ${colorClass} flex items-center justify-center shrink-0 overflow-hidden">${inner}</div>`;
    },
    // Plain inline icon indicator — no border/box chrome, matching the flat
    // footer-link icon style (Repository/Reports/Documentation in the
    // Resources panel: a bare icon in the surrounding text color). Same
    // width/alignment slot as _iconChip() so list rows still line up; the
    // bordered "chip" frame stays reserved for real image avatars (token
    // logos), a distinct, deliberate pattern matching the nav logo/hero
    // portrait/wallet chip elsewhere on the site.
    _iconGlyph(faClasses, colorStyle=''){
        return `<div class="w-9 flex items-start justify-center pt-0.5 shrink-0"><i class="fa-solid ${faClasses} text-zinc-400 text-sm"${colorStyle?` style="color:${colorStyle}"`:''}></i></div>`;
    },
    _iconImg(address, chain, size=36, extra=''){
        const src = this._tokenIcon(address, chain);
        return src ? `<img src="${src}" alt="" width="${size}" height="${size}" class="rounded-full bg-white/5 object-cover shrink-0 ${extra}" onerror="this.remove()">` : '';
    },

    async intel(){
        try{
            this._intel = await this._loadIntel();
            if(!this._intel) throw new Error('intel index unavailable');
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
                const showName = inv.name && inv.name.toLowerCase() !== (sym||'').toLowerCase();
                const explorer = this._explorerUrl(inv.target, inv.chain);
                iel.innerHTML=`
                    <div class="flex items-center justify-between gap-2 mb-3">
                        <div class="text-[10px] uppercase tracking-widest text-[#60a5fa] flex items-center gap-1.5"><i class="fa-solid fa-magnifying-glass-chart"></i> Deep Investigation</div>
                        ${this._pill(inv.verdict)}
                    </div>
                    <a href="${explorer||'#'}" target="_blank" rel="noopener" class="flex items-center gap-3 mb-1 ${explorer?'hover:opacity-80':'pointer-events-none'}">
                        ${this._iconImg(inv.target, inv.chain, 48)}
                        <div class="min-w-0">
                            <div class="text-xl leading-tight truncate">${this._esc(heading)}</div>
                            ${showName?`<div class="text-xs text-zinc-400 truncate">${this._esc(inv.name)}</div>`:''}
                            ${inv.target?`<div class="font-mono text-[11px] text-zinc-500 truncate" title="${this._esc(inv.target)}">${this._esc(this._shortAddr(inv.target))} ${explorer?'<i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-60"></i>':''}</div>`:''}
                        </div>
                    </a>
                    ${inv.score?`<div class="text-xs text-zinc-400 mt-2 mb-2">Safety score <span class="text-zinc-200 text-sm">${inv.score}</span><span class="text-zinc-600">/100</span></div>`:''}
                    <div class="text-xs text-zinc-400 leading-relaxed break-words">${this._esc(inv.summary||inv.key_finding||'')}</div>
                    <a href="${inv.url}" target="_blank" class="inline-flex items-center gap-1.5 text-[#60a5fa] text-xs mt-4 hover:underline">Read full investigation <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i></a>`;
            } else { iel.innerHTML='<div class="text-zinc-500 text-sm">No investigation logged yet.</div>'; }
            // hero: latest report
            const rep=(d.latest_summary||{}).report;
            const rel=document.getElementById('inv-report');
            if(rep){
                rel.innerHTML=`
                    <div class="flex items-center justify-between gap-2 mb-3">
                        <div class="text-[10px] uppercase tracking-widest text-[#60a5fa] flex items-center gap-1.5"><i class="fa-solid fa-file-shield"></i> Latest Report · ${this._esc(rep.type||'')}</div>
                        ${this._pill(rep.threat)}
                    </div>
                    <div class="text-xl leading-tight mb-1 break-words">${this._esc(rep.title||rep.file)}</div>
                    <div class="text-[11px] text-zinc-500 mb-3">${this._ago(rep.date)}</div>
                    <div class="text-xs text-zinc-400 leading-relaxed break-words">${this._esc((rep.summary||'').slice(0,260))}${(rep.summary||'').length>260?'…':''}</div>
                    <a href="${rep.url}" target="_blank" class="inline-flex items-center gap-1.5 text-[#60a5fa] text-xs mt-4 hover:underline">Open report <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i></a>`;
            } else { rel.innerHTML='<div class="text-zinc-500 text-sm">No report indexed.</div>'; }
            this._renderIntel();
        }catch(e){
            document.getElementById('intel-body').innerHTML='<div class="text-amber-400 text-sm">Intel index unavailable (regenerating next cycle).</div>';
        }
    },

    // Track Record stat tiles link here to jump straight to the matching
    // Archive tab instead of dropping the visitor on the section and making
    // them find it themselves.
    gotoArchive(tab){
        this._tab = tab; this._typeFilter = null; this._intelPage = 0;
        const tabsEl = document.getElementById('intel-tabs');
        if (tabsEl) {
            [...tabsEl.querySelectorAll('button[data-tab]')].forEach(b=>{
                b.className = b.dataset.tab===tab ? 'term-btn term-btn-sm term-btn-active' : 'term-btn term-btn-sm';
            });
        }
        this._renderIntel();
        document.getElementById('the-archive')?.scrollIntoView({ behavior:'smooth', block:'start' });
    },

    // Generic search text + date extractor per tab's differently-shaped
    // items — lets one search box/sort control work across all 4 tabs
    // without each tab needing its own filter UI.
    _intelSearchText(tab, item){
        if(tab==='investigations') return [item.title, item.symbol, item.name, item.target, item.date].filter(Boolean).join(' ');
        if(tab==='reports') return [item.title, item.file, item.type, item.date].filter(Boolean).join(' ');
        if(tab==='broadcasts') return [item.title, item.file, item.date].filter(Boolean).join(' ');
        if(tab==='tools') return [item.name, item.tier, item.purpose, item.status].filter(Boolean).join(' ');
        return '';
    },
    _intelTitle(tab, item){
        return (tab==='tools' ? item.name : (item.title||item.file)) || '';
    },
    _intelDate(item){ return item.date ? new Date(item.date) : null; },

    _wireIntelControls(){
        if(this._intelWired) return;
        this._intelWired = true;
        const search = document.getElementById('intel-search');
        const sort = document.getElementById('intel-sort');
        const prev = document.getElementById('intel-prev');
        const next = document.getElementById('intel-next');
        if(search) search.addEventListener('input', ()=>{
            this._intelQuery = search.value.trim().toLowerCase();
            this._intelPage = 0;
            this._renderIntel();
        });
        if(sort) sort.addEventListener('change', ()=>{
            this._intelSort = sort.value;
            this._intelPage = 0;
            this._renderIntel();
        });
        if(prev) prev.addEventListener('click', ()=>{
            this._intelPage = Math.max(0, this._intelPage - 1);
            this._renderIntel();
        });
        if(next) next.addEventListener('click', ()=>{
            this._intelPage += 1;
            this._renderIntel();
        });
    },

    _renderIntelPagination(total){
        const countEl=document.getElementById('intel-count');
        const pageEl=document.getElementById('intel-page');
        const prev=document.getElementById('intel-prev');
        const next=document.getElementById('intel-next');
        const page=this._intelPage;
        const pages=Math.max(1, Math.ceil(total/this.INTEL_PAGE_SIZE));
        if(countEl) countEl.textContent = total
            ? `Showing ${page*this.INTEL_PAGE_SIZE+1}–${Math.min(total,(page+1)*this.INTEL_PAGE_SIZE)} of ${total}`
            : 'No entries match this filter.';
        if(pageEl) pageEl.textContent = `Page ${page+1} of ${pages}`;
        if(prev) prev.disabled = page<=0;
        if(next) next.disabled = page+1>=pages;
    },

    _renderIntel(){
        const d=this._intel; if(!d) return;
        this._wireIntelControls();
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
                    return `<button data-type="${v}" class="term-btn term-btn-sm ${on?'term-btn-active':''}">${label}${v?` <span class="opacity-60">${d.counts.reports_by_type[v]}</span>`:''}</button>`;
                }).join('');
        } else { fw.classList.add('hidden'); }

        // Search + sort across whichever tab is active, then paginate —
        // applied uniformly here so each per-tab branch below only needs to
        // render whatever page slice it's handed.
        const rawByTab = { investigations: d.investigations||[], reports: d.reports||[], broadcasts: d.broadcasts||[], tools: d.tools||[] };
        let allItems = rawByTab[tab] || [];
        if(tab==='reports' && this._typeFilter) allItems = allItems.filter(r=>r.type===this._typeFilter);
        if(this._intelQuery) allItems = allItems.filter(item => this._intelSearchText(tab,item).toLowerCase().includes(this._intelQuery));
        allItems = [...allItems].sort((a,b)=>{
            if(this._intelSort==='title_asc') return this._intelTitle(tab,a).localeCompare(this._intelTitle(tab,b));
            const da=this._intelDate(a), db=this._intelDate(b);
            if(!da && !db) return 0;
            if(!da) return 1;
            if(!db) return -1;
            return this._intelSort==='date_asc' ? da-db : db-da;
        });
        const page=this._intelPage;
        const items = allItems.slice(page*this.INTEL_PAGE_SIZE, (page+1)*this.INTEL_PAGE_SIZE);
        this._renderIntelPagination(allItems.length);

        let rows='';
        if(tab==='investigations'){
            rows=items.length?items.map(i=>{
                const sym = i.symbol || this._symFromTitle(i.title);
                const showName = i.name && i.name.toLowerCase() !== (sym||'').toLowerCase();
                const icon = this._iconImg(i.target, i.chain, 36, 'w-full h-full');
                return `
                <a href="${i.url}" target="_blank" class="card-h diff-row flex items-start gap-3 overflow-hidden">
                    ${icon ? this._iconChip(icon) : this._iconGlyph('fa-magnifying-glass-chart')}
                    <div class="min-w-0 flex-1">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <span class="min-w-0 truncate">
                                <span class="text-xs">${this._esc(sym || this._shortAddr(i.target) || i.title || 'target')}</span>
                                ${showName?`<span class="text-[11px] text-zinc-500 ml-1.5">${this._esc(i.name)}</span>`:''}
                            </span>
                            <span class="flex items-center gap-2 shrink-0">${i.score?`<span class="text-zinc-300 text-xs">${i.score}</span>`:''}${this._pill(i.verdict)}</span>
                        </div>
                        ${this._metaChips([
                            i.target?`<span class="font-mono" title="${this._esc(i.target)}">${this._esc(this._shortAddr(i.target))}</span>`:null,
                            this._esc(i.date||''),
                            this._esc(i.offering||i.chain||'deep_investigation'),
                        ])}
                        ${(i.summary||i.key_finding)?`<div class="text-[11px] text-zinc-400 mt-1.5 leading-snug break-words line-clamp-2">${this._esc(i.summary||i.key_finding)}</div>`:''}
                    </div>
                </a>`;
            }).join(''):'<div class="text-zinc-500 text-sm">No investigations logged yet.</div>';
        } else if(tab==='reports'){
            rows=items.length?items.map(r=>`
                <a href="${r.url}" target="_blank" class="card-h diff-row flex items-start gap-3 overflow-hidden">
                    ${this._iconGlyph('fa-file-lines')}
                    <div class="min-w-0 flex-1">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <span class="text-sm truncate min-w-0">${this._esc(r.title||r.file)}</span>
                            ${this._pill(r.threat)}
                        </div>
                        ${this._metaChips([this._esc(r.type), this._esc(this._ago(r.date))])}
                        ${r.summary?`<div class="text-[11px] text-zinc-400 mt-1.5 leading-snug break-words line-clamp-2">${this._esc(r.summary)}</div>`:''}
                    </div>
                </a>`).join(''):'<div class="text-zinc-500 text-sm">No reports for this filter.</div>';
        } else if(tab==='broadcasts'){
            rows=items.length?items.map(b=>`
                <a href="${b.url}" target="_blank" class="card-h diff-row flex items-start gap-3 overflow-hidden">
                    ${this._iconGlyph('fa-tower-broadcast')}
                    <div class="min-w-0 flex-1">
                        <div class="text-sm break-words">${this._esc(b.title||b.file)}</div>
                        ${this._metaChips([this._esc(this._ago(b.date))])}
                        ${b.summary?`<div class="text-[11px] text-zinc-400 mt-1.5 leading-snug break-words line-clamp-2">${this._esc(b.summary)}</div>`:''}
                    </div>
                </a>`).join(''):'<div class="text-zinc-500 text-sm">No broadcasts yet.</div>';
        } else if(tab==='tools'){
            rows=items.length?items.map(t=>{
                const ok=t.status==='verified'; const lim=t.known_limitation;
                const col=ok?'#4ade80':(lim?'#fbbf24':'#a1a1aa');
                return `<a href="${t.url||'#'}" target="_blank" class="card-h diff-row flex items-start gap-3 overflow-hidden">
                    ${this._iconGlyph(ok?'fa-circle-check':'fa-circle-dot', col)}
                    <div class="min-w-0 flex-1">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <span class="text-sm truncate min-w-0">${this._esc(t.name)}${t.version?`<span class="text-zinc-600"> v${this._esc(t.version)}</span>`:''}</span>
                            <span class="text-[11px] px-2 py-0.5 border shrink-0" style="color:${col};border-color:${col}">${this._esc(t.status||'?')}</span>
                        </div>
                        ${this._metaChips([this._esc(t.tier), t.purpose?this._esc(t.purpose):null])}
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
    // Safety net: some embedded/webview browsers report inconsistent
    // IntersectionObserver results (or none at all) for sections already in
    // the viewport at load. A section that never gets marked in-view stays
    // at opacity:0 forever — invisible, not just unanimated. If anything is
    // still hidden a few seconds after load, reveal it outright rather than
    // leave real content permanently blank.
    setTimeout(() => {
        document.querySelectorAll('.reveal:not(.in-view)').forEach(el => el.classList.add('in-view'));
    }, 2500);
}

window.addEventListener('load', () => {
    initReveal();
    App.refresh();
    setInterval(()=>App.refresh(), 300000);
    // chart range buttons
    document.getElementById('tvl-range').addEventListener('click', e => {
        const b = e.target.closest('button'); if (!b) return;
        App._chartRange = b.dataset.d;
        [...e.currentTarget.children].forEach(x=>{x.className='term-btn term-btn-sm';});
        b.className='term-btn term-btn-sm term-btn-active';
        App.chart(App._chartRange);
    });
    // Base Movers tab switching — re-sorts the already-fetched set, no new request
    document.getElementById('movers-tabs').addEventListener('click', e => {
        const b = e.target.closest('button[data-m]'); if (!b) return;
        App._moversTab = b.dataset.m;
        [...e.currentTarget.children].forEach(x=>{x.className='term-btn term-btn-sm';});
        b.className='term-btn term-btn-sm term-btn-active';
        App._renderMovers();
    });
    // Top Base Protocols sort — re-sorts the already-fetched top-8-by-TVL
    // set, no new list request. 'All-time %' is the one option that needs
    // each protocol's full TVL history, which may not be cached yet this
    // early — _ensureProtoDetail() fetches (or reuses the cache) for any
    // slug still missing it before the re-sort/redraw happens.
    document.getElementById('proto-sort').addEventListener('click', async e => {
        const b = e.target.closest('button[data-s]'); if (!b) return;
        App._protoSort = b.dataset.s;
        [...e.currentTarget.children].forEach(x=>{x.className='term-btn term-btn-sm';});
        b.className='term-btn term-btn-sm term-btn-active';
        if (App._protoSort === 'all') {
            await Promise.all((App._protoList||[]).map(p => App._ensureProtoDetail(p.slug)));
        }
        App._renderProtocolRows();
        App._enrichProtocols();
    });
    // Trending on Base / New Launches sort — re-sorts the already-fetched
    // 30-row Codex set (see App.virtuals()), no new request per click.
    document.getElementById('trending-sort').addEventListener('click', e => {
        const b = e.target.closest('button[data-s]'); if (!b) return;
        App._trendingSort = b.dataset.s;
        [...e.currentTarget.children].forEach(x=>{x.className='term-btn term-btn-sm';});
        b.className='term-btn term-btn-sm term-btn-active';
        App._renderTrendingBase();
    });
    document.getElementById('launches-sort').addEventListener('click', e => {
        const b = e.target.closest('button[data-s]'); if (!b) return;
        App._launchesSort = b.dataset.s;
        [...e.currentTarget.children].forEach(x=>{x.className='term-btn term-btn-sm';});
        b.className='term-btn term-btn-sm term-btn-active';
        App._renderNewLaunches();
    });
    // Enter key launches hunt
    document.getElementById('hunt-target').addEventListener('keypress', e=>{ if(e.key==='Enter') App.hunt(); });
    // Intel Explorer tab switching
    document.getElementById('intel-tabs').addEventListener('click', e=>{
        const b=e.target.closest('button[data-tab]'); if(!b) return;
        App._tab=b.dataset.tab; App._typeFilter=null; App._intelPage=0;
        [...e.currentTarget.querySelectorAll('button')].forEach(x=>x.className='term-btn term-btn-sm');
        b.className='term-btn term-btn-sm term-btn-active';
        App._renderIntel();
    });
    // Report type filter
    document.getElementById('intel-filter').addEventListener('click', e=>{
        const b=e.target.closest('button[data-type]'); if(!b) return;
        App._typeFilter=b.dataset.type||null; App._intelPage=0; App._renderIntel();
    });
    // Sticky nav — mobile menu toggle + auto-close on link click
    const navToggle = document.getElementById('nav-menu-toggle');
    const navPanel = document.getElementById('nav-menu-panel');
    if (navToggle && navPanel) {
        // Visibility is animated (opacity/scale), not display:none, so open/close
        // can actually transition instead of an abrupt cut — see site.css.
        const OPEN = ['visible', 'opacity-100', 'scale-100', 'translate-y-0', 'pointer-events-auto'];
        const CLOSED = ['invisible', 'opacity-0', 'scale-[0.98]', '-translate-y-1', 'pointer-events-none'];
        // Two inline SVGs swapped by `hidden`, rather than reclassing one
        // Font Awesome <i> between fa-bars/fa-xmark — the icon font is a
        // third-party CDN dependency and this control has to render without it.
        const navBars = document.getElementById('nav-menu-bars');
        const navClose = document.getElementById('nav-menu-close');
        const setOpen = (open) => {
            navPanel.classList.remove(...(open ? CLOSED : OPEN));
            navPanel.classList.add(...(open ? OPEN : CLOSED));
            navToggle.setAttribute('aria-expanded', String(open));
            navBars?.classList.toggle('hidden', open);
            navClose?.classList.toggle('hidden', !open);
        };
        navToggle.addEventListener('click', () => setOpen(navPanel.classList.contains('invisible')));
        navPanel.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setOpen(false)));
        document.addEventListener('click', (e) => {
            if (!navPanel.classList.contains('invisible') && !navPanel.contains(e.target) && !navToggle.contains(e.target)) setOpen(false);
        });
    }
    // Icon Dropdowns — GitHub-style menus for section actions
    document.addEventListener('click', (e) => {
        const dropdown = e.target.closest('.icon-dropdown');
        if (!dropdown) {
            // Close all open dropdowns when clicking outside
            document.querySelectorAll('.icon-dropdown.active').forEach(d => d.classList.remove('active'));
            return;
        }
        // Toggle the clicked dropdown and close all others
        document.querySelectorAll('.icon-dropdown.active').forEach(d => {
            if (d !== dropdown) d.classList.remove('active');
        });
        dropdown.classList.toggle('active');
    });
});
