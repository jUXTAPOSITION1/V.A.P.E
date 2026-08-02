// Featured Investigations — the expanding ledger. A dense, sortable table of
// every real deep investigation VAPE has published (data/intel-index.json's
// `investigations` array, itself built from real intel/investigations/*.md
// files by agents/build_intel_index.py::scan_investigations()). Clicking a
// row expands an inline detail panel (real risk-factor breakdown, parsed
// from the report's own "[-12] Mintable supply…" summary text — never
// fabricated); a secondary action there opens the complete report in a full
// popup, which itself supports a PDF download via report.js's existing
// letterheaded Report.build()/downloadPdf() (same "V.A.P.E. Case Report"
// branding every other paid deliverable already gets — nothing new needed
// there, just wired through with this page's own investigation data).
import { escapeHtml, simpleMarkdownToHtml } from './report.js';

const REPO = 'jUXTAPOSITION1/V.A.P.E';
const RAW = `https://raw.githubusercontent.com/${REPO}/main`;
const INTEL_INDEX_URL = `${RAW}/data/intel-index.json`;
const INV_DIR_RAW = `${RAW}/intel/investigations`;

const CHAIN_ID_MAP = { '1': 'ethereum', '8453': 'base', '42161': 'arbitrum', '10': 'optimism', '137': 'polygon', '56': 'bsc', '43114': 'avalanche' };
const EXPLORER_HOSTS = { arbitrum: 'arbiscan.io', ethereum: 'etherscan.io', optimism: 'optimistic.etherscan.io', polygon: 'polygonscan.com', bsc: 'bscscan.com', avalanche: 'snowtrace.io', base: 'basescan.org' };
export function chainSlug(chain) {
    const m = String(chain || '').match(/\d+/);
    return (m && CHAIN_ID_MAP[m[0]]) || 'base';
}
export function tokenIconUrl(address, chain) {
    if (!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) return null;
    return `https://dd.dexscreener.com/ds-data/tokens/${chainSlug(chain)}/${address.toLowerCase()}.png?size=lg`;
}
export function explorerUrl(address, chain) {
    if (!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) return null;
    return `https://${EXPLORER_HOSTS[chainSlug(chain)] || 'basescan.org'}/address/${address}`;
}
export function shortAddr(a) { return (a && a.length > 12) ? a.slice(0, 6) + '…' + a.slice(-4) : (a || ''); }
// HTML-escaping a URL interpolated into an inline JS event-handler attribute
// (e.g. onclick="...='${escapedUrl}'") does NOT stop a string-context
// breakout -- the browser HTML-decodes the attribute value before the JS
// parser ever sees it, so an escaped apostrophe decodes right back to a
// literal ' and terminates the JS string early. Validating the scheme here
// AND avoiding inline JS attributes (data-href + one delegated listener,
// see wireRowNavigation() below) closes both the injection and the
// javascript:/data: open-redirect surface in inv.url, which — unlike
// inv.file-derived hrefs — comes straight from repo data, not a fixed path
// this code builds itself.
export function safeExternalUrl(u) {
    if (!u) return null;
    try {
        const parsed = new URL(u, window.location.href);
        return (parsed.protocol === 'http:' || parsed.protocol === 'https:') ? parsed.href : null;
    } catch (e) {
        return null;
    }
}
// Delegated click handler shared by both this page's preview rows
// (investigationRowHtml()) and investigations-preview.js -- one listener
// per container instead of an inline onclick per row. Skips navigation when
// the click landed on the row's own explicit <a> (the browser already
// handles that natively; navigating twice would be wrong).
export function wireRowNavigation(containerEl) {
    if (!containerEl || containerEl.dataset.navWired) return;
    containerEl.dataset.navWired = '1';
    containerEl.addEventListener('click', (e) => {
        if (e.target.closest('a')) return;
        const row = e.target.closest('[data-href]');
        if (!row) return;
        window.location.href = row.dataset.href;
    });
}
export function ago(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const s = (Date.now() - d) / 1e3;
    if (s < 3600) return Math.max(1, Math.floor(s / 60)) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}
export const VERDICT_COLOR = { REJECT: '#fb7185', CAUTION: '#fbbf24', PROCEED: '#10b981' };
export function verdictColor(v) { return VERDICT_COLOR[(v || '').toUpperCase()] || '#a1a1aa'; }
export function scoreColor(score) {
    const n = Number(score);
    if (isNaN(n)) return '#a1a1aa';
    if (n >= 70) return '#10b981';
    if (n >= 40) return '#fbbf24';
    return '#fb7185';
}

