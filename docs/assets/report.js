// VAPE case-report PDF generator — client-side only, no server round-trip.
// Takes the real JSON a paid x402 offering (or the free preview) returned
// and lays it out as a letterheaded, hyperlinked report using jsPDF.
//
// Loaded via jsPDF's UMD build (plain <script> tag in index.html, same
// pattern as Chart.js) rather than `import()`-ing its ESM build from
// esm.sh: jsPDF's published ESM build has an unresolved bare `@babel/runtime`
// import that fails outside a real bundler — confirmed by testing it
// directly (Failed to resolve module specifier). The UMD build has no such
// issue and is what's actually loaded here, via `window.jspdf.jsPDF`.
import { knownIcon, tokenIconByAddress, resolveProtocolLogo } from './icons.js';

const ACCENT = [74, 222, 128];
const EMERALD = [16, 185, 129];
const AMBER = [251, 191, 36];
const ROSE = [251, 113, 133];
const INK = [24, 24, 27];
const MUTED = [113, 113, 122];

const VERDICT_LABELS = { PROCEED: "GO", CAUTION: "CAUTION", REJECT: "NO-GO", LOW: "LOW RISK", HIGH: "HIGH RISK", MEDIUM: "MEDIUM RISK", EXTREME: "EXTREME RISK" };

// Same abbreviation/sign-coloring convention app.js already uses for the
// site's live metrics strip, duplicated here (rather than imported) since
// report.js renders arbitrary deliverable JSON, not just app.js's own data.
function fmtUsdCompact(n) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    const v = Number(n);
    // Global crypto market cap runs into the trillions — app.js's own
    // metrics-strip formatter tops out at "B" because nothing it renders
    // gets that large, but a market_intel report's global_market_cap_usd
    // routinely does, so this needs the extra tier to stay legible.
    if (Math.abs(v) >= 1e12) return '$' + (v / 1e12).toFixed(2) + 'T';
    if (Math.abs(v) >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
    if (Math.abs(v) >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
    return '$' + v.toLocaleString();
}
function pctHtml(n) {
    if (typeof n !== 'number' || isNaN(n)) return '—';
    return `<span class="${n >= 0 ? 'text-emerald-400' : 'text-rose-400'}">${n >= 0 ? '+' : ''}${n.toFixed(2)}%</span>`;
}

function verdictColor(v) {
    if (v === "PROCEED" || v === "LOW" || v === "GO") return EMERALD;
    if (v === "CAUTION" || v === "MEDIUM") return AMBER;
    if (v === "REJECT" || v === "HIGH" || v === "EXTREME") return ROSE;
    return MUTED;
}

// Domain acronyms that should stay fully uppercase instead of Title Case
// ("tvl" -> "TVL", not "Tvl") — same list a reader would expect from any
// on-chain/finance report.
const ACRONYMS = new Set(['tvl', 'apy', 'apr', 'usd', 'eth', 'btc', 'nft', 'acp', 'pdf', 'url', 'id', 'dex', 'rpc', 'llm', 'ai', 'sla']);
// A handful of field names read better as a fixed phrase than anything the
// generic acronym/title-case rules below would produce.
const LABEL_OVERRIDES = { fear_greed: 'Fear & Greed Index' };
function humanLabel(key) {
    if (LABEL_OVERRIDES[key]) return LABEL_OVERRIDES[key];
    return key.replace(/_/g, ' ').replace(/\b\w+\b/g, w => ACRONYMS.has(w.toLowerCase()) ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1));
}

function basescanUrl(address) {
    return `https://basescan.org/address/${address}`;
}

// Deliverable JSON is real on-chain/API data, but individual fields (a
// token's name, a flag's free-text description) can themselves be
// attacker-influenced (e.g. a malicious token's on-chain name()) — same
// class of risk already handled in profile.js, so escape before innerHTML.
function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function verdictClass(v) {
    if (v === "PROCEED" || v === "LOW" || v === "GO") return 'border border-emerald-500 text-emerald-500';
    if (v === "CAUTION" || v === "MEDIUM") return 'border border-amber-400 text-amber-400';
    if (v === "REJECT" || v === "HIGH" || v === "EXTREME") return 'border border-rose-400 text-rose-400';
    return 'border border-white/20 text-zinc-300';
}

