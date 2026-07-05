// VAPE shared icon resolver — real, official logos only. Never a guessed or
// synthetic image URL: if we can't confirm the source, we show no icon
// rather than risk showing the wrong project's mark.
//
// Three tiers, in order of reliability:
//   1. KNOWN_ICONS  — a small, hand-verified table for assets that appear in
//      almost every report (BTC, ETH, USDC, Base, Uniswap, VAPE's own
//      token). Sourced from CoinGecko's public asset CDN and Base's own
//      brand assets — stable, official, and used unauthenticated across the
//      industry for exactly this purpose.
//   2. tokenIconByAddress() — for any token with a real contract address,
//      DexScreener's per-chain token-image CDN (same pattern already used
//      for investigation/scan cards elsewhere on this site).
//   3. resolveProtocolLogo() — for a named DeFi protocol with no address in
//      hand (e.g. market_intel's `top_protocols: string[]`), match the name
//      against DefiLlama's live `/protocols` list (the same list the Live
//      Intelligence Feed section already renders) and reuse its `.logo`
//      field. Only an exact, case-insensitive name match qualifies — no
//      fuzzy matching, so a near-miss never shows an unrelated logo.

export const KNOWN_ICONS = {
    bitcoin: 'https://assets.coingecko.com/coins/images/1/small/bitcoin.png',
    btc: 'https://assets.coingecko.com/coins/images/1/small/bitcoin.png',
    ethereum: 'https://assets.coingecko.com/coins/images/279/small/ethereum.png',
    eth: 'https://assets.coingecko.com/coins/images/279/small/ethereum.png',
    usdc: 'https://assets.coingecko.com/coins/images/6319/small/usdc.png',
    usdt: 'https://assets.coingecko.com/coins/images/325/small/Tether.png',
    base: 'https://raw.githubusercontent.com/base-org/brand-kit/main/logo/symbol/Base_Symbol_Blue.svg',
    uniswap: 'https://assets.coingecko.com/coins/images/12504/small/uni.jpg',
    virtual: 'https://assets.coingecko.com/coins/images/33409/small/GF6TSSro_400x400.jpg',
};

const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

export function chainSlug(chain) {
    const s = String(chain || '');
    if (/42161|arbitrum/i.test(s)) return 'arbitrum';
    if (/^1$|ethereum/i.test(s)) return 'ethereum';
    return 'base';
}

export function tokenIconByAddress(address, chain) {
    if (!address || !ADDRESS_RE.test(address)) return null;
    return `https://dd.dexscreener.com/ds-data/tokens/${chainSlug(chain)}/${address.toLowerCase()}.png?size=lg`;
}

// Symbol/name -> known logo, case-insensitive, no fuzzy matching.
export function knownIcon(label) {
    if (!label) return null;
    const key = String(label).trim().toLowerCase();
    return KNOWN_ICONS[key] || null;
}

let _protocolLogoPromise = null;
async function _loadProtocolLogos() {
    if (!_protocolLogoPromise) {
        _protocolLogoPromise = fetch('https://api.llama.fi/protocols')
            .then(r => r.json())
            .then(list => {
                const map = new Map();
                (Array.isArray(list) ? list : []).forEach(p => {
                    if (p && p.name && p.logo) map.set(String(p.name).toLowerCase(), p.logo);
                });
                return map;
            })
            .catch(() => new Map());
    }
    return _protocolLogoPromise;
}

// Async, best-effort, cached for the page's lifetime — exact name match only.
export async function resolveProtocolLogo(name) {
    if (!name) return null;
    const map = await _loadProtocolLogos();
    return map.get(String(name).trim().toLowerCase()) || null;
}
