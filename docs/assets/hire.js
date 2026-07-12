// VAPE hire flow — x402 (real, in-browser, instant) and ACP (links out to the
// real Virtuals job flow, since ACP job creation needs Privy + Alchemy
// Account Kit smart accounts that this zero-bundler site doesn't run).
const ACP_AGENT_URL = 'https://app.virtuals.io/acp/agent/019eaf60-592a-7f5c-99a2-3e85199303fe';
const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

// offeringName arrives here via an inline onclick="Hire.openX402('${o.name}', ...)"
// string built in app.js, and exception messages can echo back arbitrary text
// (e.g. from a fetch error) — both get written into innerHTML below, so escape
// them at the sink, same pattern already used in report.js.
function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// VAPE's market-data tools (worker /data/<name>, worker/src/dataHandlers.ts).
// Different route prefix, varied inputs, and a rich-data (not verdict) result.
// Each spec's `inputs` drives the modal fields; empty = a zero-input call.
const DATA_OFFERINGS = {
    token_intel:     { inputs: [{ k: 'address', label: 'Token contract address', ph: '0x… token', addr: true },
                                    { k: 'chain', label: 'Chain slug', ph: 'base', def: 'base' },
                                    { k: 'slug', label: 'Protocol slug (optional — adds fees/unlocks/treasury)', ph: 'aave', opt: true }] },
    token_chart:     { inputs: [{ k: 'address', label: 'Token contract address', ph: '0x… token', addr: true },
                                    { k: 'chain', label: 'Chain slug', ph: 'base', def: 'base' },
                                    { k: 'span', label: 'Days of history', ph: '30', def: '30' }] },
    protocol:        { inputs: [{ k: 'slug', label: 'Protocol slug', ph: 'aerodrome' }] },
    protocol_fees:   { inputs: [{ k: 'slug', label: 'Protocol slug', ph: 'aave' }] },
    unlocks:         { inputs: [{ k: 'slug', label: 'Protocol slug', ph: 'aptos' }] },
    treasury:        { inputs: [{ k: 'slug', label: 'Protocol slug', ph: 'uniswap' }] },
    chain_protocols: { inputs: [{ k: 'chain', label: 'Chain name', ph: 'Base', def: 'Base' }] },
    chain_overview:  { inputs: [{ k: 'chain', label: 'Chain name', ph: 'Base', def: 'Base' }] },
    chain_fees:      { inputs: [{ k: 'chain', label: 'Chain slug', ph: 'base', def: 'base' }] },
    dex_volumes:     { inputs: [{ k: 'chain', label: 'Chain slug', ph: 'base', def: 'base' }] },
    derivatives:     { inputs: [] },
    yields:          { inputs: [{ k: 'chain', label: 'Chain (optional)', ph: 'Base', opt: true },
                                    { k: 'project', label: 'Project (optional)', ph: 'aave-v3', opt: true },
                                    { k: 'symbol', label: 'Symbol (optional)', ph: 'USDC', opt: true }] },
    stablecoins:     { inputs: [] },
    bridges:         { inputs: [] },
};

