// VAPE case-report PDF generator — client-side only, no API key, no server
// round-trip. Takes the real JSON a paid x402 offering (or the free preview)
// returned and lays it out as a letterheaded, hyperlinked report using jsPDF
// (loaded from esm.sh, same zero-bundler pattern as wallet.js's connectors).
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

const Report = {
    _jsPDF: null,
    async _load() {
        if (this._jsPDF) return this._jsPDF;
        const mod = await import('https://esm.sh/jspdf@4.2.1');
        this._jsPDF = mod.jsPDF;
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

    async downloadPdf(opts) {
        const doc = await this.build(opts);
        const shortAddr = (opts.requestedAddress || '').slice(0, 8);
        const stamp = new Date().toISOString().slice(0, 10);
        doc.save(`VAPE-${opts.offering}-${shortAddr}-${stamp}.pdf`);
    },
};

window.Report = Report;
