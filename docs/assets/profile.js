import { tokenIconByAddress } from './icons.js';

// VAPE wallet profile ("Portfolio Intelligence"). Two data paths:
//  - Worker path (window.WORKER_BASE set, vape-x402 deployed with an Alchemy
//    key): full auto-discovered ETH + ERC-20 balances via /portfolio, plus
//    NFT holdings via /nfts — no curated list needed, Alchemy has already
//    indexed every token/NFT the wallet actually holds.
//  - Fallback path (no worker, or it errors): native ETH + a curated,
//    verified Base token list (docs/assets/base-tokens.json), read live via
//    public RPC (mainnet.base.org). No NFTs on this path — see
//    docs/assets/base-tokens.json for why that list is small and verified
//    rather than "everything".
// Both paths price tokens the same way: one batched CoinGecko contract-
// address lookup, preferring the vape-x402 worker's /prices proxy (attaches
// a CoinGecko Demo API key server-side for better rate-limit headroom) and
// falling back to a direct, unauthenticated CoinGecko call if the worker
// isn't deployed or errors.
const RPC_URL = 'https://mainnet.base.org';

// Token/NFT names and symbols are read straight off arbitrary on-chain
// contract metadata (via Alchemy for auto-discovered holdings) — anyone can
// mint a token or NFT with a malicious name() and dust it to any wallet, so
// this text is attacker-controlled and must never go into innerHTML unescaped.
function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

