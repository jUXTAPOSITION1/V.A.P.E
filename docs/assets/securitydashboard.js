// VAPE's own Security Dashboard — reads data/security-dashboard.json (a
// fully-regenerated snapshot, refreshed every 6h by
// agents/build_security_dashboard.py) plus data/security-dashboard-history.jsonl
// (one real appended line per run, feeding the threat-level-over-time toggle).
// Every field traces to a real file (skillforge/memory/findings.jsonl, its
// tamper-evidence chain, data/attack-feed.json) or a real GitHub API response
// (Actions Runs, Code Scanning Alerts) — a lane whose signal can't be reached
// reports null and renders an honest "unavailable" state, never a fabricated
// number. See the module's own inline comments for exactly how each widget's
// visual encoding maps back to a real underlying field.

const SECDASH_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/security-dashboard.json';
const SECDASH_HISTORY_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/security-dashboard-history.jsonl';

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// The 5-bucket severity taxonomy agents/build_security_dashboard.py's
// normalize_severity() produces — order matters for stacking/legend display
// (most severe first).
const SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
const SEV_VAR = { CRITICAL: '--sev-critical', HIGH: '--sev-high', MEDIUM: '--sev-medium', LOW: '--sev-low', INFO: '--sev-info' };
function sevColor(bucket) { return cssVar(SEV_VAR[bucket] || SEV_VAR.INFO); }

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

// One entry per real security workflow this repo runs, mapped to the six
// Risk Breakdown category cards. Every source field name here is real
// (agents/build_security_dashboard.py's build_lanes() output) — a card with
// no corresponding lane in a given snapshot simply renders "unavailable."
const CARD_DEFS = [
    { id: 'codeql', title: 'Static Analysis', icon: 'fa-magnifying-glass-chart', laneIds: ['codeql'] },
    { id: 'dependency-audit', title: 'Dependencies (SCA)', icon: 'fa-box-archive', laneIds: ['dependency-audit'] },
    { id: 'security-lint', title: 'CI / Workflow Hardening', icon: 'fa-gears', laneIds: ['security-lint'] },
    { id: 'redteam', title: 'AI Red-Team', icon: 'fa-robot', laneIds: ['redteam', 'redteam-deep'] },
    { id: 'intel-sweeps', title: 'On-Chain Attack Intelligence', icon: 'fa-satellite-dish', laneIds: ['intel-sweeps'] },
    { id: 'ledger-integrity', title: 'Findings Ledger Integrity', icon: 'fa-link', laneIds: ['findings-seal', 'review-ledger'] },
];

