// VAPE hire flow — x402 (real, in-browser, instant) and ACP (links out to the
// real Virtuals job flow, since ACP job creation needs Privy + Alchemy
// Account Kit smart accounts that this zero-bundler site doesn't run).
const ACP_AGENT_URL = 'https://app.virtuals.io/acp/agent/019eaf60-592a-7f5c-99a2-3e85199303fe';
const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;
const TX_HASH_RE = /^0x[a-fA-F0-9]{64}$/;
// GitHub owner/repo names are [A-Za-z0-9_.-]+ per GitHub's own naming rules —
// gate before either value is sent to the worker (see openBountyOps() below).
const GH_SLUG_RE = /^[A-Za-z0-9_.-]+$/;

// offeringName arrives here via an inline onclick="Hire.openX402('${o.name}', ...)"
// string built in app.js, and exception messages can echo back arbitrary text
// (e.g. from a fetch error) — both get written into innerHTML below, so escape
// them at the sink, same pattern already used in report.js.
function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// Tags every x402 request this site's own wallet-connect flow makes with
// X-VAPE-Client: site — the worker uses this to always route a real human's
// in-browser payment through CDP (the facilitator Basescan actually
// recognizes and labels) rather than risk the 50/50 VAPOR/CDP split landing
// on VAPOR's still-unlabeled address for the one traffic class where a
// person is looking at Basescan afterward expecting to see it tagged as an
// x402 payment.
//
// @x402/fetch's wrapFetchWithPayment (verified against the actual published
// source, not assumed) ALWAYS calls the fetch it wraps with a single, fully-
// formed Request object — never a (url, init) pair — and on the signed
// retry, the wallet-signed X-PAYMENT header is already set directly on that
// Request before it ever reaches here. A prior version of this function
// built headers from `init.headers`, which is always empty in every call
// this wrapper makes — the payment header lives on `input` itself, not a
// second argument, so that version silently produced a request with ONLY
// X-VAPE-Client and no X-PAYMENT, making the signed retry look unauthenticated
// again (a second 402) — exactly the "Payment failed: Worker returned 402"
// regression this replaces. `new Request(input, init)` clones whatever was
// passed in — a plain URL string or an existing Request — preserving all of
// its existing headers (X-PAYMENT included), and `.headers.set(...)` only
// touches the one key we're adding, never removing anything else already set.
function siteTaggedFetch(input, init) {
    const request = new Request(input, init);
    request.headers.set('X-VAPE-Client', 'site');
    return fetch(request);
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
    yields:          { inputs: [{ k: 'chain', label: 'Chain (optional)', ph: 'Base', opt: true },
                                    { k: 'project', label: 'Project (optional)', ph: 'aave-v3', opt: true },
                                    { k: 'symbol', label: 'Symbol (optional)', ph: 'USDC', opt: true }] },
    stablecoins:     { inputs: [] },
    bridges:         { inputs: [] },
    // Base mainnet only — the Alchemy-backed pipeline behind this offering
    // (worker/src/dataHandlers.ts, rebuilt off Codex after its wallet-
    // analytics fields turned out to be paid-plan-gated) has no other chain
    // configured, so there's no real chain selector to show here.
    wallet_pnl_deepdive: { inputs: [{ k: 'address', label: 'Wallet address to hire the deep-dive for', ph: '0x… wallet', addr: true }] },
};

