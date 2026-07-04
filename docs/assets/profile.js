// VAPE wallet profile ("Your Case File") — keyless: native ETH + a curated,
// verified Base token list (docs/assets/base-tokens.json), read live via
// public RPC (mainnet.base.org) + CoinGecko contract-address pricing.
// No indexer, no NFTs, no historical PnL — see docs/assets/base-tokens.json
// for why the token list is small and verified rather than "everything".
const RPC_URL = 'https://mainnet.base.org';

const Profile = {
    _tokenList: null,
    _chart: null,
    _manual: [], // user-added {symbol,address,decimals}

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

    async loadHoldings(address) {
        if (!this._tokenList) {
            this._tokenList = (await (await fetch('assets/base-tokens.json')).json()).tokens;
        }
        const list = [...this._tokenList, ...this._manual];
        const [ethBal, ...tokenBals] = await Promise.all([
            this._ethBalance(address),
            ...list.map(t => this._tokenBalance(t.address, address, t.decimals)),
        ]);
        const priced = await this._prices(list.map(t => t.address.toLowerCase()));
        const ethPrice = (window.App && App._ethPrice) || 0;

        const holdings = [{
            symbol: 'ETH', name: 'Ether', address: null,
            balance: ethBal, priceUsd: ethPrice, valueUsd: ethBal * ethPrice,
        }];
        list.forEach((t, i) => {
            const bal = tokenBals[i];
            const p = priced[t.address.toLowerCase()] || {};
            // WETH has no independent market — CoinGecko's contract lookup can
            // miss it; it's worth exactly ETH, so fall back to the ETH price.
            const priceUsd = p.usd || (t.symbol === 'WETH' ? ethPrice : 0);
            holdings.push({ symbol: t.symbol, name: t.name, address: t.address, balance: bal, priceUsd, valueUsd: bal * priceUsd, change24h: p.usd_24h_change });
        });
        return holdings.sort((a, b) => b.valueUsd - a.valueUsd);
    },

    async render(address) {
        const root = document.getElementById('profile-root');
        root.innerHTML = `<div class="text-center py-8 text-zinc-500 text-sm"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Reading your case file from Base…</div>`;
        let holdings;
        try {
            holdings = await this.loadHoldings(address);
        } catch (e) {
            root.innerHTML = `<div class="text-amber-400 text-sm">Couldn't read holdings right now (RPC/price feed hiccup) — try again in a moment.</div>`;
            return;
        }
        const total = holdings.reduce((s, h) => s + h.valueUsd, 0);
        const nonzero = holdings.filter(h => h.balance > 0);

        root.innerHTML = `
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
                <div class="lg:col-span-4 glass rounded-2xl p-5 flex flex-col justify-center">
                    <div class="text-zinc-400 text-xs uppercase tracking-wider">Total tracked value</div>
                    <div class="stat font-display text-3xl text-cyan-400 mt-1">${fmtUsd(total)}</div>
                    <div class="text-[11px] text-zinc-600 mt-2">${nonzero.length} of ${holdings.length} tracked assets held · native ETH + curated Base tokens</div>
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
            <div id="profile-holdings" class="space-y-2"></div>`;

        this._renderHoldingsTable(holdings);
        this._renderDonut(nonzero.length ? nonzero : holdings.slice(0, 1));

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
                    <div class="font-semibold truncate">${h.symbol}</div>
                    <div class="text-xs text-zinc-500 truncate">${h.name || ''}</div>
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
