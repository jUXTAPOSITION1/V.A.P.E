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
const CYAN = [34, 211, 238];
const EMERALD = [16, 185, 129];
const AMBER = [251, 191, 36];
const ROSE = [251, 113, 133];
const INK = [24, 24, 27];
const MUTED = [113, 113, 122];

const VERDICT_LABELS = { PROCEED: "GO", CAUTION: "CAUTION", REJECT: "NO-GO", LOW: "LOW RISK", HIGH: "HIGH RISK", MEDIUM: "MEDIUM RISK", EXTREME: "EXTREME RISK" };

function verdictColor(v) {
    if (v === "PROCEED" || v === "LOW" || v === "GO") return EMERALD;
    if (v === "CAUTION" || v === "MEDIUM") return AMBER;
    if (v === "REJECT" || v === "HIGH" || v === "EXTREME") return ROSE;
    return MUTED;
}

function humanLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
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
    if (v === "PROCEED" || v === "LOW" || v === "GO") return 'bg-emerald-500/20 text-emerald-400';
    if (v === "CAUTION" || v === "MEDIUM") return 'bg-amber-500/20 text-amber-400';
    if (v === "REJECT" || v === "HIGH" || v === "EXTREME") return 'bg-rose-500/20 text-rose-400';
    return 'bg-white/10 text-zinc-300';
}

function renderDeliverableHtml(obj, depth = 0) {
    const skip = new Set(['flags', 'address', 'verdict', 'rug_risk', 'combined', 'token_verdict']);
    return Object.entries(obj).filter(([k]) => depth > 0 || !skip.has(k)).map(([key, val]) => {
        const indent = depth ? `style="margin-left:${depth * 14}px"` : '';
        if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
            return `<div class="mb-1.5" ${indent}>
                <div class="text-[11px] font-semibold text-zinc-300 mb-1">${escapeHtml(humanLabel(key))}</div>
                ${renderDeliverableHtml(val, depth + 1)}
            </div>`;
        }
        const display = Array.isArray(val) ? val.join(', ') : (val === null || val === undefined ? '—' : String(val));
        return `<div class="flex justify-between gap-3 text-xs py-1 border-b border-white/5" ${indent}>
            <span class="text-zinc-500 shrink-0">${escapeHtml(humanLabel(key))}</span>
            <span class="text-zinc-300 text-right break-all">${escapeHtml(display)}</span>
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
        doc.setTextColor(...CYAN);
        doc.text('AUTONOMOUS ON-CHAIN DETECTIVE  ·  ERC-8004 #54988  ·  BASE', margin + 68, 62);
        doc.setTextColor(160, 160, 165);
        doc.textWithLink('github.com/jUXTAPOSITION1/V.A.P.E', margin + 68, 76, { url: 'https://github.com/jUXTAPOSITION1/V.A.P.E' });
        y = 128;

        // ── Title block ─────────────────────────────────────────────
        doc.setTextColor(...INK);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(16);
        doc.text('CASE REPORT', margin, y);
        y += 6;
        doc.setDrawColor(...CYAN);
        doc.setLineWidth(1.5);
        doc.line(margin, y, margin + 90, y);
        y += 22;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
        doc.setTextColor(...MUTED);
        const generated = new Date().toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
        const rows = [
            ['Offering', humanLabel(opts.offering)],
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
                doc.setTextColor(...CYAN);
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
        const skip = new Set(['flags', 'address', 'verdict', 'rug_risk', 'combined', 'token_verdict']);
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
        const addrHtml = addr ? `<a href="${basescanUrl(addr)}" target="_blank" rel="noopener" class="text-cyan-400 hover:underline">${escapeHtml(addr)}</a>` : '—';
        const flags = Array.isArray(deliverable.flags) ? deliverable.flags : [];
        return `
            <div class="text-left">
                <div class="flex items-center justify-between gap-3 mb-3">
                    <div class="font-display text-sm">${escapeHtml(humanLabel(opts.offering || ''))}</div>
                    ${verdictField ? `<span class="inline-block px-3 py-1 rounded-lg font-display text-xs shrink-0 ${verdictClass(verdictField)}">${escapeHtml(VERDICT_LABELS[verdictField] || verdictField)}</span>` : ''}
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

    async downloadPdf(opts) {
        const doc = await this.build(opts);
        const shortAddr = (opts.requestedAddress || '').slice(0, 8);
        const stamp = new Date().toISOString().slice(0, 10);
        doc.save(`VAPE-${opts.offering}-${shortAddr}-${stamp}.pdf`);
    },
};

window.Report = Report;
