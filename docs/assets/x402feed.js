// VAPE's live x402 transaction ledger — every paid job the worker fulfills,
// logged the instant it settles (worker/src/lib/jobLog.ts) and shown here
// exactly as reported by the free /x402/feed + /x402/stats endpoints. Real
// on-chain proof, not just VAPE's word: each row's tx hash comes straight
// from the x402 facilitator's own settlement response and links to
// Basescan, so any entry is independently checkable.
import { tokenIconByAddress } from './icons.js';

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function basescanTxUrl(hash) { return `https://basescan.org/tx/${hash}`; }
function basescanAddrUrl(addr) { return `https://basescan.org/address/${addr}`; }
function verdictClass(v) {
    if (v === 'PROCEED' || v === 'LOW' || v === 'GO') return 'border border-emerald-500 text-emerald-500';
    if (v === 'CAUTION' || v === 'MEDIUM') return 'border border-amber-400 text-amber-400';
    if (v === 'REJECT' || v === 'HIGH' || v === 'EXTREME') return 'border border-rose-400 text-rose-400';
    return 'border border-white/20 text-zinc-400';
}
function ago(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const s = Math.max(0, (Date.now() - d.getTime()) / 1000);
    if (s < 60) return Math.floor(s) + 's ago';
    if (s < 3600) return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}