// Real per-investigation-date activity, bucketed for one of 4 ranges — the
// exact same function backs both this page's own sparkline AND the main
// site's Investigations preview (investigations-preview.js imports this
// directly rather than reimplementing it), so "the same sparkline" is
// literal, not just visually similar.
//   day   -> last 24h,  hourly buckets (24 bars)
//   week  -> last 7d,   daily buckets  (7 bars)
//   month -> last 30d,  daily buckets  (30 bars)
//   all   -> full real history from the earliest investigation to now,
//            bucketed so the bar count never exceeds ~52 regardless of how
//            long VAPE has been running (bucket width grows with the real
//            span instead of hardcoding a unit).
export const SPARK_RANGES = ['day', 'week', 'month', 'all'];
// Each bucket carries its count (bar height) AND the average safety score of
// investigations logged in that window (bar color) -- so the sparkline shows
// not just how much activity there was, but how it was ranked: a tall red
// bucket is a busy, risky stretch; a tall green one is a busy, clean one. A
// bucket with no scored investigations stays uncolored (no fabricated
// signal) rather than defaulting to any particular color.
export function sparklineBuckets(investigations, range) {
    const now = Date.now();
    const items = investigations
        .map(inv => ({ d: new Date(inv.date), score: inv.score != null && inv.score !== '' ? Number(inv.score) : null }))
        .filter(x => !isNaN(x.d));
    let bucketMs, n;
    if (range === 'day') { bucketMs = 3600e3; n = 24; }
    else if (range === 'month') { bucketMs = 86400e3; n = 30; }
    else if (range === 'all') {
        const earliest = items.length ? Math.min(...items.map(x => x.d.getTime())) : now;
        const spanMs = Math.max(86400e3, now - earliest);
        n = 52;
        bucketMs = Math.max(86400e3, Math.ceil(spanMs / n));
        n = Math.max(1, Math.min(52, Math.ceil(spanMs / bucketMs)));
    } else { bucketMs = 86400e3; n = 7; } // 'week'

    const buckets = Array.from({ length: n }, () => ({ count: 0, scoreSum: 0, scoreN: 0 }));
    items.forEach(({ d, score }) => {
        const diff = Math.floor((now - d.getTime()) / bucketMs);
        if (diff < 0) return;
        // 'all' sizes n from the same spanMs used to compute diff, so the
        // very oldest item can land exactly on diff === n (a rounding edge,
        // not out-of-range) -- fold it into the last bucket instead of
        // dropping it. day/week/month have a fixed real window, so an
        // out-of-range diff there is genuinely too old and stays excluded.
        const bucketDiff = range === 'all' ? Math.min(diff, n - 1) : diff;
        if (bucketDiff >= n) return;
        const b = buckets[n - 1 - bucketDiff];
        b.count++;
        if (score != null && !isNaN(score)) { b.scoreSum += score; b.scoreN++; }
    });
    return buckets.map(b => ({ count: b.count, avgScore: b.scoreN ? b.scoreSum / b.scoreN : null }));
}
// A compact, non-expanding row — the same title/chain/verdict/score/date
// cells _rowHtml() below renders for the full ledger, minus the click-to-
// expand detail panel and PDF/report popup (a preview has nowhere to put an
// expanded panel and no reason to duplicate the full page's report reader).
// Exported so the main-site preview renders literally these cells, not a
// re-implementation of them.
export function investigationRowHtml(inv) {
    const v = (inv.verdict || '').toUpperCase();
    const vColor = verdictColor(v);
    const sColor = scoreColor(inv.score);
    const icon = tokenIconUrl(inv.target, inv.chain);
    const heading = inv.symbol || shortAddr(inv.target) || inv.title || 'Investigation';
    const score = inv.score != null && inv.score !== '' ? Number(inv.score) : null;
    const href = inv.file ? `investigation.html?file=${encodeURIComponent(inv.file)}` : (safeExternalUrl(inv.url) || 'investigations.html');
    const linkAttrs = inv.file ? '' : ' target="_blank" rel="noopener"';
    return `<tr class="invl-row" data-idx="0" data-href="${escapeHtml(href)}" style="--row-verdict:${escapeHtml(vColor)};--row-verdict-wash:${vColor}14">
        <td>
            <div class="invl-title-cell">
                ${icon ? `<img src="${escapeHtml(icon)}" alt="" class="invl-icon" onerror="this.style.display='none'">` : `<div class="invl-icon flex items-center justify-center"><i class="fa-solid fa-magnifying-glass-chart text-[9px] text-zinc-600"></i></div>`}
                <div class="min-w-0">
                    <div class="invl-title">${escapeHtml(heading)}</div>
                    <div class="invl-addr">${escapeHtml(shortAddr(inv.target) || '—')}</div>
                </div>
            </div>
        </td>
        <td class="invl-addr">${escapeHtml((inv.chain || '').replace(/\s*\(.*\)/, '') || '—')}</td>
        <td>${v ? `<span class="invl-verdict-pill" style="color:${vColor}">${escapeHtml(v)}</span>` : '—'}</td>
        <td>${score != null ? `<span class="invl-score-cell"><span class="invl-score-bar-wrap"><span class="invl-score-bar-fill" style="width:${Math.max(0, Math.min(100, score))}%;background:${sColor}"></span></span><span style="color:${sColor}">${escapeHtml(String(score))}</span></span>` : '—'}</td>
        <td class="invl-time" title="${escapeHtml(inv.date || '')}">${escapeHtml(ago(inv.date))}</td>
        <td><a href="${escapeHtml(href)}"${linkAttrs} class="text-zinc-500 hover:text-zinc-200" title="Open"><i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a></td>
    </tr>`;
}

