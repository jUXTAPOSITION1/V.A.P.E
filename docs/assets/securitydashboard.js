// VAPE's own Security Dashboard — reads data/security-dashboard.json (a
// fully-regenerated snapshot, refreshed every 6h by
// agents/build_security_dashboard.py) plus data/security-dashboard-history.jsonl
// (one real appended line per run, feeding the threat-level-over-time toggle).
// Every field traces to a real file (skillforge/memory/findings.jsonl, its
// tamper-evidence chain, data/attack-feed.json) or a real GitHub API response
// (Actions Runs, Code Scanning Alerts) — a lane whose signal can't be reached
// reports null and renders an honest "unavailable" state, never a fabricated
// number. Deliberately compact/single-screen layout (gauge, severity list +
// donut, and a lane picker share one row; six Risk Breakdown cards share
// another) rather than one full-width panel per widget.

const SECDASH_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/security-dashboard.json';
const SECDASH_HISTORY_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/security-dashboard-history.jsonl';

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
    { id: 'codeql', title: 'Static Analysis', laneIds: ['codeql'] },
    { id: 'dependency-audit', title: 'Dependencies', laneIds: ['dependency-audit'] },
    { id: 'security-lint', title: 'CI Hardening', laneIds: ['security-lint'] },
    { id: 'redteam', title: 'AI Red-Team', laneIds: ['redteam', 'redteam-deep'] },
    { id: 'intel-sweeps', title: 'On-Chain Intel', laneIds: ['intel-sweeps'] },
    { id: 'ledger-integrity', title: 'Ledger Integrity', laneIds: ['findings-seal', 'review-ledger'] },
];

