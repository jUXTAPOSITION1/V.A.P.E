// Main-site preview of the full Investigations page (investigations.html) —
// reuses that page's own row markup, sparkline renderer, and range-toggle
// wiring (investigations-ledger.js) rather than re-implementing a
// lookalike, so the preview can never visually drift from the real page.
// Shows the same stat line + activity sparkline (day/week/month/all-time)
// + the most recent handful of investigations, then sends the reader to
// investigations.html for the full record and the interactive Verdict
// Breakdown (a preview section has no room to reproduce that safely).
import { investigationRowHtml, wireSparkRangeToggle, wireRowNavigation } from './investigations-ledger.js?v=1';

const REPO = 'jUXTAPOSITION1/V.A.P.E';
const INTEL_INDEX_URL = `https://raw.githubusercontent.com/${REPO}/main/data/intel-index.json`;
const PREVIEW_COUNT = 6;

const InvestigationsPreview = {
    _all: [],

    async init() {
        try {
            // No cache-buster here -- this preview only ever needs the same
            // freshness the rest of the main site's fetches settle for, and
            // letting the browser serve a recent cached copy on repeat
            // visits avoids re-downloading the full multi-hundred-KB index
            // just to render 6 rows.
            const data = await (await fetch(INTEL_INDEX_URL)).json();
            this._all = Array.isArray(data.investigations) ? data.investigations.slice() : [];
        } catch (e) {
            const body = document.getElementById('invp-body');
            if (body) body.innerHTML = '<tr><td colspan="6" class="text-zinc-500 text-xs py-6 text-center">Investigations index is briefly unreachable.</td></tr>';
            const updated = document.getElementById('invp-updated');
            if (updated) updated.textContent = 'unavailable';
            ['invp-total', 'invp-reject', 'invp-caution', 'invp-proceed', 'invp-avg-score'].forEach(id => {
                const el = document.getElementById(id);
                if (el) { el.classList.remove('skeleton'); el.textContent = '—'; }
            });
            return;
        }
        const updated = document.getElementById('invp-updated');
        if (updated) updated.textContent = this._all.length ? `${this._all.length.toLocaleString()} on record` : 'no investigations yet';
        this._renderStats();
        this._renderTable();
        wireSparkRangeToggle(document.getElementById('invp-spark-range'), document.getElementById('invp-spark'), () => this._all, 'all');
    },

    _renderStats() {
        const counts = { REJECT: 0, CAUTION: 0, PROCEED: 0 };
        let scoreSum = 0, scoreN = 0;
        this._all.forEach(inv => {
            const v = (inv.verdict || '').toUpperCase();
            if (counts[v] !== undefined) counts[v]++;
            const s = Number(inv.score);
            if (!isNaN(s)) { scoreSum += s; scoreN++; }
        });
        const set = (id, v) => { const e = document.getElementById(id); if (e) { e.classList.remove('skeleton'); e.textContent = v; } };
        set('invp-total', this._all.length.toLocaleString());
        set('invp-reject', counts.REJECT.toLocaleString());
        set('invp-caution', counts.CAUTION.toLocaleString());
        set('invp-proceed', counts.PROCEED.toLocaleString());
        set('invp-avg-score', scoreN ? Math.round(scoreSum / scoreN) + '/100' : '…');
    },

    _renderTable() {
        const body = document.getElementById('invp-body');
        if (!body) return;
        const rows = this._all.slice()
            .sort((a, b) => new Date(b.date) - new Date(a.date))
            .slice(0, PREVIEW_COUNT);
        body.innerHTML = rows.length
            ? rows.map(investigationRowHtml).join('')
            : '<tr><td colspan="6" class="text-zinc-500 text-xs py-6 text-center">No investigations logged yet.</td></tr>';
        wireRowNavigation(body);
    },
};

window.InvestigationsPreview = InvestigationsPreview;
document.addEventListener('DOMContentLoaded', () => InvestigationsPreview.init());
