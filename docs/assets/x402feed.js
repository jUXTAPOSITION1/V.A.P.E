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
// smoothing a trader would want to see through day-to-day noise. Callers
// exclude any still-forming current bucket before calling this (see
// _renderChart) — folding a partial period into the average would drag it
// down every single time the period rolls over, which is a real analytical
// error, not just a display quirk.
function movingAverage(values, window) {
    const out = [];
    for (let i = 0; i < values.length; i++) {
        const start = Math.max(0, i - window + 1);
        const slice = values.slice(start, i + 1);
        out.push(slice.reduce((s, v) => s + v, 0) / slice.length);
    }
    return out;
}

// Compact axis-tick formatting for USD values — "$1.2K" beyond 1000 rather
// than a wide "$1234.00" that eats into the plot area, standard practice on
// any real trading/analytics y-axis.
function fmtUsdCompact(v) {
    const abs = Math.abs(v);
    if (abs >= 1_000_000) return '$' + (v / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
    if (abs >= 1000) return '$' + (v / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return '$' + v.toFixed(2);
}

const X402Feed = {
    _chart: null,
    _pollHandle: null,
    _days: 30,
    _rawDaily: [],
    _revenueStyle: 'bar',
    _activityDays: 30,
    _feed: { q: '', status: '', sort: 'ts_desc', offset: 0 },
    _feedTotal: 0,
    _feedInFlight: 0,

    async init() {
        this._wireRangeToggle();
        this._wireStyleToggle();
        this._wireActivityRangeToggle();
        this._wireFeedControls();
        await Promise.all([this._loadStats(), this._loadActivity(), this._loadFeed(), this._renderDirectoryLinks()]);
        // 25s: cheap enough not to hammer the worker's edge cache (both
        // endpoints cache 10-30s server-side anyway), frequent enough that
        // "live" isn't a lie.
        if (!this._pollHandle) {
            this._pollHandle = setInterval(() => { this._loadStats(); this._loadActivity(); this._loadFeed(); }, 25000);
        }
    },

    _wireActivityRangeToggle() {
        const wrap = document.getElementById('x402-activity-range');
        if (!wrap) return;
        wrap.querySelectorAll('.x402-activity-range-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const days = Number(btn.dataset.days) || 30;
                if (days === this._activityDays) return;
                this._activityDays = days;
                wrap.querySelectorAll('.x402-activity-range-btn').forEach(b => {
                    const active = b === btn;
                    b.classList.remove(...RANGE_BTN_ACTIVE);
                    if (active) b.classList.add(...RANGE_BTN_ACTIVE);
                    b.setAttribute('aria-pressed', String(active));
                });
                this._loadActivity();
            });
        });
    },

    // Real, sub-day bucketing, not a re-skin of the daily /x402/stats feed —
    // this is the concrete fix for "it buckets everyday regardless of
    // range" (explicit direction 2026-08-01). /x402/feed carries each job's
    // real settlement timestamp (worker/src/lib/jobLog.ts's JobRecord.ts),
    // so short/medium windows get genuine hourly/multi-hour resolution
    // instead of one bar per calendar day — matching the reference widget,
    // whose own tooltips show hour-level buckets ("Jul 27 17:00") even at a
    // 7-day view. Only the 90D+ tier falls back to the pre-aggregated daily
    // /x402/stats feed, where daily resolution is already the right call
    // (2000+ hourly bars would be unreadable, and infeasible to fetch raw).
    _activityBucketMinutes(days) {
        if (days <= 7) return 60;      // hourly
        if (days <= 30) return 180;    // every 3 hours
        return null;                   // fall back to daily /x402/stats
    },

    async _loadActivity() {
        const setTxt = (id, v) => { const n = document.getElementById(id); if (n) n.textContent = v; };
        const days = this._activityDays;
        try {
            const bucketMin = this._activityBucketMinutes(days);
            const buckets = bucketMin
                ? await this._activityBucketsFromFeed(days, bucketMin)
                : await this._activityBucketsFromStats(days);
            const jobs = buckets.reduce((s, b) => s + b.jobs, 0);
            const volume = buckets.reduce((s, b) => s + b.revenue_usd, 0);
            const buyers = new Set();
            buckets.forEach(b => (b.payers || []).forEach(p => buyers.add(p)));
            setTxt('x402-activity-jobs-value', jobs.toLocaleString());
            setTxt('x402-activity-volume-value', '$' + volume.toLocaleString(undefined, { maximumFractionDigits: 2 }));
            setTxt('x402-activity-buyers-value', buyers.size ? buyers.size.toLocaleString() : (buckets.reduce((s, b) => s + (b.buyers || 0), 0) || '—'));
            this._renderSparkline('x402-activity-jobs-spark', buckets, b => b.jobs);
            this._renderSparkline('x402-activity-volume-spark', buckets, b => b.revenue_usd);
            this._renderSparkline('x402-activity-buyers-spark', buckets, b => (b.payers ? b.payers.size : (b.buyers || 0)));
        } catch (e) {
            // Leave the last-good values on screen rather than blanking a
            // live number over one flaky poll.
        }
    },

    // Fetches real per-job records (real `ts`/`payer`, not a pre-aggregate)
    // and buckets them client-side at `bucketMin`-minute resolution over the
    // trailing `days` window. `limit` is generous relative to VAPE's real
    // observed volume (~27 jobs/day per the live x402scan listing) — 30 days
    // of full volume is ~800 records, well under RECENT_CAP.
    async _activityBucketsFromFeed(days, bucketMin) {
        const r = await fetch(`${window.WORKER_BASE}/x402/feed?limit=2000&sort=ts_desc`);
        if (r.status === 503) return [];
        const { jobs } = await r.json();
        const bucketMs = bucketMin * 60000;
        const now = Date.now();
        const count = Math.ceil((days * 1440) / bucketMin);
        const start = now - count * bucketMs;
        const buckets = [];
        for (let i = 0; i < count; i++) {
            buckets.push({ ts: start + i * bucketMs, jobs: 0, revenue_usd: 0, payers: new Set() });
        }
        for (const j of (jobs || [])) {
            const t = Date.parse(j.ts);
            if (isNaN(t) || t < start) continue;
            const idx = Math.min(count - 1, Math.floor((t - start) / bucketMs));
            const b = buckets[idx];
            if (!b) continue;
            b.jobs += 1;
            if (j.status === 'settled') b.revenue_usd += Number(j.amount_usd) || 0;
            if (j.payer) b.payers.add(String(j.payer).toLowerCase());
        }
        return buckets;
    },

    // Fallback for windows too wide to bucket sub-daily from raw records —
    // reuses the same pre-aggregated daily array the big Volume & Revenue
    // chart below already fetches, just shaped to match _renderSparkline's
    // expectations (`ts` instead of `date`).
    async _activityBucketsFromStats(days) {
        const r = await fetch(`${window.WORKER_BASE}/x402/stats?days=${days}`);
        if (r.status === 503) return [];
        const stats = await r.json();
        return (stats.daily || []).map(d => ({ ts: Date.parse(d.date + 'T00:00:00Z'), jobs: d.jobs, revenue_usd: d.revenue_usd, buyers: d.buyers || 0 }));
    },

    // Plain div bars, not Chart.js — these are decorative, glanceable
    // sparklines (one per Activity tile), not an interactive chart; a few
    // hundred absolutely-positioned divs is cheaper and simpler than
    // standing up a whole Chart.js instance three times over for the same
    // effect. Tooltip mirrors the reference widget's own hover behavior
    // (exact bucket time + value), not just the bare number.
    _renderSparkline(id, buckets, valueOf) {
        const el = document.getElementById(id);
        if (!el) return;
        if (!buckets.length) { el.innerHTML = ''; return; }
        const values = buckets.map(valueOf);
        const max = Math.max(1, ...values);
        el.innerHTML = buckets.map((b, i) => {
            const v = values[i];
            const pct = Math.max(3, Math.round((v / max) * 100));
            const latest = i === buckets.length - 1 ? ' is-latest' : '';
            const when = new Date(b.ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric' });
            return `<div class="activity-sparkline-bar${latest}" style="height:${pct}%" title="${escapeHtml(when)}: ${escapeHtml(String(v))}"></div>`;
        }).join('');
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

    _wireStyleToggle() {
        const wrap = document.getElementById('x402-style-toggle');
        if (!wrap) return;
        wrap.querySelectorAll('.x402-style-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const style = btn.dataset.style;
                if (style === this._revenueStyle) return;
                this._revenueStyle = style;
                wrap.querySelectorAll('.x402-style-btn').forEach(b => {
                    const active = b === btn;
                    b.classList.remove(...RANGE_BTN_ACTIVE);
                    if (active) b.classList.add(...RANGE_BTN_ACTIVE);
                    b.setAttribute('aria-pressed', String(active));
                });
                this._renderChart(this._rawDaily);
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

    // The primary x402scan/402index listing links now live as static cards
    // directly in index.html's "Listed On" block (real, hand-verified URLs
    // that don't need a fetch to render) — this only fills in the per-offering
    // 402index.io deep links underneath, once reputation.json resolves.
    async _renderDirectoryLinks() {
        const el = document.getElementById('x402-directory-links');
        if (!el) return;
        const links = await directoryLinks();
        if (!links.length) return;
        const parts = [`<span class="text-zinc-600 w-full mb-1">Per-offering 402index.io listings:</span>`];
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

        // The backend buckets by UTC calendar day (worker/src/lib/jobLog.ts),
        // so the rightmost bucket — whenever its date is today in UTC — is
        // still accumulating and will look like it "resets" the moment the
        // next UTC day begins (00:00 UTC, a fixed but non-obvious local
        // clock time depending on the viewer's own timezone). That's not a
        // bug in the data, but silently treating a partial period exactly
        // like a closed one is a real, well-known charting mistake — every
        // real trading/analytics dashboard (TradingView, exchange candles,
        // DefiLlama, etc.) marks the in-progress current period distinctly
        // instead. Doing the same here: lighter fill for that one bar, and
        // excluded from the moving average below so a fresh/partial bucket
        // doesn't drag the average down every single rollover.
        const todayUtc = new Date().toISOString().slice(0, 10);
        const lastIsPartial = bucketed.length > 0 && bucketed[bucketed.length - 1].date === todayUtc;

        const maWindow = Math.min(7, Math.max(3, Math.round(bucketed.length / 6)));
        const maInput = lastIsPartial ? revenue.slice(0, -1) : revenue;
        const maRaw = maInput.length >= 3 ? movingAverage(maInput, maWindow) : [];
        const ma = lastIsPartial ? [...maRaw, null] : maRaw;

        // Running cumulative revenue across the visible range — the third
        // "advanced chart" dimension traders expect alongside a per-bar
        // value and its moving average.
        let running = 0;
        const cumulative = revenue.map(v => (running += v));

        if (this._chart) this._chart.destroy();
        const ctx = canvas.getContext('2d');

        // Blue (Jobs line) + amber/gold (Revenue) is a standard dual-series
        // pairing on real trading terminals — high contrast against each
        // other and against the dark background, and blue is the site's
        // existing secondary accent (#60a5fa, used by Featured Investigation/
        // Bounty Command Center) rather than a color invented just for this.
        const REVENUE_COLOR = '#fbbf24';
        const REVENUE_PARTIAL_COLOR = 'rgba(251,191,36,0.35)';
        const JOBS_COLOR = '#60a5fa';
        const MA_COLOR = '#a78bfa';
        const CUMULATIVE_COLOR = '#2dd4bf';

        const h = canvas.parentElement?.clientHeight || 256;
        const gFull = ctx.createLinearGradient(0, 0, 0, h);
        gFull.addColorStop(0, 'rgba(251,191,36,0.30)'); gFull.addColorStop(1, 'rgba(251,191,36,0)');
        const gPartial = ctx.createLinearGradient(0, 0, 0, h);
        gPartial.addColorStop(0, 'rgba(251,191,36,0.12)'); gPartial.addColorStop(1, 'rgba(251,191,36,0)');

        // Per-bar color arrays so only the still-forming bucket gets the
        // lighter "in progress" treatment — every closed period looks
        // identical and fully readable.
        const revenueBg = revenue.map((_, i) => (lastIsPartial && i === revenue.length - 1) ? gPartial : gFull);
        const revenueBorder = revenue.map((_, i) => (lastIsPartial && i === revenue.length - 1) ? REVENUE_PARTIAL_COLOR : REVENUE_COLOR);

        // The canvas sits in a height-controlled wrapper (.chart-shell-lg in
        // docs/index.html) rather than deriving its height from a fixed
        // aspect ratio — on narrow viewports a 2:1 ratio squashed the chart
        // into an unreadable sliver, so maintainAspectRatio is off and the
        // wrapper's own responsive clamp() height drives the size.
        const narrow = window.innerWidth < 640;
        const wide = window.innerWidth >= 1024;
        const revenueIsArea = this._revenueStyle === 'area';

        this._chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    revenueIsArea
                        ? { label: 'Revenue (USD)', data: revenue, type: 'line', borderColor: REVENUE_COLOR, backgroundColor: gFull, fill: true, tension: 0.25, pointRadius: 0, borderWidth: 1.5, yAxisID: 'y', order: 3 }
                        : { label: 'Revenue (USD)', data: revenue, backgroundColor: revenueBg, borderColor: revenueBorder, borderWidth: 1, yAxisID: 'y', order: 3 },
                    { label: 'Jobs', data: jobs, type: 'line', borderColor: JOBS_COLOR, backgroundColor: 'transparent', tension: 0.3, pointRadius: 2, pointBackgroundColor: JOBS_COLOR, borderWidth: 1.5, yAxisID: 'y1', order: 2 },
                    { label: `${maWindow}-period MA`, data: ma, type: 'line', borderColor: MA_COLOR, backgroundColor: 'transparent', borderDash: [4, 3], borderWidth: 1.5, tension: 0.3, pointRadius: 0, yAxisID: 'y', order: 1, spanGaps: false },
                    { label: 'Cumulative', data: cumulative, type: 'line', borderColor: CUMULATIVE_COLOR, backgroundColor: 'transparent', borderWidth: 1, pointRadius: 0, yAxisID: 'y2', order: 0, hidden: true },
                ],
            },
            plugins: [crosshairPlugin],
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: '#a1a1aa', boxWidth: 10, usePointStyle: true, font: { size: narrow ? 9 : 11 } } },
                    tooltip: {
                        backgroundColor: 'rgba(9,9,11,0.95)', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1,
                        callbacks: {
                            title: items => {
                                const idx = items[0]?.dataIndex;
                                const base = items[0]?.label ?? '';
                                return idx === bucketed.length - 1 && lastIsPartial ? `${base} (today, in progress)` : base;
                            },
                            label: item => {
                                if (item.dataset.label === 'Jobs') return `Jobs: ${item.parsed.y}`;
                                if (item.parsed.y == null) return null;
                                return `${item.dataset.label}: ${fmtUsdCompact(item.parsed.y)}`;
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        position: 'left',
                        title: { display: !narrow, text: 'Revenue (USD)', color: '#71717a', font: { size: 10 } },
                        ticks: { color: '#71717a', font: { size: narrow ? 9 : 11 }, callback: v => fmtUsdCompact(v), maxTicksLimit: wide ? 8 : 5 },
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        border: { color: 'rgba(255,255,255,0.1)' },
                        beginAtZero: true,
                    },
                    y1: {
                        position: 'right',
                        title: { display: !narrow, text: 'Jobs settled', color: '#71717a', font: { size: 10 } },
                        ticks: { color: '#71717a', stepSize: 1, precision: 0, font: { size: narrow ? 9 : 11 } },
                        grid: { display: false },
                        border: { color: 'rgba(255,255,255,0.1)' },
                        beginAtZero: true,
                    },
                    y2: { display: false },
                    x: {
                        title: { display: !narrow, text: 'Date (UTC)', color: '#71717a', font: { size: 10 } },
                        ticks: { color: '#71717a', maxTicksLimit: wide ? 12 : (narrow ? 4 : 8), font: { size: narrow ? 9 : 11 } },
                        grid: { display: false },
                        border: { color: 'rgba(255,255,255,0.1)' },
                    },
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