// `prices` ({ethereum, bitcoin, ...}) and `top_protocols` (string[]) are the
// two shapes market_intel actually returns with no address attached (see
// worker/src/lib/marketIntel.ts) — special-cased here so BTC/ETH and named
// Base protocols get their real logos instead of a plain text row. Protocol
// name -> logo needs a live DefiLlama lookup (no slug/logo in the raw
// deliverable), so those chips render icon-less first and are filled in by
// `enhanceIcons()` once the caller inserts this HTML into the DOM.
function renderDeliverableHtml(obj, depth = 0) {
    const skip = new Set(['flags', 'address', 'verdict', 'rug_risk', 'combined', 'token_verdict', 'name', 'symbol']);
    // A "<key>_classification" sibling (e.g. fear_greed / fear_greed_classification)
    // is a label for <key>'s value, not an independent fact — fold it into
    // one row instead of showing "Fear Greed 42" and "Fear Greed Classification
    // Fear" as two disconnected lines.
    for (const k of Object.keys(obj)) {
        if (k.endsWith('_classification') && obj[k.replace(/_classification$/, '')] !== undefined) {
            skip.add(k);
        }
    }
    return Object.entries(obj).filter(([k]) => depth > 0 || !skip.has(k)).map(([key, val]) => {
        const indent = depth ? `style="margin-left:${depth * 14}px"` : '';
        if (obj[`${key}_classification`] !== undefined && (typeof val === 'number' || typeof val === 'string')) {
            return `<div class="flex justify-between gap-3 text-xs py-1 border-b border-white/5" ${indent}>
                <span class="text-zinc-500 shrink-0">${escapeHtml(humanLabel(key))}</span>
                <span class="text-zinc-300 text-right">${escapeHtml(String(val))} · ${escapeHtml(String(obj[`${key}_classification`]))}</span>
            </div>`;
        }
        if (key === 'prices' && val !== null && typeof val === 'object' && !Array.isArray(val)) {
            return `<div class="mb-1.5" ${indent}>
                <div class="text-[11px] font-semibold text-zinc-300 mb-1">${escapeHtml(humanLabel(key))}</div>
                ${Object.entries(val).map(([sym, price]) => {
                    const icon = knownIcon(sym);
                    return `<div class="flex justify-between gap-3 text-xs py-1 border-b border-white/5">
                        <span class="text-zinc-500 shrink-0 flex items-center gap-1.5">${icon ? `<img src="${icon}" alt="" class="w-4 h-4 rounded-full shrink-0" onerror="this.remove()">` : ''}${escapeHtml(humanLabel(sym))}</span>
                        <span class="text-zinc-300 text-right">${price === null || price === undefined ? '—' : `$${price}`}</span>
                    </div>`;
                }).join('')}
            </div>`;
        }
        if (key === 'top_protocols' && Array.isArray(val)) {
            return `<div class="mb-1.5" ${indent}>
                <div class="text-[11px] font-semibold text-zinc-300 mb-1">${escapeHtml(humanLabel(key))}</div>
                <div class="flex flex-wrap gap-1.5">
                    ${val.map(name => `
                        <span class="protocol-chip inline-flex items-center gap-1.5 px-2 py-1 border border-white/10 text-xs text-zinc-300" data-protocol="${escapeHtml(String(name))}">
                            <img class="protocol-chip-icon w-3.5 h-3.5 rounded-full shrink-0" alt="" style="display:none" onerror="this.style.display='none'" onload="this.style.display=''">
                            ${escapeHtml(String(name))}
                        </span>`).join('')}
                </div>
            </div>`;
        }
        if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
            return `<div class="mb-1.5" ${indent}>
                <div class="text-[11px] font-semibold text-zinc-300 mb-1">${escapeHtml(humanLabel(key))}</div>
                ${renderDeliverableHtml(val, depth + 1)}
            </div>`;
        }
        // An array of OBJECTS (e.g. social_verification.checked's
        // {type,url,reachable,excerpt} entries) would otherwise fall through
        // to the plain-array branch below, whose val.join(', ') stringifies
        // each object as the literal text "[object Object]". Render each
        // item as its own nested field block instead.
        if (Array.isArray(val) && val.length && val.every(v => v !== null && typeof v === 'object' && !Array.isArray(v))) {
            return `<div class="mb-1.5" ${indent}>
                <div class="text-[11px] font-semibold text-zinc-300 mb-1">${escapeHtml(humanLabel(key))}</div>
                ${val.map(item => `<div class="pl-2 mb-1 border-l border-white/10">${renderDeliverableHtml(item, depth + 1)}</div>`).join('')}
            </div>`;
        }
        // A raw "-1.2" or "4300000000" reads as noise next to prose fields —
        // format percent/USD-suffixed numeric fields the same way the live
        // site's own metrics strip does, with a shortened, de-suffixed label
        // ("Base TVL 24H Change" rather than "Base Tvl 24h Change Pct").
        if (key.endsWith('_pct') && typeof val === 'number') {
            const label = humanLabel(key.replace(/_pct$/, ''));
            return `<div class="flex justify-between gap-3 text-xs py-1 border-b border-white/5" ${indent}>
                <span class="text-zinc-500 shrink-0">${escapeHtml(label)}</span>
                <span class="text-right">${pctHtml(val)}</span>
            </div>`;
        }
        // base_tvl (market_intel) is a real dollar figure but predates the
        // _usd-suffix convention the newer fields use — special-cased by
        // name rather than renamed, since that key is also embedded in
        // hundreds of already-published historical report snapshots this
        // repo never edits retroactively.
        if ((key.endsWith('_usd') || key === 'base_tvl') && (typeof val === 'number' || val === null)) {
            const label = humanLabel(key.replace(/_usd$/, ''));
            return `<div class="flex justify-between gap-3 text-xs py-1 border-b border-white/5" ${indent}>
                <span class="text-zinc-500 shrink-0">${escapeHtml(label)}</span>
                <span class="text-zinc-300 text-right">${fmtUsdCompact(val)}</span>
            </div>`;
        }
        const display = Array.isArray(val) ? val.join(', ') : (val === null || val === undefined ? '—' : String(val));
        // token_scan deliverables (token_safety_check) carry `symbol` alongside
        // `address`/`chain_id` at the same level — real per-token icon, same
        // DexScreener CDN already used for investigation/scan cards.
        const icon = key === 'symbol' && val ? (tokenIconByAddress(obj.address, obj.chain_id) || knownIcon(val)) : null;
        return `<div class="flex justify-between gap-3 text-xs py-1 border-b border-white/5" ${indent}>
            <span class="text-zinc-500 shrink-0">${escapeHtml(humanLabel(key))}</span>
            <span class="text-zinc-300 text-right break-all flex items-center gap-1.5 justify-end">${icon ? `<img src="${icon}" alt="" class="w-4 h-4 rounded-full shrink-0" onerror="this.remove()">` : ''}${escapeHtml(display)}</span>
        </div>`;
    }).join('');
}