export function renderSparkline(el, investigations, range) {
    if (!el) return;
    const buckets = sparklineBuckets(investigations, range || 'all');
    const max = Math.max(1, ...buckets.map(b => b.count));
    el.innerHTML = buckets.map((b, i) => {
        const pct = Math.max(6, Math.round((b.count / max) * 100));
        const latest = i === buckets.length - 1 ? ' is-latest' : '';
        const style = b.avgScore != null ? `height:${pct}%;background:${scoreColor(b.avgScore)}` : `height:${pct}%`;
        const title = b.avgScore != null ? `${b.count} investigation(s) · avg score ${Math.round(b.avgScore)}/100` : `${b.count} investigation(s)`;
        return `<span class="invl-spark-bar${latest}" style="${style}" title="${escapeHtml(title)}"></span>`;
    }).join('');
}
// Wires a `.invl-range-btn[data-range]` toggle group to re-render the given
// sparkline element on click, tracking active state via `.is-active`.
export function wireSparkRangeToggle(toggleEl, sparkEl, getInvestigations, initial) {
    if (!toggleEl || toggleEl.dataset.wired) return;
    toggleEl.dataset.wired = '1';
    let current = initial || 'all';
    const render = () => renderSparkline(sparkEl, getInvestigations(), current);
    const setState = activeBtn => {
        toggleEl.querySelectorAll('.invl-range-btn').forEach(b => {
            const active = b === activeBtn;
            b.classList.toggle('is-active', active);
            b.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    };
    toggleEl.querySelectorAll('.invl-range-btn').forEach(btn => {
        if (btn.dataset.range === current) setState(btn);
        btn.addEventListener('click', () => {
            current = btn.dataset.range;
            setState(btn);
            render();
        });
    });
    render();
}

// Real risk-factor deltas straight out of the report's own summary text
// (agents/investigate.py writes "[-12] Mintable supply…; [-30] Same
// deployer…" — a genuine per-factor score breakdown, not a derived guess).
function parseRiskFactors(summary) {
    const out = [];
    const re = /\[([+-]?\d+)\]\s*([^;]+)/g;
    let m;
    while ((m = re.exec(String(summary || ''))) !== null) {
        out.push({ delta: parseInt(m[1], 10), label: m[2].trim().replace(/\.$/, '') });
    }
    return out;
}

// Strips the leading avatar/badge/metadata block, same convention as
// investigation.js's bodyAfterFrontmatter() — this page duplicates the small
// helper rather than importing a page script that also runs its own
// DOMContentLoaded init.
function bodyAfterFrontmatter(text) {
    const parts = text.split(/^---$/m);
    return parts.length > 1 ? parts.slice(1).join('\n\n').trim() : text;
}

const Ledger = {
    _all: [],
    _query: '',
    _verdictFilter: '',
    _sortKey: 'date',
    _sortDir: 'desc',
    _page: 0,
    _pageSize: 12,
    _donut: null,
    _reportCache: {},

    async init() {
        this._wireControls();
        try {
            const data = await (await fetch(`${INTEL_INDEX_URL}?t=` + Date.now())).json();
            this._all = Array.isArray(data.investigations) ? data.investigations.slice() : [];
        } catch (e) {
            document.getElementById('invl-body').innerHTML = '<tr><td colspan="6" class="text-zinc-500 text-xs py-6 text-center">Investigations index is briefly unreachable.</td></tr>';
            return;
        }
        const updated = document.getElementById('invl-updated');
        if (updated) updated.textContent = this._all.length ? `${this._all.length} on record` : 'no investigations yet';
        this._renderStats();
        this._renderVerdictBreakdown();
        wireSparkRangeToggle(document.getElementById('invl-spark-range'), document.getElementById('invl-spark'), () => this._all, 'all');
        this._render();
    },

    _wireControls() {
        const search = document.getElementById('invl-search');
        const verdictSelect = document.getElementById('invl-verdict-filter');
        const prevBtn = document.getElementById('invl-prev');
        const nextBtn = document.getElementById('invl-next');
        if (search) {
            let t;
            search.addEventListener('input', () => {
                clearTimeout(t);
                t = setTimeout(() => { this._query = search.value; this._page = 0; this._render(); }, 150);
            });
        }
        if (verdictSelect) {
            verdictSelect.addEventListener('change', () => { this._verdictFilter = verdictSelect.value; this._syncVerdictFilter(); });
        }
        if (prevBtn) prevBtn.addEventListener('click', () => { this._page = Math.max(0, this._page - 1); this._render(); });
        if (nextBtn) nextBtn.addEventListener('click', () => { this._page += 1; this._render(); });
        document.querySelectorAll('.invl-table thead th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const key = th.dataset.sort;
                if (this._sortKey === key) this._sortDir = this._sortDir === 'asc' ? 'desc' : 'asc';
                else { this._sortKey = key; this._sortDir = key === 'title' ? 'asc' : 'desc'; }
                this._page = 0;
                this._updateSortIndicators();
                this._render();
            });
        });
        this._updateSortIndicators();
    },

    // Keeps aria-sort + the visible arrow (site.css's .invl-sort-arrow) in
    // sync with the active column/direction — a keyboard or screen-reader
    // user gets the same sort state a sighted mouse user already sees from
    // the ledger's own row order.
    _updateSortIndicators() {
        document.querySelectorAll('.invl-table thead th[data-sort]').forEach(th => {
            const btn = th.querySelector('.invl-sort-btn');
            if (!btn) return;
            btn.querySelector('.invl-sort-arrow')?.remove();
            if (th.dataset.sort === this._sortKey) {
                th.setAttribute('aria-sort', this._sortDir === 'asc' ? 'ascending' : 'descending');
                const arrow = document.createElement('span');
                arrow.className = 'invl-sort-arrow';
                arrow.innerHTML = this._sortDir === 'asc' ? '&#9650;' : '&#9660;';
                btn.appendChild(arrow);
            } else {
                th.setAttribute('aria-sort', 'none');
            }
        });
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
        set('invl-total', this._all.length.toLocaleString());
        set('invl-reject', counts.REJECT.toLocaleString());
        set('invl-caution', counts.CAUTION.toLocaleString());
        set('invl-proceed', counts.PROCEED.toLocaleString());
        set('invl-avg-score', scoreN ? Math.round(scoreSum / scoreN) + '/100' : '…');
    },

    // Verdict Breakdown — a full-width section at the bottom of the page
    // (not a cramped side panel), built to actually carry detail and let a
    // reader act on it: a bigger beveled donut (site.css's .invl-donut-wrap
    // does the depth/glow styling — real 2D proportions underneath, no
    // fake-3D perspective distortion of the slices themselves) with a real
    // center total, plus a legend that's a genuine per-verdict data table
    // (count, share, and average score — not just a color key) where every
    // row is also a filter control: clicking Reject/Caution/Proceed here
    // drives the exact same this._verdictFilter the <select> above the
    // table already uses, so the chart and the ledger never disagree.
    _renderVerdictBreakdown() {
        const canvas = document.getElementById('invl-verdict-donut');
        const legendEl = document.getElementById('invl-verdict-legend');
        const totalEl = document.getElementById('invl-donut-total');
        const clearBtn = document.getElementById('invl-verdict-clear');
        if (!canvas && !legendEl) return;

        const buckets = { REJECT: [], CAUTION: [], PROCEED: [], OTHER: [] };
        this._all.forEach(inv => {
            const v = (inv.verdict || '').toUpperCase();
            (buckets[v] || buckets.OTHER).push(inv);
        });
        const avgScore = rows => {
            const scores = rows.map(r => Number(r.score)).filter(n => !isNaN(n));
            return scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;
        };
        const total = this._all.length || 1;
        const series = [
            ['REJECT', 'Reject', buckets.REJECT.length, VERDICT_COLOR.REJECT],
            ['CAUTION', 'Caution', buckets.CAUTION.length, VERDICT_COLOR.CAUTION],
            ['PROCEED', 'Proceed', buckets.PROCEED.length, VERDICT_COLOR.PROCEED],
            ['', 'Unclassified', buckets.OTHER.length, '#71717a'],
        ].filter(([, , n]) => n > 0);

        if (totalEl) totalEl.textContent = this._all.length.toLocaleString();

        if (canvas && typeof Chart !== 'undefined') {
            if (this._donut) this._donut.destroy();
            this._donut = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: series.map(s => s[1]),
                    datasets: [{ data: series.map(s => s[2]), backgroundColor: series.map(s => s[3]), borderWidth: 0, hoverOffset: 10 }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: '70%',
                    onClick: (_evt, elements) => { if (elements.length) this._applyVerdictFilter(series[elements[0].index][0]); },
                    onHover: (evt, elements) => { if (evt.native) evt.native.target.style.cursor = elements.length ? 'pointer' : ''; },
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: c => `${c.label}: ${c.parsed} (${Math.round(c.parsed / total * 100)}%)` } },
                    },
                },
            });
        }

        if (legendEl) {
            // Unclassified has no matching value in the verdict filter
            // (which is only ever REJECT/CAUTION/PROCEED, same as the
            // <select> above) — rendered as a plain row, not a click
            // target, rather than wiring it to a filter it can't perform.
            legendEl.innerHTML = series.map(([code, label, n, color]) => {
                const pct = Math.round(n / total * 100);
                const avg = avgScore(buckets[code] || buckets.OTHER);
                const active = code && this._verdictFilter === code;
                const tag = code ? 'button' : 'div';
                const typeAttr = code ? ' type="button"' : '';
                return `<${tag}${typeAttr} class="invl-verdict-row${active ? ' is-active' : ''}${code ? '' : ' is-static'}" data-verdict="${code}">
                    <span class="invl-verdict-row-dot" style="background:${color}"></span>
                    <span class="invl-verdict-row-label">${escapeHtml(label)}</span>
                    <span class="invl-verdict-row-count">${n.toLocaleString()}</span>
                    <span class="invl-verdict-row-pct">${pct}%</span>
                    <span class="invl-verdict-row-avg">${avg != null ? `avg ${avg}/100` : 'avg —'}</span>
                </${tag}>`;
            }).join('');
            legendEl.querySelectorAll('.invl-verdict-row[data-verdict]:not(.is-static)').forEach(row => {
                row.addEventListener('click', () => this._applyVerdictFilter(row.dataset.verdict));
            });
        }

        if (clearBtn) {
            clearBtn.hidden = !this._verdictFilter;
            clearBtn.onclick = () => this._clearVerdictFilter();
        }
    },

    // Toggles off if the same verdict is clicked twice — click-to-filter
    // controls read as pressed/unpressed, not one-way switches. Keeps the
    // plain <select> above the table in sync too, since it's the same
    // this._verdictFilter state either control can set.
    _applyVerdictFilter(code) {
        if (!code) return; // Unclassified slice/row — informational only, not filterable
        this._verdictFilter = this._verdictFilter === code ? '' : code;
        this._syncVerdictFilter();
    },
    _clearVerdictFilter() {
        this._verdictFilter = '';
        this._syncVerdictFilter();
    },
    _syncVerdictFilter() {
        const select = document.getElementById('invl-verdict-filter');
        if (select) select.value = this._verdictFilter;
        this._page = 0;
        this._render();
        this._renderVerdictBreakdown();
        if (this._verdictFilter) document.getElementById('invl-body')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    },

    _filtered() {
        const q = this._query.trim().toLowerCase();
        let rows = this._all.filter(inv => {
            if (this._verdictFilter && (inv.verdict || '').toUpperCase() !== this._verdictFilter) return false;
            if (!q) return true;
            const hay = `${inv.symbol || ''} ${inv.name || ''} ${inv.title || ''} ${inv.target || ''} ${inv.date || ''}`.toLowerCase();
            return hay.includes(q);
        });
        const dir = this._sortDir === 'asc' ? 1 : -1;
        const key = this._sortKey;
        rows = rows.slice().sort((a, b) => {
            if (key === 'score') return dir * ((Number(a.score) || 0) - (Number(b.score) || 0));
            if (key === 'date') return dir * (new Date(a.date || 0) - new Date(b.date || 0));
            const av = String(a[key] || a.symbol || '').toLowerCase();
            const bv = String(b[key] || b.symbol || '').toLowerCase();
            return dir * av.localeCompare(bv);
        });
        return rows;
    },

    _render() {
        const body = document.getElementById('invl-body');
        const countEl = document.getElementById('invl-count');
        const pageEl = document.getElementById('invl-page');
        const prevBtn = document.getElementById('invl-prev');
        const nextBtn = document.getElementById('invl-next');
        if (!body) return;

        const rows = this._filtered();
        const size = this._pageSize;
        const total = rows.length;
        const pages = Math.max(1, Math.ceil(total / size));
        if (this._page > pages - 1) this._page = pages - 1;
        const page = this._page;
        const slice = rows.slice(page * size, (page + 1) * size);

        if (!slice.length) {
            body.innerHTML = '<tr><td colspan="6" class="text-zinc-500 text-xs py-6 text-center">No investigations match this filter.</td></tr>';
        } else {
            body.innerHTML = slice.map((inv, i) => this._rowHtml(inv, page * size + i)).join('');
            body.querySelectorAll('.invl-row').forEach(tr => {
                tr.addEventListener('click', () => {
                    const detail = body.querySelector(`.invl-detail[data-for="${tr.dataset.idx}"]`);
                    if (detail) detail.classList.toggle('is-open');
                    tr.classList.toggle('is-expanded');
                });
            });
            body.querySelectorAll('[data-open-report]').forEach(btn => {
                btn.addEventListener('click', e => {
                    e.stopPropagation();
                    this.openReport(btn.dataset.openReport, btn);
                });
            });
        }

        if (countEl) countEl.textContent = total ? `Showing ${page * size + 1}–${Math.min(total, (page + 1) * size)} of ${total}` : 'No entries match this filter.';
        if (pageEl) pageEl.textContent = `Page ${page + 1} of ${pages}`;
        if (prevBtn) prevBtn.disabled = page <= 0;
        if (nextBtn) nextBtn.disabled = page + 1 >= pages;
    },

    _rowHtml(inv, idx) {
        const v = (inv.verdict || '').toUpperCase();
        const vColor = verdictColor(v);
        const sColor = scoreColor(inv.score);
        const icon = tokenIconUrl(inv.target, inv.chain);
        const explorer = explorerUrl(inv.target, inv.chain);
        const heading = inv.symbol || shortAddr(inv.target) || inv.title || 'Investigation';
        const score = inv.score != null && inv.score !== '' ? Number(inv.score) : null;
        const factors = parseRiskFactors(inv.summary);
        const maxAbs = Math.max(1, ...factors.map(f => Math.abs(f.delta)));
        const canOpenReport = inv.source === 'report' && !!inv.file;

        return `<tr class="invl-row" data-idx="${idx}" style="--row-verdict:${escapeHtml(vColor)};--row-verdict-wash:${vColor}14">
            <td>
                <div class="invl-title-cell">
                    ${icon ? `<img src="${escapeHtml(icon)}" alt="" class="invl-icon" onerror="this.style.display='none'">` : `<div class="invl-icon flex items-center justify-center"><i class="fa-solid fa-magnifying-glass-chart text-[9px] text-zinc-600"></i></div>`}
                    <div class="min-w-0">
                        <div class="invl-title">${escapeHtml(heading)}</div>
                        <div class="invl-addr">${escapeHtml(shortAddr(inv.target) || '—')}</div>
                    </div>
                </div>
            </td>
            <td class="invl-addr">${escapeHtml((inv.chain || '').replace(/\s*\(.*\)/, '') || '—')}</td>
            <td>${v ? `<span class="invl-verdict-pill" style="color:${vColor}">${escapeHtml(v)}</span>` : '—'}</td>
            <td>
                ${score != null ? `<span class="invl-score-cell"><span class="invl-score-bar-wrap"><span class="invl-score-bar-fill" style="width:${Math.max(0, Math.min(100, score))}%;background:${sColor}"></span></span><span style="color:${sColor}">${escapeHtml(String(score))}</span></span>` : '—'}
            </td>
            <td class="invl-time" title="${escapeHtml(inv.date || '')}">${escapeHtml(ago(inv.date))}</td>
            <td>
                <div class="invl-chevron-cell">
                    ${explorer ? `<a href="${escapeHtml(explorer)}" target="_blank" rel="noopener" onclick="event.stopPropagation()" class="text-zinc-500 hover:text-zinc-200" title="View on explorer"><i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>` : ''}
                    <i class="fa-solid fa-chevron-down invl-chevron"></i>
                </div>
            </td>
        </tr>
        <tr class="invl-detail" data-for="${idx}">
            <td colspan="6">
                <div class="invl-detail-inner">
                    ${inv.summary ? `<div class="invl-detail-summary">${escapeHtml(inv.summary)}</div>` : ''}
                    ${factors.length ? `<div class="invl-detail-factors">
                        ${factors.slice(0, 8).map(f => {
                            const w = Math.abs(f.delta) / maxAbs * 50;
                            const left = f.delta < 0 ? 50 - w : 50;
                            const color = f.delta < 0 ? '#fb7185' : '#10b981';
                            return `<div class="invl-factor-row">
                                <span class="invl-factor-label" title="${escapeHtml(f.label)}">${escapeHtml(f.label)}</span>
                                <span class="invl-factor-bar-wrap"><span class="invl-factor-bar" style="left:${left}%;width:${w}%;background:${color}"></span></span>
                                <span class="invl-factor-delta" style="color:${color}">${f.delta > 0 ? '+' : ''}${f.delta}</span>
                            </div>`;
                        }).join('')}
                    </div>` : ''}
                    <div class="invl-detail-actions">
                        ${canOpenReport
                            ? `<button type="button" data-open-report="${escapeHtml(inv.file)}" class="term-btn term-btn-sm"><i class="fa-solid fa-expand"></i> View full report</button>
                               <a href="investigation.html?file=${encodeURIComponent(inv.file)}" onclick="event.stopPropagation()" class="term-btn term-btn-sm"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open full page</a>`
                            : inv.url ? `<a href="${escapeHtml(inv.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()" class="term-btn term-btn-sm"><i class="fa-solid fa-arrow-up-right-from-square"></i> View source record</a>` : ''}
                    </div>
                </div>
            </td>
        </tr>`;
    },

    // ── Full-report popup ───────────────────────────────────────────────
    _modal: null,
    _escHandler: null,
    _modalTrigger: null,
    _closeModal() {
        if (this._escHandler) { document.removeEventListener('keydown', this._escHandler); this._escHandler = null; }
        if (this._modal) { this._modal.remove(); this._modal = null; }
        if (this._modalTrigger) { this._modalTrigger.focus(); this._modalTrigger = null; }
    },

    async openReport(file, triggerEl) {
        this._closeModal();
        this._modalTrigger = triggerEl || null;
        const inv = this._all.find(i => i.file === file) || {};
        const modal = document.createElement('div');
        modal.id = 'invl-report-modal';
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" data-close></div>
            <div class="relative popover p-6 max-h-[88vh] overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="invl-report-title">
                <div class="flex items-center justify-between mb-4 gap-3">
                    <h3 id="invl-report-title" class="text-base flex items-center gap-2 min-w-0">
                        <i class="fa-solid fa-magnifying-glass-chart text-zinc-500 shrink-0"></i>
                        <span class="truncate">${escapeHtml(inv.symbol || inv.title || 'Investigation Report')}</span>
                    </h3>
                    <button data-close class="text-zinc-500 hover:text-white shrink-0"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div id="invl-report-body" class="text-sm text-zinc-400">Loading full report…</div>
            </div>`;
        document.body.appendChild(modal);
        this._modal = modal;
        modal.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', () => this._closeModal()));
        this._escHandler = e => { if (e.key === 'Escape') this._closeModal(); };
        document.addEventListener('keydown', this._escHandler);
        const closeBtn = modal.querySelector('[data-close]');
        if (closeBtn) closeBtn.focus();

        const body = document.getElementById('invl-report-body');
        try {
            let text = this._reportCache[file];
            if (!text) {
                const res = await fetch(`${INV_DIR_RAW}/${encodeURIComponent(file)}?t=` + Date.now());
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                text = await res.text();
                this._reportCache[file] = text;
            }
            const rawBody = bodyAfterFrontmatter(text);
            const v = (inv.verdict || '').toUpperCase();
            const vColor = verdictColor(v);
            const score = inv.score != null && inv.score !== '' ? Number(inv.score) : null;
            const sColor = scoreColor(inv.score);
            body.innerHTML = `
                <div class="flex flex-wrap items-center gap-2 text-[11px] text-zinc-500 mb-3">
                    ${v ? `<span class="invl-verdict-pill" style="color:${vColor}">${escapeHtml(v)}</span>` : ''}
                    ${inv.target ? `<span class="font-mono">${escapeHtml(shortAddr(inv.target))}</span>` : ''}
                    ${inv.chain ? `<span>${escapeHtml(inv.chain)}</span>` : ''}
                    ${inv.date ? `<span>${escapeHtml(inv.date)}</span>` : ''}
                </div>
                ${score != null ? `<div class="invl-report-score-row">
                    <span class="text-[11px] text-zinc-500 shrink-0">Score</span>
                    <span class="invl-report-score-bar-wrap"><span class="invl-report-score-bar-fill" style="width:${Math.max(0, Math.min(100, score))}%;background:${sColor}"></span></span>
                    <span class="text-xs font-mono shrink-0" style="color:${sColor}">${escapeHtml(String(score))}/100</span>
                </div>` : ''}
                <article class="article-body">${simpleMarkdownToHtml(rawBody)}</article>
                <div class="flex flex-wrap items-center gap-2 mt-6 pt-4 border-t border-white/10">
                    <button type="button" id="invl-download-pdf" class="term-btn term-btn-sm"><i class="fa-solid fa-file-pdf"></i> Download PDF</button>
                    <a href="investigation.html?file=${encodeURIComponent(file)}" class="term-btn term-btn-sm"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open as full page</a>
                    <span id="invl-pdf-status" class="text-[11px] text-rose-400"></span>
                </div>`;
            const pdfBtn = document.getElementById('invl-download-pdf');
            if (pdfBtn) pdfBtn.addEventListener('click', () => this._downloadPdf(inv, rawBody));
        } catch (e) {
            body.innerHTML = `<div class="text-zinc-500 text-sm py-6 text-center">This report could not be loaded. It may have been moved or the archive is briefly unreachable.</div>`;
        }
    },

    // Reuses report.js's existing letterheaded PDF builder — every paid x402
    // deliverable already gets this exact "V.A.P.E." branded case-report
    // layout (see report.js::Report.build()'s letterhead + FULL AUDIT REPORT
    // markdown branch), so an investigation's PDF export carries the same
    // real V.A.P.E Report identity rather than a bespoke one-off layout.
    async _downloadPdf(inv, rawBody) {
        const status = document.getElementById('invl-pdf-status');
        if (!window.Report) {
            if (status) status.textContent = 'PDF export unavailable — try reloading the page.';
            return;
        }
        try {
            await window.Report.downloadPdf({
                offering: 'investigation',
                requestedAddress: inv.target || null,
                hiredBy: 'Public record',
                via: 'preview',
                result: {
                    deliverable: {
                        symbol: inv.symbol,
                        name: inv.name,
                        verdict: inv.verdict,
                        report_content: rawBody,
                    },
                    source: 'vape-investigations',
                    disclaimer: 'Real on-chain data. Not investment advice.',
                },
            });
        } catch (e) {
            // jsPDF unavailable/blocked (e.g. a wallet webview blocking a
            // third-party CDN or file download) — the on-screen report
            // itself still works either way, but the user clicked a button
            // and deserves a reason it didn't do anything.
            if (status) status.textContent = 'Could not generate the PDF — the on-screen report above is still complete.';
        }
    },
};

document.addEventListener('DOMContentLoaded', () => Ledger.init());