const Hire = {
    _modal: null,

    openAcp(offeringName) {
        window.open(ACP_AGENT_URL, '_blank', 'noopener');
    },

    openX402(offeringName, priceUsd) {
        // Market-data tools take varied inputs and return rich data (not a
        // verdict), so they get their own modal/result path.
        if (DATA_OFFERINGS[offeringName]) return this.openData(offeringName, priceUsd);
        this._closeModal();
        const needsAddress = offeringName !== 'market_intel';
        const modal = document.createElement('div');
        modal.id = 'hire-modal';
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" data-close></div>
            <div class="relative glass rounded-2xl p-6 w-full max-w-md">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-display text-lg flex items-center gap-2"><i class="fa-solid fa-bolt text-cyan-400"></i> Commission VAPE</h3>
                    <button data-close class="text-zinc-500 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div id="hire-body">
                    <div class="text-sm text-zinc-400 mb-1">${escapeHtml(offeringName.replace(/_/g,' '))} <span class="text-cyan-400 font-mono">$${priceUsd}</span></div>
                    <p class="text-xs text-zinc-500 mb-4">Settles via x402: your wallet signs a gasless USDC authorization for the exact price above — no gas fee, no subscription, settles on Base mainnet.</p>
                    ${needsAddress ? `
                    <label class="text-xs text-zinc-500 block mb-1">Target contract address</label>
                    <input id="hire-address" type="text" placeholder="0x… token/contract to investigate" class="w-full bg-zinc-900/80 border border-white/10 focus:border-cyan-500 outline-none px-3 py-2 rounded-lg text-xs font-mono mb-4">
                    ` : '<div class="mb-4"></div>'}
                    <button id="hire-submit" class="w-full bg-cyan-600 hover:bg-cyan-500 transition px-4 py-2.5 rounded-xl font-display text-sm">Authorize &amp; Execute</button>
                    <div id="hire-status" class="text-xs text-zinc-500 mt-3"></div>
                </div>
            </div>`;
        document.body.appendChild(modal);
        this._modal = modal;
        modal.querySelectorAll('[data-close]').forEach(el => el.onclick = () => this._closeModal());
        modal.querySelector('#hire-submit').onclick = () => this._runX402(offeringName, priceUsd, needsAddress);
    },

    _closeModal() {
        if (this._modal) { this._modal.remove(); this._modal = null; }
    },

    async _runX402(offeringName, priceUsd, needsAddress) {
        const status = document.getElementById('hire-status');
        const submitBtn = document.getElementById('hire-submit');
        const set = (html, cls) => { status.innerHTML = html; status.className = `text-xs mt-3 ${cls || 'text-zinc-500'}`; };

        if (!window.Wallet || !Wallet.state().connected) { set('Connect a wallet first (top right), then try again.', 'text-amber-400'); return; }
        let address = '';
        if (needsAddress) {
            address = (document.getElementById('hire-address').value || '').trim();
            if (!ADDRESS_RE.test(address)) { set('Enter a valid 0x… contract address.', 'text-amber-400'); return; }
        }
        if (!window.WORKER_BASE) { set("VAPE's payment worker isn't configured yet.", 'text-amber-400'); return; }

        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50');
        set('<i class="fa-solid fa-spinner fa-spin"></i> Checking network…');
        const onBase = await Wallet.ensureBase();
        if (!onBase) { set('Switch your wallet to Base mainnet and try again.', 'text-amber-400'); submitBtn.disabled = false; submitBtn.classList.remove('opacity-50'); return; }

        try {
            set('<i class="fa-solid fa-spinner fa-spin"></i> Loading payment protocol…');
            const [{ wrapFetchWithPaymentFromConfig }, { ExactEvmScheme }, { createWalletClient, custom }] = await Promise.all([
                import('https://esm.sh/@x402/fetch@2.17.0'),
                import('https://esm.sh/@x402/evm@2.17.0'),
                import('https://esm.sh/viem@2'),
            ]);
            const account = Wallet.state().account;
            const provider = Wallet.getProvider();
            const walletClient = createWalletClient({ account, transport: custom(provider) });
            // ExactEvmScheme expects a plain {address, signTypedData} signer —
            // bridge viem's WalletClient (whose signTypedData needs an account
            // arg) into that shape.
            const signer = {
                address: account,
                signTypedData: (args) => walletClient.signTypedData({ account, ...args }),
            };
            const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
                schemes: [{ network: 'eip155:8453', client: new ExactEvmScheme(signer) }],
            });

            set('<i class="fa-solid fa-spinner fa-spin"></i> Requesting payment terms…');
            const url = needsAddress
                ? `${window.WORKER_BASE}/scan/${offeringName}?address=${address}`
                : `${window.WORKER_BASE}/scan/${offeringName}`;
            set('<i class="fa-solid fa-spinner fa-spin"></i> Sign the request in your wallet…');
            const res = await fetchWithPayment(url);
            const result = await res.json().catch(() => ({}));
            if (!res.ok) {
                // Payment may have already settled by the time a non-2xx comes back (e.g.
                // bounty_deep_dive's dispatch-configuration gap) — surface the worker's
                // actual error message rather than a bare status code, since that's the
                // buyer's only way to know their money went through even though the
                // deliverable didn't (see worker/src/index.ts's 503 case).
                throw new Error(result.error || `Worker returned ${res.status}`);
            }
            await this._renderResult(offeringName, priceUsd, address, result);
        } catch (e) {
            const msg = (e && e.message) || String(e);
            set(`Payment failed: ${escapeHtml(msg.slice(0, 200))}`, 'text-rose-400');
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50');
        }
    },

    async _renderResult(offeringName, priceUsd, address, result) {
        const body = document.getElementById('hire-body');
        if (!body) return;
        // bounty_deep_dive is async — payment gates a real GitHub Actions job
        // (worker/src/index.ts's /scan/bounty_deep_dive), not an inline result.
        // No deliverable exists yet, so this needs its own "queued" rendering
        // instead of the "Paid & delivered" success state below.
        if (result.status === 'accepted') {
            const walletAddress = (window.Wallet && Wallet.state().account) || null;
            try {
                if (window.CaseHistory && walletAddress) {
                    CaseHistory.save({ offering: offeringName, priceUsd, via: 'x402', walletAddress, targetAddress: address, verdict: 'QUEUED', result });
                }
            } catch (e) { /* non-fatal */ }
            body.innerHTML = `
                <div class="text-center mb-4">
                    <i class="fa-solid fa-clock text-cyan-400 text-3xl mb-2"></i>
                    <div class="font-display text-lg">Paid — audit queued</div>
                    <div class="text-xs text-zinc-500">${escapeHtml(offeringName.replace(/_/g,' '))} · $${priceUsd} settled on Base</div>
                </div>
                <div class="glass rounded-xl p-4 mb-4 text-sm text-zinc-300 leading-relaxed">${escapeHtml(result.message || 'Deep-dive audit queued — report lands within 24h.')}</div>
                <a href="${escapeHtml(result.track || 'https://github.com/jUXTAPOSITION1/V.A.P.E/tree/main/intel/audits/poc-reports')}" target="_blank" rel="noopener" class="w-full inline-flex items-center justify-center gap-2 bg-cyan-600 hover:bg-cyan-500 transition px-4 py-2.5 rounded-xl font-display text-sm"><i class="fa-solid fa-arrow-up-right-from-square"></i> Track the audit ledger</a>
                <div class="text-xs text-zinc-500 mt-3 text-center">Saved to your Engagement History in "Portfolio Intelligence" below — check back for the finished report.</div>`;
            return;
        }
        const deliverable = result.deliverable || {};
        const verdict = deliverable.verdict || deliverable.rug_risk || deliverable.combined || deliverable.token_verdict;
        const walletAddress = (window.Wallet && Wallet.state().account) || null;
        const reportOpts = { offering: offeringName, priceUsd, requestedAddress: address, hiredBy: walletAddress, result, via: 'x402' };

        // Render the actual report content first, synchronously, before any
        // risky async work (PDF generation needs a CDN script, saving to
        // localStorage) — those can fail independently in a restrictive
        // browser (e.g. Base Wallet's in-app webview) without ever hiding
        // the thing that was actually paid for.
        let inlineReport = '';
        try { inlineReport = Report.buildHtmlSummary(reportOpts); } catch (e) { /* fall through with empty inline report */ }
        body.innerHTML = `
            <div class="text-center mb-4">
                <i class="fa-solid fa-circle-check text-cyan-400 text-3xl mb-2"></i>
                <div class="font-display text-lg">Paid & delivered</div>
                <div class="text-xs text-zinc-500">${escapeHtml(offeringName.replace(/_/g,' '))} · $${priceUsd} settled on Base</div>
            </div>
            <div class="glass rounded-xl p-4 mb-4">${inlineReport || '<div class="text-xs text-amber-400">Could not render report preview — use Copy JSON below for the raw result.</div>'}</div>
            <div class="flex gap-2">
                <button id="hire-download" class="flex-1 bg-cyan-600 hover:bg-cyan-500 transition px-4 py-2.5 rounded-xl font-display text-sm"><i class="fa-solid fa-file-pdf"></i> Download PDF</button>
                <button id="hire-copy" class="flex-1 bg-white/10 hover:bg-white/15 transition px-4 py-2.5 rounded-xl font-display text-sm"><i class="fa-solid fa-copy"></i> Copy JSON</button>
            </div>
            <div id="hire-copy-status" class="text-xs text-zinc-500 mt-3 text-center">Saved to your Engagement History in "Portfolio Intelligence" below.</div>`;
        Report.enhanceIcons(body);
        document.getElementById('hire-download').onclick = () => Report.downloadPdf(reportOpts);
        document.getElementById('hire-copy').onclick = async () => {
            await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
            document.getElementById('hire-copy-status').textContent = 'Copied raw JSON to clipboard.';
        };

        // Everything below is best-effort — the report above is already
        // fully visible regardless of what happens here.
        try {
            if (window.CaseHistory && walletAddress) {
                CaseHistory.save({ offering: offeringName, priceUsd, via: 'x402', walletAddress, targetAddress: address, verdict, result });
            }
        } catch (e) { /* non-fatal — report is already shown above */ }
        try {
            await Report.downloadPdf(reportOpts);
        } catch (e) { /* PDF/download not available in this browser — inline report above still stands */ }
    },

    // ── VAPE market-data tools ($0.01 each) ───────────────────────────────────
    openData(offeringName, priceUsd) {
        this._closeModal();
        const spec = DATA_OFFERINGS[offeringName];
        const title = offeringName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const fields = spec.inputs.map(f => `
            <label class="text-xs text-zinc-500 block mb-1">${escapeHtml(f.label)}</label>
            <input data-key="${escapeHtml(f.k)}" type="text" placeholder="${escapeHtml(f.ph || '')}" value="${escapeHtml(f.def || '')}"
                   class="w-full bg-zinc-900/80 border border-white/10 focus:border-cyan-500 outline-none px-3 py-2 rounded-lg text-xs font-mono mb-3">`).join('');
        const modal = document.createElement('div');
        modal.id = 'hire-modal';
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" data-close></div>
            <div class="relative glass rounded-2xl p-6 w-full max-w-md">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-display text-lg flex items-center gap-2"><i class="fa-solid fa-bolt text-cyan-400"></i> ${escapeHtml(title)}</h3>
                    <button data-close class="text-zinc-500 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div id="hire-body">
                    <div class="text-sm text-zinc-400 mb-1"><span class="text-cyan-400 font-mono">$${priceUsd}</span></div>
                    <p class="text-xs text-zinc-500 mb-4">Settles via x402: your wallet signs a gasless USDC authorization for the exact price above — no gas fee, no subscription, settles on Base mainnet.</p>
                    ${fields || '<div class="mb-1"></div>'}
                    <button id="hire-submit" class="w-full bg-cyan-600 hover:bg-cyan-500 transition px-4 py-2.5 rounded-xl font-display text-sm mt-1">Authorize &amp; Fetch</button>
                    <div id="hire-status" class="text-xs text-zinc-500 mt-3"></div>
                </div>
            </div>`;
        document.body.appendChild(modal);
        this._modal = modal;
        modal.querySelectorAll('[data-close]').forEach(el => el.onclick = () => this._closeModal());
        modal.querySelector('#hire-submit').onclick = () => this._runData(offeringName, priceUsd, spec);
    },

    async _runData(offeringName, priceUsd, spec) {
        const status = document.getElementById('hire-status');
        const submitBtn = document.getElementById('hire-submit');
        const set = (html, cls) => { status.innerHTML = html; status.className = `text-xs mt-3 ${cls || 'text-zinc-500'}`; };

        if (!window.Wallet || !Wallet.state().connected) { set('Connect a wallet first (top right), then try again.', 'text-amber-400'); return; }
        if (!window.WORKER_BASE) { set("VAPE's payment worker isn't configured yet.", 'text-amber-400'); return; }

        // Collect + validate inputs from the modal.
        const params = {};
        for (const f of spec.inputs) {
            const el = document.querySelector(`#hire-body [data-key="${f.k}"]`);
            const v = (el && el.value || '').trim();
            if (!v) {
                if (f.opt) continue;
                set(`Enter ${escapeHtml(f.label.toLowerCase())}.`, 'text-amber-400');
                return;
            }
            if (f.addr && !ADDRESS_RE.test(v)) { set('Enter a valid 0x… address.', 'text-amber-400'); return; }
            params[f.k] = v;
        }

        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50');
        set('<i class="fa-solid fa-spinner fa-spin"></i> Checking network…');
        const onBase = await Wallet.ensureBase();
        if (!onBase) { set('Switch your wallet to Base mainnet and try again.', 'text-amber-400'); submitBtn.disabled = false; submitBtn.classList.remove('opacity-50'); return; }

        try {
            set('<i class="fa-solid fa-spinner fa-spin"></i> Loading payment protocol…');
            const [{ wrapFetchWithPaymentFromConfig }, { ExactEvmScheme }, { createWalletClient, custom }] = await Promise.all([
                import('https://esm.sh/@x402/fetch@2.17.0'),
                import('https://esm.sh/@x402/evm@2.17.0'),
                import('https://esm.sh/viem@2'),
            ]);
            const account = Wallet.state().account;
            const provider = Wallet.getProvider();
            const walletClient = createWalletClient({ account, transport: custom(provider) });
            const signer = { address: account, signTypedData: (args) => walletClient.signTypedData({ account, ...args }) };
            const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
                schemes: [{ network: 'eip155:8453', client: new ExactEvmScheme(signer) }],
            });

            const qs = Object.keys(params).length
                ? '?' + Object.entries(params).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&') : '';
            set('<i class="fa-solid fa-spinner fa-spin"></i> Sign the request in your wallet…');
            const res = await fetchWithPayment(`${window.WORKER_BASE}/data/${offeringName}${qs}`);
            const result = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(result.error || `Worker returned ${res.status}`);
            this._renderDataResult(offeringName, priceUsd, params, result);
        } catch (e) {
            const msg = (e && e.message) || String(e);
            set(`Payment failed: ${escapeHtml(msg.slice(0, 200))}`, 'text-rose-400');
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50');
        }
    },

    _renderDataResult(offeringName, priceUsd, params, result) {
        const body = document.getElementById('hire-body');
        if (!body) return;
        const deliverable = (result && result.deliverable) || {};
        const walletAddress = (window.Wallet && Wallet.state().account) || null;
        body.innerHTML = `
            <div class="text-center mb-4">
                <i class="fa-solid fa-circle-check text-cyan-400 text-3xl mb-2"></i>
                <div class="font-display text-lg">Paid &amp; delivered</div>
                <div class="text-xs text-zinc-500">${escapeHtml(offeringName.replace(/_/g, ' '))} · $${priceUsd} settled on Base</div>
            </div>
            <div class="glass rounded-xl p-4 mb-4 max-h-80 overflow-y-auto">${this._dataHtml(deliverable)}</div>
            <button id="hire-copy" class="w-full bg-white/10 hover:bg-white/15 transition px-4 py-2.5 rounded-xl font-display text-sm"><i class="fa-solid fa-copy"></i> Copy JSON</button>
            <div id="hire-copy-status" class="text-xs text-zinc-500 mt-3 text-center">Saved to your Engagement History in "Portfolio Intelligence" below.</div>`;
        document.getElementById('hire-copy').onclick = async () => {
            await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
            document.getElementById('hire-copy-status').textContent = 'Copied raw JSON to clipboard.';
        };
        try {
            if (window.CaseHistory && walletAddress) {
                CaseHistory.save({ offering: offeringName, priceUsd, via: 'x402', walletAddress,
                    targetAddress: params.address || params.slug || params.chain || '', verdict: 'DATA', result });
            }
        } catch (e) { /* non-fatal — data is already shown above */ }
    },

    // Rich, logo-aware renderer for a market-data deliverable. Handles the
    // common shapes (a logo + scalars, and any array of rows that may carry
    // per-row logos) generically, so every tool renders without a bespoke
    // layout each. Everything is escaped; logos use the same onerror-hide
    // pattern the rest of the site uses for token/protocol icons.
    _dataHtml(d) {
        if (!d || typeof d !== 'object') return `<div class="text-xs text-zinc-400">${escapeHtml(String(d))}</div>`;
        if (d.error) return `<div class="text-xs text-amber-400">${escapeHtml(String(d.error))}</div>`;
        const img = (url) => url ? `<img src="${escapeHtml(url)}" class="w-5 h-5 rounded-full inline-block align-middle mr-1.5" onerror="this.style.display='none'">` : '';
        const fmt = (v) => {
            if (v == null) return '—';
            if (typeof v === 'number') return v.toLocaleString(undefined, { maximumFractionDigits: 6 });
            return escapeHtml(String(v));
        };
        const rows = [];
        if (d.logo || d.name || d.symbol) {
            rows.push(`<div class="flex items-center gap-1 mb-2 text-sm text-zinc-100">${img(d.logo)}<span class="font-semibold">${escapeHtml(d.name || d.symbol || '')}</span>${d.symbol && d.name ? `<span class="text-zinc-500 text-xs ml-1">${escapeHtml(d.symbol)}</span>` : ''}</div>`);
        }
        // Scalar fields (skip noisy/internal keys and arrays/objects handled below).
        const skip = new Set(['logo', 'name', 'symbol', 'ts', 'chain', 'address', 'prices']);
        for (const [k, v] of Object.entries(d)) {
            if (skip.has(k) || v == null) continue;
            if (Array.isArray(v)) continue;
            if (typeof v === 'object') {
                // one level of nesting (e.g. price:{price,confidence}, first_price:{age_days})
                const sub = Object.entries(v).filter(([, x]) => x != null && typeof x !== 'object')
                    .map(([sk, sx]) => `<span class="text-zinc-400">${escapeHtml(sk)}</span> ${fmt(sx)}`).join(' · ');
                if (sub) rows.push(`<div class="text-xs mb-1"><span class="text-cyan-400 font-mono">${escapeHtml(k)}</span> — ${sub}</div>`);
                continue;
            }
            rows.push(`<div class="text-xs mb-1 flex justify-between gap-3"><span class="text-zinc-500 font-mono">${escapeHtml(k)}</span><span class="text-zinc-200 text-right">${fmt(v)}</span></div>`);
        }
        // Arrays of rows (protocols, dexs, bridges, stablecoins, pools, venues…).
        // Respect the same skip set as the scalar pass so the raw `prices`
        // series (token_chart's [{timestamp,price}]) isn't rendered as a
        // blank generic row list — it's a chart series, not a row table.
        for (const [k, v] of Object.entries(d)) {
            if (skip.has(k)) continue;
            if (!Array.isArray(v) || !v.length || typeof v[0] !== 'object') continue;
            const items = v.slice(0, 12).map(row => {
                const title = row.name || row.symbol || row.project || row.pool || '';
                const metricKey = ['depeg', 'apy', 'tvl_usd', 'vol_24h', 'fees_24h', 'circulating_usd', 'last_daily_volume']
                    .find(mk => row[mk] != null);
                const metric = metricKey ? `<span class="text-cyan-400 font-mono text-[11px] whitespace-nowrap">${escapeHtml(metricKey)}: ${fmt(row[metricKey])}</span>` : '';
                return `<div class="flex items-center justify-between gap-2 py-0.5"><span class="flex items-center min-w-0 text-xs text-zinc-200">${img(row.logo)}<span class="truncate">${escapeHtml(title)}</span></span>${metric}</div>`;
            }).join('');
            rows.push(`<div class="mt-2"><div class="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">${escapeHtml(k)} (${v.length})</div>${items}</div>`);
        }
        return rows.join('') || `<pre class="text-[11px] text-zinc-400 whitespace-pre-wrap">${escapeHtml(JSON.stringify(d, null, 2))}</pre>`;
    },
};

window.Hire = Hire;