const Profile = {
    _tokenList: null,
    _chart: null,
    _barChart: null,
    _manual: [], // user-added {symbol,address,decimals}
    _viaWorker: false,

    async _rpc(method, params = []) {
        const r = await fetch(RPC_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method, params, id: 1 }),
        });
        const j = await r.json();
        if (j.error) throw new Error(j.error.message || 'RPC error');
        return j.result;
    },

    async _ethBalance(address) {
        const hex = await this._rpc('eth_getBalance', [address, 'latest']);
        return parseInt(hex, 16) / 1e18;
    },

    async _tokenBalance(tokenAddress, ownerAddress, decimals) {
        // balanceOf(address) selector 0x70a08231 + owner padded to 32 bytes
        const data = '0x70a08231' + ownerAddress.slice(2).toLowerCase().padStart(64, '0');
        try {
            const hex = await this._rpc('eth_call', [{ to: tokenAddress, data }, 'latest']);
            if (!hex || hex === '0x') return 0;
            return parseInt(hex, 16) / Math.pow(10, decimals);
            // Note: parseInt loses precision above 2^53 — fine for a display-only
            // balance at normal token-decimal scales, not for accounting.
        } catch (e) { return 0; }
    },

    async _prices(addresses) {
        if (!addresses.length) return {};
        if (window.WORKER_BASE) {
            try {
                const res = await fetch(`${window.WORKER_BASE}/prices?addresses=${addresses.join(',')}`);
                if (res.ok) return await res.json();
            } catch (e) { /* fall through to direct CoinGecko */ }
        }
        try {
            const url = `https://api.coingecko.com/api/v3/simple/token_price/base?contract_addresses=${addresses.join(',')}&vs_currencies=usd&include_24hr_change=true`;
            return await (await fetch(url)).json();
        } catch (e) { return {}; }
    },

    // Estimated cost-basis P&L, opt-in (heavier: Alchemy transfer history +
    // CoinGecko historical price per token) — needs the worker deployed with
    // both ALCHEMY_API_KEY and COINGECKO_API_KEY. See worker/src/lib/
    // costBasis.ts for exactly what this does and doesn't compute (a single
    // first-acquisition price point per token, not full weighted-average
    // accounting) — that honesty is preserved end-to-end into the UI labels.
    async loadCostBasis(address) {
        if (!window.WORKER_BASE) return { error: 'not-configured' };
        try {
            const res = await fetch(`${window.WORKER_BASE}/cost-basis?address=${address}`);
            if (res.status === 503) return { error: 'not-configured' };
            if (!res.ok) return { error: 'upstream-failed' };
            const data = await res.json();
            return { results: data.results || [] };
        } catch (e) {
            return { error: 'upstream-failed' };
        }
    },

    // Full auto-discovered ETH + ERC-20 balances via the vape-x402 worker's
    // Alchemy-backed /portfolio route. Returns null (not throws) on any
    // failure — every caller falls back to the direct-RPC + curated-list path.
    // Records the *why* in this._workerError so the fallback coverage note
    // below can show a real reason instead of just "worker unavailable" —
    // that's the one piece of information nobody can see without devtools.
    async _discoverViaWorker(address) {
        this._workerError = null;
        if (!window.WORKER_BASE) { this._workerError = 'WORKER_BASE not set'; return null; }
        try {
            const res = await fetch(`${window.WORKER_BASE}/portfolio?address=${address}`);
            if (!res.ok) {
                let detail = '';
                try { detail = (await res.json()).error || ''; } catch (e) { /* non-JSON error body */ }
                this._workerError = `worker returned HTTP ${res.status}${detail ? ': ' + detail : ''}`;
                return null;
            }
            const data = await res.json();
            return {
                ethBalance: data.ethBalance,
                tokens: (data.tokens || []).map(t => ({ symbol: t.symbol, name: t.name, address: t.contractAddress, decimals: t.decimals, balance: t.balance })),
            };
        } catch (e) {
            this._workerError = `worker request failed: ${(e && e.message) || e}`;
            return null;
        }
    },

    async _discoverViaRpc(address) {
        if (!this._tokenList) {
            this._tokenList = (await (await fetch('assets/base-tokens.json')).json()).tokens;
        }
        const [ethBalance, ...bals] = await Promise.all([
            this._ethBalance(address),
            ...this._tokenList.map(t => this._tokenBalance(t.address, address, t.decimals)),
        ]);
        return { ethBalance, tokens: this._tokenList.map((t, i) => ({ ...t, balance: bals[i] })) };
    },

    async loadHoldings(address) {
        const viaWorker = await this._discoverViaWorker(address);
        this._viaWorker = !!viaWorker;
        const { ethBalance, tokens } = viaWorker || await this._discoverViaRpc(address);

        // Manually-added tokens are one-off user entries that might not be in
        // Alchemy's index yet (or the curated list) — always balance-check
        // them directly, skipping any that the discovery pass already found.
        const known = new Set(tokens.map(t => t.address.toLowerCase()));
        const manualToCheck = this._manual.filter(m => !known.has(m.address.toLowerCase()));
        const manualBals = await Promise.all(manualToCheck.map(m => this._tokenBalance(m.address, address, m.decimals)));
        const allTokens = [...tokens, ...manualToCheck.map((m, i) => ({ ...m, balance: manualBals[i] }))];

        const priced = await this._prices(allTokens.map(t => t.address.toLowerCase()));
        const ethPrice = (window.App && App._ethPrice) || 0;

        const holdings = [{
            symbol: 'ETH', name: 'Ether', address: null,
            balance: ethBalance, priceUsd: ethPrice, valueUsd: ethBalance * ethPrice,
        }];
        allTokens.forEach(t => {
            const p = priced[t.address.toLowerCase()] || {};
            // WETH has no independent market — CoinGecko's contract lookup can
            // miss it; it's worth exactly ETH, so fall back to the ETH price.
            const priceUsd = p.usd || (t.symbol === 'WETH' ? ethPrice : 0);
            holdings.push({ symbol: t.symbol, name: t.name, address: t.address, balance: t.balance, priceUsd, valueUsd: t.balance * priceUsd, change24h: p.usd_24h_change });
        });
        return holdings.sort((a, b) => b.valueUsd - a.valueUsd);
    },

    // NFT holdings — worker-only (no keyless fallback; see plan notes on why
    // NFTs were out of scope before Alchemy). Returns [] if unavailable.
    async loadNfts(address) {
        if (!window.WORKER_BASE) return [];
        try {
            const res = await fetch(`${window.WORKER_BASE}/nfts?address=${address}`);
            if (!res.ok) return [];
            const data = await res.json();
            return data.nfts || [];
        } catch (e) { return []; }
    },

    // Real 24h P&L — sums valueUsd * (change24h/100) across whatever holdings
    // CoinGecko actually returned a 24hr-change figure for. This is separate
    // from the "since acquired" cost-basis estimate below (_runCostBasis),
    // which needs a CoinGecko Demo API key (worker/src/lib/costBasis.ts) and
    // is a rougher single-acquisition-point approximation, not full
    // accounting — the two numbers answer different questions and both are
    // labeled honestly rather than blended into one figure.
    _computePnl24h(holdings) {
        const priced = holdings.filter(h => h.valueUsd > 0 && typeof h.change24h === 'number');
        if (!priced.length) return null;
        const deltaUsd = priced.reduce((s, h) => s + h.valueUsd * (h.change24h / 100), 0);
        const baseValue = priced.reduce((s, h) => s + h.valueUsd / (1 + h.change24h / 100), 0);
        const deltaPct = baseValue > 0 ? (deltaUsd / baseValue) * 100 : 0;
        return { deltaUsd, deltaPct, coverage: priced.length, total: holdings.filter(h => h.valueUsd > 0).length };
    },

    async render(address) {
        const root = document.getElementById('profile-root');
        root.innerHTML = `<div class="text-center py-8 text-zinc-500 text-sm"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Reading your portfolio from Base…</div>`;
        let holdings, nfts;
        try {
            [holdings, nfts] = await Promise.all([this.loadHoldings(address), this.loadNfts(address)]);
        } catch (e) {
            root.innerHTML = `<div class="text-amber-400 text-sm">Couldn't read holdings right now (RPC/price feed hiccup). Try again in a moment.</div>`;
            return;
        }
        const total = holdings.reduce((s, h) => s + h.valueUsd, 0);
        const nonzero = holdings.filter(h => h.balance > 0);
        const pnl = this._computePnl24h(holdings);
        const cases = (window.CaseHistory ? CaseHistory.forWallet(address) : []);
        const coverageNote = this._viaWorker
            ? 'native ETH plus every token detected in this wallet'
            : 'native ETH plus a curated set of well-known Base tokens';

        root.innerHTML = `
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <div class="panel-sm">
                    <div class="text-zinc-400 text-xs uppercase tracking-wider">Total tracked value</div>
                    <div class="stat text-3xl text-zinc-100 mt-1">${fmtUsd(total)}</div>
                    <div class="text-[11px] text-zinc-600 mt-2">${nonzero.length} of ${holdings.length} tracked assets held</div>
                </div>
                <div class="panel-sm">
                    <div class="text-zinc-400 text-xs uppercase tracking-wider">24h profit / loss</div>
                    ${pnl ? `
                        <div class="stat text-3xl mt-1 ${pnl.deltaUsd >= 0 ? 'text-emerald-400' : 'text-rose-400'}">${pnl.deltaUsd >= 0 ? '+' : ''}${fmtUsd(pnl.deltaUsd)}</div>
                        <div class="text-[11px] text-zinc-600 mt-2">${pct(pnl.deltaPct)} · based on ${pnl.coverage} of ${pnl.total} priced assets</div>
                    ` : `
                        <div class="stat text-3xl mt-1 text-zinc-600">…</div>
                        <div class="text-[11px] text-zinc-600 mt-2">No priced holdings with 24h data yet</div>
                    `}
                </div>
                <div class="panel-sm">
                    <div class="text-zinc-400 text-xs uppercase tracking-wider">Engagement history</div>
                    <div class="stat text-3xl text-zinc-100 mt-1">${cases.length}</div>
                    <div class="text-[11px] text-zinc-600 mt-2">offerings hired by this wallet, saved on this device</div>
                </div>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
                <div class="lg:col-span-7 panel-sm">
                    <div class="flex items-center justify-between mb-2">
                        <div class="text-zinc-400 text-xs uppercase tracking-wider">Composition</div>
                        <div class="text-[10px] text-zinc-600">${coverageNote}</div>
                    </div>
                    <div style="position:relative; height:200px;">
                        <canvas id="profileDonut"></canvas>
                    </div>
                </div>
                <div class="lg:col-span-5 panel-sm">
                    <div class="text-zinc-400 text-xs uppercase tracking-wider mb-2">Add any Base token</div>
                    <div class="flex gap-2">
                        <input id="profile-add-input" type="text" placeholder="0x… token contract" class="flex-1 min-w-0 bg-transparent border border-white/10 focus:border-white/30 outline-none px-3 py-2 text-xs">
                        <button id="profile-add-btn" class="term-btn term-btn-sm shrink-0"><i class="fa-solid fa-plus"></i></button>
                    </div>
                    <div id="profile-add-status" class="text-[11px] text-zinc-600 mt-2"></div>
                </div>
            </div>
            <div class="panel-sm mb-6">
                <div class="text-zinc-400 text-xs uppercase tracking-wider mb-3">Top holdings by value</div>
                <div style="position:relative; height:220px;">
                    <canvas id="profileBar"></canvas>
                </div>
            </div>
            <div class="flex items-center justify-between mb-3">
                <div class="text-zinc-400 text-xs uppercase tracking-wider">All tracked assets (${holdings.length})</div>
            </div>
            <div id="profile-holdings" class="diff-list mb-6"></div>
            <div class="panel-sm mb-6">
                <div class="flex items-center justify-between mb-2">
                    <div class="text-zinc-400 text-xs uppercase tracking-wider">Cost basis estimate <span class="text-zinc-600 normal-case">(beta)</span></div>
                    <button id="profile-costbasis-btn" class="term-btn term-btn-sm shrink-0">Run estimate</button>
                </div>
                <p class="text-[11px] text-zinc-600 mb-3">Prices each token at its <em>first</em> recorded incoming transfer to this wallet: an approximation, not a full weighted-average cost basis across every acquisition.</p>
                <div id="profile-costbasis"></div>
            </div>
            <div class="mb-6">
                <div class="text-zinc-400 text-xs uppercase tracking-wider mb-3">Engagement history</div>
                <div id="profile-cases"></div>
            </div>
            <div>
                <div class="text-zinc-400 text-xs uppercase tracking-wider mb-3">NFTs on Base</div>
                <div id="profile-nfts"></div>
            </div>`;

        this._renderHoldingsTable(holdings);
        this._renderDonut(nonzero.length ? nonzero : holdings.slice(0, 1));
        this._renderBar(nonzero);
        this._renderCases(cases);
        this._renderNfts(nfts);

        document.getElementById('profile-add-btn').onclick = () => this._addManual(address);
        document.getElementById('profile-add-input').addEventListener('keypress', e => { if (e.key === 'Enter') this._addManual(address); });
        document.getElementById('profile-costbasis-btn').onclick = () => this._runCostBasis(address);
    },

    async _runCostBasis(address) {
        const btn = document.getElementById('profile-costbasis-btn');
        const el = document.getElementById('profile-costbasis');
        btn.disabled = true;
        btn.classList.add('opacity-50');
        el.innerHTML = '<div class="text-zinc-500 text-sm"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Estimating (this can take a few seconds, one lookup per top holding)…</div>';
        const { results, error } = await this.loadCostBasis(address);
        btn.disabled = false;
        btn.classList.remove('opacity-50');
        if (error === 'not-configured') {
            el.innerHTML = '<div class="text-zinc-500 text-sm">Cost-basis analysis isn\'t available right now.</div>';
            return;
        }
        if (error || !results) {
            el.innerHTML = '<div class="text-amber-400 text-sm">Estimate failed. Try again in a moment.</div>';
            return;
        }
        if (!results.length) {
            el.innerHTML = '<div class="text-zinc-500 text-sm">No priced holdings to estimate.</div>';
            return;
        }
        el.innerHTML = results.map(r => {
            const hasPnl = typeof r.pnlUsd === 'number';
            const acquired = r.acquiredAt ? new Date(r.acquiredAt).toLocaleDateString() : '…';
            return `
            <div class="card-h diff-row flex items-center gap-3">
                <div class="min-w-0 flex-1">
                    <div class="truncate">${escapeHtml(r.symbol)}</div>
                    <div class="text-[11px] text-zinc-600 truncate">${r.note ? escapeHtml(r.note) : `first acquired ${acquired}`}</div>
                </div>
                <div class="text-right shrink-0">
                    <div class="stat text-sm ${hasPnl ? (r.pnlUsd >= 0 ? 'text-emerald-400' : 'text-rose-400') : 'text-zinc-600'}">${hasPnl ? `${r.pnlUsd >= 0 ? '+' : ''}${fmtUsd(r.pnlUsd)}` : '…'}</div>
                    <div class="text-xs text-zinc-500">${typeof r.pnlPct === 'number' ? pct(r.pnlPct) : ''}</div>
                </div>
            </div>`;
        }).join('');
    },

    _renderHoldingsTable(holdings) {
        const el = document.getElementById('profile-holdings');
        if (!el) return;
        el.innerHTML = holdings.map(h => {
            const icon = (h.address && window.App) ? App._iconImg(h.address, '8453', 28) : `<div class="w-7 h-7 border border-white/10 flex items-center justify-center text-[10px] shrink-0">${(h.symbol||'?').slice(0,2)}</div>`;
            const explorer = (h.address && window.App) ? App._explorerUrl(h.address, '8453') : null;
            const nameBlock = `
                <div class="min-w-0 flex-1">
                    <div class="truncate">${escapeHtml(h.symbol)}</div>
                    <div class="text-xs text-zinc-500 truncate">${escapeHtml(h.name || '')}</div>
                </div>`;
            return `
            <div class="card-h diff-row flex items-center gap-3">
                ${explorer
                    ? `<a href="${explorer}" target="_blank" rel="noopener" class="flex items-center gap-3 min-w-0 flex-1 hover:opacity-80">${icon}${nameBlock}</a>`
                    : `<div class="flex items-center gap-3 min-w-0 flex-1">${icon}${nameBlock}</div>`}
                <div class="text-right shrink-0">
                    <div class="stat text-sm">${h.balance < 0.0001 && h.balance > 0 ? '<0.0001' : h.balance.toLocaleString(undefined,{maximumFractionDigits:4})}</div>
                    <div class="text-xs text-zinc-500">${h.valueUsd ? fmtUsd(h.valueUsd) : '…'} ${typeof h.change24h==='number' ? pct(h.change24h) : ''}</div>
                </div>
            </div>`;
        }).join('');
    },

    _renderDonut(holdings) {
        const ctx = document.getElementById('profileDonut');
        if (!ctx || typeof Chart === 'undefined') return;
        if (this._chart) this._chart.destroy();
        const colors = ['#4ade80', '#a1a1aa', '#818cf8', '#fb7185', '#fbbf24', '#a78bfa', '#f472b6', '#60a5fa', '#34d399', '#71717a'];
        const OTHER_COLOR = '#52525b';
        const sorted = holdings.filter(h => h.valueUsd > 0).sort((a, b) => b.valueUsd - a.valueUsd);
        if (!sorted.length) { ctx.parentElement.innerHTML = '<div class="text-zinc-500 text-sm">No priced holdings to chart yet.</div>'; return; }
        // Beyond the color palette's distinct slots, individual slices stop
        // being visually readable anyway — fold the long tail into one
        // "Other" slice rather than silently dropping tokens from the chart.
        const maxSlices = colors.length;
        const data = sorted.length > maxSlices ? sorted.slice(0, maxSlices - 1) : sorted;
        const rest = sorted.length > maxSlices ? sorted.slice(maxSlices - 1) : [];
        const labels = data.map(h => h.symbol);
        const values = data.map(h => h.valueUsd);
        const palette = colors.slice(0, data.length);
        if (rest.length) {
            labels.push(`Other (${rest.length})`);
            values.push(rest.reduce((s, h) => s + h.valueUsd, 0));
            palette.push(OTHER_COLOR);
        }
        this._chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data: values, backgroundColor: palette, borderColor: '#09090b', borderWidth: 2 }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#a1a1aa', boxWidth: 10, font: { size: 10 } } },
                    tooltip: { callbacks: { label: c => `${c.label}: ${fmtUsd(c.parsed)}` } },
                },
            },
        });
    },

    _renderBar(holdings) {
        const ctx = document.getElementById('profileBar');
        if (!ctx || typeof Chart === 'undefined') return;
        if (this._barChart) this._barChart.destroy();
        const data = holdings.filter(h => h.valueUsd > 0).sort((a, b) => b.valueUsd - a.valueUsd).slice(0, 8);
        if (!data.length) { ctx.parentElement.innerHTML = '<div class="text-zinc-500 text-sm">No priced holdings to chart yet.</div>'; return; }
        this._barChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(h => h.symbol),
                datasets: [{ data: data.map(h => h.valueUsd), backgroundColor: '#4ade80', borderRadius: 4 }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => fmtUsd(c.parsed.x) } } },
                scales: {
                    x: { ticks: { color: '#a1a1aa', callback: v => fmtUsd(v) }, grid: { color: 'rgba(255,255,255,0.06)' } },
                    y: { ticks: { color: '#a1a1aa' }, grid: { display: false } },
                },
            },
        });
    },

    _relativeTime(ts) {
        const diffSec = Math.max(0, Math.round((Date.now() - ts) / 1000));
        if (diffSec < 60) return 'just now';
        const mins = Math.round(diffSec / 60);
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.round(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.round(hrs / 24);
        return `${days}d ago`;
    },

    // Case history is x402 hires only (docs/assets/hire.js saves to
    // CaseHistory on success) — ACP jobs are created and fulfilled entirely
    // off-site via Virtuals' own platform, so there's no client-side result
    // to persist here.
    _renderCases(cases) {
        const el = document.getElementById('profile-cases');
        if (!el) return;
        if (!cases.length) {
            el.innerHTML = '<div class="text-zinc-500 text-sm">No engagements yet from this wallet on this device. Authorize an x402 service above in "Engagement Options" and it\'ll show up here.</div>';
            return;
        }
        el.innerHTML = cases.slice(0, 50).map((c, i) => {
            const explorer = (c.targetAddress && window.App) ? App._explorerUrl(c.targetAddress, '8453') : null;
            let reportHtml = '';
            try {
                reportHtml = window.Report ? Report.buildHtmlSummary({ offering: c.offering, priceUsd: c.priceUsd, requestedAddress: c.targetAddress, hiredBy: c.walletAddress, result: c.result, via: c.via || 'x402' }) : '';
            } catch (e) { /* fall back to just the header row + JSON copy button */ }
            // Real token logo for the card avatar when the engagement targeted
            // a specific contract — same DexScreener CDN used everywhere else
            // on the site — falling back to the generic bolt glyph otherwise
            // (e.g. market_intel has no single target address).
            const cardIcon = c.targetAddress ? tokenIconByAddress(c.targetAddress, c.result?.deliverable?.chain_id) : null;
            return `
            <div class="card-h diff-row">
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 border border-white/10 flex items-center justify-center shrink-0 relative overflow-hidden">
                        <i class="fa-solid fa-bolt text-zinc-400 text-sm"></i>
                        ${cardIcon ? `<img src="${escapeHtml(cardIcon)}" alt="" class="absolute inset-0 w-full h-full object-cover" onerror="this.remove()">` : ''}
                    </div>
                    <div class="min-w-0 flex-1">
                        <div class="truncate">${escapeHtml((c.offering || '').replace(/_/g, ' '))} <span class="text-zinc-500 font-normal">· $${c.priceUsd}</span></div>
                        <div class="text-xs text-zinc-500 truncate">
                            ${c.verdict ? `<span class="text-zinc-300">${escapeHtml(String(c.verdict))}</span> · ` : ''}
                            ${c.targetAddress ? (explorer ? `<a href="${explorer}" target="_blank" rel="noopener" class="hover:text-zinc-200">${escapeHtml(App._shortAddr(c.targetAddress))}</a> · ` : `${escapeHtml(App._shortAddr ? App._shortAddr(c.targetAddress) : c.targetAddress)} · `) : ''}
                            ${this._relativeTime(c.timestamp)}
                        </div>
                    </div>
                    <div class="flex gap-2 shrink-0">
                        <button data-case-idx="${i}" class="case-pdf-btn term-btn term-btn-sm" title="Download PDF"><i class="fa-solid fa-file-pdf"></i></button>
                        <button data-case-idx="${i}" class="case-copy-btn term-btn term-btn-sm" title="Copy JSON"><i class="fa-solid fa-copy"></i></button>
                    </div>
                </div>
                ${reportHtml ? `
                <details class="mt-3" ${i === 0 ? 'open' : ''}>
                    <summary class="text-xs text-zinc-400 cursor-pointer select-none">View full report</summary>
                    <div class="mt-3 pt-3 border-t border-white/10">${reportHtml}</div>
                </details>` : ''}
            </div>`;
        }).join('');
        if (window.Report) Report.enhanceIcons(el);
        el.querySelectorAll('.case-pdf-btn').forEach(btn => btn.onclick = async () => {
            const c = cases[Number(btn.dataset.caseIdx)];
            await Report.downloadPdf({ offering: c.offering, priceUsd: c.priceUsd, requestedAddress: c.targetAddress, hiredBy: c.walletAddress, result: c.result, via: c.via || 'x402' });
        });
        el.querySelectorAll('.case-copy-btn').forEach(btn => btn.onclick = async () => {
            const c = cases[Number(btn.dataset.caseIdx)];
            await navigator.clipboard.writeText(JSON.stringify(c.result, null, 2));
        });
    },

    _renderNfts(nfts) {
        const el = document.getElementById('profile-nfts');
        if (!el) return;
        if (!window.WORKER_BASE) {
            el.innerHTML = '<div class="text-zinc-500 text-sm">NFT holdings aren\'t available right now.</div>';
            return;
        }
        if (!nfts.length) {
            el.innerHTML = '<div class="text-zinc-500 text-sm">No NFTs found on Base for this wallet.</div>';
            return;
        }
        el.innerHTML = `<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">${nfts.slice(0, 24).map(n => `
            <div class="card-h border border-white/10 overflow-hidden">
                <div class="aspect-square bg-zinc-900/80 flex items-center justify-center">
                    ${n.image
                        ? `<img src="${escapeHtml(n.image)}" alt="${escapeHtml(n.name)}" class="w-full h-full object-cover" loading="lazy" onerror="this.remove()">`
                        : '<i class="fa-solid fa-image text-zinc-600 text-xl"></i>'}
                </div>
                <div class="px-3 py-2">
                    <div class="text-xs truncate">${escapeHtml(n.name)}</div>
                    <div class="text-[10px] text-zinc-500 truncate">${escapeHtml(n.collectionName || '')}</div>
                </div>
            </div>`).join('')}</div>`;
    },

    async _addManual(walletAddress) {
        const input = document.getElementById('profile-add-input');
        const status = document.getElementById('profile-add-status');
        const addr = (input.value || '').trim();
        if (!/^0x[a-fA-F0-9]{40}$/.test(addr)) { status.textContent = 'Enter a valid 0x… contract address.'; status.className = 'text-[11px] text-amber-400 mt-2'; return; }
        status.textContent = 'Checking…';
        status.className = 'text-[11px] text-zinc-500 mt-2';
        try {
            // Assume 18 decimals unless the contract tells us otherwise (decimals() selector 0x313ce567)
            let decimals = 18;
            try {
                const dHex = await this._rpc('eth_call', [{ to: addr, data: '0x313ce567' }, 'latest']);
                if (dHex && dHex !== '0x') decimals = parseInt(dHex, 16);
            } catch (e) { /* fall back to 18 */ }
            this._manual.push({ symbol: addr.slice(0, 6) + '…', name: 'Manually added', address: addr, decimals });
            input.value = '';
            status.textContent = 'Added. Refreshing holdings…';
            await this.render(walletAddress);
        } catch (e) {
            status.textContent = 'Could not read that contract. Is it an ERC-20 on Base?';
            status.className = 'text-[11px] text-amber-400 mt-2';
        }
    },

    reset() {
        document.getElementById('profile-root').innerHTML = `
            <div class="text-center py-10 text-zinc-500 text-sm">
                <i class="fa-solid fa-wallet text-2xl mb-3 opacity-50"></i>
                <div>Connect a wallet above to access your portfolio.</div>
            </div>`;
    },
};

window.addEventListener('DOMContentLoaded', () => {
    const tryInit = () => {
        if (!window.Wallet) { setTimeout(tryInit, 50); return; }
        Wallet.onChange(state => {
            if (state.connected) Profile.render(state.account);
            else Profile.reset();
        });
    };
    tryInit();
});
