// VAPE's own Security Dashboard — reads data/security-dashboard.json (a
// fully-regenerated snapshot, refreshed every 6h by
// agents/build_security_dashboard.py) plus data/security-dashboard-history.jsonl
// (one real appended line per run, feeding the threat-level-over-time toggle).
// Every field traces to a real file (skillforge/memory/findings.jsonl, its
// tamper-evidence chain, data/attack-feed.json) or a real GitHub API response
// (Actions Runs, Code Scanning Alerts) — a lane whose signal can't be reached
// reports null and renders an honest "unavailable" state, never a fabricated
// number.

const SECDASH_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/security-dashboard.json';
const SECDASH_HISTORY_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/security-dashboard-history.jsonl';
const REPO_BLOB = 'https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/';

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// The 5-bucket severity taxonomy agents/build_security_dashboard.py's
// normalize_severity() produces — order matters for stacking/list display
// (most severe first).
const SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
const SEV_VAR = { CRITICAL: '--sev-critical', HIGH: '--sev-high', MEDIUM: '--sev-medium', LOW: '--sev-low', INFO: '--sev-info' };
const SEV_TITLE = { CRITICAL: 'Critical', HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low', INFO: 'Info' };
const KNOWN_VERDICTS = ['PROCEED', 'CAUTION', 'REJECT'];
function sevColor(bucket) { return cssVar(SEV_VAR[bucket] || SEV_VAR.INFO); }
// Fixed top-to-bottom severity tier for the Signal Timeline's y-axis —
// CRITICAL always plots highest, INFO always lowest, regardless of which
// buckets a given day actually has data in.
function sevTier(bucket) { return SEV_ORDER.length - SEV_ORDER.indexOf(bucket); }

const THREAT_ORDER = ['LOW', 'MEDIUM', 'HIGH'];
const THREAT_ICON = { LOW: 'fa-circle-check', MEDIUM: 'fa-triangle-exclamation', HIGH: 'fa-triangle-exclamation' };

function ago(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return 'unknown';
    const mins = Math.max(0, Math.floor((Date.now() - d.getTime()) / 60000));
    if (mins < 60) return `${mins}m ago`;
    if (mins < 1440) return `${Math.floor(mins / 60)}h ago`;
    return `${Math.floor(mins / 1440)}d ago`;
}

function statusBadge(text, colorVar, icon) {
    return `<span class="secdash-badge" style="color:${escapeHtml(colorVar)}; border-color:${escapeHtml(colorVar)}55">` +
        `<i class="fa-solid ${escapeHtml(icon)} text-[9px]"></i>${escapeHtml(text)}</span>`;
}

const SEV_ICON = { CRITICAL: 'fa-circle-exclamation', HIGH: 'fa-circle-exclamation', MEDIUM: 'fa-triangle-exclamation', LOW: 'fa-circle-check', INFO: 'fa-circle-question' };

// One entry per real security workflow this repo runs, mapped to the six
// Risk Breakdown category cards. Every source field name here is real
// (agents/build_security_dashboard.py's build_lanes() output) — a category
// with no corresponding lane in a given snapshot simply renders "unavailable."
const CARD_DEFS = [
    { id: 'codeql', title: 'Static Analysis', laneIds: ['codeql'] },
    { id: 'dependency-audit', title: 'Dependencies', laneIds: ['dependency-audit'] },
    { id: 'security-lint', title: 'CI Hardening', laneIds: ['security-lint'] },
    { id: 'redteam', title: 'AI Red-Team', laneIds: ['redteam', 'redteam-deep'] },
    { id: 'intel-sweeps', title: 'On-Chain Intel', laneIds: ['intel-sweeps'] },
    { id: 'ledger-integrity', title: 'Ledger Integrity', laneIds: ['findings-seal', 'review-ledger'] },
];

// A small custom Chart.js plugin (no external library, no hand-rolled orbit
// physics) that adds three purely-decorative-but-real-data-driven touches to
// the bubble charts below: a soft ambient glow behind each bubble, faint
// dashed "orbit" lines from a fixed centroid to each bubble (Category Signal
// Map only), and a centered text label for bubbles large enough to hold one
// (the same letter/count already computed from real data — never a second,
// separately-invented value). Registered once, opted into per-chart via
// `options.plugins.secdashBubbleFx`.
function registerSecdashChartPlugins() {
    if (typeof Chart === 'undefined' || Chart.__secdashFxRegistered) return;
    Chart.__secdashFxRegistered = true;
    Chart.register({
        id: 'secdashBubbleFx',
        beforeDatasetsDraw(chart) {
            const cfg = chart.config.options.plugins && chart.config.options.plugins.secdashBubbleFx;
            if (!cfg) return;
            const ctx = chart.ctx;
            if (cfg.orbitCenter) {
                const meta = chart.getDatasetMeta(0);
                const cx = chart.scales.x.getPixelForValue(cfg.orbitCenter.x);
                const cy = chart.scales.y.getPixelForValue(cfg.orbitCenter.y);
                ctx.save();
                ctx.strokeStyle = 'rgba(148, 163, 250, 0.16)';
                ctx.setLineDash([2, 3]);
                ctx.lineWidth = 1;
                (meta.data || []).forEach(el => {
                    ctx.beginPath();
                    ctx.moveTo(cx, cy);
                    ctx.lineTo(el.x, el.y);
                    ctx.stroke();
                });
                ctx.restore();
            }
            if (cfg.glow) {
                ctx.save();
                ctx.shadowColor = 'rgba(148, 163, 250, 0.55)';
                ctx.shadowBlur = 12;
                chart.__secdashShadowOn = true;
            }
        },
        afterDatasetsDraw(chart) {
            const cfg = chart.config.options.plugins && chart.config.options.plugins.secdashBubbleFx;
            if (!cfg) return;
            const ctx = chart.ctx;
            if (chart.__secdashShadowOn) { ctx.restore(); chart.__secdashShadowOn = false; }
            if (cfg.centerLabel) {
                const meta = chart.getDatasetMeta(0);
                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'rgba(244, 244, 245, 0.92)';
                (meta.data || []).forEach((el, i) => {
                    const r = (cfg.pointRadii && cfg.pointRadii[i]) || 0;
                    if (r < (cfg.minRadius || 9)) return;
                    const text = cfg.centerLabel(i);
                    if (!text) return;
                    ctx.font = `600 ${Math.min(11, Math.max(8, r * 0.55))}px ui-monospace, monospace`;
                    ctx.fillText(text, el.x, el.y);
                });
                ctx.restore();
            }
        },
    });
}

const SecurityDashboard = {
    _data: null,
    _history: [],
    _lanes: [],
    _laneDetailOpenIdx: null,
    _signalMapOpenIdx: null,
    _signalMapSignals: null,
    _signalMapById: null,
    _gaugeChart: null,
    _sevChart: null,
    _timelineChart: null,
    _signalMapChart: null,
    _timelineSeries: 'severity',
    _ledgerQuery: '',
    _ledgerSevFilter: '',
    _ledgerPage: 0,
    _ledgerPageSize: 10,

    async init() {
        registerSecdashChartPlugins();
        const [data, history] = await Promise.all([this._fetchJson(), this._fetchHistory()]);
        this._data = data;
        this._history = history;
        if (!data) {
            this._renderUnavailable();
            return;
        }
        this._renderUpdated();
        // Each panel renders independently — one throwing (a malformed field
        // in a given lane, a missing canvas) must not leave its siblings
        // stuck in their skeleton state.
        for (const fn of [this._renderGauge, this._renderSeverityDonut,
            this._renderCategoryMap, this._renderTimeline, this._renderVerdictBars, this._wireTimelineToggle,
            this._renderLedger, this._wireLedgerControls, this._renderLedgerSpark]) {
            try { fn.call(this); } catch (e) { console.error('[SecurityDashboard]', fn.name, e); }
        }
    },

    async _fetchJson() {
        try {
            const res = await fetch(`${SECDASH_URL}?t=${Date.now()}`);
            if (!res.ok) return null;
            return await res.json();
        } catch (e) {
            return null;
        }
    },

    async _fetchHistory() {
        try {
            const res = await fetch(`${SECDASH_HISTORY_URL}?t=${Date.now()}`);
            if (!res.ok) return [];
            const text = await res.text();
            return text.trim().split('\n').filter(Boolean).map(l => {
                try { return JSON.parse(l); } catch (e) { return null; }
            }).filter(Boolean);
        } catch (e) {
            return [];
        }
    },

    _renderUnavailable() {
        const el = document.getElementById('secdash-updated');
        if (el) el.textContent = 'unavailable this cycle';
        const gaugeLabel = document.getElementById('secdash-gauge-label');
        if (gaugeLabel) gaugeLabel.innerHTML = '<span class="text-zinc-500 text-xs">No snapshot yet</span>';
        const sevList = document.getElementById('secdash-sev-list');
        if (sevList) sevList.innerHTML = '<li class="text-zinc-500">Snapshot unavailable.</li>';
        const legend = document.getElementById('secdash-signalmap-legend');
        if (legend) legend.innerHTML = CARD_DEFS.map(def =>
            `<div class="secdash-signalmap-item"><span class="secdash-signalmap-letter">?</span>` +
            `<span class="secdash-signalmap-body"><span class="secdash-signalmap-title">${escapeHtml(def.title)}</span>` +
            `<span class="secdash-signalmap-delta">Unavailable.</span></span></div>`).join('');
        const verdictBody = document.getElementById('secdash-verdict-body');
        if (verdictBody) verdictBody.innerHTML = '<span class="text-zinc-500 text-xs">Snapshot unavailable.</span>';
        const ledger = document.getElementById('secdash-ledger-body');
        if (ledger) ledger.innerHTML = '<tr><td colspan="5" class="text-zinc-500 text-xs py-4 text-center">Snapshot unavailable.</td></tr>';
    },

    _renderUpdated() {
        const el = document.getElementById('secdash-updated');
        if (el) el.innerHTML = `<i class="fa-solid fa-clock text-[10px]"></i>updated ${escapeHtml(ago(this._data.generated_at))}`;
    },

    // Threat-level arc gauge — a Chart.js doughnut rotated into a half-circle
    // (see site.css's .secdash-gauge-wrap comment). The underlying value is
    // security_sweep.py::compute_threat_level()'s real ordinal 3-state
    // category (LOW/MEDIUM/HIGH), rendered as progressive fill up to that
    // level's position — legitimate here specifically because it IS an
    // ordinal category, not a fabricated continuous score. Always paired
    // with the explicit text label below it. The delta line is a real
    // comparison against the previous appended history point, never a
    // fabricated week-over-week percentage.
    _renderGauge() {
        const canvas = document.getElementById('secdashGauge');
        const label = document.getElementById('secdash-gauge-label');
        const level = (this._data.overall_threat_level || '').toUpperCase();
        const idx = THREAT_ORDER.indexOf(level);
        const frac = idx >= 0 ? (idx + 1) / THREAT_ORDER.length : 0;
        const color = idx === 2 ? sevColor('CRITICAL') : idx === 1 ? sevColor('MEDIUM') : idx === 0 ? sevColor('LOW') : sevColor('INFO');

        const healthDot = document.querySelector('.secdash-health-dot');
        if (healthDot) healthDot.style.background = color;

        // The label/delta text carry the actual signal and must render even
        // if Chart.js itself is slow/blocked/failed to load — only the arc
        // drawing below needs the library.
        if (label) {
            const icon = THREAT_ICON[level] || 'fa-circle-question';
            label.innerHTML = idx >= 0
                ? `<div style="color:${escapeHtml(color)}" class="font-semibold text-sm"><i class="fa-solid ${escapeHtml(icon)} text-[11px] mr-1"></i>${escapeHtml(level)}</div>`
                : '<span class="text-zinc-500 text-xs">No signal</span>';
        }

        if (canvas && typeof Chart !== 'undefined') {
            if (this._gaugeChart) this._gaugeChart.destroy();
            this._gaugeChart = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [frac, 1 - frac],
                        backgroundColor: [color, cssVar('--bg-panel-sm') || '#27272a'],
                        borderWidth: 0,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    rotation: -90,
                    circumference: 180,
                    cutout: '72%',
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                },
            });
        }

        const deltaEl = document.getElementById('secdash-gauge-delta');
        if (deltaEl) {
            const prev = this._history.length >= 2 ? this._history[this._history.length - 2] : null;
            const prevIdx = prev ? THREAT_ORDER.indexOf((prev.overall_threat_level || '').toUpperCase()) : -1;
            if (!prev) {
                deltaEl.textContent = 'tracking since launch';
            } else if (idx < 0 || prevIdx < 0) {
                deltaEl.textContent = 'no comparable signal';
            } else if (prevIdx === idx) {
                deltaEl.textContent = 'steady vs last check';
            } else if (idx > prevIdx) {
                deltaEl.innerHTML = `<span style="color:${escapeHtml(sevColor('HIGH'))}">&#9650; worsened</span> vs last check`;
            } else {
                deltaEl.innerHTML = `<span style="color:${escapeHtml(sevColor('LOW'))}">&#9660; improved</span> vs last check`;
            }
        }

        // A second real-data line explaining WHY the level reads the way it
        // does, rather than leaving the arc + one word to speak for itself.
        const contextEl = document.getElementById('secdash-gauge-context');
        if (contextEl) {
            const bySev = this._data.findings_by_severity;
            const critHigh = bySev ? (bySev.CRITICAL || 0) + (bySev.HIGH || 0) : null;
            contextEl.textContent = critHigh == null ? 'no severity signal yet' : `${critHigh.toLocaleString()} critical/high finding(s) open`;
        }
    },

    // Findings Count: a real count+percentage list (doubling as the
    // required legend for a ≥2-series chart) beside a small donut with a
    // real total in its center.
    _renderSeverityDonut() {
        const canvas = document.getElementById('secdashSeverityDonut');
        const listEl = document.getElementById('secdash-sev-list');
        const bySev = this._data.findings_by_severity || {};
        const labels = SEV_ORDER.filter(k => (bySev[k] || 0) > 0);
        const values = labels.map(k => bySev[k]);
        const colors = labels.map(sevColor);
        const total = values.reduce((a, b) => a + b, 0);

        // The count/percentage list carries the real numbers and needs no
        // chart library — render it unconditionally so a slow/blocked/failed
        // Chart.js load never leaves this panel stuck on its skeleton.
        if (listEl) {
            listEl.innerHTML = labels.length
                ? labels.map((k, i) => `<li>
                    <span class="secdash-sev-chip" style="background:${escapeHtml(colors[i])}"></span>
                    <span class="secdash-sev-label">${escapeHtml(SEV_TITLE[k] || k)}</span>
                    <span class="secdash-sev-count">${values[i].toLocaleString()}</span>
                    <span class="secdash-sev-pct">${((values[i] / total) * 100).toFixed(1)}%</span>
                </li>`).join('')
                : '<li class="text-zinc-500">No findings logged yet.</li>';
        }

        const totalValue = document.getElementById('secdash-sev-donut-total-value');
        if (totalValue) totalValue.textContent = total.toLocaleString();

        if (!canvas || typeof Chart === 'undefined') return;
        if (this._sevChart) this._sevChart.destroy();
        const wrap = canvas.closest('.secdash-sev-donut-wrap');
        if (!labels.length) {
            if (wrap) wrap.style.visibility = 'hidden';
            return;
        }
        if (wrap) wrap.style.visibility = '';
        this._sevChart = new Chart(canvas, {
            type: 'doughnut',
            data: { labels, datasets: [{ data: values, backgroundColor: colors, borderColor: cssVar('--bg-page') || '#09090b', borderWidth: 2 }] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                // The adjacent list already shows every segment's exact
                // count + percentage at all times, so a hover tooltip adds
                // no information here.
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
            },
        });
    },

    // Per-lane status/color/title — shared by the Category Signal Map's own
    // detail panel below (_toggleSignalMapDetail). The Automated Lanes ring
    // that used to also read these (_renderLanesRing/_renderLanesPanel/
    // _toggleLaneDetail/_renderLanesA11yList) was replaced by VAPE Ave
    // (docs/assets/cityscape.js, data/city-state.json's 10 lane-checkpoint
    // buildings) on 2026-08-02 — every real per-workflow lane still has its
    // own building there instead of its own ring segment.
    _laneStatus(lane) {
        if (lane.last_run_conclusion == null) return 'never';
        return lane.last_run_conclusion === 'success' ? 'pass' : 'fail';
    },

    _laneStatusColor(status) {
        return status === 'pass' ? sevColor('LOW') : status === 'fail' ? sevColor('CRITICAL') : sevColor('INFO');
    },

    _laneStatusTitle(status) {
        return status === 'pass' ? 'Passing' : status === 'fail' ? 'Failing' : 'Never run';
    },

    // Shared per-category signal calculation — the ONE place that decides
    // what each of the six real security lanes' status/magnitude/delta text
    // is. Both the Category Signal Map bubble chart and its caption list
    // below read from this, so they can never drift out of sync with each
    // other.
    _categorySignal(def, byId) {
        const lanes = def.laneIds.map(id => byId[id]).filter(Boolean);
        if (!lanes.length) {
            return { title: def.title, ringStatus: 'info', color: sevColor('INFO'), magnitude: 0.2, delta: 'No data this cycle.', letter: '?' };
        }
        const primary = lanes[0];
        let letter, ringStatus, delta, magnitude;

        if (def.id === 'codeql') {
            const open = primary.open_alerts;
            const persisted = primary.persisted_high_critical_30d || 0;
            const clear = open === 0 && persisted === 0;
            letter = open == null ? '?' : clear ? 'OK' : 'H';
            ringStatus = open == null ? 'info' : clear ? 'low' : 'other';
            delta = open == null ? 'unavailable' : `${open} open alert(s), ${persisted} persisted 30d`;
            magnitude = open == null ? 0.2 : Math.max(0.22, Math.min(1, open / 50));
        } else if (def.id === 'dependency-audit' || def.id === 'security-lint') {
            const ok = primary.last_run_conclusion === 'success';
            letter = ok ? 'OK' : primary.last_run_conclusion == null ? '?' : '!';
            ringStatus = ok ? 'low' : primary.last_run_conclusion == null ? 'info' : 'other';
            delta = primary.last_run_at ? `last run ${ago(primary.last_run_at)}` : 'never run';
            magnitude = ok ? 0.3 : primary.last_run_conclusion == null ? 0.2 : 0.55;
        } else if (def.id === 'redteam') {
            const bd = primary.severity_breakdown || {};
            const total = SEV_ORDER.reduce((s, k) => s + (bd[k] || 0), 0);
            const bad = (bd.CRITICAL || 0) + (bd.HIGH || 0);
            letter = total === 0 ? 'OK' : bad > 0 ? 'H' : 'L';
            ringStatus = (total === 0 || bad === 0) ? 'low' : 'other';
            delta = `${total} finding(s), 30d`;
            magnitude = Math.max(0.22, Math.min(1, total / 20));
        } else if (def.id === 'intel-sweeps') {
            const ratio = typeof primary.coverage_ratio === 'number' ? primary.coverage_ratio : null;
            letter = primary.threat_level === 'HIGH' ? 'H' : primary.threat_level === 'MEDIUM' ? 'M' : primary.threat_level === 'LOW' ? 'L' : '?';
            ringStatus = primary.threat_level === 'LOW' ? 'low' : (primary.threat_level === 'HIGH' || primary.threat_level === 'MEDIUM') ? 'other' : 'info';
            const gaps = (primary.gap_patterns || []).length;
            delta = ratio == null ? 'unavailable' : `${Math.round(ratio * 100)}% covered, ${gaps} gap(s)`;
            magnitude = ratio == null ? 0.2 : Math.max(0.22, 1 - ratio);
        } else { // ledger-integrity
            const seal = lanes.find(l => l.id === 'findings-seal') || primary;
            const drift = lanes.find(l => l.id === 'review-ledger');
            const intact = seal.chain_intact;
            letter = intact === true ? 'OK' : intact === false ? '!' : '?';
            ringStatus = intact === true ? 'low' : intact === false ? 'other' : 'info';
            const worsened = drift ? (drift.worsened_30d || 0) : 0;
            const improved = drift ? (drift.improved_30d || 0) : 0;
            delta = `${worsened} worse / ${improved} better, 30d`;
            magnitude = Math.max(0.25, Math.min(1, (worsened + improved) / 10));
        }

        const color = ringStatus === 'low' ? sevColor('LOW') : ringStatus === 'info' ? sevColor('INFO') : sevColor('HIGH');
        return { title: def.title, ringStatus, color, magnitude, delta, letter };
    },

    // Category Signal Map — six real lanes rendered as a staggered bubble
    // cluster (Chart.js `bubble`, real primitive, no hand-rolled orbit
    // physics): fixed x-slot per category (never reordered), radius scaled
    // from that category's own real signal magnitude, color = the same
    // clear/issue/no-signal status already used everywhere else on this
    // dashboard. A caption list beneath carries the exact delta text each
    // bubble represents, since a bubble chart has no room for per-point
    // labels.
    _renderCategoryMap() {
        const canvas = document.getElementById('secdashSignalMap');
        const legend = document.getElementById('secdash-signalmap-legend');
        const byId = {};
        for (const lane of this._data.lanes || []) byId[lane.id] = lane;
        const signals = CARD_DEFS.map(def => this._categorySignal(def, byId));
        this._signalMapSignals = signals;
        this._signalMapById = byId;

        if (legend) {
            legend.innerHTML = signals.map((s, i) => `<div class="secdash-signalmap-item" data-idx="${i}">
                <span class="secdash-signalmap-letter" style="color:${escapeHtml(s.color)}">${escapeHtml(s.letter)}</span>
                <span class="secdash-signalmap-body">
                    <span class="secdash-signalmap-title">${escapeHtml(s.title)}</span>
                    <span class="secdash-signalmap-delta">${escapeHtml(s.delta)}</span>
                </span>
            </div>`).join('');
            legend.querySelectorAll('.secdash-signalmap-item').forEach(el => {
                el.addEventListener('click', () => this._toggleSignalMapDetail(Number(el.dataset.idx)));
            });
        }

        if (!canvas || typeof Chart === 'undefined') return;
        if (this._signalMapChart) this._signalMapChart.destroy();
        // A real min-width (120px per category) on the chart container so
        // bubbles keep a legible, non-overlapping size and the panel scrolls
        // horizontally on a narrow viewport instead of crushing all six
        // together (see .secdash-signalmap-scroll in site.css).
        const chartWrap = canvas.closest('.secdash-signalmap-chart');
        if (chartWrap) chartWrap.style.minWidth = `${CARD_DEFS.length * 120}px`;
        const points = signals.map((s, i) => ({
            x: i,
            y: i % 2 === 0 ? 1.2 : 0.8,
            r: 10 + s.magnitude * 22,
            label: s.title,
            delta: s.delta,
            letter: s.letter,
            color: s.color,
        }));
        // Centroid for the faint orbit lines — the middle x-slot at the
        // staggered rows' vertical midpoint, not a computed center-of-mass
        // (this is a decorative radar motif, not a physics simulation).
        const orbitCenter = { x: (CARD_DEFS.length - 1) / 2, y: 1 };
        this._signalMapChart = new Chart(canvas, {
            type: 'bubble',
            data: {
                datasets: [{
                    data: points,
                    backgroundColor: points.map(p => p.color + 'b3'),
                    borderColor: points.map(p => p.color),
                    borderWidth: 1.5,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 10, bottom: 10 } },
                onClick: (evt, elements) => {
                    if (elements.length) this._toggleSignalMapDetail(elements[0].index);
                },
                onHover: (evt, elements) => {
                    evt.native.target.style.cursor = elements.length ? 'pointer' : '';
                },
                scales: {
                    x: { min: -0.6, max: CARD_DEFS.length - 0.4, display: false },
                    y: { min: -0.5, max: 2.5, display: false },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: items => points[items[0].dataIndex].label,
                            label: item => points[item.dataIndex].delta,
                        },
                    },
                    secdashBubbleFx: {
                        glow: true,
                        orbitCenter,
                        centerLabel: i => points[i].letter,
                        pointRadii: points.map(p => p.r),
                        minRadius: 11,
                    },
                },
            },
        });
    },

    // Click-driven detail panel — the ONE place that renders the real
    // underlying data behind a Category Signal Map bubble: every lane
    // joined via CARD_DEFS.laneIds, plus (for On-Chain Intel specifically)
    // the real `gap_patterns` field already fetched by
    // agents/build_security_dashboard.py but never surfaced anywhere in
    // the UI until now.
    _toggleSignalMapDetail(idx) {
        const panel = document.getElementById('secdash-signalmap-detail');
        if (!panel) return;
        const legend = document.getElementById('secdash-signalmap-legend');
        if (this._signalMapOpenIdx === idx) {
            panel.hidden = true;
            this._signalMapOpenIdx = null;
            legend?.querySelectorAll('.secdash-signalmap-item').forEach(el => el.classList.remove('is-active'));
            return;
        }
        this._signalMapOpenIdx = idx;
        const def = CARD_DEFS[idx];
        const byId = this._signalMapById || {};
        const lanes = (def.laneIds || []).map(id => byId[id]).filter(Boolean);
        const rowsHtml = lanes.map(l => {
            const status = this._laneStatus(l);
            const color = this._laneStatusColor(status);
            const when = l.last_run_at ? ago(l.last_run_at) : 'no runs yet';
            return `<div class="secdash-signalmap-detail-row">
                <span class="secdash-signalmap-detail-label" style="color:${escapeHtml(color)}">${escapeHtml(l.label || l.id)}</span>
                <span class="secdash-signalmap-detail-value">${escapeHtml(l.headline || this._laneStatusTitle(status))} · ${escapeHtml(when)}</span>
            </div>`;
        }).join('');
        const primary = lanes[0];
        const gaps = def.id === 'intel-sweeps' && primary && Array.isArray(primary.gap_patterns) ? primary.gap_patterns : [];
        const gapsHtml = gaps.length ? `<div class="secdash-signalmap-detail-gaps">${gaps.map(g => `<span class="secdash-signalmap-detail-gap">${escapeHtml(g.label || g.id)}</span>`).join('')}</div>` : '';
        panel.innerHTML = `
            <div class="secdash-signalmap-detail-title">${escapeHtml(def.title)}<span class="secdash-signalmap-detail-close" data-close>Close ✕</span></div>
            ${rowsHtml || '<div class="text-zinc-500 text-[10.5px]">No underlying lane data.</div>'}
            ${gaps.length ? `<div class="secdash-signalmap-detail-label" style="margin-top:0.5rem;display:block;">Uncovered attack patterns (${gaps.length})</div>${gapsHtml}` : ''}
        `;
        panel.hidden = false;
        panel.querySelector('[data-close]')?.addEventListener('click', (e) => { e.stopPropagation(); this._toggleSignalMapDetail(idx); });
        legend?.querySelectorAll('.secdash-signalmap-item').forEach((el, i) => el.classList.toggle('is-active', i === idx));
    },

    // Findings-by-severity bubble timeline (real per-day counts,
    // agents/build_security_dashboard.py now buckets by calendar day, not
    // ISO week) — x = date, y = fixed severity tier (CRITICAL always plots
    // highest, INFO lowest, regardless of which buckets a given day has
    // data in), r = that day+severity's real count. Toggles to a
    // threat-level-over-time line, same as before. One y-axis throughout —
    // never a dual-axis combo.
    _setChartEmpty(emptyEl, canvas, message) {
        if (message) {
            if (emptyEl) { emptyEl.textContent = message; emptyEl.hidden = false; }
            canvas.style.visibility = 'hidden';
        } else {
            if (emptyEl) emptyEl.hidden = true;
            canvas.style.visibility = '';
        }
        const legend = document.getElementById('secdash-timeline-legend');
        if (legend) legend.hidden = !!message || this._timelineSeries !== 'severity';
    },

    _renderTimeline() {
        const canvas = document.getElementById('secdashTimelineChart');
        const emptyEl = document.getElementById('secdash-timeline-empty');
        const legend = document.getElementById('secdash-timeline-legend');
        if (!canvas || typeof Chart === 'undefined') return;
        if (this._timelineChart) { this._timelineChart.destroy(); this._timelineChart = null; }

        let cfg;
        if (this._timelineSeries === 'severity') {
            const timeline = this._data.findings_timeline || [];
            if (!timeline.length) {
                this._setChartEmpty(emptyEl, canvas, 'No timeline data yet.');
                return;
            }
            if (legend) {
                legend.innerHTML = SEV_ORDER.map(k => `<span class="secdash-timeline-legend-item">
                    <span class="secdash-sev-chip" style="background:${escapeHtml(sevColor(k))}"></span>${escapeHtml(SEV_TITLE[k])}
                </span>`).join('');
            }
            const labels = timeline.map(t => t.period);
            // A real min-width (28px per day) on the chart container, same
            // rationale as the Category Signal Map above — one bubble per
            // day+severity needs real horizontal room, so it scrolls on a
            // narrow viewport instead of every day's bubbles overlapping.
            const chartWrap = canvas.closest('.chart-shell');
            if (chartWrap) chartWrap.style.minWidth = `${Math.max(500, labels.length * 28)}px`;
            const points = [];
            timeline.forEach((t, x) => {
                SEV_ORDER.forEach(k => {
                    const count = t[k] || 0;
                    if (count > 0) points.push({ x, y: sevTier(k), r: Math.max(4, Math.min(20, Math.sqrt(count) * 3.5)), sev: k, count, period: t.period });
                });
            });
            cfg = {
                type: 'bubble',
                data: {
                    datasets: [{
                        data: points,
                        backgroundColor: points.map(p => sevColor(p.sev) + 'b3'),
                        borderColor: points.map(p => sevColor(p.sev)),
                        borderWidth: 1,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                title: items => points[items[0].dataIndex].period,
                                label: item => `${SEV_TITLE[points[item.dataIndex].sev]}: ${points[item.dataIndex].count}`,
                            },
                        },
                        secdashBubbleFx: {
                            glow: true,
                            centerLabel: i => String(points[i].count),
                            pointRadii: points.map(p => p.r),
                            minRadius: 9,
                        },
                    },
                    scales: {
                        x: {
                            min: -0.5, max: labels.length - 0.5,
                            ticks: {
                                color: '#71717a', font: { size: 9 },
                                callback: v => labels[v] ? labels[v].slice(5) : '',
                                maxRotation: 0, autoSkip: true,
                            },
                            grid: { display: false },
                        },
                        y: {
                            min: 0.3, max: SEV_ORDER.length + 0.7,
                            ticks: { color: '#71717a', stepSize: 1, font: { size: 9 }, callback: v => SEV_TITLE[SEV_ORDER[SEV_ORDER.length - v]] || '' },
                            grid: { color: 'rgba(255,255,255,0.05)' },
                        },
                    },
                },
            };
        } else {
            if (legend) legend.innerHTML = '';
            const chartWrap = canvas.closest('.chart-shell');
            if (chartWrap) chartWrap.style.minWidth = '';
            const points = this._history;
            if (!points.length) {
                this._setChartEmpty(emptyEl, canvas, 'Tracking since launch. No history yet.');
                return;
            }
            const levelToY = { LOW: 1, MEDIUM: 2, HIGH: 3 };
            cfg = {
                type: 'line',
                data: {
                    labels: points.map(p => new Date(p.ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })),
                    datasets: [{
                        label: 'Threat level', data: points.map(p => levelToY[(p.overall_threat_level || '').toUpperCase()] || null),
                        borderColor: sevColor('HIGH'), backgroundColor: 'transparent', stepped: true, pointRadius: 3,
                    }],
                },
                options: {
                    ...this._barOptions(false),
                    scales: {
                        ...this._barOptions(false).scales,
                        y: { min: 0.5, max: 3.5, ticks: { color: '#71717a', stepSize: 1, callback: v => ({ 1: 'LOW', 2: 'MEDIUM', 3: 'HIGH' }[v] || '') }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    },
                },
            };
        }
        this._setChartEmpty(emptyEl, canvas, null);
        this._timelineChart = new Chart(canvas, cfg);
    },

    _barOptions(stacked) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#a1a1aa', boxWidth: 8, font: { size: 9.5 } } } },
            scales: {
                x: { stacked, ticks: { color: '#71717a', font: { size: 9.5 } }, grid: { display: false } },
                y: { stacked, ticks: { color: '#71717a', font: { size: 9.5 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
            },
        };
    },

    // Findings per Status — a compact per-verdict bar list (dot + label +
    // proportional fill + count + %), not a full Chart.js canvas. Real
    // per-verdict counts from findings_by_verdict, same data the old bar
    // chart read; just rendered as a small purpose-built component sized to
    // sit beside the equally-compact Risk Level strip (see index.html's
    // lg:grid-cols-2 pairing).
    _renderVerdictBars() {
        const body = document.getElementById('secdash-verdict-body');
        if (!body) return;
        const byVerdict = this._data.findings_by_verdict || {};
        const order = ['PROCEED', 'CAUTION', 'REJECT'];
        const titles = { PROCEED: 'Proceed', CAUTION: 'Caution', REJECT: 'Reject' };
        const colors = { PROCEED: sevColor('LOW'), CAUTION: sevColor('MEDIUM'), REJECT: sevColor('HIGH') };
        const rows = order.filter(k => (byVerdict[k] || 0) > 0);
        const total = order.reduce((s, k) => s + (byVerdict[k] || 0), 0);
        if (!rows.length) {
            body.innerHTML = '<span class="text-zinc-500 text-xs">No verdict-bearing findings yet.</span>';
            return;
        }
        const max = Math.max(...rows.map(k => byVerdict[k]));
        body.innerHTML = rows.map(k => {
            const v = byVerdict[k];
            const pct = total ? (v / total) * 100 : 0;
            const widthPct = max ? (v / max) * 100 : 0;
            const color = colors[k];
            return `<div class="secdash-verdict-row">
                <span class="secdash-verdict-dot" style="background:${escapeHtml(color)}"></span>
                <span class="secdash-verdict-label">${escapeHtml(titles[k])}</span>
                <span class="secdash-verdict-bar-wrap"><span class="secdash-verdict-bar" style="width:${widthPct}%;background:${escapeHtml(color)}"></span></span>
                <span class="secdash-verdict-count">${v.toLocaleString()}</span>
                <span class="secdash-verdict-pct">${pct.toFixed(1)}%</span>
            </div>`;
        }).join('');
    },

    _wireTimelineToggle() {
        const group = document.getElementById('secdash-timeline-toggle');
        if (!group) return;
        group.querySelectorAll('.secdash-timeline-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._timelineSeries = btn.dataset.series;
                group.querySelectorAll('.secdash-timeline-btn').forEach(b => {
                    b.classList.toggle('term-btn-active', b === btn);
                    b.setAttribute('aria-pressed', String(b === btn));
                });
                this._renderTimeline();
            });
        });
    },

    // Findings Ledger — a real, searchable/filterable/paginated table over
    // security-dashboard.json's findings_recent (the most recent ~150 real
    // findings.jsonl rows, newest first). Row click expands a detail line
    // with the full real record: absolute timestamp, tags, verdict (only
    // when it's a real PROCEED/CAUTION/REJECT investigation verdict — some
    // sources like news_reporter.py reuse this same JSON key for an
    // unrelated news category, so a value outside that set is shown as
    // plain context text instead of a misleading verdict badge), and a
    // link to the source report when one exists.
    _ledgerRows() {
        const all = this._data.findings_recent || [];
        const q = this._ledgerQuery.trim().toLowerCase();
        return all.filter(r => {
            if (this._ledgerSevFilter && r.severity !== this._ledgerSevFilter) return false;
            if (!q) return true;
            const hay = [r.title, r.source, ...(r.tags || [])].filter(Boolean).join(' ').toLowerCase();
            return hay.includes(q);
        });
    },

    _renderLedger() {
        const body = document.getElementById('secdash-ledger-body');
        const countEl = document.getElementById('secdash-ledger-count');
        const pageEl = document.getElementById('secdash-ledger-page');
        const prevBtn = document.getElementById('secdash-ledger-prev');
        const nextBtn = document.getElementById('secdash-ledger-next');
        if (!body) return;

        const rows = this._ledgerRows();
        const size = this._ledgerPageSize;
        const total = rows.length;
        const pages = Math.max(1, Math.ceil(total / size));
        if (this._ledgerPage > pages - 1) this._ledgerPage = pages - 1;
        const page = this._ledgerPage;
        const slice = rows.slice(page * size, page * size + size);

        if (!total) {
            body.innerHTML = `<tr><td colspan="5" class="text-zinc-500 text-xs py-4 text-center">${this._data.findings_recent && this._data.findings_recent.length ? 'No findings match this filter.' : 'No findings logged yet.'}</td></tr>`;
        } else {
            body.innerHTML = slice.map((r, i) => this._ledgerRowHtml(r, page * size + i)).join('');
            body.querySelectorAll('.secdash-ledger-row').forEach(tr => {
                tr.addEventListener('click', () => {
                    const detail = body.querySelector(`.secdash-ledger-detail[data-for="${tr.dataset.idx}"]`);
                    if (detail) detail.classList.toggle('is-open');
                    tr.classList.toggle('is-expanded');
                });
            });
        }

        if (countEl) countEl.textContent = total ? `Showing ${page * size + 1}–${Math.min(total, page * size + size)} of ${total}` : 'No results';
        if (pageEl) pageEl.textContent = `Page ${page + 1} of ${pages}`;
        if (prevBtn) prevBtn.disabled = page <= 0;
        if (nextBtn) nextBtn.disabled = page >= pages - 1;
    },

    _ledgerRowHtml(r, idx) {
        const sevColorVal = sevColor(r.severity);
        // Subtle severity wash on the first cell only — a decorative
        // reinforcement of the badge's own icon+text right beside it, never
        // the sole conveyor of meaning. A small pulsing health dot on
        // CRITICAL rows is a genuine "needs attention" cue, reusing the
        // site's existing live-dot animation.
        const rowWash = (r.severity === 'CRITICAL' || r.severity === 'HIGH') ? `${sevColorVal}12` : 'transparent';
        const healthDot = r.severity === 'CRITICAL' ? `<span class="secdash-ledger-health-dot" style="color:${escapeHtml(sevColorVal)}"></span>` : '';
        const tagsHtml = (r.tags || []).slice(0, 4).map(t => `<span class="secdash-ledger-tag">${escapeHtml(t)}</span>`).join('');
        const allTagsHtml = (r.tags || []).map(t => `<span class="secdash-ledger-tag">${escapeHtml(t)}</span>`).join('');
        const verdictKnown = KNOWN_VERDICTS.includes(r.verdict);
        const reportUrl = r.report ? REPO_BLOB + r.report : null;
        const absTime = r.timestamp ? new Date(r.timestamp).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'unknown';
        return `<tr class="secdash-ledger-row" data-idx="${idx}" style="--row-sev:${escapeHtml(sevColorVal)};--row-sev-wash:${escapeHtml(rowWash)}">
            <td><span class="secdash-badge" style="color:${escapeHtml(sevColorVal)};border-color:${escapeHtml(sevColorVal)}55">
                <i class="fa-solid ${escapeHtml(SEV_ICON[r.severity] || 'fa-circle-question')} text-[9px]"></i>${escapeHtml(SEV_TITLE[r.severity] || r.severity)}
            </span>${healthDot}</td>
            <td class="secdash-ledger-title">${escapeHtml(r.title || 'Untitled finding')}</td>
            <td class="secdash-ledger-source">${escapeHtml((r.source || '').replace(/^agents\//, ''))}</td>
            <td class="secdash-ledger-tags">${tagsHtml}</td>
            <td class="secdash-ledger-time" title="${escapeHtml(r.timestamp || '')}">${escapeHtml(ago(r.timestamp))}<i class="fa-solid fa-chevron-down secdash-ledger-chevron"></i></td>
        </tr>
        <tr class="secdash-ledger-detail" data-for="${idx}">
            <td colspan="5">
                <div class="secdash-ledger-detail-inner">
                    <div class="secdash-ledger-detail-field"><span class="secdash-ledger-detail-label">ID</span><span class="font-mono">${escapeHtml(r.id || '—')}</span></div>
                    <div class="secdash-ledger-detail-field"><span class="secdash-ledger-detail-label">Severity</span>${escapeHtml(SEV_TITLE[r.severity] || r.severity)}</div>
                    <div class="secdash-ledger-detail-field"><span class="secdash-ledger-detail-label">Logged</span>${escapeHtml(absTime)} (${escapeHtml(ago(r.timestamp))})</div>
                    ${verdictKnown ? `<div class="secdash-ledger-detail-field"><span class="secdash-ledger-detail-label">Verdict</span>${escapeHtml(r.verdict)}</div>` : ''}
                    ${allTagsHtml ? `<div class="secdash-ledger-detail-tags">${allTagsHtml}</div>` : ''}
                    ${reportUrl ? `<div class="secdash-ledger-detail-link"><a href="${escapeHtml(reportUrl)}" target="_blank" rel="noopener" class="text-zinc-300 hover:underline">View source report <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a></div>` : ''}
                </div>
            </td>
        </tr>`;
    },

    // Ledger header mini-sparkline — real daily finding-volume trend, the
    // same findings_timeline data backing the Signal Timeline chart above,
    // just summed across severities per day. Plain div bars (see
    // x402feed.js's own _renderSparkline for the established pattern this
    // mirrors at a much smaller scale), not a second Chart.js instance, for
    // a glance-value accent beside the panel title.
    _renderLedgerSpark() {
        const el = document.getElementById('secdash-ledger-spark');
        if (!el) return;
        const timeline = (this._data.findings_timeline || []).slice(-14);
        if (!timeline.length) { el.innerHTML = ''; return; }
        const totals = timeline.map(t => SEV_ORDER.reduce((s, k) => s + (t[k] || 0), 0));
        const max = Math.max(1, ...totals);
        el.innerHTML = timeline.map((t, i) => {
            const pct = Math.max(6, Math.round((totals[i] / max) * 100));
            const latest = i === timeline.length - 1 ? ' is-latest' : '';
            return `<div class="secdash-ledger-spark-bar${latest}" style="height:${pct}%" title="${escapeHtml(t.period)}: ${totals[i]} finding(s)"></div>`;
        }).join('');
    },

    _wireLedgerControls() {
        const search = document.getElementById('secdash-ledger-search');
        const sevSelect = document.getElementById('secdash-ledger-sev-filter');
        const prevBtn = document.getElementById('secdash-ledger-prev');
        const nextBtn = document.getElementById('secdash-ledger-next');
        if (search) {
            search.addEventListener('input', () => {
                this._ledgerQuery = search.value;
                this._ledgerPage = 0;
                this._renderLedger();
            });
        }
        if (sevSelect) {
            sevSelect.innerHTML = '<option value="">All severities</option>' +
                SEV_ORDER.map(k => `<option value="${k}">${escapeHtml(SEV_TITLE[k])}</option>`).join('');
            sevSelect.addEventListener('change', () => {
                this._ledgerSevFilter = sevSelect.value;
                this._ledgerPage = 0;
                this._renderLedger();
            });
        }
        if (prevBtn) prevBtn.addEventListener('click', () => { this._ledgerPage = Math.max(0, this._ledgerPage - 1); this._renderLedger(); });
        if (nextBtn) nextBtn.addEventListener('click', () => { this._ledgerPage += 1; this._renderLedger(); });
    },
};

window.SecurityDashboard = SecurityDashboard;
document.addEventListener('DOMContentLoaded', () => SecurityDashboard.init());