const SecurityDashboard = {
    _data: null,
    _history: [],
    _timelineChart: null,
    _timelineSeries: 'severity',

    async init() {
        const [data, history] = await Promise.all([this._fetchJson(), this._fetchHistory()]);
        this._data = data;
        this._history = history;
        if (!data) {
            this._renderUnavailable();
            return;
        }
        this._renderUpdated();
        this._renderGauge();
        this._renderSeverityDonut();
        this._renderLanes();
        this._renderCards();
        this._renderTimeline();
        this._renderVerdictChart();
        this._wireTimelineToggle();
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
    // with the explicit text label below it.
    _renderGauge() {
        const canvas = document.getElementById('secdashGauge');
        const label = document.getElementById('secdash-gauge-label');
        if (!canvas || typeof Chart === 'undefined') return;
        const level = (this._data.overall_threat_level || '').toUpperCase();
        const idx = THREAT_ORDER.indexOf(level);
        const frac = idx >= 0 ? (idx + 1) / THREAT_ORDER.length : 0;
        const color = idx === 2 ? sevColor('CRITICAL') : idx === 1 ? sevColor('MEDIUM') : idx === 0 ? sevColor('LOW') : sevColor('INFO');
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
                cutout: '75%',
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
            },
        });
        if (label) {
            const icon = THREAT_ICON[level] || 'fa-circle-question';
            label.innerHTML = idx >= 0
                ? `<div style="color:${escapeHtml(color)}" class="font-semibold text-sm"><i class="fa-solid ${escapeHtml(icon)} text-[11px] mr-1"></i>${escapeHtml(level)}</div>`
                : '<span class="text-zinc-500 text-xs">No signal</span>';
        }
    },

    _renderSeverityDonut() {
        const canvas = document.getElementById('secdashSeverityDonut');
        if (!canvas || typeof Chart === 'undefined') return;
        const bySev = this._data.findings_by_severity || {};
        const labels = SEV_ORDER.filter(k => (bySev[k] || 0) > 0);
        const values = labels.map(k => bySev[k]);
        const colors = labels.map(sevColor);
        if (this._sevChart) this._sevChart.destroy();
        if (!labels.length) {
            canvas.parentElement.innerHTML = '<div class="text-zinc-500 text-sm">No findings logged yet.</div>';
            return;
        }
        const total = values.reduce((a, b) => a + b, 0);
        this._sevChart = new Chart(canvas, {
            type: 'doughnut',
            data: { labels, datasets: [{ data: values, backgroundColor: colors, borderColor: cssVar('--bg-page') || '#09090b', borderWidth: 2 }] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#a1a1aa', boxWidth: 10, font: { size: 10 } } },
                    tooltip: { callbacks: { label: c => `${c.label}: ${c.parsed} (${((c.parsed / total) * 100).toFixed(1)}%)` } },
                },
            },
        });
    },

    // "Automated Security Lanes" strip — one tile per real workflow's last
    // run, from the dashboard's own `lanes` array. Replaces the reference
    // screenshot's fabricated "Active Campaigns" concept (VAPE has no
    // campaign notion) while keeping its horizontal-scroll motion, since the
    // underlying list is real.
    _renderLanes() {
        const el = document.getElementById('secdash-lanes');
        if (!el) return;
        const lanes = this._data.lanes || [];
        if (!lanes.length) {
            el.innerHTML = '<div class="text-zinc-500 text-sm">No lane data this cycle.</div>';
            return;
        }
        el.innerHTML = lanes.map(lane => {
            const ok = lane.last_run_conclusion === 'success';
            const color = lane.last_run_conclusion == null ? sevColor('INFO') : ok ? sevColor('LOW') : sevColor('CRITICAL');
            const icon = lane.last_run_conclusion == null ? 'fa-circle-question' : ok ? 'fa-circle-check' : 'fa-circle-xmark';
            return `<div class="panel-sm secdash-lane-tile">
                <span class="text-[11px] text-zinc-400 leading-snug">${escapeHtml(lane.label || lane.id)}</span>
                <span style="color:${escapeHtml(color)}" class="text-xs font-medium"><i class="fa-solid ${escapeHtml(icon)} text-[10px] mr-1"></i>${escapeHtml(lane.headline || lane.last_run_conclusion || 'unavailable')}</span>
                <span class="text-[10px] text-zinc-600">${lane.last_run_at ? escapeHtml(ago(lane.last_run_at)) : 'no runs yet'}</span>
            </div>`;
        }).join('');
    },

    // Six Risk Breakdown cards, each a ring + status badge + a horizontal
    // stacked bar built from THAT card's own real sub-fields (not a forced
    // fit onto the 5-severity taxonomy — most lanes don't carry a severity
    // breakdown at all, so inventing one there would fabricate structure
    // that doesn't exist). The ring's fill is deliberately coarse (1.0 when
    // clear, a fixed lower fraction otherwise) rather than a fabricated
    // fine-grained percentage with no real denominator behind it — the
    // exact real count/label is always shown as the ring's center text and
    // in the stat line beneath it.
    _renderCards() {
        const el = document.getElementById('secdash-cards');
        if (!el) return;
        const byId = {};
        for (const lane of this._data.lanes || []) byId[lane.id] = lane;
        el.innerHTML = CARD_DEFS.map(def => this._renderCard(def, byId)).join('');
    },

    _renderCard(def, byId) {
        const lanes = def.laneIds.map(id => byId[id]).filter(Boolean);
        if (!lanes.length) {
            return `<div class="panel-sm secdash-card">
                <div class="secdash-card-head"><i class="fa-solid ${escapeHtml(def.icon)} text-zinc-500"></i><span class="text-sm text-zinc-300">${escapeHtml(def.title)}</span></div>
                <span class="text-xs text-zinc-600">No data this cycle.</span>
            </div>`;
        }
        const primary = lanes[0];
        let segs, ringFrac, ringText, badge, stat;

        if (def.id === 'codeql') {
            const open = primary.open_alerts;
            const persisted = primary.persisted_high_critical_30d || 0;
            const clear = open === 0 && persisted === 0;
            ringFrac = clear ? 1 : 0.65;
            ringText = open == null ? '—' : String(open);
            badge = clear ? statusBadge('clear', sevColor('LOW'), 'fa-circle-check') : statusBadge(`${open ?? '?'} open`, sevColor('HIGH'), 'fa-triangle-exclamation');
            stat = `${open == null ? 'unavailable' : `${open} open alert(s)`} · ${persisted} persisted HIGH/CRITICAL, 30d`;
            segs = open == null ? [] : (clear ? [{ v: 1, c: sevColor('LOW') }] : [{ v: Math.max(open, 1), c: sevColor('HIGH') }, { v: persisted, c: sevColor('CRITICAL') }]);
        } else if (def.id === 'dependency-audit' || def.id === 'security-lint') {
            const ok = primary.last_run_conclusion === 'success';
            ringFrac = ok ? 1 : primary.last_run_conclusion == null ? 0 : 0.65;
            ringText = ok ? 'OK' : primary.last_run_conclusion == null ? '—' : '!';
            badge = ok ? statusBadge('passing', sevColor('LOW'), 'fa-circle-check')
                : primary.last_run_conclusion == null ? statusBadge('no runs yet', sevColor('INFO'), 'fa-circle-question')
                    : statusBadge(escapeHtml(primary.last_run_conclusion), sevColor('CRITICAL'), 'fa-circle-xmark');
            stat = `Last run: ${primary.last_run_at ? ago(primary.last_run_at) : 'never'}`;
            segs = primary.last_run_conclusion == null ? [] : [{ v: 1, c: ok ? sevColor('LOW') : sevColor('CRITICAL') }];
        } else if (def.id === 'redteam') {
            const bd = primary.severity_breakdown || {};
            const total = SEV_ORDER.reduce((s, k) => s + (bd[k] || 0), 0);
            const bad = (bd.CRITICAL || 0) + (bd.HIGH || 0);
            ringFrac = total === 0 ? 1 : bad === 0 ? 1 : 0.65;
            ringText = String(total);
            badge = bad > 0 ? statusBadge(`${bad} HIGH/CRIT`, sevColor('HIGH'), 'fa-triangle-exclamation') : statusBadge('clean', sevColor('LOW'), 'fa-circle-check');
            const deepNote = lanes[1] ? ` · deep sweep: ${lanes[1].headline || 'n/a'}` : '';
            stat = `${primary.headline || 'no data'}${deepNote}`;
            segs = SEV_ORDER.filter(k => (bd[k] || 0) > 0).map(k => ({ v: bd[k], c: sevColor(k) }));
        } else if (def.id === 'intel-sweeps') {
            const ratio = typeof primary.coverage_ratio === 'number' ? primary.coverage_ratio : null;
            ringFrac = ratio == null ? 0 : ratio;
            ringText = ratio == null ? '—' : `${Math.round(ratio * 100)}%`;
            badge = statusBadge(primary.threat_level || 'unknown', primary.threat_level === 'HIGH' ? sevColor('CRITICAL') : primary.threat_level === 'MEDIUM' ? sevColor('MEDIUM') : sevColor('LOW'), 'fa-satellite-dish');
            const gaps = (primary.gap_patterns || []).length;
            stat = ratio == null ? 'unavailable' : `${Math.round(ratio * 100)}% of known attack patterns covered · ${gaps} gap(s)`;
            segs = ratio == null ? [] : [{ v: ratio, c: sevColor('LOW') }, { v: 1 - ratio, c: sevColor('MEDIUM') }];
        } else { // ledger-integrity
            const seal = lanes.find(l => l.id === 'findings-seal') || primary;
            const drift = lanes.find(l => l.id === 'review-ledger');
            const intact = seal.chain_intact;
            ringFrac = intact === true ? 1 : intact === false ? 0.4 : 0.65;
            ringText = intact === true ? 'OK' : intact === false ? '!' : '—';
            badge = intact === true ? statusBadge('intact', sevColor('LOW'), 'fa-link')
                : intact === false ? statusBadge('broken', sevColor('CRITICAL'), 'fa-link-slash')
                    : statusBadge('unknown', sevColor('INFO'), 'fa-circle-question');
            const worsened = drift ? (drift.worsened_30d || 0) : 0;
            const improved = drift ? (drift.improved_30d || 0) : 0;
            stat = `Chain ${intact === true ? 'intact' : intact === false ? 'broken' : 'unknown'} · ${worsened} worsened / ${improved} improved, 30d`;
            segs = (worsened + improved) === 0 ? [{ v: 1, c: sevColor('LOW') }] : [{ v: worsened, c: sevColor('HIGH') }, { v: improved, c: sevColor('LOW') }];
        }

        const ringSvg = this._ringSvg(ringFrac, segs.length && segs[0] ? segs[0].c : sevColor('INFO'));
        const barHtml = segs.length
            ? `<div class="secdash-sev-bar">${segs.map(s => `<div class="secdash-sev-seg" style="flex:${Math.max(s.v, 0.02)} 0 auto; background:${escapeHtml(s.c)}"></div>`).join('')}</div>`
            : `<div class="secdash-sev-bar"><div class="secdash-sev-seg" style="flex:1 0 auto; background:${escapeHtml(sevColor('INFO'))}"></div></div>`;

        return `<div class="panel-sm secdash-card">
            <div class="secdash-card-head">
                <div class="secdash-ring-wrap">${ringSvg}<span class="secdash-ring-value">${escapeHtml(ringText)}</span></div>
                <div class="flex-1 min-w-0">
                    <div class="text-sm text-zinc-300 flex items-center gap-1.5"><i class="fa-solid ${escapeHtml(def.icon)} text-zinc-500 text-xs"></i>${escapeHtml(def.title)}</div>
                    ${badge}
                </div>
            </div>
            ${barHtml}
            <span class="text-[10.5px] text-zinc-600">${escapeHtml(stat)}</span>
        </div>`;
    },

    // A plain inline SVG ring (no Chart.js instance per card — six live
    // chart instances for a coarse two-tone ring would be wasteful) using
    // stroke-dasharray for the fill fraction, matching the reference's
    // small ring-gauge shape.
    _ringSvg(frac, color) {
        const r = 18, c = 2 * Math.PI * r, filled = Math.max(0, Math.min(1, frac)) * c;
        return `<svg viewBox="0 0 44 44" width="46" height="46">
            <circle cx="22" cy="22" r="${r}" fill="none" stroke="${escapeHtml(cssVar('--bg-panel-sm') || '#27272a')}" stroke-width="4"/>
            <circle cx="22" cy="22" r="${r}" fill="none" stroke="${escapeHtml(color)}" stroke-width="4"
                stroke-dasharray="${filled} ${c}" stroke-linecap="round" transform="rotate(-90 22 22)"/>
        </svg>`;
    },

    // Findings-by-severity-over-time (bar, grouped by severity) with a
    // toggle to threat-level-over-time (line) — one y-axis, never a dual-axis
    // combo. The severity series is backfillable today from real historical
    // findings.jsonl timestamps; the threat-level series has no retained
    // history before this dashboard shipped, so it starts sparse and grows
    // forward with every real run appended to security-dashboard-history.jsonl
    // — never backfilled or faked to look fuller than it is.
    _renderTimeline() {
        const canvas = document.getElementById('secdashTimelineChart');
        const note = document.getElementById('secdash-timeline-note');
        if (!canvas || typeof Chart === 'undefined') return;
        if (this._timelineChart) this._timelineChart.destroy();

        let cfg;
        if (this._timelineSeries === 'severity') {
            const timeline = this._data.findings_timeline || [];
            if (!timeline.length) {
                canvas.parentElement.innerHTML = '<div class="text-zinc-500 text-sm">No timeline data yet.</div>';
                return;
            }
            cfg = {
                type: 'bar',
                data: {
                    labels: timeline.map(t => t.period),
                    datasets: SEV_ORDER.filter(k => timeline.some(t => (t[k] || 0) > 0)).map(k => ({
                        label: k, data: timeline.map(t => t[k] || 0), backgroundColor: sevColor(k), stack: 'sev',
                    })),
                },
                options: this._barOptions(true),
            };
            if (note) note.textContent = 'Bucketed by real ISO week, from VAPE’s own findings ledger.';
        } else {
            const points = this._history;
            if (!points.length) {
                canvas.parentElement.innerHTML = '<div class="text-zinc-500 text-sm">Tracking since launch — no history yet. Check back after the next scheduled run.</div>';
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
            if (note) note.textContent = 'Tracking since this dashboard launched — never backfilled.';
        }
        this._timelineChart = new Chart(canvas, cfg);
    },

    _barOptions(stacked) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#a1a1aa', boxWidth: 10, font: { size: 10 } } } },
            scales: {
                x: { stacked, ticks: { color: '#71717a', font: { size: 10 } }, grid: { display: false } },
                y: { stacked, ticks: { color: '#71717a', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
            },
        };
    },

    _renderVerdictChart() {
        const canvas = document.getElementById('secdashVerdictChart');
        if (!canvas || typeof Chart === 'undefined') return;
        const byVerdict = this._data.findings_by_verdict || {};
        const order = ['PROCEED', 'CAUTION', 'REJECT'];
        const colors = { PROCEED: sevColor('LOW'), CAUTION: sevColor('MEDIUM'), REJECT: sevColor('HIGH') };
        const labels = order.filter(k => (byVerdict[k] || 0) > 0);
        if (!labels.length) {
            canvas.parentElement.innerHTML = '<div class="text-zinc-500 text-sm">No verdict-bearing findings yet.</div>';
            return;
        }
        if (this._verdictChart) this._verdictChart.destroy();
        this._verdictChart = new Chart(canvas, {
            type: 'bar',
            data: { labels, datasets: [{ data: labels.map(k => byVerdict[k]), backgroundColor: labels.map(k => colors[k]), borderRadius: 4 }] },
            options: { ...this._barOptions(false), plugins: { legend: { display: false } } },
        });
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
};

window.SecurityDashboard = SecurityDashboard;
document.addEventListener('DOMContentLoaded', () => SecurityDashboard.init());
