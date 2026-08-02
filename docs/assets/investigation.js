// V.A.P.E full investigation report reader (investigation.html?file=<intel/
// investigations/investigation-*.md filename>). Fetches the real markdown
// report straight from GitHub raw content and renders it as a real, full
// page — reuses report.js's own markdown renderer (now with table support)
// rather than shipping a second one, and mirrors article.js's
// frontmatter-stripping approach for the investigation report format
// written by agents/investigate.py::write_report().
import { escapeHtml, simpleMarkdownToHtml } from './report.js';

const REPO = 'jUXTAPOSITION1/V.A.P.E';
const RAW = `https://raw.githubusercontent.com/${REPO}/main`;
const INV_DIR_RAW = `${RAW}/intel/investigations`;

// Mirrors agents/build_intel_index.py::_field() -- pulls a '**Label:**
// value' line out of the raw markdown VAPE's own report writer emits.
function field(text, label) {
    const re = new RegExp(`\\*?\\*?${label}\\*?\\*?\\s*[:：]\\s*(.+)`, 'i');
    const m = text.match(re);
    return m ? m[1].trim().replace(/^\*+|\*+$/g, '').trim() : null;
}

function firstHeading(text) {
    for (const line of text.split('\n')) {
        const s = line.trim();
        if (s.startsWith('#')) return s.replace(/^#+\s*/, '').trim();
    }
    return null;
}

// Strips the leading avatar/badge/metadata block (raw HTML + shields.io
// badges + Target/Chain/Date/Verdict bullets) so the body renderer only ever
// sees the real report sections (Executive Summary through the closing
// attribution line) — never the frontmatter re-rendered as a stray heading/
// paragraph. Rejoins the remaining sections with a blank line rather than a
// literal "---" (simpleMarkdownToHtml has no <hr> rule, so a bare "---"
// would otherwise render as visible dashes) — same convention as
// article.js's own bodyAfterFrontmatter().
function bodyAfterFrontmatter(text) {
    const parts = text.split(/^---$/m);
    return parts.length > 1 ? parts.slice(1).join('\n\n').trim() : text;
}

// Same 5-chain map + icon/explorer URL builders as app.js's intel explorer —
// duplicated here rather than imported since this page loads independently
// of app.js (matching article.js's own established pattern of small,
// page-local duplication instead of a shared client bundle).
const CHAIN_ID_MAP = { '1': 'ethereum', '8453': 'base', '42161': 'arbitrum', '10': 'optimism', '137': 'polygon', '56': 'bsc', '43114': 'avalanche' };
const EXPLORER_HOSTS = { arbitrum: 'arbiscan.io', ethereum: 'etherscan.io', optimism: 'optimistic.etherscan.io', polygon: 'polygonscan.com', bsc: 'bscscan.com', avalanche: 'snowtrace.io', base: 'basescan.org' };
function chainSlug(chain) {
    const m = String(chain || '').match(/\d+/);
    return (m && CHAIN_ID_MAP[m[0]]) || 'base';
}
function tokenIconUrl(address, chain) {
    if (!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) return null;
    return `https://dd.dexscreener.com/ds-data/tokens/${chainSlug(chain)}/${address.toLowerCase()}.png?size=lg`;
}
function explorerUrl(address, chain) {
    if (!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) return null;
    return `https://${EXPLORER_HOSTS[chainSlug(chain)] || 'basescan.org'}/address/${address}`;
}
function shortAddr(a) { return (a && a.length > 12) ? a.slice(0, 6) + '…' + a.slice(-4) : (a || ''); }

function verdictColor(v) {
    v = (v || '').toUpperCase();
    if (v === 'REJECT') return '#fb7185';
    if (v === 'CAUTION') return '#fbbf24';
    if (v === 'PROCEED') return '#10b981';
    return '#a1a1aa';
}

function renderError(msg) {
    document.getElementById('investigation-root').innerHTML = `
        <div class="text-center py-20">
            <i class="fa-solid fa-magnifying-glass-chart text-2xl mb-3 opacity-40 block"></i>
            <div class="text-zinc-400 text-sm">${escapeHtml(msg)}</div>
            <a href="index.html#the-archive" class="term-btn term-btn-sm inline-block mt-5">&larr; Back to The Archive</a>
        </div>`;
}

async function init() {
    const file = new URLSearchParams(window.location.search).get('file');
    if (!file || !/^investigation-[\w.-]+\.md$/.test(file)) {
        renderError('No investigation report specified.');
        return;
    }
    let text;
    try {
        const res = await fetch(`${INV_DIR_RAW}/${encodeURIComponent(file)}?t=${Date.now()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        text = await res.text();
    } catch (e) {
        renderError('This report could not be loaded. It may have been moved or the archive is briefly unreachable.');
        return;
    }

    const title = firstHeading(text) || 'Investigation';
    const symMatch = title.match(/Investigation\s*[—-]\s*(.+)$/);
    const symbol = symMatch ? symMatch[1].trim() : null;
    const target = (field(text, 'Target') || '').replace(/[`*]/g, '').trim() || null;
    const chain = (field(text, 'Chain') || '').replace(/[`*]/g, '').trim() || null;
    const dateStr = field(text, 'Date');
    const verdictRaw = field(text, 'Verdict') || '';
    const verdictMatch = verdictRaw.match(/(PROCEED|CAUTION|REJECT)/i);
    const verdict = verdictMatch ? verdictMatch[1].toUpperCase() : null;
    const scoreMatch = verdictRaw.match(/\((\d{1,3})\s*\/\s*100\)/);
    const score = scoreMatch ? scoreMatch[1] : null;

    document.title = `${symbol || shortAddr(target) || 'Investigation'}: V.A.P.E Investigation Report`;
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc && verdict) metaDesc.setAttribute('content', `V.A.P.E deep investigation: ${verdict}${score ? ` (${score}/100)` : ''}.`);

    const icon = tokenIconUrl(target, chain);
    const explorer = explorerUrl(target, chain);
    const heading = symbol || shortAddr(target) || title;
    const vColor = verdictColor(verdict);

    const bodyHtml = simpleMarkdownToHtml(bodyAfterFrontmatter(text));

    document.getElementById('investigation-root').innerHTML = `
        <a href="index.html#the-archive" class="text-xs text-zinc-500 hover:text-zinc-200 transition inline-flex items-center gap-1.5 mb-6">
            <i class="fa-solid fa-arrow-left text-[10px]"></i> Back to The Archive
        </a>
        <div class="inv-header">
            ${icon
                ? `<img src="${escapeHtml(icon)}" alt="" class="inv-icon" onerror="this.outerHTML='<div class=&quot;inv-icon-fallback&quot;><i class=&quot;fa-solid fa-magnifying-glass-chart&quot;></i></div>'">`
                : `<div class="inv-icon-fallback"><i class="fa-solid fa-magnifying-glass-chart"></i></div>`}
            <div class="min-w-0 flex-1">
                <div class="text-[10px] uppercase tracking-widest text-[#60a5fa] flex items-center gap-1.5 mb-1"><i class="fa-solid fa-magnifying-glass-chart"></i> Deep Investigation</div>
                <h1 class="article-headline !mb-1 !text-2xl sm:!text-3xl">${escapeHtml(heading)}</h1>
                <div class="inv-meta-row">
                    ${verdict ? `<span class="px-2 py-0.5 border text-[11px] whitespace-nowrap" style="color:${vColor};border-color:${vColor}">${escapeHtml(verdict)}${score ? ` ${escapeHtml(score)}/100` : ''}</span>` : ''}
                    ${target ? `<a href="${explorer || '#'}" target="_blank" rel="noopener" class="font-mono hover:text-zinc-200 ${explorer ? '' : 'pointer-events-none'}" title="${escapeHtml(target)}">${escapeHtml(shortAddr(target))} ${explorer ? '<i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-60"></i>' : ''}</a>` : ''}
                    ${dateStr ? `<span>${escapeHtml(dateStr)}</span>` : ''}
                </div>
            </div>
        </div>
        <article class="article-body">${bodyHtml}</article>
    `;
}

document.addEventListener('DOMContentLoaded', init);
