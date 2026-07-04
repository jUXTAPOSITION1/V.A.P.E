// VAPE hire flow — x402 (real, in-browser, instant) and ACP (links out to the
// real Virtuals job flow, since ACP job creation needs Privy + Alchemy
// Account Kit smart accounts that this zero-bundler site doesn't run).
const ACP_AGENT_URL = 'https://app.virtuals.io/acp/agent/019eaf60-592a-7f5c-99a2-3e85199303fe';
const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

const Hire = {
    _modal: null,

    openAcp(offeringName) {
        window.open(ACP_AGENT_URL, '_blank', 'noopener');
    },

    openX402(offeringName, priceUsd) {
        this._closeModal();
        const needsAddress = offeringName !== 'market_intel';
        const modal = document.createElement('div');
        modal.id = 'hire-modal';
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" data-close></div>
            <div class="relative glass rounded-2xl p-6 w-full max-w-md">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-display text-lg flex items-center gap-2"><i class="fa-solid fa-bolt text-cyan-400"></i> Hire VAPE</h3>
                    <button data-close class="text-zinc-500 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div id="hire-body">
                    <div class="text-sm text-zinc-400 mb-1">${offeringName.replace(/_/g,' ')} <span class="text-cyan-400 font-mono">$${priceUsd}</span></div>
                    <p class="text-xs text-zinc-500 mb-4">Pays via x402: your wallet signs a gasless USDC authorization for the exact price above — no gas fee, no subscription, settles on Base mainnet.</p>
                    ${needsAddress ? `
                    <label class="text-xs text-zinc-500 block mb-1">Target contract address</label>
                    <input id="hire-address" type="text" placeholder="0x… token/contract to investigate" class="w-full bg-zinc-900/80 border border-white/10 focus:border-cyan-500 outline-none px-3 py-2 rounded-lg text-xs font-mono mb-4">
                    ` : '<div class="mb-4"></div>'}
                    <button id="hire-submit" class="w-full bg-cyan-600 hover:bg-cyan-500 transition px-4 py-2.5 rounded-xl font-display text-sm">Pay & Run</button>
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
            if (!res.ok) throw new Error(`Worker returned ${res.status}`);
            const result = await res.json();
            this._renderResult(offeringName, priceUsd, address, result);
        } catch (e) {
            const msg = (e && e.message) || String(e);
            set(`Payment failed: ${msg.slice(0, 200)}`, 'text-rose-400');
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50');
        }
    },

    async _renderResult(offeringName, priceUsd, address, result) {
        const body = document.getElementById('hire-body');
        if (!body) return;
        const deliverable = result.deliverable || {};
        const verdict = deliverable.verdict || deliverable.rug_risk || deliverable.combined || deliverable.token_verdict;
        const walletAddress = Wallet.state().account;
        if (window.CaseHistory && walletAddress) {
            CaseHistory.save({ offering: offeringName, priceUsd, via: 'x402', walletAddress, targetAddress: address, verdict, result });
        }
        const reportOpts = { offering: offeringName, priceUsd, requestedAddress: address, hiredBy: walletAddress, result, via: 'x402' };
        body.innerHTML = `
            <div class="text-center mb-4">
                <i class="fa-solid fa-circle-check text-emerald-400 text-3xl mb-2"></i>
                <div class="font-display text-lg">Paid & delivered</div>
                <div class="text-xs text-zinc-500">${offeringName.replace(/_/g,' ')} · $${priceUsd} settled on Base</div>
            </div>
            ${verdict ? `<div class="text-center mb-4"><span class="inline-block px-4 py-1.5 rounded-lg font-display text-sm bg-white/10">${verdict}</span></div>` : ''}
            <div class="flex gap-2">
                <button id="hire-download" class="flex-1 bg-cyan-600 hover:bg-cyan-500 transition px-4 py-2.5 rounded-xl font-display text-sm"><i class="fa-solid fa-file-pdf"></i> Download PDF</button>
                <button id="hire-copy" class="flex-1 bg-white/10 hover:bg-white/15 transition px-4 py-2.5 rounded-xl font-display text-sm"><i class="fa-solid fa-copy"></i> Copy JSON</button>
            </div>
            <div id="hire-copy-status" class="text-xs text-zinc-500 mt-3 text-center">Generating your case report…</div>
            <div class="text-[11px] text-zinc-600 mt-3 text-center">Also saved to your Case History in "Your Case File" below.</div>`;
        document.getElementById('hire-download').onclick = () => Report.downloadPdf(reportOpts);
        document.getElementById('hire-copy').onclick = async () => {
            await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
            document.getElementById('hire-copy-status').textContent = 'Copied raw JSON to clipboard.';
        };
        // Auto-download the PDF the moment the case is delivered, so the
        // deliverable populates immediately rather than waiting on a second
        // click — the manual button above still works for re-downloading.
        const status = document.getElementById('hire-copy-status');
        try {
            await Report.downloadPdf(reportOpts);
            if (status) status.textContent = 'PDF downloaded automatically — use the button above to get it again.';
        } catch (e) {
            if (status) status.textContent = 'Auto-download failed — use the "Download PDF" button above.';
        }
    },
};

window.Hire = Hire;
