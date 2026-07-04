// VAPE wallet profile ("Your Case File"). Two data paths:
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
// address lookup, entirely client-side (no secret involved).
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
        try {
            const url = `https://api.coingecko.com/api/v3/simple/token_price/base?contract_addresses=${addresses.join(',')}&vs_currencies=usd&include_24hr_change=true`;
            return await (await fetch(url)).json();
        } catch (e) { return {}; }
    },

    // Full auto-discovered ETH + ERC-20 balances via the vape-x402 worker's
    // Alchemy-backed /portfolio route. Returns null (not throws) on any
    // failure — every caller falls back to the direct-RPC + curated-list path.
    async _discoverViaWorker(address) {
        if (!window.WORKER_BASE) return null;
        try {
            const res = await fetch(`${window.WORKER_BASE}/portfolio?address=${address}`);
            if (!res.ok) return null;
            const data = await res.json();
            return {
                ethBalance: data.ethBalance,
                tokens: (data.tokens || []).map(t => ({ symbol: t.symbol, name: t.name, address: t.contractAddress, decimals: t.decimals, balance: t.balance })),
            };
        } catch (e) { return null; }
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

    async render(address) {
        const root = document.getElementById('profile-root');
        root.innerHTML = `<div class="text-center py-8 text-zinc-500 text-sm"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Reading your case file from Base…</div>`;
        let holdings, nfts;
        try {
            [holdings, nfts] = await Promise.all([this.loadHoldings(address), this.loadNfts(address)]);
        } catch (e) {
            root.innerHTML = `<div class="text-amber-400 text-sm">Couldn't read holdings right now (RPC/price feed hiccup) — try again in a moment.</div>`;
            return;
        }
        const total = holdings.reduce((s, h) => s + h.valueUsd, 0);
        const nonzero = holdings.filter(h => h.balance > 0);
        const coverageNote = this._viaWorker
            ? 'native ETH + every ERC-20 Alchemy has indexed for this wallet'
            : 'native ETH + curated Base tokens (deploy the VAPE worker for full auto-discovery)';

        root.innerHTML = `
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
                <div class="lg:col-span-4 glass rounded-2xl p-5 flex flex-col justify-center">
                    <div class="text-zinc-400 text-xs uppercase tracking-wider">Total tracked value</div>
                    <div class="stat font-display text-3xl text-cyan-400 mt-1">${fmtUsd(total)}</div>
                    <div class="text-[11px] text-zinc-600 mt-2">${nonzero.length} of ${holdings.length} tracked assets held · ${coverageNote}</div>
                </div>
                <div class="lg:col-span-4 glass rounded-2xl p-5">
                    <div style="position:relative; height:180px;">
                        <canvas id="profileDonut"></canvas>
                    </div>
                </div>
                <div class="lg:col-span-4 glass rounded-2xl p-5">
                    <div class="text-zinc-400 text-xs uppercase tracking-wider mb-2">Add any Base token</div>
                    <div class="flex gap-2">
                        <input id="profile-add-input" type="text" placeholder="0x… token contract" class="flex-1 min-w-0 bg-zinc-900/80 border border-white/10 focus:border-cyan-500 outline-none px-3 py-2 rounded-lg text-xs font-mono">
                        <button id="profile-add-btn" class="bg-cyan-600 hover:bg-cyan-500 px-3 py-2 rounded-lg text-xs shrink-0"><i class="fa-solid fa-plus"></i></button>
                    </div>
                    <div id="profile-add-status" class="text-[11px] text-zinc-600 mt-2"></div>
                </div>
            </div>
            <div class="glass rounded-2xl p-5 mb-6">
                <div class="text-zinc-400 text-xs uppercase tracking-wider mb-3">Top holdings by value</div>
                <div style="position:relative; height:220px;">
                    <canvas id="profileBar"></canvas>
                </div>
            </div>
            <div id="profile-holdings" class="space-y-2 mb-6"></div>
            <div>
                <div class="text-zinc-400 text-xs uppercase tracking-wider mb-3">NFTs on Base</div>
                <div id="profile-nfts"></div>
            </div>`;

        this._renderHoldingsTable(holdings);
        this._renderDonut(nonzero.length ? nonzero : holdings.slice(0, 1));
        this._renderBar(nonzero);
        this._renderNfts(nfts);

        document.getElementById('profile-add-btn').onclick = () => this._addManual(address);
        document.getElementById('profile-add-input').addEventListener('keypress', e => { if (e.key === 'Enter') this._addManual(address); });
    },

    _renderHoldingsTable(holdings) {
        const el = document.getElementById('profile-holdings');
        if (!el) return;
        el.innerHTML = holdings.map(h => {
            const icon = (h.address && window.App) ? App._iconImg(h.address, '8453', 28) : `<div class="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center text-[10px] font-display shrink-0">${(h.symbol||'?').slice(0,2)}</div>`;
            return `
            <div class="card-h glass rounded-xl px-4 py-3 flex items-center gap-3">
                ${icon}
                <div class="min-w-0 flex-1">
                    <div class="font-semibold truncate">${escapeHtml(h.symbol)}</div>
                    <div class="text-xs text-zinc-500 truncate">${escapeHtml(h.name || '')}</div>
                </div>
                <div class="text-right shrink-0">
                    <div class="stat font-display text-sm">${h.balance < 0.0001 && h.balance > 0 ? '<0.0001' : h.balance.toLocaleString(undefined,{maximumFractionDigits:4})}</div>
                    <div class="text-xs text-zinc-500">${h.valueUsd ? fmtUsd(h.valueUsd) : '—'} ${typeof h.change24h==='number' ? pct(h.change24h) : ''}</div>
                </div>
            </div>`;
        }).join('');
    },

    _renderDonut(holdings) {
        const ctx = document.getElementById('profileDonut');
        if (!ctx || typeof Chart === 'undefined') return;
        if (this._chart) this._chart.destroy();
        const colors = ['#22d3ee', '#10b981', '#c9a86a', '#818cf8', '#fb7185', '#fbbf24', '#a78bfa'];
        const data = holdings.filter(h => h.valueUsd > 0);
        if (!data.length) { ctx.parentElement.innerHTML = '<div class="text-zinc-500 text-sm">No priced holdings to chart yet.</div>'; return; }
        this._chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(h => h.symbol),
                datasets: [{ data: data.map(h => h.valueUsd), backgroundColor: colors, borderColor: '#09090b', borderWidth: 2 }],
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
                datasets: [{ data: data.map(h => h.valueUsd), backgroundColor: '#22d3ee', borderRadius: 4 }],
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

    _renderNfts(nfts) {
        const el = document.getElementById('profile-nfts');
        if (!el) return;
        if (!window.WORKER_BASE) {
            el.innerHTML = '<div class="text-zinc-500 text-sm">NFT holdings need the VAPE worker deployed (Alchemy-backed) — see worker/README.md.</div>';
            return;
        }
        if (!nfts.length) {
            el.innerHTML = '<div class="text-zinc-500 text-sm">No NFTs found on Base for this wallet.</div>';
            return;
        }
        el.innerHTML = `<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">${nfts.slice(0, 24).map(n => `
            <div class="card-h glass rounded-xl overflow-hidden">
                <div class="aspect-square bg-zinc-900/80 flex items-center justify-center">
                    ${n.image
                        ? `<img src="${escapeHtml(n.image)}" alt="${escapeHtml(n.name)}" class="w-full h-full object-cover" loading="lazy" onerror="this.remove()">`
                        : '<i class="fa-solid fa-image text-zinc-600 text-xl"></i>'}
                </div>
                <div class="px-3 py-2">
                    <div class="text-xs font-semibold truncate">${escapeHtml(n.name)}</div>
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
            status.textContent = 'Added — refreshing holdings…';
            await this.render(walletAddress);
        } catch (e) {
            status.textContent = 'Could not read that contract — is it an ERC-20 on Base?';
            status.className = 'text-[11px] text-amber-400 mt-2';
        }
    },

    reset() {
        document.getElementById('profile-root').innerHTML = `
            <div class="text-center py-10 text-zinc-500 text-sm">
                <i class="fa-solid fa-wallet text-2xl mb-3 opacity-50"></i>
                <div>Connect a wallet above to open your case file.</div>
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