const Report = {
    _jsPDF: null,
    async _load() {
        if (this._jsPDF) return this._jsPDF;
        // window.jspdf is set by the UMD <script> tag in index.html, a
        // classic script that always finishes before this module script
        // runs — but poll briefly anyway in case of unusual load ordering.
        for (let i = 0; i < 100 && !window.jspdf; i++) await new Promise(r => setTimeout(r, 50));
        if (!window.jspdf) throw new Error('jsPDF failed to load');
        this._jsPDF = window.jspdf.jsPDF;
        return this._jsPDF;
    },

    // opts: { offering, priceUsd, requestedAddress, hiredBy, result: {offering,status,deliverable,source,disclaimer}, via: 'x402'|'preview' }
    async build(opts) {
        const jsPDF = await this._load();
        const doc = new jsPDF({ unit: 'pt', format: 'letter' });
        const W = doc.internal.pageSize.getWidth();
        const margin = 48;
        let y = margin;

        // ── Letterhead ──────────────────────────────────────────────
        doc.setFillColor(9, 9, 11);
        doc.rect(0, 0, W, 96, 'F');
        try {
            const img = await this._loadImage('assets/vape-avatar.jpg');
            doc.addImage(img, 'JPEG', margin, 20, 56, 56, undefined, 'FAST');
        } catch (e) { /* letterhead still works without the portrait */ }
        doc.setTextColor(255, 255, 255);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(20);
        doc.text('V.A.P.E.', margin + 68, 46);
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(9);
        doc.setTextColor(...ACCENT);
        doc.text('ON-CHAIN INTELLIGENCE SYSTEM  ·  ERC-8004 #54988  ·  BASE', margin + 68, 62);
        doc.setTextColor(160, 160, 165);
        doc.textWithLink('github.com/jUXTAPOSITION1/V.A.P.E', margin + 68, 76, { url: 'https://github.com/jUXTAPOSITION1/V.A.P.E' });
        y = 128;

        // ── Title block ─────────────────────────────────────────────
        doc.setTextColor(...INK);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(16);
        doc.text('CASE REPORT', margin, y);
        y += 6;
        doc.setDrawColor(...ACCENT);
        doc.setLineWidth(1.5);
        doc.line(margin, y, margin + 90, y);
        y += 22;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
        doc.setTextColor(...MUTED);
        const generated = new Date().toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
        const pdfDeliverable = (opts.result && opts.result.deliverable) || {};
        const pdfTokenParts = [];
        if (pdfDeliverable.symbol) pdfTokenParts.push(`$${pdfDeliverable.symbol}`);
        const pdfTokenName = pdfDeliverable.name || pdfDeliverable.contract_name;
        if (pdfTokenName && pdfTokenName !== pdfDeliverable.symbol) pdfTokenParts.push(pdfTokenName);
        const rows = [
            ['Offering', humanLabel(opts.offering)],
            ...(pdfTokenParts.length ? [['Token', pdfTokenParts.join(' ')]] : []),
            ['Fulfillment', opts.via === 'x402' ? 'Paid via x402 (on-chain, real-time)' : 'Free preview scan'],
            ['Price', opts.priceUsd != null ? `$${opts.priceUsd}` : '—'],
            ['Target address', opts.requestedAddress || '—'],
            ['Hired by', opts.hiredBy || '—'],
            ['Generated', generated],
        ];
        rows.forEach(([k, v]) => {
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(...INK);
            doc.text(`${k}:`, margin, y);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(...MUTED);
            const isAddr = k === 'Target address' && v && v.startsWith('0x');
            if (isAddr) {
                doc.setTextColor(...ACCENT);
                doc.textWithLink(v, margin + 110, y, { url: basescanUrl(v) });
            } else {
                doc.text(String(v), margin + 110, y);
            }
            y += 16;
        });
        y += 8;

        // ── Verdict badge ───────────────────────────────────────────
        const deliverable = (opts.result && opts.result.deliverable) || {};
        const verdictField = deliverable.verdict || deliverable.rug_risk || deliverable.combined || deliverable.token_verdict;
        if (verdictField) {
            const c = verdictColor(verdictField);
            doc.setFillColor(...c);
            doc.roundedRect(margin, y, 140, 28, 5, 5, 'F');
            doc.setTextColor(9, 9, 11);
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(13);
            doc.text(VERDICT_LABELS[verdictField] || verdictField, margin + 70, y + 19, { align: 'center' });
            y += 44;
        }

        // ── Deliverable detail table ────────────────────────────────
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        doc.setTextColor(...INK);
        doc.text('FINDINGS', margin, y);
        y += 4;
        doc.setDrawColor(220, 220, 225);
        doc.setLineWidth(0.75);
        doc.line(margin, y, W - margin, y);
        y += 16;

        y = this._renderObject(doc, deliverable, margin, y, W - margin * 2);

        // ── Flags list, if present ──────────────────────────────────
        if (Array.isArray(deliverable.flags) && deliverable.flags.length) {
            y += 6;
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(10);
            doc.setTextColor(...INK);
            doc.text('Flags raised:', margin, y);
            y += 14;
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(9);
            deliverable.flags.forEach(f => {
                if (y > 720) { doc.addPage(); y = margin; }
                doc.setTextColor(...ROSE);
                doc.text('•', margin, y);
                doc.setTextColor(...MUTED);
                doc.text(String(f), margin + 12, y);
                y += 13;
            });
        }

        // ── Footer / disclaimer ──────────────────────────────────────
        const pages = doc.internal.getNumberOfPages();
        for (let p = 1; p <= pages; p++) {
            doc.setPage(p);
            const H = doc.internal.pageSize.getHeight();
            doc.setDrawColor(230, 230, 235);
            doc.setLineWidth(0.5);
            doc.line(margin, H - 56, W - margin, H - 56);
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(7.5);
            doc.setTextColor(...MUTED);
            const disclaimer = (opts.result && opts.result.disclaimer) || 'Real on-chain data. Not investment advice.';
            doc.text(disclaimer, margin, H - 42, { maxWidth: W - margin * 2 });
            doc.text(`VAPE Case Report · Page ${p} of ${pages} · Data source: ${(opts.result && opts.result.source) || 'vape-real-data'}`, margin, H - 28);
        }

        return doc;
    },

    _renderObject(doc, obj, x, y, maxWidth, depth = 0) {
        const H = doc.internal.pageSize.getHeight();
        // Skip fields already surfaced in the header block or verdict badge above.
        const skip = new Set(['flags', 'address', 'verdict', 'rug_risk', 'combined', 'token_verdict', 'name', 'symbol']);
        for (const [key, val] of Object.entries(obj)) {
            if (skip.has(key) && depth === 0) continue;
            if (y > H - 90) { doc.addPage(); y = 48; }
            if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(9.5);
                doc.setTextColor(...INK);
                doc.text(`${humanLabel(key)}:`, x + depth * 12, y);
                y += 14;
                y = this._renderObject(doc, val, x, y, maxWidth, depth + 1);
                continue;
            }
            // Same "[object Object]" risk as renderDeliverableHtml() above —
            // an array of objects (e.g. social_verification.checked) needs
            // its own nested rendering, not a plain join().
            if (Array.isArray(val) && val.length && val.every(v => v !== null && typeof v === 'object' && !Array.isArray(v))) {
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(9.5);
                doc.setTextColor(...INK);
                doc.text(`${humanLabel(key)}:`, x + depth * 12, y);
                y += 14;
                for (const item of val) {
                    y = this._renderObject(doc, item, x, y, maxWidth, depth + 1);
                }
                continue;
            }
            const display = Array.isArray(val) ? val.join(', ') : (val === null || val === undefined ? '—' : String(val));
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(9.5);
            doc.setTextColor(...INK);
            doc.text(`${humanLabel(key)}:`, x + depth * 12, y);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(...MUTED);
            const lines = doc.splitTextToSize(display, maxWidth - 150 - depth * 12);
            doc.text(lines, x + 150, y);
            y += 14 * Math.max(1, lines.length);
        }
        return y;
    },

    _loadImage(src) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = src;
        });
    },

    // Synchronous, no jsPDF dependency, no network — the actual report
    // content rendered as HTML, so it's visible immediately on payment
    // completion and in Case History regardless of whether the PDF/download
    // path works in a given browser (e.g. an in-app wallet webview that
    // blocks third-party CDN scripts or file downloads).
    buildHtmlSummary(opts) {
        const deliverable = (opts.result && opts.result.deliverable) || {};
        const verdictField = deliverable.verdict || deliverable.rug_risk || deliverable.combined || deliverable.token_verdict;
        const generated = new Date().toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
        const disclaimer = (opts.result && opts.result.disclaimer) || 'Real on-chain data. Not investment advice.';
        const source = (opts.result && opts.result.source) || 'vape-real-data';
        const addr = opts.requestedAddress;
        const addrHtml = addr ? `<a href="${escapeHtml(basescanUrl(addr))}" target="_blank" rel="noopener" class="text-zinc-300 hover:underline">${escapeHtml(addr)}</a>` : '—';
        const flags = Array.isArray(deliverable.flags) ? deliverable.flags : [];
        // Same real-token icon used for the `symbol` row above, surfaced once
        // more at the top of the card — the case-report equivalent of the
        // logo the user sees on every investigation/scan card elsewhere.
        const assetIcon = addr ? tokenIconByAddress(addr, deliverable.chain_id) : null;
        // Token identity (symbol + project name) belongs front-and-center next
        // to the icon, above the offering name — a buyer scans the card to
        // confirm "is this the token I paid to check" before anything else.
        const tokenSymbol = deliverable.symbol;
        const tokenName = deliverable.name || deliverable.contract_name;
        const identityParts = [];
        if (tokenSymbol) identityParts.push(`$${tokenSymbol}`);
        if (tokenName && tokenName !== tokenSymbol) identityParts.push(tokenName);
        const titleHtml = identityParts.length
            ? `<div class="min-w-0">
                    <div class="text-sm truncate">${escapeHtml(identityParts.join(' '))}</div>
                    <div class="text-[10px] text-zinc-500 truncate">${escapeHtml(humanLabel(opts.offering || ''))}</div>
                </div>`
            : `<div class="text-sm truncate">${escapeHtml(humanLabel(opts.offering || ''))}</div>`;
        return `
            <div class="text-left">
                <div class="flex items-center justify-between gap-3 mb-3">
                    <div class="flex items-center gap-2 min-w-0">
                        ${assetIcon ? `<img src="${assetIcon}" alt="" class="w-6 h-6 rounded-full shrink-0" onerror="this.remove()">` : ''}
                        ${titleHtml}
                    </div>
                    ${verdictField ? `<span class="inline-block px-3 py-1 text-xs shrink-0 ${verdictClass(verdictField)}">${escapeHtml(VERDICT_LABELS[verdictField] || verdictField)}</span>` : ''}
                </div>
                <div class="text-[11px] text-zinc-500 mb-3 space-y-0.5">
                    <div>Target: ${addrHtml}</div>
                    <div>${opts.via === 'x402' ? 'Paid via x402' : 'Free preview'} ${opts.priceUsd != null ? `· $${opts.priceUsd}` : ''} · ${escapeHtml(generated)}</div>
                </div>
                <div class="mb-2">${renderDeliverableHtml(deliverable)}</div>
                ${flags.length ? `
                    <div class="mt-2">
                        <div class="text-[11px] font-semibold text-zinc-300 mb-1">Flags raised</div>
                        ${flags.map(f => `<div class="text-xs text-rose-400 flex gap-1.5"><span>•</span><span class="text-zinc-400">${escapeHtml(String(f))}</span></div>`).join('')}
                    </div>` : ''}
                <div class="text-[10px] text-zinc-600 mt-3">${escapeHtml(disclaimer)} · Source: ${escapeHtml(source)}</div>
            </div>`;
    },

    // Fills in the `.protocol-chip-icon` placeholders left by
    // renderDeliverableHtml()'s `top_protocols` handling, once `container`
    // (the element the buildHtmlSummary() HTML was inserted into) is in the
    // DOM. Real logo or nothing — never a guessed icon, so a chip just stays
    // text-only if DefiLlama has no exact name match.
    async enhanceIcons(container) {
        if (!container) return;
        const chips = [...container.querySelectorAll('.protocol-chip[data-protocol]')];
        await Promise.all(chips.map(async chip => {
            const logo = await resolveProtocolLogo(chip.dataset.protocol);
            if (!logo) return;
            const img = chip.querySelector('.protocol-chip-icon');
            if (img) img.src = logo;
        }));
    },

    async downloadPdf(opts) {
        const doc = await this.build(opts);
        const shortAddr = (opts.requestedAddress || '').slice(0, 8);
        const stamp = new Date().toISOString().slice(0, 10);
        doc.save(`VAPE-${opts.offering}-${shortAddr}-${stamp}.pdf`);
    },
};

window.Report = Report;