const Hire = {
    _modal: null,

    // Shared address/GitHub-repo toggle for bounty_deep_dive engagements —
    // the same input shapes are needed whether the buyer is hiring against a
    // specific Bounty Ops program (openBountyOps, pre-scoped, may default to
    // repo mode) or through the generic Commission modal (openX402, address
    // mode by default, no program context) — see docs/ACP_PROTOCOL.md's
    // dual-routing note. One implementation so both stay in sync; the fields
    // container is rendered by the caller (id may differ), so this only
    // fills it in and wires the toggle buttons already present in `modal`.
    _renderAddressRepoFields(fieldsEl, mode, hints) {
        const h = hints || {};
        fieldsEl.innerHTML = mode === 'repo' ? `
            <label class="text-xs text-zinc-500 block mb-1">GitHub repo${h.repo ? ` — ${h.repo}` : ' to audit'}</label>
            <input id="hire-repo" type="text" placeholder="owner/repo" class="w-full bg-transparent border border-white/10 focus:border-white/30 outline-none px-3 py-2 text-xs font-mono mb-4">
        ` : `
            <label class="text-xs text-zinc-500 block mb-1">Target contract address${h.address ? ` ${h.address}` : ' to investigate'}</label>
            <input id="hire-address" type="text" placeholder="0x… token/contract" class="w-full bg-transparent border border-white/10 focus:border-white/30 outline-none px-3 py-2 text-xs font-mono mb-4">
        `;
    },

    // Single "owner/repo" field (not separate owner + repo inputs) — parsed
    // here right before submission. Returns {owner, repo} or null on anything
    // that doesn't look like a real GitHub slug pair.
    _parseOwnerRepo(value) {
        const parts = (value || '').trim().split('/');
        if (parts.length !== 2) return null;
        const [owner, repo] = parts.map(p => p.trim());
        if (!owner || !repo || !GH_SLUG_RE.test(owner) || !GH_SLUG_RE.test(repo)) return null;
        return { owner, repo };
    },

    _wireAddressRepoToggle(modal, fieldsEl, initialMode, hints) {
        let mode = initialMode;
        this._renderAddressRepoFields(fieldsEl, mode, hints);
        modal.querySelectorAll('[data-mode]').forEach(btn => btn.onclick = () => {
            mode = btn.dataset.mode;
            modal.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('term-btn-active', b === btn));
            this._renderAddressRepoFields(fieldsEl, mode, hints);
        });
        return () => mode;
    },

    // ACP engagement sunset from the site 2026-07-31 (x402 is now VAPE's sole
    // commerce rail) -- every "Engage via ACP" call site was removed from
    // index.html, so this is no longer reachable from the UI. Left in place
    // (not deleted) rather than stripped from the repo.
    openAcp(offeringName) {
        window.open(ACP_AGENT_URL, '_blank', 'noopener');
    },

    openX402(offeringName, priceUsd) {
        // Market-data tools take varied inputs and return rich data (not a
        // verdict), so they get their own modal/result path.
        if (DATA_OFFERINGS[offeringName]) return this.openData(offeringName, priceUsd);
        this._closeModal();
        // tx_decode takes a 32-byte tx hash, not a 20-byte contract address —
        // its own input shape/regex/param key. bulk_safety_bundle takes 5-25
        // addresses at once, not a single one. Both distinct from every
        // other scan offering below.
        const isTxHash = offeringName === 'tx_decode';
        const isBulk = offeringName === 'bulk_safety_bundle';
        // bounty_deep_dive already accepts either an on-chain address or a
        // GitHub owner/repo server-side (worker/src/index.ts's hasAddress/
        // hasRepo branches) — openBountyOps() below already exposes both via
        // its own toggle when hiring from a matched Bounty Ops program; this
        // generic Commission modal previously only ever rendered the address
        // field, so a repo-based engagement had no path in here at all.
        const isRepoToggle = offeringName === 'bounty_deep_dive';
        // website_review takes a plain website URL, not a contract address —
        // a general phishing/scam-page content read, distinct from every
        // address-based security offering (see worker/src/lib/websiteReview.ts).
        const isUrl = offeringName === 'website_review';
        const needsAddress = !isTxHash && !isBulk && !isRepoToggle && !isUrl && !['market_intel', 'community_intel_broadcast'].includes(offeringName);
        const modal = document.createElement('div');
        modal.id = 'hire-modal';
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" data-close></div>
            <div class="relative popover p-6 w-full max-w-md">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg flex items-center gap-2"><i class="fa-solid fa-bolt text-zinc-400"></i> Commission VAPE</h3>
                    <button data-close class="text-zinc-500 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div id="hire-body">
                    <div class="text-sm text-zinc-400 mb-1">${escapeHtml(offeringName.replace(/_/g,' '))} <span class="text-zinc-200 font-mono">$${priceUsd}</span></div>
                    <p class="text-xs text-zinc-500 mb-4">Settles via x402: your wallet signs a gasless USDC authorization for the exact price above — no gas fee, no subscription, settles on Base mainnet.</p>
                    ${isTxHash ? `
                    <label class="text-xs text-zinc-500 block mb-1">Transaction hash</label>
                    <input id="hire-address" type="text" placeholder="0x… 32-byte tx hash to decode" class="w-full bg-transparent border border-white/10 focus:border-white/30 outline-none px-3 py-2 text-xs font-mono mb-4">
                    ` : isBulk ? `
                    <label class="text-xs text-zinc-500 block mb-1">5-25 token addresses (one per line, or comma-separated)</label>
                    <textarea id="hire-address" rows="5" placeholder="0x…&#10;0x…&#10;0x…" class="w-full bg-transparent border border-white/10 focus:border-white/30 outline-none px-3 py-2 text-xs font-mono mb-4 resize-none"></textarea>
                    ` : isRepoToggle ? `
                    <div class="flex gap-2 mb-4">
                        <button data-mode="address" class="flex-1 term-btn term-btn-active">Contract address</button>
                        <button data-mode="repo" class="flex-1 term-btn">GitHub repo</button>
                    </div>
                    <div id="hire-bounty-fields"></div>
                    ` : isUrl ? `
                    <label class="text-xs text-zinc-500 block mb-1">Website URL to review</label>
                    <input id="hire-address" type="text" placeholder="https:// the site to check for phishing/scam red flags" class="w-full bg-transparent border border-white/10 focus:border-white/30 outline-none px-3 py-2 text-xs font-mono mb-4">
                    ` : needsAddress ? `
                    <label class="text-xs text-zinc-500 block mb-1">Target contract address</label>
                    <input id="hire-address" type="text" placeholder="0x… token/contract to investigate" class="w-full bg-transparent border border-white/10 focus:border-white/30 outline-none px-3 py-2 text-xs font-mono mb-4">
                    ` : '<div class="mb-4"></div>'}
                    <button id="hire-submit" class="w-full term-btn">Authorize &amp; Execute</button>
                    <div id="hire-status" class="text-xs text-zinc-500 mt-3"></div>
                </div>
            </div>`;
        document.body.appendChild(modal);
        this._modal = modal;
        modal.querySelectorAll('[data-close]').forEach(el => el.onclick = () => this._closeModal());
        const getMode = isRepoToggle
            ? this._wireAddressRepoToggle(modal, modal.querySelector('#hire-bounty-fields'), 'address')
            : null;
        modal.querySelector('#hire-submit').onclick = () => {
            const status = document.getElementById('hire-status');
            let value = '';
            if (isRepoToggle) {
                const fail = (msg) => { status.innerHTML = msg; status.className = 'text-xs mt-3 text-amber-400'; };
                if (getMode() === 'address') {
                    const address = (document.getElementById('hire-address').value || '').trim();
                    if (!ADDRESS_RE.test(address)) return fail('Enter a valid 0x… contract address.');
                    this._runX402(offeringName, priceUsd, { address }, address);
                } else {
                    const parsed = this._parseOwnerRepo(document.getElementById('hire-repo').value);
                    if (!parsed) return fail('Enter a valid GitHub repo as owner/repo.');
                    this._runX402(offeringName, priceUsd, parsed, `${parsed.owner}/${parsed.repo}`);
                }
                return;
            }
            if (isUrl) {
                value = (document.getElementById('hire-address').value || '').trim();
                let parsed;
                try { parsed = new URL(value); } catch { parsed = null; }
                if (!parsed || (parsed.protocol !== 'http:' && parsed.protocol !== 'https:')) {
                    status.innerHTML = 'Enter a valid http(s) URL.';
                    status.className = 'text-xs mt-3 text-amber-400';
                    return;
                }
                this._runX402(offeringName, priceUsd, { url: value }, value);
                return;
            }
            if (isTxHash) {
                value = (document.getElementById('hire-address').value || '').trim();
                if (!TX_HASH_RE.test(value)) {
                    status.innerHTML = 'Enter a valid 0x… 32-byte transaction hash.';
                    status.className = 'text-xs mt-3 text-amber-400';
                    return;
                }
                this._runX402(offeringName, priceUsd, { tx_hash: value }, value);
                return;
            }
            if (isBulk) {
                const list = (document.getElementById('hire-address').value || '')
                    .split(/[\s,]+/).map(a => a.trim()).filter(Boolean);
                if (list.length < 5 || list.length > 25 || !list.every(a => ADDRESS_RE.test(a))) {
                    status.innerHTML = 'Enter 5-25 valid 0x… addresses (one per line or comma-separated).';
                    status.className = 'text-xs mt-3 text-amber-400';
                    return;
                }
                this._runX402(offeringName, priceUsd, { addresses: list.join(',') }, `${list.length} tokens`);
                return;
            }
            if (needsAddress) {
                value = (document.getElementById('hire-address').value || '').trim();
                if (!ADDRESS_RE.test(value)) {
                    status.innerHTML = 'Enter a valid 0x… contract address.';
                    status.className = 'text-xs mt-3 text-amber-400';
                    return;
                }
            }
            this._runX402(offeringName, priceUsd, needsAddress ? { address: value } : {}, value);
        };
    },

    // Hire VAPE for a specific matched Bounty Ops program (Task: hire-from-
    // Bounty-Ops). Unlike the generic Commission panel, this call is pre-scoped
    // to one real, already-tracked program — the buyer only supplies whatever
    // targeting info the bounty-radar record itself doesn't carry (no program
    // record has a resolvable source-repo/address field, only a link to the
    // platform's own program page). Routes to the right pipeline using the
    // same vapeFitReason/tags classification agents/scout.py already computed:
    // "...matches agents/external_audit.py" (Move/Sui or general repo) needs a
    // GitHub owner/repo; "...matches agents/deep_dive_audit.py" (Solidity/EVM)
    // needs an on-chain address. The toggle lets a buyer override VAPE's guess
    // since the classification is a heuristic, not a guarantee.
    openBountyOps(slug) {
        const record = (window.App && App._bountyOpsList && App._bountyOpsList[slug]) || null;
        if (!record) return;
        this._closeModal();
        const reason = `${record.vapeFitReason || ''} ${(record.tags || []).join(' ')}`;
        const repoDefault = /external_audit/i.test(reason) || /\bmove\b|\bsui\b/i.test(reason);
        const modal = document.createElement('div');
        modal.id = 'hire-modal';
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" data-close></div>
            <div class="relative popover p-6 w-full max-w-md">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg flex items-center gap-2"><i class="fa-solid fa-bolt text-zinc-400"></i> Hire VAPE for this bounty</h3>
                    <button data-close class="text-zinc-500 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div id="hire-body">
                    <div class="text-sm text-zinc-200 mb-1">${escapeHtml(record.name || 'Bounty program')}</div>
                    <div class="text-xs text-zinc-500 mb-4">${escapeHtml(record.platform || '')}${record.prizeUsd ? ` · up to $${Number(record.prizeUsd).toLocaleString()}` : ''} · bounty_deep_dive <span class="text-zinc-200 font-mono">$1</span></div>
                    <p class="text-xs text-zinc-500 mb-4">Settles via x402: your wallet signs a gasless USDC authorization for $1 — no gas fee, no subscription. VAPE audits this specific program and delivers a submission-ready PoC with full technical detail.</p>
                    <div class="flex gap-2 mb-4">
                        <button data-mode="address" class="flex-1 term-btn${repoDefault ? '' : ' term-btn-active'}">Contract address</button>
                        <button data-mode="repo" class="flex-1 term-btn${repoDefault ? ' term-btn-active' : ''}">GitHub repo</button>
                    </div>
                    <div id="hire-bounty-fields"></div>
                    <button id="hire-submit" class="w-full term-btn mt-1">Authorize &amp; Execute</button>
                    <div id="hire-status" class="text-xs text-zinc-500 mt-3"></div>
                </div>
            </div>`;
        document.body.appendChild(modal);
        this._modal = modal;
        modal.querySelectorAll('[data-close]').forEach(el => el.onclick = () => this._closeModal());

        const fieldsEl = modal.querySelector('#hire-bounty-fields');
        const getMode = this._wireAddressRepoToggle(modal, fieldsEl, repoDefault ? 'repo' : 'address',
            { repo: "this program's own source repo", address: "in this program's scope" });

        modal.querySelector('#hire-submit').onclick = () => {
            const status = document.getElementById('hire-status');
            const fail = (msg) => { status.innerHTML = msg; status.className = 'text-xs mt-3 text-amber-400'; };
            const mode = getMode();
            if (mode === 'address') {
                const address = (document.getElementById('hire-address').value || '').trim();
                if (!ADDRESS_RE.test(address)) return fail('Enter a valid 0x… contract address.');
                this._runX402('bounty_deep_dive', 1, { address }, address);
            } else {
                const parsed = this._parseOwnerRepo(document.getElementById('hire-repo').value);
                if (!parsed) return fail('Enter a valid GitHub repo as owner/repo.');
                this._runX402('bounty_deep_dive', 1, { ...parsed, program_name: record.name }, `${parsed.owner}/${parsed.repo}`);
            }
        };
    },

    _closeModal() {
        if (this._modal) { this._modal.remove(); this._modal = null; }
        if (this._pollTimer) { clearInterval(this._pollTimer); this._pollTimer = null; }
        if (this._dataChart) { this._dataChart.destroy(); this._dataChart = null; }
    },

    // Live in-page polling for an async bounty_deep_dive job — worker/src/
    // index.ts's GET /scan/bounty_deep_dive/status?job=<id>, backed by
    // VAPE_JOBS KV. Keeps polling for the modal's lifetime (audits can run up
    // to the workflow's 60-minute timeout, so a short fixed budget would give
    // up on a real in-progress job) — _closeModal() above is what actually
    // stops it once the buyer navigates away.
    _pollBountyJob(jobId, offeringName, priceUsd, targetLabel) {
        const startedAt = Date.now();
        // The workflow itself times out at 60 minutes (deep-dive-bounty.yml /
        // external-bounty-audit.yml) — this buffer covers queueing/dispatch
        // lag on top of that. Without a ceiling, a job that crashes or hangs
        // before ever POSTing to /callback would show "still running" forever.
        const MAX_POLL_MS = 90 * 60 * 1000;
        const giveUp = (message, cls) => {
            clearInterval(this._pollTimer);
            this._pollTimer = null;
            const el = document.getElementById('hire-poll-elapsed');
            if (el) { el.textContent = message; el.className = `mt-2 ${cls || 'text-zinc-500'}`; }
        };
        const tick = async () => {
            if (Date.now() - startedAt > MAX_POLL_MS) {
                giveUp("Still hasn't reported back after 90 minutes — unusual, but your payment is safe either way. The audit ledger (link above) is the source of truth if this modal gives up first.", 'text-amber-400');
                return;
            }
            if (!window.WORKER_BASE) return;
            let data;
            try {
                const res = await fetch(`${window.WORKER_BASE}/scan/bounty_deep_dive/status?job=${encodeURIComponent(jobId)}`);
                if (!res.ok) return; // transient (404 while KV write races the first poll, 503, network) — just try again next tick
                data = await res.json();
            } catch (e) { return; }
            if (data && data.status === 'done') {
                clearInterval(this._pollTimer);
                this._pollTimer = null;
                await this._renderResult(offeringName, priceUsd, targetLabel, {
                    status: 'ok', deliverable: data.result || {}, source: 'vape-real-data',
                    disclaimer: 'Real on-chain data. Not investment advice.',
                });
                return;
            }
            if (data && data.status === 'failed') {
                // giveUp() sets this via textContent, not innerHTML, so data.error
                // (real but untrusted — VAPE's own dispatch-failure text, not
                // attacker-controlled, but still external to this file) needs no
                // escaping here; escaping it would double-escape and corrupt display.
                giveUp(`Dispatch failed server-side (${String(data.error || 'unknown error')}) — your payment settled but the audit never started. Contact VAPE via X (@based_vape) to resolve.`, 'text-rose-400');
                return;
            }
            const el = document.getElementById('hire-poll-elapsed');
            if (el) {
                const mins = Math.floor((Date.now() - startedAt) / 60000);
                el.textContent = mins < 1 ? 'just started' : `${mins} minute${mins === 1 ? '' : 's'} elapsed — still running`;
            }
        };
        if (this._pollTimer) clearInterval(this._pollTimer);
        this._pollTimer = setInterval(tick, 20000);
        tick();
    },

    // params becomes the /scan/<offeringName> query string verbatim (e.g.
    // {address} for an on-chain target, or {owner,repo,ref,program_name} for
    // a repo-scoped bounty_deep_dive engagement — see openBountyOps() below).
    // targetLabel is display/record-keeping only (CaseHistory, report header).
    async _runX402(offeringName, priceUsd, params, targetLabel) {
        const status = document.getElementById('hire-status');
        const submitBtn = document.getElementById('hire-submit');
        const set = (html, cls) => { status.innerHTML = html; status.className = `text-xs mt-3 ${cls || 'text-zinc-500'}`; };

        if (!window.Wallet || !Wallet.state().connected) { set('Connect a wallet first (top right), then try again.', 'text-amber-400'); return; }
        if (!window.WORKER_BASE) { set("VAPE's payment worker isn't configured yet.", 'text-amber-400'); return; }

        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50');
        set('<i class="fa-solid fa-spinner fa-spin"></i> Checking network…');
        const onBase = await Wallet.ensureBase();
        if (!onBase) { set('Switch your wallet to Base mainnet and try again.', 'text-amber-400'); submitBtn.disabled = false; submitBtn.classList.remove('opacity-50'); return; }

        try {
            set('<i class="fa-solid fa-spinner fa-spin"></i> Loading payment protocol…');
            const [{ wrapFetchWithPaymentFromConfig }, { ExactEvmScheme }, { createWalletClient, custom }] = await Promise.all([
                import('https://esm.sh/@x402/fetch@2.19.0'),
                import('https://esm.sh/@x402/evm@2.19.0'),
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
            const fetchWithPayment = wrapFetchWithPaymentFromConfig(siteTaggedFetch, {
                schemes: [{ network: 'eip155:8453', client: new ExactEvmScheme(signer) }],
            });

            set('<i class="fa-solid fa-spinner fa-spin"></i> Requesting payment terms…');
            const qs = Object.entries(params || {}).filter(([, v]) => v)
                .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
            const url = `${window.WORKER_BASE}/scan/${offeringName}` + (qs ? `?${qs}` : '');
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
            await this._renderResult(offeringName, priceUsd, targetLabel, result);
        } catch (e) {
            const msg = (e && e.message) || String(e);
            set(`Payment failed: ${escapeHtml(msg.slice(0, 200))}`, 'text-rose-400');
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50');
        }
    },

    async _renderResult(offeringName, priceUsd, targetLabel, result) {
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
                    CaseHistory.save({ offering: offeringName, priceUsd, via: 'x402', walletAddress, targetAddress: targetLabel, verdict: 'QUEUED', result });
                }
            } catch (e) { /* non-fatal */ }
            // Real privacy gap this closes: this used to fall back to a public
            // GitHub-tree link ("Track the audit ledger") into intel/audits/
            // poc-reports/ — but a paid audit's PoC is exactly the sensitive
            // technical detail the buyer alone still needs to submit to a
            // bounty program, and that directory no longer gets a buyer's
            // report committed to it at all (see deep-dive-bounty.yml's
            // matching fix). The private, already-working delivery path
            // (worker KV job polling below, or CaseHistory's own localStorage
            // record) is now the ONLY path — no public fallback link.
            if (result.job) {
                // Live-polled path: worker minted a job id (VAPE_JOBS is
                // configured), so this modal updates itself in place once
                // the audit finishes.
                body.innerHTML = `
                    <div class="text-center mb-4">
                        <i class="fa-solid fa-spinner fa-spin text-zinc-300 text-3xl mb-2"></i>
                        <div class="text-lg">Audit running</div>
                        <div class="text-xs text-zinc-500">${escapeHtml(offeringName.replace(/_/g,' '))} · $${priceUsd} settled on Base</div>
                    </div>
                    <div class="border border-white/10 p-4 mb-4 text-sm text-zinc-300 leading-relaxed">
                        VAPE is running the full audit now — real static/symbolic tooling plus a frontier-tier LLM pass, not a canned check. This can take up to an hour; leave this open and the report will render right here — it's private to this engagement, never published anywhere.
                        <div id="hire-poll-elapsed" class="text-zinc-500 mt-2">just started</div>
                    </div>
                    <div class="text-xs text-zinc-500 mt-3 text-center">Saved to your Engagement History in "Portfolio Intelligence" below — reopen this page (same wallet) if you close the tab.</div>`;
                this._pollBountyJob(result.job, offeringName, priceUsd, targetLabel);
                return;
            }
            body.innerHTML = `
                <div class="text-center mb-4">
                    <i class="fa-solid fa-clock text-zinc-300 text-3xl mb-2"></i>
                    <div class="text-lg">Paid — audit queued</div>
                    <div class="text-xs text-zinc-500">${escapeHtml(offeringName.replace(/_/g,' '))} · $${priceUsd} settled on Base</div>
                </div>
                <div class="border border-white/10 p-4 mb-4 text-sm text-zinc-300 leading-relaxed">${escapeHtml(result.message || 'Audit queued — a submission-ready PoC report lands as soon as it completes, delivered privately, never published.')}</div>
                <div class="text-xs text-zinc-500 mt-3 text-center">Saved to your Engagement History in "Portfolio Intelligence" below — check back for the finished report.</div>`;
            return;
        }
        const deliverable = result.deliverable || {};
        const verdict = deliverable.verdict || deliverable.rug_risk || deliverable.combined || deliverable.token_verdict;
        const walletAddress = (window.Wallet && Wallet.state().account) || null;
        const reportOpts = { offering: offeringName, priceUsd, requestedAddress: targetLabel, hiredBy: walletAddress, result, via: 'x402' };

        // Render the actual report content first, synchronously, before any
        // risky async work (PDF generation needs a CDN script, saving to
        // localStorage) — those can fail independently in a restrictive
        // browser (e.g. Base Wallet's in-app webview) without ever hiding
        // the thing that was actually paid for.
        let inlineReport = '';
        try { inlineReport = Report.buildHtmlSummary(reportOpts); } catch (e) { /* fall through with empty inline report */ }
        body.innerHTML = `
            <div class="text-center mb-4">
                <i class="fa-solid fa-circle-check text-zinc-300 text-3xl mb-2"></i>
                <div class="text-lg">Paid & delivered</div>
                <div class="text-xs text-zinc-500">${escapeHtml(offeringName.replace(/_/g,' '))} · $${priceUsd} settled on Base</div>
            </div>
            <div class="border border-white/10 p-4 mb-4">${inlineReport || '<div class="text-xs text-amber-400">Could not render report preview — use Copy JSON below for the raw result.</div>'}</div>
            <div class="flex gap-2">
                <button id="hire-download" class="flex-1 term-btn"><i class="fa-solid fa-file-pdf"></i> Download PDF</button>
                <button id="hire-copy" class="flex-1 term-btn"><i class="fa-solid fa-copy"></i> Copy JSON</button>
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
                CaseHistory.save({ offering: offeringName, priceUsd, via: 'x402', walletAddress, targetAddress: targetLabel, verdict, result });
            }
        } catch (e) { /* non-fatal — report is already shown above */ }
        try {
            await Report.downloadPdf(reportOpts);
        } catch (e) { /* PDF/download not available in this browser — inline report above still stands */ }
    },

    // ── VAPE market-data tools ($0.01 each) ───────────────────────────────────
    // prefill optionally pre-populates input fields by key (e.g. {address:
    // '0x...'}) — used by callers that already know the target, like a
    // top-holder row linking straight into a hire for that specific wallet.
    openData(offeringName, priceUsd, prefill) {
        this._closeModal();
        const spec = DATA_OFFERINGS[offeringName];
        const title = offeringName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const fields = spec.inputs.map(f => `
            <label class="text-xs text-zinc-500 block mb-1">${escapeHtml(f.label)}</label>
            <input data-key="${escapeHtml(f.k)}" type="text" placeholder="${escapeHtml(f.ph || '')}" value="${escapeHtml((prefill && prefill[f.k]) || f.def || '')}"
                   class="w-full bg-transparent border border-white/10 focus:border-white/30 outline-none px-3 py-2 text-xs font-mono mb-3">`).join('');
        const modal = document.createElement('div');
        modal.id = 'hire-modal';
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" data-close></div>
            <div class="relative popover p-6 w-full max-w-md">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg flex items-center gap-2"><i class="fa-solid fa-bolt text-zinc-400"></i> ${escapeHtml(title)}</h3>
                    <button data-close class="text-zinc-500 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div id="hire-body">
                    <div class="text-sm text-zinc-400 mb-1"><span class="text-zinc-200 font-mono">$${priceUsd}</span></div>
                    <p class="text-xs text-zinc-500 mb-4">Settles via x402: your wallet signs a gasless USDC authorization for the exact price above — no gas fee, no subscription, settles on Base mainnet.</p>
                    ${fields || '<div class="mb-1"></div>'}
                    <button id="hire-submit" class="w-full term-btn mt-1">Authorize &amp; Fetch</button>
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
                import('https://esm.sh/@x402/fetch@2.19.0'),
                import('https://esm.sh/@x402/evm@2.19.0'),
                import('https://esm.sh/viem@2'),
            ]);
            const account = Wallet.state().account;
            const provider = Wallet.getProvider();
            const walletClient = createWalletClient({ account, transport: custom(provider) });
            const signer = { address: account, signTypedData: (args) => walletClient.signTypedData({ account, ...args }) };
            const fetchWithPayment = wrapFetchWithPaymentFromConfig(siteTaggedFetch, {
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
        const targetAddress = params.address || params.slug || params.chain || '';
        const reportOpts = { offering: offeringName, priceUsd, requestedAddress: targetAddress, hiredBy: walletAddress, result, via: 'x402' };
        body.innerHTML = `
            <div class="text-center mb-4">
                <i class="fa-solid fa-circle-check text-zinc-300 text-3xl mb-2"></i>
                <div class="text-lg">Paid &amp; delivered</div>
                <div class="text-xs text-zinc-500">${escapeHtml(offeringName.replace(/_/g, ' '))} · $${priceUsd} settled on Base</div>
            </div>
            <div class="border border-white/10 p-4 mb-4 max-h-80 overflow-y-auto">${this._dataHtml(deliverable)}</div>
            <div class="flex gap-2">
                <button id="hire-download" class="flex-1 term-btn"><i class="fa-solid fa-file-pdf"></i> Download PDF</button>
                <button id="hire-copy" class="flex-1 term-btn"><i class="fa-solid fa-copy"></i> Copy JSON</button>
            </div>
            <div id="hire-copy-status" class="text-xs text-zinc-500 mt-3 text-center">Saved to your Engagement History in "Portfolio Intelligence" below.</div>`;
        this._renderDataChart(deliverable.prices);
        document.getElementById('hire-download').onclick = () => Report.downloadPdf(reportOpts);
        document.getElementById('hire-copy').onclick = async () => {
            await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
            document.getElementById('hire-copy-status').textContent = 'Copied raw JSON to clipboard.';
        };
        try {
            if (window.CaseHistory && walletAddress) {
                CaseHistory.save({ offering: offeringName, priceUsd, via: 'x402', walletAddress,
                    targetAddress, verdict: 'DATA', result });
            }
        } catch (e) { /* non-fatal — data is already shown above */ }
        // Best-effort auto-download, same as the verdict-offering flow
        // (_renderResult) — the inline preview above is already fully
        // visible regardless of whether this succeeds.
        Report.downloadPdf(reportOpts).catch(() => { /* PDF/download not available in this browser — inline preview above still stands */ });
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
        // http(s)-only guard before ever putting a provider-supplied string into
        // an href — an <a> (unlike <img src>) will happily execute a
        // javascript: URI on click, so this can't just reuse img()'s pattern.
        const safeHref = (url) => typeof url === 'string' && /^https?:\/\//i.test(url) ? url : null;
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
                if (sub) rows.push(`<div class="text-xs mb-1"><span class="text-zinc-400 font-mono">${escapeHtml(k)}</span> — ${sub}</div>`);
                continue;
            }
            rows.push(`<div class="text-xs mb-1 flex justify-between gap-3"><span class="text-zinc-500 font-mono">${escapeHtml(k)}</span><span class="text-zinc-200 text-right">${fmt(v)}</span></div>`);
        }
        // token_chart's `prices` ([{timestamp,price}]) is a real chart series,
        // not a row table — render an actual canvas (see _renderDataChart,
        // wired up by the caller once this HTML is in the DOM) instead of
        // dropping the field entirely, which is what happened before this fix
        // (the whole point of the offering silently missing from its own
        // deliverable).
        if (Array.isArray(d.prices) && d.prices.length && typeof d.prices[0] === 'object') {
            rows.push(`<div class="mt-2 chart-shell-sm"><canvas id="hire-data-chart"></canvas></div>`);
        }
        // Arrays of rows (protocols, dexs, bridges, stablecoins, pools, venues…).
        // Respect the same skip set as the scalar pass so the raw `prices`
        // series (already handled as a chart above) isn't ALSO rendered as a
        // blank generic row list.
        for (const [k, v] of Object.entries(d)) {
            if (skip.has(k)) continue;
            if (!Array.isArray(v) || !v.length || typeof v[0] !== 'object') continue;
            const items = v.slice(0, 12).map(row => {
                const title = row.name || row.symbol || row.project || row.pool || '';
                const metricKey = ['depeg', 'apy', 'tvl_usd', 'vol_24h', 'fees_24h', 'circulating_usd', 'last_daily_volume']
                    .find(mk => row[mk] != null);
                const metric = metricKey ? `<span class="text-zinc-400 font-mono text-[11px] whitespace-nowrap">${escapeHtml(metricKey)}: ${fmt(row[metricKey])}</span>` : '';
                // yields' pool_url/project_url (worker/src/lib/defillama.ts::
                // yieldPools()) — a pool's `pool` id is an opaque UUID with no
                // other human-readable source, so without a link the buyer has
                // no way to verify a listed yield is real before depositing.
                // Any future row shape with a plain `url` (e.g. the hacks feed)
                // gets the same treatment for free.
                const linkUrl = safeHref(row.pool_url || row.project_url || row.url);
                const titleHtml = escapeHtml(title);
                const titleEl = linkUrl
                    ? `<a href="${escapeHtml(linkUrl)}" target="_blank" rel="noopener" class="truncate hover:underline">${titleHtml}</a>`
                    : `<span class="truncate">${titleHtml}</span>`;
                return `<div class="flex items-center justify-between gap-2 py-0.5"><span class="flex items-center min-w-0 text-xs text-zinc-200">${img(row.logo)}${titleEl}</span>${metric}</div>`;
            }).join('');
            rows.push(`<div class="mt-2"><div class="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">${escapeHtml(k)} (${v.length})</div>${items}</div>`);
        }
        return rows.join('') || `<pre class="text-[11px] text-zinc-400 whitespace-pre-wrap">${escapeHtml(JSON.stringify(d, null, 2))}</pre>`;
    },

    // token_chart's actual deliverable — a daily price series — rendered as a
    // real line chart on the '#hire-data-chart' canvas _dataHtml() leaves
    // behind. Mirrors app.js's _renderProtoChart styling. No-op (not an
    // error) for every other market-data tool, none of which return `prices`
    // as a timestamp/price series.
    _dataChart: null,
    _renderDataChart(prices) {
        if (this._dataChart) { this._dataChart.destroy(); this._dataChart = null; }
        if (!Array.isArray(prices) || !prices.length) return;
        const canvas = document.getElementById('hire-data-chart');
        if (!canvas || typeof Chart === 'undefined') return;
        const points = prices.filter(p => p && typeof p.price === 'number' && (p.timestamp || p.timestamp === 0));
        if (!points.length) return;
        const labels = points.map(p => new Date(p.timestamp * (p.timestamp < 1e12 ? 1000 : 1)).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
        const data = points.map(p => p.price);
        const g = canvas.getContext('2d').createLinearGradient(0, 0, 0, 160);
        g.addColorStop(0, 'rgba(74,222,128,0.30)'); g.addColorStop(1, 'rgba(74,222,128,0)');
        this._dataChart = new Chart(canvas, {
            type: 'line',
            data: { labels, datasets: [{ data, borderColor: '#4ade80', backgroundColor: g, fill: true, tension: 0.25, pointRadius: 0, borderWidth: 2 }] },
            options: {
                responsive: true, maintainAspectRatio: false, plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: c => `$${c.parsed.y.toLocaleString(undefined, { maximumFractionDigits: 6 })}` } },
                },
                scales: {
                    y: { ticks: { color: '#52525b', maxTicksLimit: 5 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    x: { ticks: { color: '#52525b', maxTicksLimit: 6 }, grid: { display: false } },
                },
            },
        });
    },
};

window.Hire = Hire;
