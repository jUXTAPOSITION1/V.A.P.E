// VAPE's live attack feed — the ticker between the nav and hero, and the
// full "Threat Ledger" section between the two case-study sections, both
// read the same data/attack-feed.json. That file is written by
// agents/security_sweep.py straight from DeFiLlama's real hacks feed (the
// same data its intel/reports/security-*.md reports use) — real, dated
// incidents only. An empty or unreachable feed renders an honest empty
// state; nothing here is ever fabricated to fill space.
import { resolveProtocolLogo } from './icons.js';

const ATTACK_FEED_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/attack-feed.json';
const REPORT_BLOB_BASE = 'https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/';

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function severityClass(amountUsdM) {
    const n = Number(amountUsdM) || 0;
    if (n >= 10) return { text: 'text-rose-400', pill: 'bg-rose-500/15 text-rose-400', dot: 'bg-rose-500' };
    if (n >= 1) return { text: 'text-amber-400', pill: 'bg-amber-500/15 text-amber-400', dot: 'bg-amber-500' };
    return { text: 'text-zinc-400', pill: 'bg-white/10 text-zinc-400', dot: 'bg-zinc-500' };
}

function fmtLoss(amountUsdM) {
    const n = Number(amountUsdM) || 0;
    if (n === 0) return '<$0.01M';
    if (n < 1) return `$${Math.round(n * 1000).toLocaleString()}K`;
    return `$${n.toLocaleString(undefined, { maximumFractionDigits: n >= 100 ? 0 : 1 })}M`;
}

function ago(dateStr) {
    const d = new Date(dateStr + 'T00:00:00Z');
    if (isNaN(d)) return dateStr;
    const days = Math.max(0, Math.floor((Date.now() - d.getTime()) / 86400000));
    if (days === 0) return 'today';
    if (days === 1) return 'yesterday';
    if (days < 30) return `${days}d ago`;
    return `${Math.round(days / 30)}mo ago`;
}

const THREAT_BADGE = {
    HIGH: '<span class="text-rose-400"><i class="fa-solid fa-circle text-[7px] align-middle mr-1"></i>THREAT LEVEL: HIGH</span>',
    MEDIUM: '<span class="text-amber-400"><i class="fa-solid fa-circle text-[7px] align-middle mr-1"></i>THREAT LEVEL: MEDIUM</span>',
    LOW: '<span class="text-emerald-400"><i class="fa-solid fa-circle text-[7px] align-middle mr-1"></i>THREAT LEVEL: LOW</span>',
};