const SecurityDashboard = {
    _data: null,
    _history: [],
    _lanes: [],
    _gaugeChart: null,
    _sevChart: null,
    _verdictChart: null,
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
        // Each panel renders independently — one throwing (a malformed field
        // in a given lane, a missing canvas) must not leave its siblings
        // stuck in their skeleton state.
        for (const fn of [this._renderGauge, this._renderSeverityDonut, this._renderLanes,
            this._renderCards, this._renderTimeline, this._renderVerdictChart, this._wireTimelineToggle]) {
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
        const laneDetail = document.getElementById('secdash-lane-detail');
        if (laneDetail) laneDetail.innerHTML = '<span class="text-zinc-500 text-xs">Snapshot unavailable.</span>';
        const cards = document.getElementById('secdash-cards');
        if (cards) {
            cards.innerHTML = CARD_DEFS.map(def =>
                `<div class="panel-sm secdash-card"><div class="secdash-card-title">${escapeHtml(def.title)}</div>` +
                `<span class="secdash-card-delta">Unavailable.</span></div>`).join('');
        }
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
    },

    // Findings Count: a real count+percentage list (doubling as the
    // required legend for a ≥2-series chart) beside a small donut with a
    // real total in its center — matches the reference's list-plus-donut
    // composition, more scannable than a bottom legend alone.
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
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: c => `${c.label}: ${c.parsed} (${((c.parsed / total) * 100).toFixed(1)}%)` } },
                },
            },
        });
        const totalValue = document.getElementById('secdash-sev-donut-total-value');
        if (totalValue) totalValue.textContent = total.toLocaleString();
    },

    // Automated Lanes — a <select> over the real per-workflow list driving
    // one compact status readout, with pagination dots to page through the
    // rest. Replaces the reference screenshot's fabricated "Active
    // Campaigns" gauge+carousel concept (VAPE has no campaign notion) while
    // keeping its dropdown+paged-indicator composition.
    _renderLanes() {
        const select = document.getElementById('secdash-lane-select');
        const detail = document.getElementById('secdash-lane-detail');
        const dots = document.getElementById('secdash-lane-dots');
        if (!select || !detail) return;
        const lanes = this._data.lanes || [];
        this._lanes = lanes;
        if (!lanes.length) {
            detail.innerHTML = '<span class="text-zinc-500 text-xs">No lane data this cycle.</span>';
            select.innerHTML = '';
            if (dots) dots.innerHTML = '';
            return;
        }
        select.innerHTML = lanes.map((l, i) => `<option value="${i}">${escapeHtml(l.label || l.id)}</option>`).join('');
        select.addEventListener('change', () => this._renderLaneDetail(Number(select.value)));
        if (dots) {
            dots.innerHTML = lanes.map((l, i) => `<button type="button" class="secdash-lane-dot" data-idx="${i}" aria-current="false" aria-label="${escapeHtml(l.label || l.id)}"></button>`).join('');
            dots.querySelectorAll('.secdash-lane-dot').forEach(btn => {
                btn.addEventListener('click', () => this._renderLaneDetail(Number(btn.dataset.idx)));
            });
        }
        this._renderLaneDetail(0);
    },

    _renderLaneDetail(idx) {
        const detail = document.getElementById('secdash-lane-detail');
        const dots = document.getElementById('secdash-lane-dots');
        const select = document.getElementById('secdash-lane-select');
        const lane = this._lanes[idx];
        if (!detail || !lane) return;
        const ok = lane.last_run_conclusion === 'success';
        const color = lane.last_run_conclusion == null ? sevColor('INFO') : ok ? sevColor('LOW') : sevColor('CRITICAL');
        const icon = lane.last_run_conclusion == null ? 'fa-circle-question' : ok ? 'fa-circle-check' : 'fa-circle-xmark';
        detail.innerHTML = `
            ${statusBadge(lane.headline || lane.last_run_conclusion || 'unavailable', color, icon)}
            <span class="text-[10px] text-zinc-600">${lane.last_run_at ? escapeHtml(ago(lane.last_run_at)) : 'no runs yet'}</span>
        `;
        if (dots) dots.querySelectorAll('.secdash-lane-dot').forEach((d, i) => {
            d.classList.toggle('is-active', i === idx);
            d.setAttribute('aria-current', String(i === idx));
        });
        if (select) select.value = String(idx);
    },

    // Six compact Risk Breakdown cards, one row (not a wrapping grid of
    // larger cards) — each a small ring + single-letter status badge (the
    // reference's own colored-circle-with-letter convention), a title, a
    // real delta line, and a tick-bar built from THAT card's own real
    // sub-fields with the exact real counts printed beneath it. Most lanes
    // only carry a pass/fail conclusion, not a severity split, so the bar's
    // segments/tick numbers are whatever that lane genuinely has — never
    // forced onto the 5-severity taxonomy where no real breakdown exists.
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
                <div class="secdash-card-head">
                    <div class="secdash-ring-wrap">${this._ringSvg(0, sevColor('INFO'))}<span class="secdash-ring-badge" style="color:${escapeHtml(sevColor('INFO'))}">?</span></div>
                    <div class="flex-1 min-w-0"><div class="secdash-card-title">${escapeHtml(def.title)}</div></div>
                </div>
                <span class="secdash-card-delta">No data this cycle.</span>
            </div>`;
        }
        const primary = lanes[0];
        // ringStatus drives the ring fill fraction explicitly (never derived
        // from comparing rendered colors, which breaks if two severity
        // tokens ever resolve to the same hex): 'low' = full ring (all
        // clear), 'info' = empty ring (no signal), anything else = a
        // partial ring indicating an open issue.
        let segs, letter, letterColor, delta, ticks, ringStatus;

        if (def.id === 'codeql') {
            const open = primary.open_alerts;
            const persisted = primary.persisted_high_critical_30d || 0;
            const clear = open === 0 && persisted === 0;
            letter = open == null ? '?' : clear ? 'OK' : 'H';
            ringStatus = open == null ? 'info' : clear ? 'low' : 'other';
            letterColor = ringStatus === 'info' ? sevColor('INFO') : ringStatus === 'low' ? sevColor('LOW') : sevColor('HIGH');
            delta = open == null ? 'unavailable' : `${persisted} persisted, 30d`;
            segs = open == null ? [] : (clear ? [{ v: 1, c: sevColor('LOW') }] : [{ v: Math.max(open, 1), c: sevColor('HIGH') }, { v: persisted, c: sevColor('CRITICAL') }]);
            ticks = open == null ? [] : [open, persisted];
        } else if (def.id === 'dependency-audit' || def.id === 'security-lint') {
            const ok = primary.last_run_conclusion === 'success';
            letter = ok ? 'OK' : primary.last_run_conclusion == null ? '?' : '!';
            ringStatus = ok ? 'low' : primary.last_run_conclusion == null ? 'info' : 'other';
            letterColor = ringStatus === 'low' ? sevColor('LOW') : ringStatus === 'info' ? sevColor('INFO') : sevColor('CRITICAL');
            delta = primary.last_run_at ? ago(primary.last_run_at) : 'never run';
            segs = primary.last_run_conclusion == null ? [] : [{ v: 1, c: ok ? sevColor('LOW') : sevColor('CRITICAL') }];
            ticks = [];
        } else if (def.id === 'redteam') {
            const bd = primary.severity_breakdown || {};
            const total = SEV_ORDER.reduce((s, k) => s + (bd[k] || 0), 0);
            const bad = (bd.CRITICAL || 0) + (bd.HIGH || 0);
            letter = total === 0 ? 'OK' : bad > 0 ? 'H' : 'L';
            ringStatus = (total === 0 || bad === 0) ? 'low' : 'other';
            letterColor = ringStatus === 'low' ? sevColor('LOW') : sevColor('HIGH');
            delta = `${total} findings, 30d`;
            segs = SEV_ORDER.filter(k => (bd[k] || 0) > 0).map(k => ({ v: bd[k], c: sevColor(k) }));
            ticks = SEV_ORDER.filter(k => (bd[k] || 0) > 0).map(k => bd[k]);
        } else if (def.id === 'intel-sweeps') {
            const ratio = typeof primary.coverage_ratio === 'number' ? primary.coverage_ratio : null;
            letter = primary.threat_level === 'HIGH' ? 'H' : primary.threat_level === 'MEDIUM' ? 'M' : primary.threat_level === 'LOW' ? 'L' : '?';
            ringStatus = primary.threat_level === 'LOW' ? 'low' : (primary.threat_level === 'HIGH' || primary.threat_level === 'MEDIUM') ? 'other' : 'info';
            letterColor = primary.threat_level === 'HIGH' ? sevColor('CRITICAL') : primary.threat_level === 'MEDIUM' ? sevColor('MEDIUM')
                : primary.threat_level === 'LOW' ? sevColor('LOW') : sevColor('INFO');
            const gaps = (primary.gap_patterns || []).length;
            delta = ratio == null ? 'unavailable' : `${Math.round(ratio * 100)}% covered, ${gaps} gap(s)`;
            segs = ratio == null ? [] : [{ v: ratio, c: sevColor('LOW') }, { v: 1 - ratio, c: sevColor('MEDIUM') }];
            ticks = [];
        } else { // ledger-integrity
            const seal = lanes.find(l => l.id === 'findings-seal') || primary;
            const drift = lanes.find(l => l.id === 'review-ledger');
            const intact = seal.chain_intact;
            letter = intact === true ? 'OK' : intact === false ? '!' : '?';
            ringStatus = intact === true ? 'low' : intact === false ? 'other' : 'info';
            letterColor = ringStatus === 'low' ? sevColor('LOW') : ringStatus === 'info' ? sevColor('INFO') : sevColor('CRITICAL');
            const worsened = drift ? (drift.worsened_30d || 0) : 0;
            const improved = drift ? (drift.improved_30d || 0) : 0;
            delta = `${worsened} worse / ${improved} better, 30d`;
            segs = (worsened + improved) === 0 ? [{ v: 1, c: sevColor('LOW') }] : [{ v: worsened, c: sevColor('HIGH') }, { v: improved, c: sevColor('LOW') }];
            ticks = (worsened + improved) === 0 ? [] : [worsened, improved];
        }

        const ringFrac = ringStatus === 'low' ? 1 : ringStatus === 'info' ? 0 : 0.7;
        const ringSvg = this._ringSvg(ringFrac, letterColor);
        const barHtml = segs.length
            ? `<div class="secdash-tick-bar">${segs.map(s => `<div class="secdash-tick-seg" style="flex:${Math.max(s.v, 0.02)} 0 auto; background:${escapeHtml(s.c)}"></div>`).join('')}</div>`
            : `<div class="secdash-tick-bar"><div class="secdash-tick-seg" style="flex:1 0 auto; background:${escapeHtml(sevColor('INFO'))}"></div></div>`;
        const ticksHtml = ticks.length
            ? `<div class="secdash-tick-labels">${ticks.map(t => `<span>${escapeHtml(String(t))}</span>`).join('')}</div>`
            : '';

        return `<div class="panel-sm secdash-card">
            <div class="secdash-card-head">
                <div class="secdash-ring-wrap">${ringSvg}<span class="secdash-ring-badge" style="color:${escapeHtml(letterColor)}">${escapeHtml(letter)}</span></div>
                <div class="flex-1 min-w-0"><div class="secdash-card-title">${escapeHtml(def.title)}</div></div>
            </div>
            ${barHtml}
            ${ticksHtml}
            <span class="secdash-card-delta">${escapeHtml(delta)}</span>
        </div>`;
    },

    // A plain inline SVG ring (no Chart.js instance per card — six live
    // chart instances for a coarse two-tone ring would be wasteful) using
    // stroke-dasharray for the fill fraction, matching the reference's
    // small ring-gauge shape.
    _ringSvg(frac, color) {
        const r = 13, c = 2 * Math.PI * r, filled = Math.max(0, Math.min(1, frac)) * c;
        return `<svg viewBox="0 0 32 32" width="34" height="34">
            <circle cx="16" cy="16" r="${r}" fill="none" stroke="${escapeHtml(cssVar('--bg-panel-sm') || '#27272a')}" stroke-width="3"/>
            <circle cx="16" cy="16" r="${r}" fill="none" stroke="${escapeHtml(color)}" stroke-width="3"
                stroke-dasharray="${filled} ${c}" stroke-linecap="round" transform="rotate(-90 16 16)"/>
        </svg>`;
    },

    // Findings-by-severity-over-time (bar, grouped by severity) with a
    // toggle to threat-level-over-time (line) — one y-axis, never a dual-axis
    // combo. The severity series is backfillable today from real historical
    // findings.jsonl timestamps; the threat-level series has no retained
    // history before this dashboard shipped, so it starts sparse and grows
    // forward with every real run appended to security-dashboard-history.jsonl
    // — never backfilled or faked to look fuller than it is.
    // Empty states toggle a sibling node rather than replacing
    // canvas.parentElement.innerHTML — destroying the canvas element would
    // permanently break every later render call (the severity/threat-level
    // toggle above all) since _renderTimeline/_renderVerdictChart both
    // guard on `if (!canvas) return`.
    _setChartEmpty(emptyEl, canvas, message) {
        if (message) {
            if (emptyEl) { emptyEl.textContent = message; emptyEl.hidden = false; }
            canvas.style.visibility = 'hidden';
        } else {
            if (emptyEl) emptyEl.hidden = true;
            canvas.style.visibility = '';
        }
    },

    _renderTimeline() {
        const canvas = document.getElementById('secdashTimelineChart');
        const emptyEl = document.getElementById('secdash-timeline-empty');
        if (!canvas || typeof Chart === 'undefined') return;
        if (this._timelineChart) { this._timelineChart.destroy(); this._timelineChart = null; }

        let cfg;
        if (this._timelineSeries === 'severity') {
            const timeline = this._data.findings_timeline || [];
            if (!timeline.length) {
                this._setChartEmpty(emptyEl, canvas, 'No timeline data yet.');
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
        } else {
            const points = this._history;
            if (!points.length) {
                this._setChartEmpty(emptyEl, canvas, 'Tracking since launch — no history yet.');
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

    _renderVerdictChart() {
        const canvas = document.getElementById('secdashVerdictChart');
        const emptyEl = document.getElementById('secdash-verdict-empty');
        if (!canvas || typeof Chart === 'undefined') return;
        const byVerdict = this._data.findings_by_verdict || {};
        const order = ['PROCEED', 'CAUTION', 'REJECT'];
        const colors = { PROCEED: sevColor('LOW'), CAUTION: sevColor('MEDIUM'), REJECT: sevColor('HIGH') };
        const labels = order.filter(k => (byVerdict[k] || 0) > 0);
        if (this._verdictChart) { this._verdictChart.destroy(); this._verdictChart = null; }
        if (!labels.length) {
            this._setChartEmpty(emptyEl, canvas, 'No verdict-bearing findings yet.');
            return;
        }
        this._setChartEmpty(emptyEl, canvas, null);
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
