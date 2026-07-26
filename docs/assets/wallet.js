// VAPE wallet connect — vanilla JS, no bundler. EIP-6963 multi-injected-wallet
// discovery (MetaMask, Coinbase extension, Rabby, etc.) + Coinbase Wallet SDK
// (mobile/non-extension) + WalletConnect (everything else, QR/mobile).
//
// Project ID from https://cloud.reown.com — public identifier, safe to embed
// client-side (identifies the app to the relay network, no auth power).
const WALLETCONNECT_PROJECT_ID = '624e168bc87a042f6e09ec7301ea357d';

// EIP-6963 `info` (name/icon/uuid) is announced by whatever browser extension
// dispatches the event — a malicious or compromised extension can spoof it to
// impersonate a real wallet, so treat it exactly like any other untrusted
// external string and escape before it goes into innerHTML (same pattern used
// throughout report.js/hire.js/profile.js for on-chain-sourced text).
function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

const BASE_CHAIN_HEX = '0x2105'; // 8453
const BASE_PARAMS = {
    chainId: BASE_CHAIN_HEX,
    chainName: 'Base',
    nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    rpcUrls: ['https://mainnet.base.org'],
    blockExplorerUrls: ['https://basescan.org'],
};

const Wallet = {
    _providers: new Map(), // uuid -> {info, provider}
    _active: null,         // { provider, connectorType, uuid? }
    _account: null,
    _chainId: null,
    _listeners: [],

    onChange(cb) { this._listeners.push(cb); },
    _emit() { this._listeners.forEach(cb => { try { cb(this.state()); } catch (e) {} }); },
    state() { return { account: this._account, chainId: this._chainId, connected: !!this._account }; },
    // Raw EIP-1193 provider for the active connection — needed by hire.js to
    // build a viem WalletClient for EIP-712 signing (x402 payment authorization).
    getProvider() { return this._active?.provider || null; },

    init() {
        window.addEventListener('eip6963:announceProvider', (e) => {
            const { info, provider } = e.detail || {};
            if (info && provider) this._providers.set(info.uuid, { info, provider });
        });
        window.dispatchEvent(new Event('eip6963:requestProvider'));
        this._renderConnectButton();
        this._tryEagerReconnect();
    },

    async _tryEagerReconnect() {
        const saved = localStorage.getItem('vape_wallet_connector');
        if (!saved) return;
        // small delay so eip6963 announcements land first
        await new Promise(r => setTimeout(r, 200));
        try {
            if (saved === 'injected') {
                const legacy = window.ethereum;
                const first = [...this._providers.values()][0];
                const provider = first ? first.provider : legacy;
                if (!provider) return;
                const accounts = await provider.request({ method: 'eth_accounts' });
                if (accounts && accounts[0]) await this._bind(provider, 'injected', accounts[0]);
            }
            // Coinbase/WalletConnect SDKs restore their own sessions on reconnect;
            // left inert here — activated explicitly on next §3/§7 pass if needed.
        } catch (e) { /* silent — no popup on load */ }
    },

    async _bind(provider, connectorType, account) {
        // `account` comes straight from the provider's own eth_requestAccounts
        // response. A real wallet always returns a well-formed address, but the
        // "provider" itself can be a spoofed EIP-6963 announcement (see the
        // escapeHtml note above) — its `request()` is attacker-controlled JS
        // that could return any string. This value is rendered unescaped as
        // text and inside href/aria-label attributes in several places below,
        // so reject anything that isn't a real address before trusting it.
        if (!ADDRESS_RE.test(account || '')) {
            console.error('[wallet] provider returned a malformed account, refusing to connect:', account);
            alert('This wallet returned an invalid account and was not connected.');
            return;
        }
        this._active = { provider, connectorType };
        this._account = account;
        try {
            this._chainId = parseInt(await provider.request({ method: 'eth_chainId' }), 16);
        } catch (e) { this._chainId = null; }
        localStorage.setItem('vape_wallet_connector', connectorType);
        provider.on?.('accountsChanged', (accs) => {
            const next = accs[0] || null;
            if (next && !ADDRESS_RE.test(next)) {
                console.error('[wallet] accountsChanged returned a malformed account, disconnecting:', next);
                this.disconnect();
                return;
            }
            this._account = next;
            if (!this._account) this.disconnect();
            else { this._renderConnectButton(); this._emit(); }
        });
        provider.on?.('chainChanged', (hex) => {
            this._chainId = parseInt(hex, 16);
            this._renderConnectButton();
            this._emit();
        });
        this._renderConnectButton();
        this._emit();
    },

    async connectInjected(uuid) {
        const entry = uuid ? this._providers.get(uuid) : [...this._providers.values()][0];
        const provider = entry ? entry.provider : window.ethereum;
        if (!provider) { alert('No injected wallet found. Install MetaMask or another browser wallet extension.'); return; }
        const accounts = await provider.request({ method: 'eth_requestAccounts' });
        await this._bind(provider, 'injected', accounts[0]);
        this._closePopover();
    },

    async connectCoinbase() {
        try {
            const { default: CoinbaseWalletSDK } = await import('https://esm.sh/@coinbase/wallet-sdk@4');
            const sdk = new CoinbaseWalletSDK({ appName: 'VAPE', appLogoUrl: 'https://juxtaposition1.github.io/V.A.P.E/assets/apple-touch-icon.png' });
            const provider = sdk.makeWeb3Provider({ options: 'smartWalletOnly' });
            const accounts = await provider.request({ method: 'eth_requestAccounts' });
            await this._bind(provider, 'coinbase', accounts[0]);
        } catch (e) {
            console.error('[wallet] Coinbase Wallet connect failed', e);
            alert('Coinbase Wallet connect failed — see console for details.');
        }
        this._closePopover();
    },

    async connectWalletConnect() {
        if (!WALLETCONNECT_PROJECT_ID) {
            alert('WalletConnect needs a Project ID (free at cloud.reown.com) — not configured yet. Use an injected wallet or Coinbase Wallet for now.');
            return;
        }
        try {
            const { EthereumProvider } = await import('https://esm.sh/@walletconnect/ethereum-provider@2');
            const provider = await EthereumProvider.init({
                projectId: WALLETCONNECT_PROJECT_ID,
                chains: [8453],
                showQrModal: true,
                metadata: {
                    name: 'VAPE',
                    description: 'Autonomous on-chain intelligence system for Base & Virtuals',
                    url: 'https://juxtaposition1.github.io/V.A.P.E/',
                    icons: ['https://juxtaposition1.github.io/V.A.P.E/assets/apple-touch-icon.png'],
                },
            });
            await provider.connect();
            await this._bind(provider, 'walletconnect', provider.accounts[0]);
        } catch (e) {
            console.error('[wallet] WalletConnect connect failed', e);
            alert('WalletConnect connect failed — see console for details.');
        }
        this._closePopover();
    },

    async ensureBase() {
        if (!this._active) return false;
        if (this._chainId === 8453) return true;
        try {
            await this._active.provider.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: BASE_CHAIN_HEX }] });
            return true;
        } catch (err) {
            if (err && err.code === 4902) {
                try {
                    await this._active.provider.request({ method: 'wallet_addEthereumChain', params: [BASE_PARAMS] });
                    return true;
                } catch (e2) { return false; }
            }
            return false;
        }
    },

    disconnect() {
        try { this._active?.provider?.disconnect?.(); } catch (e) {}
        this._active = null;
        this._account = null;
        this._chainId = null;
        localStorage.removeItem('vape_wallet_connector');
        this._renderConnectButton();
        this._emit();
    },

    _short(a) { return a ? a.slice(0, 6) + '…' + a.slice(-4) : ''; },

    _closePopover() { document.getElementById('wallet-popover')?.remove(); },

    _renderConnectButton() {
        const root = document.getElementById('wallet-area');
        if (!root) return;
        if (this._account) {
            const onBase = this._chainId === 8453;
            root.innerHTML = `
                <div class="relative">
                    <button id="wallet-chip-btn" class="wallet-chip px-3 py-1.5 flex items-center gap-2 text-xs" aria-label="${onBase ? `Connected wallet ${this._account}, on Base. Click to disconnect.` : `Connected wallet ${this._account}, wrong network. Click to switch to Base.`}">
                        <span class="w-2 h-2 rounded-full ${onBase ? 'bg-emerald-500' : 'bg-amber-400 chain-badge-warn'}" aria-hidden="true"></span>
                        <span class="font-mono">${this._short(this._account)}</span>
                        ${onBase ? '' : '<span class="text-amber-400">Switch to Base</span>'}
                        <i class="fa-solid fa-chevron-down text-[9px] opacity-60" aria-hidden="true"></i>
                    </button>
                </div>`;
            document.getElementById('wallet-chip-btn').onclick = async (e) => {
                if (!onBase) { await this.ensureBase(); return; }
                this._openAccountPopover(e.currentTarget);
            };
        } else {
            root.innerHTML = `<button id="wallet-connect-btn" class="term-btn term-btn-sm" aria-label="Connect a wallet" aria-haspopup="true">
                <i class="fa-solid fa-wallet" aria-hidden="true"></i> Connect
            </button>`;
            document.getElementById('wallet-connect-btn').onclick = (e) => this._openPopover(e.currentTarget);
        }
    },

    // Popovers are appended to <body> (so they aren't clipped by any
    // ancestor's overflow/backdrop-filter stacking context) and positioned
    // with `fixed` using the anchor's live viewport rect — `absolute` here
    // would resolve against the initial containing block (the very top of
    // the whole document, not the viewport), so opening the wallet menu
    // after scrolling down rendered the popover off-screen above the fold.
    _placeNearAnchor(pop, anchor) {
        const r = anchor.getBoundingClientRect();
        pop.style.position = 'fixed';
        pop.style.top = `${r.bottom + 8}px`;
        pop.style.right = `${Math.max(8, window.innerWidth - r.right)}px`;
    },

    async _openAccountPopover(anchor) {
        this._closePopover();
        const pop = document.createElement('div');
        pop.id = 'wallet-popover';
        pop.className = 'popover p-4 w-72 max-w-[calc(100vw-2rem)] z-50 text-zinc-200';
        pop.innerHTML = `
            <div class="flex items-center gap-2 mb-3">
                <span class="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>
                <span class="font-mono text-xs break-all">${this._account}</span>
            </div>
            <div class="grid grid-cols-2 gap-2 mb-3">
                <div class="border border-white/10 p-2.5">
                    <div class="text-[10px] uppercase tracking-wider text-zinc-500">Balance</div>
                    <div id="wallet-pop-balance" class="text-sm mt-0.5"><i class="fa-solid fa-spinner fa-spin text-xs"></i></div>
                </div>
                <div class="border border-white/10 p-2.5">
                    <div class="text-[10px] uppercase tracking-wider text-zinc-500">Network</div>
                    <div class="text-sm mt-0.5 text-emerald-500">Base</div>
                </div>
            </div>
            <div class="flex flex-col gap-1.5">
                <button id="wallet-pop-case-file" class="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/10 text-left text-sm"><i class="fa-solid fa-id-card-clip w-5 text-center text-zinc-400"></i> View portfolio</button>
                <button id="wallet-pop-copy" class="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/10 text-left text-sm"><i class="fa-solid fa-copy w-5 text-center"></i> Copy address</button>
                <a href="https://basescan.org/address/${this._account}" target="_blank" rel="noopener" class="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/10 text-left text-sm"><i class="fa-solid fa-arrow-up-right-from-square w-5 text-center"></i> View on block explorer</a>
                <button id="wallet-pop-disconnect" class="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/10 text-left text-sm text-rose-400"><i class="fa-solid fa-right-from-bracket w-5 text-center"></i> Disconnect</button>
            </div>`;
        document.body.appendChild(pop);
        this._placeNearAnchor(pop, anchor);
        document.getElementById('wallet-pop-case-file').onclick = () => {
            this._closePopover();
            document.getElementById('your-case-file')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        };
        document.getElementById('wallet-pop-copy').onclick = async () => {
            await navigator.clipboard.writeText(this._account);
            const btn = document.getElementById('wallet-pop-copy');
            btn.innerHTML = '<i class="fa-solid fa-check w-5 text-center text-emerald-500"></i> Copied!';
        };
        document.getElementById('wallet-pop-disconnect').onclick = () => { this._closePopover(); this.disconnect(); };
        setTimeout(() => {
            document.addEventListener('click', function closeOnce(e) {
                if (!pop.contains(e.target) && e.target !== anchor) { pop.remove(); document.removeEventListener('click', closeOnce); }
            });
        }, 0);

        // Quick balance read — public RPC, same source as the rest of the site.
        try {
            const r = await fetch('https://mainnet.base.org', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: '2.0', method: 'eth_getBalance', params: [this._account, 'latest'], id: 1 }),
            }).then(r => r.json());
            const eth = parseInt(r.result, 16) / 1e18;
            const el = document.getElementById('wallet-pop-balance');
            if (el) el.textContent = `${eth < 0.0001 && eth > 0 ? '<0.0001' : eth.toFixed(4)} ETH`;
        } catch (e) {
            const el = document.getElementById('wallet-pop-balance');
            if (el) el.textContent = '—';
        }
    },

    _openPopover(anchor) {
        this._closePopover();
        const discovered = [...this._providers.values()];
        const rows = discovered.length
            ? discovered.map(({ info }) => `<button data-uuid="${escapeHtml(info.uuid)}" class="wc-injected w-full flex items-center gap-2 px-3 py-2 hover:bg-white/10 text-left text-sm">
                    <img src="${escapeHtml(info.icon)}" alt="" class="w-5 h-5 rounded" onerror="this.remove()"> ${escapeHtml(info.name)}
                </button>`).join('')
            : `<button data-uuid="" class="wc-injected w-full flex items-center gap-2 px-3 py-2 hover:bg-white/10 text-left text-sm">
                    <i class="fa-solid fa-plug w-5 text-center"></i> Browser wallet
                </button>`;
        const pop = document.createElement('div');
        pop.id = 'wallet-popover';
        pop.className = 'popover p-2 w-64 max-w-[calc(100vw-2rem)] z-50 text-zinc-200';
        pop.innerHTML = `
            <div class="text-[10px] uppercase tracking-widest text-zinc-500 px-3 py-1.5">Detected</div>
            ${rows}
            <div class="text-[10px] uppercase tracking-widest text-zinc-500 px-3 py-1.5 mt-1">Other</div>
            <button id="wc-coinbase" class="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/10 text-left text-sm"><i class="fa-solid fa-circle w-5 text-center text-zinc-400"></i> Coinbase Wallet</button>
            <button id="wc-walletconnect" class="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/10 text-left text-sm"><i class="fa-solid fa-qrcode w-5 text-center text-zinc-400"></i> WalletConnect</button>
        `;
        document.body.appendChild(pop);
        this._placeNearAnchor(pop, anchor);
        pop.querySelectorAll('.wc-injected').forEach(btn => btn.onclick = () => this.connectInjected(btn.dataset.uuid || undefined));
        document.getElementById('wc-coinbase').onclick = () => this.connectCoinbase();
        document.getElementById('wc-walletconnect').onclick = () => this.connectWalletConnect();
        setTimeout(() => {
            document.addEventListener('click', function closeOnce(e) {
                if (!pop.contains(e.target) && e.target !== anchor) { pop.remove(); document.removeEventListener('click', closeOnce); }
            });
        }, 0);
    },
};

window.Wallet = Wallet;
window.addEventListener('DOMContentLoaded', () => Wallet.init());