const AttackFeed = {
    _data: null,
    _rotateHandle: null,
    _rotateIdx: 0,
    _paused: false,
    HOLD_MS: 5200,
    TRANSITION_MS: 320,

    async init() {
        try {
            const res = await fetch(`${ATTACK_FEED_URL}?t=${Date.now()}`);
            this._data = await res.json();
        } catch (e) {
            this._data = null;
        }
        this._renderTicker();
        this._renderLedger();
    },

    _incidents() {
        return (this._data && Array.isArray(this._data.incidents)) ? this._data.incidents : [];
    },

    // Placeholder only — never blocks the ticker/ledger's first paint on a
    // network round-trip for a purely decorative logo. `icons.js`'s
    // resolveProtocolLogo() (same page-lifetime-cached DeFiLlama /protocols
    // lookup already used by report.js's protocol chips, exact-name-match
    // only) fills these in asynchronously via _enhanceIcons() right after
    // render, same pattern as report.js::enhanceIcons().
    _iconHtml(name, sizeClass) {
        // visibility, not display: sizeClass already reserves a fixed box, so
        // a resolved icon fades in without shifting the adjacent text —
        // display:none/'' would pop the box in and reflow the row, most
        // visible during the ticker's periodic re-renders.
        return `<img class="protocol-icon ${sizeClass} rounded-full bg-white/5 object-cover shrink-0" data-protocol="${escapeHtml(name)}" alt="" style="visibility:hidden" onerror="this.style.visibility='hidden'" onload="this.style.visibility='visible'">`;
    },

    async _enhanceIcons(container) {
        if (!container) return;
        const imgs = [...container.querySelectorAll('.protocol-icon[data-protocol]')];
        await Promise.all(imgs.map(async img => {
            try {
                const logo = await resolveProtocolLogo(img.dataset.protocol);
                if (logo) img.src = logo;
            } catch (e) { /* decorative only — ignore lookup failures */ }
        }));
    },

    // Order matches how someone actually reads a threat line: what got hit,
    // how much it cost, what happened, how recent — not an absolute date
    // stamp up front eating space before you even know what the incident is.
    // Name/amount/recency are always visible; the technique description
    // shares space with the name and shrinks first on narrow viewports
    // rather than disappearing outright, so mobile still gets some of it.
    _tickerLineHtml(item) {
        const sev = severityClass(item.amount_usd_m);
        return `<span class="w-1.5 h-1.5 rounded-full ${sev.dot} shrink-0"></span>
            ${this._iconHtml(item.name, 'w-4 h-4')}
            <span class="text-zinc-200 font-medium truncate min-w-0" style="flex:2 1 0%">${escapeHtml(item.name)}</span>
            <span class="${sev.text} font-semibold shrink-0">${fmtLoss(item.amount_usd_m)}</span>
            <span class="text-zinc-600 truncate min-w-0" style="flex:1 1 0%">${escapeHtml(item.technique || '')}</span>
            <span class="text-zinc-700 shrink-0 font-mono text-[11px]">${escapeHtml(ago(item.date))}</span>`;
    },

    _renderTicker() {
        const line = document.getElementById('attack-ticker-line');
        const progress = document.getElementById('attack-ticker-progress');
        const wrap = document.getElementById('attack-ticker');
        if (!line || !wrap) return;

        const incidents = this._incidents();
        if (!incidents.length) {
            line.innerHTML = '<span class="text-zinc-600">No incidents in the tracked feed this cycle — the ticker fills in as soon as one lands.</span>';
            if (progress) progress.style.left = '-10%';
            return;
        }

        const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const render = () => {
            line.innerHTML = this._tickerLineHtml(incidents[this._rotateIdx]);
            this._enhanceIcons(line);
        };
        render();

        if (reduceMotion || incidents.length === 1) {
            if (progress) progress.parentElement.style.display = 'none';
            return; // static — no auto-rotation, no motion
        }

        const runProgress = () => {
            if (!progress) return;
            progress.style.transition = 'none';
            progress.style.left = '-10%';
            void progress.offsetWidth; // force reflow so the next transition actually animates from the start
            progress.style.transition = `left ${this.HOLD_MS}ms linear`;
            progress.style.left = '105%';
        };
        runProgress();

        const advance = () => {
            if (this._paused) return;
            line.classList.add('opacity-0', '-translate-y-1');
            setTimeout(() => {
                this._rotateIdx = (this._rotateIdx + 1) % incidents.length;
                render();
                line.classList.remove('opacity-0', '-translate-y-1');
                runProgress();
            }, this.TRANSITION_MS);
        };
        this._rotateHandle = setInterval(advance, this.HOLD_MS + this.TRANSITION_MS);

        // Pause on hover/focus — an auto-rotating feed that can't be paused
        // to actually read is a real accessibility miss (WCAG 2.2.2), not
        // just a nicety.
        // A CSS transition animates the rendered position, but the
        // specified `left` value is already '105%' from the instant the
        // transition starts — dropping the transition mid-flight without
        // freezing the position first snaps it straight to that end value
        // instead of holding wherever it visually was.
        const pause = () => {
            this._paused = true;
            if (!progress) return;
            const frozenLeft = getComputedStyle(progress).left;
            progress.style.transition = 'none';
            progress.style.left = frozenLeft;
        };
        const resume = () => { this._paused = false; runProgress(); };
        wrap.addEventListener('mouseenter', pause);
        wrap.addEventListener('mouseleave', resume);
        wrap.addEventListener('focusin', pause);
        wrap.addEventListener('focusout', resume);
    },

    _lessonHtml(lesson) {
        if (!lesson) return '';
        let tone = 'text-cyan-500/80';
        let note = lesson.prevention
            ? (lesson.covered_by ? 'already covered' : (lesson.out_of_scope ? 'out of scope' : 'coverage gap — noted'))
            : 'unclassified — investigated anyway';
        if (lesson.backtest && lesson.backtest.would_have_flagged === false) {
            tone = 'text-rose-400/80';
            note = 'model backtest miss';
        } else if (lesson.prevention && lesson.covered_by) {
            tone = 'text-emerald-500/70';
        }
        const title = lesson.prevention ? `${lesson.label}. Prevention: ${lesson.prevention}` : lesson.label;
        return `<div class="text-[10.5px] ${tone} mt-1 leading-relaxed" title="${escapeHtml(title)}">
            <i class="fa-solid fa-shield-halved text-[9px] mr-1"></i>${escapeHtml(lesson.label)} — ${escapeHtml(note)}</div>`;
    },

    // Stacked, not a single truncating row: a fixed date column used to eat
    // enough width on narrow screens that the name, technique, and lesson
    // all got ellipsis-cut to near-illegibility. Name+amount share the top
    // line (name truncates only if it's genuinely too long to fit next to
    // the amount badge); technique/chains and the lesson line wrap freely
    // instead of truncating; date+recency move to a compact trailing line.
    _ledgerRow(item) {
        const sev = severityClass(item.amount_usd_m);
        const chains = (item.chains || []).join(', ') || 'unknown chain';
        return `
        <div class="flex flex-col gap-1 bg-white/[0.03] hover:bg-white/[0.06] transition rounded-xl px-3.5 py-3">
            <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1 flex items-center gap-1.5">
                    ${this._iconHtml(item.name, 'w-4 h-4')}<span class="text-zinc-100 text-sm font-medium truncate">${escapeHtml(item.name)}</span>
                </div>
                <span class="shrink-0 px-2.5 py-1 rounded-lg text-xs font-semibold ${sev.pill}">${fmtLoss(item.amount_usd_m)}</span>
            </div>
            <div class="text-zinc-500 text-xs leading-relaxed">${escapeHtml(item.technique || 'technique unspecified')} · ${escapeHtml(chains)}</div>
            ${this._lessonHtml(item.lesson)}
            <div class="text-[10.5px] text-zinc-700 font-mono mt-0.5">${escapeHtml(item.date)} · ${escapeHtml(ago(item.date))}</div>
        </div>`;
    },

    _renderLedger() {
        const body = document.getElementById('threat-ledger-body');
        const updated = document.getElementById('threat-ledger-updated');
        const threatEl = document.getElementById('threat-ledger-threat');
        const sourceLink = document.getElementById('threat-ledger-source');
        if (!body) return;

        const data = this._data;
        const incidents = this._incidents();

        if (!data) {
            body.innerHTML = `<div class="text-center py-10 text-zinc-500 text-xs">
                <i class="fa-solid fa-satellite-dish text-xl mb-2 opacity-50 block"></i>
                Live threat feed temporarily unavailable — try again shortly.
            </div>`;
            if (updated) updated.textContent = 'unavailable';
            return;
        }

        if (!incidents.length) {
            body.innerHTML = `<div class="text-center py-10 text-zinc-500 text-xs">
                <i class="fa-solid fa-shield-halved text-xl mb-2 opacity-50 block"></i>
                No incidents in the tracked feed's lookback window right now.
            </div>`;
        } else {
            body.innerHTML = incidents.map(i => this._ledgerRow(i)).join('');
            this._enhanceIcons(body);
        }

        if (updated && data.generated_at) {
            const d = new Date(data.generated_at);
            updated.textContent = isNaN(d) ? 'synced' : `synced ${d.toLocaleString()}`;
        }
        if (threatEl && data.threat_level) {
            threatEl.innerHTML = THREAT_BADGE[data.threat_level] || `THREAT LEVEL: ${escapeHtml(data.threat_level)}`;
        }
        if (sourceLink && data.source_report) {
            sourceLink.href = REPORT_BLOB_BASE + data.source_report;
        }
    },
};

window.AttackFeed = AttackFeed;
document.addEventListener('DOMContentLoaded', () => AttackFeed.init());