function debounce(fn, ms) {
    let t = null;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// Real, verified per-offering listing pages — transcribed from the actual
// 402index.io registration responses (see agents/publish_reputation.py's
// _402INDEX_SERVICE_IDS for provenance), never guessed. reputation.json is
// the live copy of this same data; kept here too so the ledger section can
// render its directory links even before App.reputation() has resolved.
let _directoryLinks = null;
async function directoryLinks() {
    if (_directoryLinks) return _directoryLinks;
    try {
        const rep = await (await fetch(`https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/reputation.json?t=${Date.now()}`)).json();
        _directoryLinks = (rep.capabilities?.offerings || []).filter(o => o.directory_url);
    } catch { _directoryLinks = []; }
    return _directoryLinks;
}

const RANGE_BTN_ACTIVE = ['term-btn-active'];
const PAGE_SIZE = 25;

// A vertical crosshair synced to the hovered point — the one bit of genuine
// "trading terminal" chrome here — implemented as a plain Chart.js plugin
// (no chartjs-plugin-crosshair dependency; the site already loads bare
// chart.js@4 from a CDN and this is ~10 lines of canvas drawing).
const crosshairPlugin = {
    id: 'x402Crosshair',
    afterDraw(chart) {
        const active = chart.getActiveElements();
        if (!active || !active.length) return;
        const { ctx, chartArea } = chart;
        const x = active[0].element.x;
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([3, 3]);
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgba(255,255,255,0.25)';
        ctx.stroke();
        ctx.restore();
    },
};

// Simple moving average over whatever bucket granularity is on screen
// (daily/weekly/monthly) — a real indicator, not decoration: it's the same
// smoothing a trader would want to see through day-to-day noise.
function movingAverage(values, window) {
    const out = [];
    for (let i = 0; i < values.length; i++) {
        const start = Math.max(0, i - window + 1);
        const slice = values.slice(start, i + 1);
        out.push(slice.reduce((s, v) => s + v, 0) / slice.length);
    }
    return out;
}

const X402Feed = {
    _chart: null,
    _pollHandle: null,
    _days: 30,
    _rawDaily: [],
    _feed: { q: '', status: '', sort: 'ts_desc', offset: 0 },
    _feedTotal: 0,
    _feedInFlight: 0,

    async init() {
        this._wireRangeToggle();
        this._wireFeedControls();
        await Promise.all([this._loadStats(), this._loadFeed(), this._renderDirectoryLinks()]);
        // 25s: cheap enough not to hammer the worker's edge cache (both
        // endpoints cache 10-30s server-side anyway), frequent enough that
        // "live" isn't a lie.
        if (!this._pollHandle) {
            this._pollHandle = setInterval(() => { this._loadStats(); this._loadFeed(); }, 25000);
        }
    },

    _wireRangeToggle() {
        const wrap = document.getElementById('x402-range-toggle');
        if (!wrap) return;
        wrap.querySelectorAll('.x402-range-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const raw = btn.dataset.days;
                const days = raw === 'all' ? 'all' : (Number(raw) || 30);
                if (days === this._days) return;
                this._days = days;
                wrap.querySelectorAll('.x402-range-btn').forEach(b => {
                    const active = b === btn;
                    b.classList.remove(...RANGE_BTN_ACTIVE);
                    if (active) b.classList.add(...RANGE_BTN_ACTIVE);
                    b.setAttribute('aria-pressed', String(active));
                });
                this._loadStats();
            });
        });
    },

    _wireFeedControls() {
        const search = document.getElementById('x402-feed-search');
        const status = document.getElementById('x402-feed-status');
        const sort = document.getElementById('x402-feed-sort');
        const prev = document.getElementById('x402-feed-prev');
        const next = document.getElementById('x402-feed-next');
        if (search) {
            search.addEventListener('input', debounce(() => {
                this._feed.q = search.value.trim();
                this._feed.offset = 0;
                this._loadFeed();
            }, 300));
        }
        if (status) {
            status.addEventListener('change', () => {
                this._feed.status = status.value;
                this._feed.offset = 0;
                this._loadFeed();
            });
        }
        if (sort) {
            sort.addEventListener('change', () => {
                this._feed.sort = sort.value;
                this._feed.offset = 0;
                this._loadFeed();
            });
        }
        if (prev) {
            prev.addEventListener('click', () => {
                this._feed.offset = Math.max(0, this._feed.offset - PAGE_SIZE);
                this._loadFeed();
            });
        }
        if (next) {
            next.addEventListener('click', () => {
                this._feed.offset += PAGE_SIZE;
                this._loadFeed();
            });
        }
    },

    async _renderDirectoryLinks() {
        const el = document.getElementById('x402-directory-links');
        if (!el) return;
        // x402scan doesn't depend on reputation.json, so it renders immediately
        // rather than waiting on a fetch that only the 402index links need.
        el.innerHTML = `<a href="https://www.x402scan.com/" target="_blank" rel="noopener" class="term-btn term-btn-sm"><i class="fa-solid fa-magnifying-glass"></i> Browse x402scan</a>`;
        const links = await directoryLinks();
        if (!links.length) return;
        const parts = [el.innerHTML,
            `<a href="https://402index.io/" target="_blank" rel="noopener" class="term-btn term-btn-sm"><i class="fa-solid fa-book"></i> 402 Index directory</a>`,
        ];
        links.forEach(o => {
            parts.push(`<a href="${escapeHtml(o.directory_url)}" target="_blank" rel="noopener" class="term-btn term-btn-sm font-mono">${escapeHtml(o.name)} <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>`);
        });
        el.innerHTML = parts.join('');
    },

    async _loadStats() {
        const setTxt = (id, v) => { const n = document.getElementById(id); if (n) n.textContent = v; };
        const updated = document.getElementById('x402-updated');
        try {
            const r = await fetch(`${window.WORKER_BASE}/x402/stats?days=${this._days}`);
            if (r.status === 503) {
                this._notConfigured();
                return;
            }
            const stats = await r.json();
            const t = stats.totals || {};
            const settled = t.jobs - (t.errors || 0);
            const successRate = t.jobs ? Math.round((settled / t.jobs) * 100) : null;
            setTxt('x402-jobs', t.jobs != null ? t.jobs.toLocaleString() : '—');
            setTxt('rep-x402-jobs', t.jobs != null ? t.jobs.toLocaleString() : '—');
            setTxt('x402-revenue', t.revenue_usd != null ? '$' + t.revenue_usd.toFixed(2) : '—');
            setTxt('x402-success', successRate != null ? successRate + '%' : '—');
            if (updated) updated.innerHTML = `<span class="w-2 h-2 bg-emerald-500 rounded-full live-dot"></span>live`;

            this._rawDaily = stats.daily || [];
            this._renderRangeStats(this._rawDaily);
            this._renderChart(this._rawDaily);
        } catch (e) {
            if (updated) updated.textContent = 'ledger unavailable';
        }
    },

    // Range-scoped detail beyond the global (all-time) stat line above —
    // exactly what the raw `daily` array for the selected range already
    // contains, computed client-side for free.
    _renderRangeStats(daily) {
        const setTxt = (id, v) => { const n = document.getElementById(id); if (n) n.textContent = v; };
        if (!daily.length) {
            setTxt('x402-range-revenue', '—'); setTxt('x402-range-jobs', '—');
            setTxt('x402-range-avg', '—'); setTxt('x402-range-best', '—');
            return;
        }
        const revenue = daily.reduce((s, d) => s + d.revenue_usd, 0);
        const jobs = daily.reduce((s, d) => s + d.jobs, 0);
        const best = daily.reduce((b, d) => (d.revenue_usd > b.revenue_usd ? d : b), daily[0]);
        setTxt('x402-range-revenue', '$' + revenue.toFixed(2));
        setTxt('x402-range-jobs', jobs.toLocaleString());
        setTxt('x402-range-avg', '$' + (revenue / daily.length).toFixed(2));
        setTxt('x402-range-best', best.revenue_usd > 0
            ? `$${best.revenue_usd.toFixed(2)} (${new Date(best.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })})`
            : '—');
    },

    async _loadFeed() {
        const el = document.getElementById('x402-feed');
        if (!el) return;
        const myRequest = ++this._feedInFlight;
        try {
            const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(this._feed.offset) });
            if (this._feed.q) params.set('q', this._feed.q);
            if (this._feed.status) params.set('status', this._feed.status);
            if (this._feed.sort) params.set('sort', this._feed.sort);
            const [r, links] = await Promise.all([
                fetch(`${window.WORKER_BASE}/x402/feed?${params.toString()}`),
                directoryLinks(),
            ]);
            if (myRequest !== this._feedInFlight) return; // a newer request superseded this one
            if (r.status === 503) { this._notConfigured(); return; }
            const { jobs, total } = await r.json();
            this._feedTotal = total ?? (jobs ? jobs.length : 0);
            if (!jobs || !jobs.length) {
                el.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-zinc-500 text-xs">
                    <i class="fa-solid fa-satellite-dish text-xl mb-2 opacity-50 block"></i>
                    ${this._feed.q || this._feed.status ? 'No jobs match this filter.' : "No jobs logged yet — this fills in the moment VAPE's next paid job settles."}
                </td></tr>`;
            } else {
                const serviceUrlByOffering = Object.fromEntries(links.map(o => [o.name, o.directory_url]));
                el.innerHTML = jobs.map(j => this._row(j, serviceUrlByOffering)).join('');
            }
            this._renderFeedPagination();
        } catch (e) {
            el.innerHTML = `<tr><td colspan="8" class="text-amber-400 text-xs text-center py-6">Live ledger temporarily unavailable.</td></tr>`;
        }
    },

    _renderFeedPagination() {
        const countEl = document.getElementById('x402-feed-count');
        const pageEl = document.getElementById('x402-feed-page');
        const prev = document.getElementById('x402-feed-prev');
        const next = document.getElementById('x402-feed-next');
        const total = this._feedTotal;
        const page = Math.floor(this._feed.offset / PAGE_SIZE) + 1;
        const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
        if (countEl) {
            const from = total === 0 ? 0 : this._feed.offset + 1;
            const to = Math.min(total, this._feed.offset + PAGE_SIZE);
            countEl.textContent = `Showing ${from.toLocaleString()}–${to.toLocaleString()} of ${total.toLocaleString()} jobs`;
        }
        if (pageEl) pageEl.textContent = `Page ${page} of ${pages}`;
        if (prev) prev.disabled = this._feed.offset <= 0;
        if (next) next.disabled = this._feed.offset + PAGE_SIZE >= total;
    },

    _row(j, serviceUrlByOffering = {}) {
        const icon = tokenIconByAddress(j.address, j.chain_id);
        const label = j.symbol ? `$${j.symbol}` : (j.address ? j.address.slice(0, 8) + '…' : '—');
        const targetCell = j.address
            ? `<a href="${basescanAddrUrl(j.address)}" target="_blank" rel="noopener" class="text-zinc-200 hover:text-white flex items-center gap-1.5">${icon ? `<img src="${icon}" alt="" class="w-4 h-4 rounded-full shrink-0" onerror="this.remove()">` : ''}<span class="whitespace-nowrap">${escapeHtml(label)}</span></a>`
            : `<span class="text-zinc-500">${escapeHtml(label)}</span>`;
        const statusDot = j.status === 'settled'
            ? '<span class="w-1.5 h-1.5 bg-emerald-500 rounded-full inline-block" title="settled"></span>'
            : '<span class="w-1.5 h-1.5 bg-rose-500 rounded-full inline-block" title="error"></span>';
        const verdictPill = j.verdict
            ? `<span class="px-1.5 py-0.5 text-[10px] ${verdictClass(j.verdict)}">${escapeHtml(j.verdict)}</span>`
            : '<span class="text-zinc-700 text-[10px]">—</span>';
        const tx = j.tx_hash
            ? `<a href="${basescanTxUrl(j.tx_hash)}" target="_blank" rel="noopener" title="View settlement tx on block explorer" class="text-zinc-300 hover:text-white underline decoration-zinc-700">${j.tx_hash.slice(0, 6)}…${j.tx_hash.slice(-4)}</a>`
            : '<span class="text-zinc-700">unsettled</span>';
        // Each of the 6 auto offerings has a real, verified 402index.io service
        // listing (see agents/publish_reputation.py's _402INDEX_SERVICE_IDS) —
        // link straight to it so a job's offering is independently checkable
        // too, not just its settlement tx.
        const serviceUrl = serviceUrlByOffering[j.offering];
        const offeringLabel = serviceUrl
            ? `<a href="${escapeHtml(serviceUrl)}" target="_blank" rel="noopener" title="View ${escapeHtml(j.offering)} on 402index.io" class="text-zinc-500 hover:text-zinc-300 underline decoration-zinc-800 whitespace-nowrap">${escapeHtml(j.offering)}</a>`
            : `<span class="text-zinc-500 whitespace-nowrap">${escapeHtml(j.offering)}</span>`;
        return `
        <tr class="border-b border-white/5 hover:bg-white/[0.02]">
            <td class="py-2 pr-3">${statusDot}</td>
            <td class="py-2 pr-3 text-zinc-600 whitespace-nowrap" title="${escapeHtml(j.ts || '')}">${ago(j.ts)}</td>
            <td class="py-2 pr-3">${offeringLabel}</td>
            <td class="py-2 pr-3">${targetCell}</td>
            <td class="py-2 pr-3 text-zinc-100 font-medium whitespace-nowrap">$${Number(j.amount_usd).toFixed(2)}</td>
            <td class="py-2 pr-3">${verdictPill}</td>
            <td class="py-2 pr-3 text-zinc-600 whitespace-nowrap">${j.latency_ms != null ? j.latency_ms + 'ms' : '—'}${j.backfilled ? ' <span class="text-amber-500/70 text-[10px]" title="Reconstructed from on-chain history — logged after the fact, not watched live">hist</span>' : ''}</td>
            <td class="py-2 pr-3 whitespace-nowrap">${tx}</td>
        </tr>`;
    },

    // At wider ranges, one bar per day is unreadable — aggregate into
    // weekly (~90+ day view) or monthly (~1y+ view) buckets. Decided from
    // the actual array length (not a fixed `days` number) since "all" has
    // no fixed length up front.
    _bucketize(daily) {
        if (daily.length <= 31) return daily;
        const groupSize = daily.length > 180 ? 30 : 7;
        const buckets = [];
        for (let i = 0; i < daily.length; i += groupSize) {
            const slice = daily.slice(i, i + groupSize);
            if (!slice.length) continue;
            buckets.push({
                date: slice[slice.length - 1].date,
                jobs: slice.reduce((s, d) => s + d.jobs, 0),
                revenue_usd: slice.reduce((s, d) => s + d.revenue_usd, 0),
            });
        }
        return buckets;
    },

    _renderChart(daily) {
        const canvas = document.getElementById('x402Chart');
        if (!canvas || typeof Chart === 'undefined') return;
        const bucketed = this._bucketize(daily);
        const labels = bucketed.map(d => new Date(d.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
        const revenue = bucketed.map(d => d.revenue_usd);
        const jobs = bucketed.map(d => d.jobs);
        const maWindow = Math.min(7, Math.max(3, Math.round(bucketed.length / 6)));
        const ma = bucketed.length >= 3 ? movingAverage(revenue, maWindow) : [];
        // Running cumulative revenue across the visible range — the third
        // "advanced chart" dimension traders expect alongside a per-bar
        // value and its moving average.
        let running = 0;
        const cumulative = revenue.map(v => (running += v));
        if (this._chart) this._chart.destroy();
        const ctx = canvas.getContext('2d');
        // Emerald is the site's one deliberate accent color, used here for
        // the Revenue bars, with the Jobs line kept neutral white/grey so
        // it reads as data, not decoration.
        const h = canvas.parentElement?.clientHeight || 256;
        const g = ctx.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, 'rgba(74,222,128,0.30)'); g.addColorStop(1, 'rgba(74,222,128,0)');
        // The canvas sits in a height-controlled wrapper (see docs/index.html)
        // rather than deriving its height from a fixed aspect ratio — on
        // narrow viewports a 2:1 ratio squashed the chart into an unreadable
        // sliver, so maintainAspectRatio is off and the wrapper's own
        // responsive Tailwind height (h-64 sm:h-72 lg:h-80) drives the size.
        const narrow = window.innerWidth < 640;
        this._chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Revenue (USD)', data: revenue, backgroundColor: g, borderColor: '#4ade80', borderWidth: 1, yAxisID: 'y', order: 3 },
                    { label: 'Jobs', data: jobs, type: 'line', borderColor: '#d4d4d8', backgroundColor: 'transparent', tension: 0.3, pointRadius: 2, yAxisID: 'y1', order: 2 },
                    { label: `${maWindow}-period MA`, data: ma, type: 'line', borderColor: '#f0abfc', backgroundColor: 'transparent', borderDash: [4, 3], borderWidth: 1.5, tension: 0.3, pointRadius: 0, yAxisID: 'y', order: 1 },
                    { label: 'Cumulative', data: cumulative, type: 'line', borderColor: 'rgba(250,204,21,0.55)', backgroundColor: 'transparent', borderWidth: 1, pointRadius: 0, yAxisID: 'y2', order: 0, hidden: true },
                ],
            },
            plugins: [crosshairPlugin],
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, labels: { color: '#a1a1aa', boxWidth: 10, font: { size: narrow ? 9 : 10 } } },
                    tooltip: {
                        callbacks: {
                            title: items => items[0]?.label ?? '',
                            label: item => {
                                if (item.dataset.label === 'Revenue (USD)') return `Revenue: $${item.parsed.y.toFixed(2)}`;
                                if (item.dataset.label === 'Jobs') return `Jobs: ${item.parsed.y}`;
                                if (item.dataset.label === 'Cumulative') return `Cumulative: $${item.parsed.y.toFixed(2)}`;
                                return `${item.dataset.label}: $${item.parsed.y.toFixed(2)}`;
                            },
                        },
                    },
                },
                scales: {
                    y: { position: 'left', ticks: { color: '#52525b', font: { size: narrow ? 9 : 11 }, callback: v => '$' + v.toFixed(2) }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y1: { position: 'right', ticks: { color: '#52525b', stepSize: 1, font: { size: narrow ? 9 : 11 } }, grid: { display: false } },
                    y2: { display: false },
                    x: { ticks: { color: '#52525b', maxTicksLimit: narrow ? 4 : 8, font: { size: narrow ? 9 : 11 } }, grid: { display: false } },
                },
            },
        });
    },

    _notConfigured() {
        const feedEl = document.getElementById('x402-feed');
        if (feedEl) feedEl.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-zinc-500 text-xs">
            <i class="fa-solid fa-plug-circle-xmark text-xl mb-2 opacity-50 block"></i>
            Live ledger not wired up yet on this deploy.
        </td></tr>`;
        const updated = document.getElementById('x402-updated');
        if (updated) updated.textContent = 'not configured';
        if (this._pollHandle) { clearInterval(this._pollHandle); this._pollHandle = null; }
    },
};

window.X402Feed = X402Feed;
document.addEventListener('DOMContentLoaded', () => X402Feed.init());
