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
    if (v === 'PROCEED' || v === 'LOW' || v === 'GO') return 'bg-emerald-500/20 text-emerald-500';
    if (v === 'CAUTION' || v === 'MEDIUM') return 'bg-amber-500/20 text-amber-400';
    if (v === 'REJECT' || v === 'HIGH' || v === 'EXTREME') return 'bg-rose-500/20 text-rose-400';
    return 'bg-white/10 text-zinc-400';
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

const RANGE_BTN_ACTIVE = ['bg-violet-500/15', 'text-violet-300'];
const RANGE_BTN_INACTIVE = ['text-zinc-500', 'hover:text-zinc-200', 'hover:bg-white/5'];

const X402Feed = {
    _chart: null,
    _pollHandle: null,
    _days: 30,

    async init() {
        this._wireRangeToggle();
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
                const days = Number(btn.dataset.days) || 30;
                if (days === this._days) return;
                this._days = days;
                wrap.querySelectorAll('.x402-range-btn').forEach(b => {
                    const active = b === btn;
                    b.classList.remove(...RANGE_BTN_ACTIVE, ...RANGE_BTN_INACTIVE);
                    b.classList.add(...(active ? RANGE_BTN_ACTIVE : RANGE_BTN_INACTIVE));
                    b.setAttribute('aria-pressed', String(active));
                });
                this._loadStats();
            });
        });
    },

    async _renderDirectoryLinks() {
        const el = document.getElementById('x402-directory-links');
        if (!el) return;
        // x402scan doesn't depend on reputation.json, so it renders immediately
        // rather than waiting on a fetch that only the 402index links need.
        el.innerHTML = `<a href="https://www.x402scan.com/" target="_blank" rel="noopener" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 transition text-zinc-400"><i class="fa-solid fa-magnifying-glass"></i> Browse x402scan</a>`;
        const links = await directoryLinks();
        if (!links.length) return;
        const parts = [el.innerHTML,
            `<a href="https://402index.io/" target="_blank" rel="noopener" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 transition text-zinc-400"><i class="fa-solid fa-book"></i> 402 Index directory</a>`,
        ];
        links.forEach(o => {
            parts.push(`<a href="${escapeHtml(o.directory_url)}" target="_blank" rel="noopener" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 transition text-zinc-500 font-mono">${escapeHtml(o.name)} <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>`);
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

            this._renderChart(stats.daily || []);
        } catch (e) {
            if (updated) updated.textContent = 'ledger unavailable';
        }
    },

    async _loadFeed() {
        const el = document.getElementById('x402-feed');
        if (!el) return;
        try {
            const r = await fetch(`${window.WORKER_BASE}/x402/feed?limit=30`);
            if (r.status === 503) { this._notConfigured(); return; }
            const { jobs } = await r.json();
            if (!jobs || !jobs.length) {
                el.innerHTML = `<div class="text-center py-8 text-zinc-500 text-xs">
                    <i class="fa-solid fa-satellite-dish text-xl mb-2 opacity-50 block"></i>
                    No jobs logged yet — this fills in the moment VAPE's next paid job settles.
                </div>`;
                return;
            }
            el.innerHTML = jobs.map(j => this._row(j)).join('');
        } catch (e) {
            el.innerHTML = `<div class="text-amber-400 text-xs text-center py-6">Live ledger temporarily unavailable.</div>`;
        }
    },

    _row(j) {
        const icon = tokenIconByAddress(j.address, j.chain_id);
        const label = j.symbol ? `$${j.symbol}` : (j.address ? j.address.slice(0, 8) + '…' : '—');
        const statusDot = j.status === 'settled'
            ? '<span class="w-1.5 h-1.5 bg-emerald-500 rounded-full shrink-0"></span>'
            : '<span class="w-1.5 h-1.5 bg-rose-500 rounded-full shrink-0"></span>';
        const verdictPill = j.verdict
            ? `<span class="px-1.5 py-0.5 rounded text-[10px] shrink-0 ${verdictClass(j.verdict)}">${escapeHtml(j.verdict)}</span>`
            : '<span class="text-zinc-700 text-[10px] shrink-0">—</span>';
        const tx = j.tx_hash
            ? `<a href="${basescanTxUrl(j.tx_hash)}" target="_blank" rel="noopener" class="text-zinc-300 hover:text-white underline decoration-zinc-700 truncate">${j.tx_hash.slice(0, 6)}…${j.tx_hash.slice(-4)}</a>`
            : '<span class="text-zinc-700">unsettled</span>';
        return `
        <div class="flex items-center gap-2 bg-white/[0.03] hover:bg-white/[0.06] transition rounded-lg px-2.5 py-2 whitespace-nowrap overflow-x-auto">
            ${statusDot}
            ${icon ? `<img src="${icon}" alt="" class="w-4 h-4 rounded-full shrink-0" onerror="this.remove()">` : ''}
            <span class="text-zinc-200 shrink-0 min-w-[52px]">${escapeHtml(label)}</span>
            <span class="text-zinc-600 shrink-0">${escapeHtml(j.offering)}</span>
            <span class="text-zinc-100 font-medium shrink-0">$${Number(j.amount_usd).toFixed(2)}</span>
            ${verdictPill}
            <span class="text-zinc-600 shrink-0">${j.latency_ms != null ? j.latency_ms + 'ms' : '—'}</span>
            ${j.backfilled ? '<span class="text-amber-500/70 text-[10px] shrink-0" title="Reconstructed from on-chain history — logged after the fact, not watched live">hist</span>' : ''}
            <span class="ml-auto shrink-0">${tx}</span>
            <span class="text-zinc-700 shrink-0">${ago(j.ts)}</span>
        </div>`;
    },

    // At wider ranges, one bar per day is unreadable — aggregate into
    // weekly (90d view) or monthly (1y view) buckets. 30d and under stays
    // daily since the raw /x402/stats?days= array is already that
    // granularity and there's nothing to gain by collapsing it.
    _bucketize(daily, days) {
        if (days <= 30 || daily.length <= 31) return daily;
        const groupSize = days > 180 ? 30 : 7;
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
        const bucketed = this._bucketize(daily, this._days);
        const labels = bucketed.map(d => new Date(d.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
        const revenue = bucketed.map(d => d.revenue_usd);
        const jobs = bucketed.map(d => d.jobs);
        if (this._chart) this._chart.destroy();
        const ctx = canvas.getContext('2d');
        // Violet is this site's established "engineering ledger" accent
        // (see the Development Ledger section) — used here as the one
        // deliberate color, with the Jobs line kept neutral white/grey so
        // it reads as data, not decoration.
        const h = canvas.parentElement?.clientHeight || 256;
        const g = ctx.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, 'rgba(167,139,250,0.35)'); g.addColorStop(1, 'rgba(167,139,250,0)');
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
                    { label: 'Revenue (USD)', data: revenue, backgroundColor: g, borderColor: '#a78bfa', borderWidth: 1, yAxisID: 'y', order: 2 },
                    { label: 'Jobs', data: jobs, type: 'line', borderColor: '#d4d4d8', backgroundColor: 'transparent', tension: 0.3, pointRadius: 2, yAxisID: 'y1', order: 1 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: true, labels: { color: '#a1a1aa', boxWidth: 10, font: { size: narrow ? 9 : 10 } } } },
                scales: {
                    y: { position: 'left', ticks: { color: '#52525b', font: { size: narrow ? 9 : 11 }, callback: v => '$' + v.toFixed(2) }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y1: { position: 'right', ticks: { color: '#52525b', stepSize: 1, font: { size: narrow ? 9 : 11 } }, grid: { display: false } },
                    x: { ticks: { color: '#52525b', maxTicksLimit: narrow ? 4 : 8, font: { size: narrow ? 9 : 11 } }, grid: { display: false } },
                },
            },
        });
    },

    _notConfigured() {
        const feedEl = document.getElementById('x402-feed');
        if (feedEl) feedEl.innerHTML = `<div class="text-center py-8 text-zinc-500 text-xs">
            <i class="fa-solid fa-plug-circle-xmark text-xl mb-2 opacity-50 block"></i>
            Live ledger not wired up yet on this deploy.
        </div>`;
        const updated = document.getElementById('x402-updated');
        if (updated) updated.textContent = 'not configured';
        if (this._pollHandle) { clearInterval(this._pollHandle); this._pollHandle = null; }
    },
};

window.X402Feed = X402Feed;
document.addEventListener('DOMContentLoaded', () => X402Feed.init());
