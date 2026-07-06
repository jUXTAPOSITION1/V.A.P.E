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

const X402Feed = {
    _chart: null,
    _pollHandle: null,

    async init() {
        await Promise.all([this._loadStats(), this._loadFeed(), this._renderDirectoryLinks()]);
        // 25s: cheap enough not to hammer the worker's edge cache (both
        // endpoints cache 10-30s server-side anyway), frequent enough that
        // "live" isn't a lie.
        if (!this._pollHandle) {
            this._pollHandle = setInterval(() => { this._loadStats(); this._loadFeed(); }, 25000);
        }
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
            const r = await fetch(`${window.WORKER_BASE}/x402/stats?days=30`);
            if (r.status === 503) {
                this._notConfigured();
                return;
            }
            const stats = await r.json();
            const t = stats.totals || {};
            const settled = t.jobs - (t.errors || 0);
            const successRate = t.jobs ? Math.round((settled / t.jobs) * 100) : null;
            setTxt('x402-jobs', t.jobs != null ? t.jobs.toLocaleString() : '—');
            setTxt('x402-revenue', t.revenue_usd != null ? '$' + t.revenue_usd.toFixed(2) : '—');
            setTxt('x402-success', successRate != null ? successRate + '%' : '—');
            if (updated) updated.innerHTML = `<span class="w-2 h-2 bg-cyan-500 rounded-full live-dot"></span>live`;

            this._renderChart(stats.daily || []);
            this._renderTracker(t);
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
            ? `<a href="${basescanTxUrl(j.tx_hash)}" target="_blank" rel="noopener" class="text-cyan-500 hover:underline truncate">${j.tx_hash.slice(0, 6)}…${j.tx_hash.slice(-4)}</a>`
            : '<span class="text-zinc-700">unsettled</span>';
        return `
        <div class="flex items-center gap-2 bg-white/[0.03] hover:bg-white/[0.06] transition rounded-lg px-2.5 py-2 whitespace-nowrap overflow-x-auto">
            ${statusDot}
            ${icon ? `<img src="${icon}" alt="" class="w-4 h-4 rounded-full shrink-0" onerror="this.remove()">` : ''}
            <span class="text-zinc-200 shrink-0 min-w-[52px]">${escapeHtml(label)}</span>
            <span class="text-zinc-600 shrink-0">${escapeHtml(j.offering)}</span>
            <span class="text-cyan-400 shrink-0">$${Number(j.amount_usd).toFixed(2)}</span>
            ${verdictPill}
            <span class="text-zinc-600 shrink-0">${j.latency_ms != null ? j.latency_ms + 'ms' : '—'}</span>
            <span class="ml-auto shrink-0">${tx}</span>
            <span class="text-zinc-700 shrink-0">${ago(j.ts)}</span>
        </div>`;
    },

    _renderChart(daily) {
        const canvas = document.getElementById('x402Chart');
        if (!canvas || typeof Chart === 'undefined') return;
        const labels = daily.map(d => new Date(d.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
        const revenue = daily.map(d => d.revenue_usd);
        const jobs = daily.map(d => d.jobs);
        if (this._chart) this._chart.destroy();
        const ctx = canvas.getContext('2d');
        const g = ctx.createLinearGradient(0, 0, 0, 180);
        g.addColorStop(0, 'rgba(34,211,238,0.35)'); g.addColorStop(1, 'rgba(34,211,238,0)');
        this._chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Revenue (USD)', data: revenue, backgroundColor: g, borderColor: '#22d3ee', borderWidth: 1, yAxisID: 'y', order: 2 },
                    { label: 'Jobs', data: jobs, type: 'line', borderColor: '#fbbf24', backgroundColor: 'transparent', tension: 0.3, pointRadius: 2, yAxisID: 'y1', order: 1 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { display: true, labels: { color: '#a1a1aa', boxWidth: 10, font: { size: 10 } } } },
                scales: {
                    y: { position: 'left', ticks: { color: '#52525b', callback: v => '$' + v.toFixed(2) }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y1: { position: 'right', ticks: { color: '#52525b', stepSize: 1 }, grid: { display: false } },
                    x: { ticks: { color: '#52525b', maxTicksLimit: 8 }, grid: { display: false } },
                },
            },
        });
    },

    // Compact live tracker line embedded in the Track Record section (see
    // docs/index.html) — kept hidden until real data exists, rather than
    // showing a zeroed/placeholder tracker for a feed nobody's used yet.
    _renderTracker(totals) {
        const wrap = document.getElementById('rep-x402-tracker');
        const summary = document.getElementById('rep-x402-summary');
        if (!wrap || !summary) return;
        if (!totals.jobs) { wrap.classList.add('hidden'); return; }
        wrap.classList.remove('hidden');
        const settled = totals.jobs - (totals.errors || 0);
        summary.textContent = `${settled.toLocaleString()} x402 job${settled === 1 ? '' : 's'} settled · `
            + `$${(totals.revenue_usd || 0).toFixed(2)} revenue`
            + (totals.last_job_ts ? ` · last job ${ago(totals.last_job_ts)}` : '');
    },

    _notConfigured() {
        const feedEl = document.getElementById('x402-feed');
        if (feedEl) feedEl.innerHTML = `<div class="text-center py-8 text-zinc-500 text-xs">
            <i class="fa-solid fa-plug-circle-xmark text-xl mb-2 opacity-50 block"></i>
            Live ledger not wired up yet on this deploy.
        </div>`;
        const updated = document.getElementById('x402-updated');
        if (updated) updated.textContent = 'not configured';
        const wrap = document.getElementById('rep-x402-tracker');
        if (wrap) wrap.classList.add('hidden');
        if (this._pollHandle) { clearInterval(this._pollHandle); this._pollHandle = null; }
    },
};

window.X402Feed = X402Feed;
document.addEventListener('DOMContentLoaded', () => X402Feed.init());
