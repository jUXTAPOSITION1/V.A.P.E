// VAPE's live attack feed — the ticker between the nav and hero, and the
// full "Threat Ledger" section between the two case-study sections, both
// read the same data/attack-feed.json. That file is written by
// agents/security_sweep.py straight from DeFiLlama's real hacks feed (the
// same data its intel/reports/security-*.md reports use) — real, dated
// incidents only. An empty or unreachable feed renders an honest empty
// state; nothing here is ever fabricated to fill space.
import { resolveProtocolLogo } from './icons.js';
import { fetchStories, articleUrl, ago as agoIso } from './newswire.js';

const ATTACK_FEED_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/attack-feed.json';
const REPORT_BLOB_BASE = 'https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/';

// The top-of-page ticker is a combined feed (explicit direction 2026-08-01):
// real security incidents interleaved with VAPE's own published VAPE Wire
// articles, sorted by recency. Capped so one quiet week of incidents doesn't
// get buried under months of article backlog, or vice versa.
const TICKER_CAP = 30;

// agents/hack_agent.py writes one real, standalone analysis per incident
// (grounded only in this same feed's real fields, plus a live web search)
// and patches its path back onto the incident as `analysis_report` — every
// run, since security_sweep.py regenerates this whole file fresh each cycle
// with no knowledge of that field. Only incidents hack_agent.py has actually
// reached carry it; nothing here is ever a placeholder link.
//
// `source_url`, when present, is DeFiLlama's own real link to the original
// incident disclosure/article (agents/data_fetchers.py::_incident_source_url()
// extracts it defensively from the raw hacks feed) — a different thing from
// `analysis_report` above, which is VAPE's own write-up. Both link out
// independently; an incident with neither simply shows no link, never a
// fabricated one.

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function severityClass(amountUsdM) {
    const n = Number(amountUsdM) || 0;
    if (n >= 10) return { text: 'text-rose-400', pill: 'border border-rose-400 text-rose-400', dot: 'bg-rose-500' };
    if (n >= 1) return { text: 'text-amber-400', pill: 'border border-amber-400 text-amber-400', dot: 'bg-amber-500' };
    return { text: 'text-zinc-400', pill: 'border border-white/20 text-zinc-400', dot: 'bg-zinc-500' };
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

const LEDGER_PAGE_SIZE = 10;

const AttackFeed = {
    _data: null,
    _rotateHandle: null,
    _rotateIdx: 0,
    _paused: false,
    _phase: 'in',
    HOLD_MS: 3200,
    SLIDE_MS: 600,
    // Client-side search/filter/sort/pagination state for the Threat Ledger —
    // the full incident list is already in memory (one small JSON fetch), so
    // this filters/sorts/paginates in-browser rather than round-tripping to a
    // server, unlike x402feed.js's server-paginated /x402/feed.
    _ledger: { q: '', severity: '', sort: 'date_desc', page: 0 },

    async init() {
        // Fetched independently (and in parallel) so a failure on one feed
        // never wipes out a genuinely successful fetch of the other.
        const [data, stories] = await Promise.all([
            (async () => {
                try {
                    const res = await fetch(`${ATTACK_FEED_URL}?t=${Date.now()}`);
                    return await res.json();
                } catch (e) {
                    return null;
                }
            })(),
            fetchStories(),
        ]);
        this._data = data;
        this._tickerItems = this._buildTickerItems(this._incidents(), stories);
        this._renderTicker();
        this._wireLedgerControls();
        this._renderLedger();
    },

    // Tags each item with its type so the ticker can render/link it
    // correctly, then sorts the merged list by recency. Incident dates are
    // day-only (attack-feed.json), so they sort to the start of that UTC day;
    // story dates carry real timestamps (build_intel_index.py) — good enough
    // for a decorative rotation, not used for anything precision-sensitive.
    _buildTickerItems(incidents, stories) {
        const tagged = [
            ...incidents.map(data => ({ type: 'incident', ts: Date.parse(`${data.date}T00:00:00Z`) || 0, data })),
            ...stories.map(data => ({ type: 'news', ts: Date.parse(data.date) || 0, data })),
        ];
        tagged.sort((a, b) => b.ts - a.ts);
        return tagged.slice(0, TICKER_CAP);
    },

    _wireLedgerControls() {
        const search = document.getElementById('threat-ledger-search');
        const severity = document.getElementById('threat-ledger-severity');
        const sort = document.getElementById('threat-ledger-sort');
        const prev = document.getElementById('threat-ledger-prev');
        const next = document.getElementById('threat-ledger-next');
        if (search) {
            search.addEventListener('input', () => {
                this._ledger.q = search.value.trim().toLowerCase();
                this._ledger.page = 0;
                this._renderLedger();
            });
        }
        if (severity) {
            severity.addEventListener('change', () => {
                this._ledger.severity = severity.value;
                this._ledger.page = 0;
                this._renderLedger();
            });
        }
        if (sort) {
            sort.addEventListener('change', () => {
                this._ledger.sort = sort.value;
                this._ledger.page = 0;
                this._renderLedger();
            });
        }
        if (prev) {
            prev.addEventListener('click', () => {
                this._ledger.page = Math.max(0, this._ledger.page - 1);
                this._renderLedger();
            });
        }
        if (next) {
            next.addEventListener('click', () => {
                this._ledger.page += 1;
                this._renderLedger();
            });
        }
    },

    // "extreme"/"high"/"medium"/"low" mirror severityClass()'s own
    // >=10 / >=1 / else thresholds, but split >=10 into extreme(>=50)/high
    // so the filter has 3 real buckets above "low" instead of collapsing
    // every $10M+ hack into one bucket.
    _severityBucket(amountUsdM) {
        const n = Number(amountUsdM) || 0;
        if (n >= 50) return 'extreme';
        if (n >= 10) return 'high';
        if (n >= 1) return 'medium';
        return 'low';
    },

    _filteredSortedIncidents() {
        let list = this._incidents();
        const { q, severity, sort } = this._ledger;
        if (q) {
            list = list.filter(i => {
                const chains = (i.chains || []).join(' ').toLowerCase();
                return (i.name || '').toLowerCase().includes(q)
                    || (i.technique || '').toLowerCase().includes(q)
                    || chains.includes(q)
                    || fmtLoss(i.amount_usd_m).toLowerCase().includes(q);
            });
        }
        if (severity) {
            list = list.filter(i => this._severityBucket(i.amount_usd_m) === severity);
        }
        list = [...list].sort((a, b) => {
            if (sort === 'date_asc') return new Date(a.date) - new Date(b.date);
            if (sort === 'amount_desc') return (Number(b.amount_usd_m) || 0) - (Number(a.amount_usd_m) || 0);
            if (sort === 'amount_asc') return (Number(a.amount_usd_m) || 0) - (Number(b.amount_usd_m) || 0);
            return new Date(b.date) - new Date(a.date); // date_desc, default
        });
        return list;
    },

    _renderLedgerPagination(total) {
        const countEl = document.getElementById('threat-ledger-count');
        const pageEl = document.getElementById('threat-ledger-page');
        const prev = document.getElementById('threat-ledger-prev');
        const next = document.getElementById('threat-ledger-next');
        const page = this._ledger.page;
        const pages = Math.max(1, Math.ceil(total / LEDGER_PAGE_SIZE));
        if (countEl) {
            if (!total) countEl.textContent = 'No incidents match this filter.';
            else {
                const from = page * LEDGER_PAGE_SIZE + 1;
                const to = Math.min(total, (page + 1) * LEDGER_PAGE_SIZE);
                countEl.textContent = `Showing ${from}–${to} of ${total}`;
            }
        }
        if (pageEl) pageEl.textContent = `Page ${page + 1} of ${pages}`;
        if (prev) prev.disabled = page <= 0;
        if (next) next.disabled = page + 1 >= pages;
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
    //
    // Name uses flex:0 1 auto (capped by max-width) instead of flex-basis:0
    // — with two 0%-basis flex items, the browser splits the *available*
    // space strictly by their grow ratio regardless of actual content size,
    // so a short name like "Across" still claimed 2/3 of the row even
    // though it only needed a fraction of that, starving technique of room
    // it could easily have used (invisible on mobile, truncated mid-word on
    // desktop despite plenty of total width). Letting name size to its own
    // content first and giving technique the sole flex-grow means technique
    // gets everything name doesn't actually use.
    _incidentTickerInner(item) {
        const sev = severityClass(item.amount_usd_m);
        return `<span class="w-1.5 h-1.5 rounded-full ${sev.dot} shrink-0"></span>
            ${this._iconHtml(item.name, 'w-4 h-4')}
            <span class="text-zinc-200 font-medium truncate min-w-0" style="flex:0 1 auto;max-width:40%">${escapeHtml(item.name)}</span>
            <span class="${sev.text} font-semibold shrink-0">${fmtLoss(item.amount_usd_m)}</span>
            <span class="text-zinc-600 truncate min-w-0" style="flex:1 1 0%">${escapeHtml(item.technique || '')}</span>
            <span class="text-zinc-700 shrink-0 font-mono text-[11px]">${escapeHtml(ago(item.date))}</span>`;
    },

    // Blue matches the site's other "featured/spotlight" callouts (never
    // decoration elsewhere in this codebase) — distinct from rose, which
    // stays a dedicated threat-severity signal and must not also mean "news."
    _newsTickerInner(story) {
        return `<span class="w-1.5 h-1.5 rounded-full bg-[#60a5fa] shrink-0"></span>
            <i class="fa-solid fa-newspaper text-[11px] text-[#60a5fa] shrink-0"></i>
            <span class="text-zinc-200 font-medium truncate min-w-0" style="flex:1 1 0%">${escapeHtml(story.title || '')}</span>
            <span class="text-[#60a5fa] text-[11px] shrink-0">VAPE Wire</span>
            <span class="text-zinc-700 shrink-0 font-mono text-[11px]">${escapeHtml(agoIso(story.date))}</span>`;
    },

    // Each rendered line is its own link to its real destination — the
    // ticker's outer wrapper is a plain div (see index.html), not a single
    // blanket link, so this always wraps the row itself.
    _tickerEntryHtml(entry) {
        const inner = entry.type === 'news' ? this._newsTickerInner(entry.data) : this._incidentTickerInner(entry.data);
        const href = entry.type === 'news' ? articleUrl(entry.data) : '#threat-ledger';
        return `<a href="${escapeHtml(href)}" class="flex items-center gap-2 min-w-0 w-full" draggable="false">${inner}</a>`;
    },

    // News-ticker motion: each incident slides in from the right, comes to
    // rest and holds (readable, progress bar fills), then slides out to the
    // left before the next one enters from the right — never two headlines
    // overlapping mid-transition. A named `_phase` (in/hold/out) plus a
    // single tracked timeout handle means pause() can always cleanly cancel
    // whatever's pending; resume() just re-enters the hold phase rather than
    // trying to reconstruct exact remaining time in a sub-phase, which is a
    // fine trade for a decorative ticker.
    _renderTicker() {
        const line = document.getElementById('attack-ticker-line');
        const progress = document.getElementById('attack-ticker-progress');
        const wrap = document.getElementById('attack-ticker');
        if (!line || !wrap) return;
        this._tickerLine = line;
        this._tickerProgress = progress;

        const items = this._tickerItems || [];
        if (!items.length) {
            line.style.transition = 'none';
            line.style.transform = 'translateX(0)';
            line.innerHTML = '<span class="text-zinc-600">No incidents or stories in the live feed this cycle. It fills in as soon as one lands.</span>';
            if (progress) progress.style.left = '-10%';
            return;
        }
        this._tickerIncidents = items;

        const paint = (idx) => {
            line.innerHTML = this._tickerEntryHtml(items[idx]);
            this._enhanceIcons(line);
        };

        const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (reduceMotion || items.length === 1) {
            line.style.transition = 'none';
            line.style.transform = 'translateX(0)';
            paint(this._rotateIdx);
            if (progress) progress.parentElement.style.display = 'none';
            return; // static — no auto-rotation, no motion
        }

        // Kick off the cycle sitting off-screen right so the very first
        // headline also slides in rather than just appearing.
        line.style.transition = 'none';
        line.style.transform = 'translateX(100%)';
        paint(this._rotateIdx);
        void line.offsetWidth; // force reflow so the next transition actually animates from here

        wrap.addEventListener('mouseenter', () => this._pauseTicker());
        wrap.addEventListener('mouseleave', () => this._resumeTicker());
        wrap.addEventListener('focusin', () => this._pauseTicker());
        wrap.addEventListener('focusout', () => this._resumeTicker());
        this._wireTickerSwipe(wrap, line);

        this._slideIn();
    },

    _clearTickerTimer() {
        if (this._rotateHandle) { clearTimeout(this._rotateHandle); this._rotateHandle = null; }
    },

    _slideIn() {
        const line = this._tickerLine;
        this._phase = 'in';
        line.style.transition = `transform ${this.SLIDE_MS}ms cubic-bezier(.22,.9,.32,1)`;
        line.style.transform = 'translateX(0%)';
        this._rotateHandle = setTimeout(() => this._holdPhase(), this.SLIDE_MS);
    },

    _holdPhase() {
        this._phase = 'hold';
        this._runProgress();
        this._rotateHandle = setTimeout(() => this._slideOut(1), this.HOLD_MS);
    },

    // dir: 1 = advance (headline exits left, next enters from right — the
    // existing auto-rotate direction), -1 = go back (headline exits right,
    // previous entry re-enters from the left) — used by the swipe/drag
    // gesture below so a manual "previous" feels like the mirror image of
    // the automatic "next" rather than a different, unrelated motion.
    _slideOut(dir) {
        const line = this._tickerLine;
        this._phase = 'out';
        if (this._tickerProgress) {
            this._tickerProgress.style.transition = 'none';
            this._tickerProgress.style.left = '105%';
        }
        line.style.transition = `transform ${this.SLIDE_MS}ms cubic-bezier(.6,0,.8,.2)`;
        line.style.transform = `translateX(${dir > 0 ? '-100%' : '100%'})`;
        this._rotateHandle = setTimeout(() => {
            const len = this._tickerIncidents.length;
            this._rotateIdx = (this._rotateIdx + dir + len) % len;
            line.style.transition = 'none';
            line.style.transform = `translateX(${dir > 0 ? '100%' : '-100%'})`;
            line.innerHTML = this._tickerEntryHtml(this._tickerIncidents[this._rotateIdx]);
            this._enhanceIcons(line);
            void line.offsetWidth;
            this._slideIn();
        }, this.SLIDE_MS);
    },

    // Manual swipe/drag navigation (touch on mobile, click-drag on desktop)
    // — the ticker was auto-rotate-only before, with no way to deliberately
    // go back to a headline that already scrolled past. Reuses the exact
    // same slide pipeline as the auto-rotation so a manual nudge looks
    // identical to the automatic one, just fired on demand and in either
    // direction. Locked out mid-transition (_phase 'in'/'out') so a fast
    // double-swipe can't desync _rotateIdx from what's actually on screen.
    _manualNav(dir) {
        if (!this._tickerIncidents || this._tickerIncidents.length < 2) return;
        if (this._phase === 'in' || this._phase === 'out') return;
        this._clearTickerTimer();
        this._slideOut(dir);
    },

    // Pointer Events unify touch/mouse/pen in one listener set — swipe on a
    // phone and click-drag with a mouse both work without separate touch*
    // handlers. Threshold-gated (SWIPE_PX) so a normal tap still follows the
    // wrapping <a href="#threat-ledger"> link instead of being eaten as a
    // zero-distance "swipe"; only a real drag past the threshold both
    // triggers navigation AND suppresses that click (see the capturing
    // click listener below).
    SWIPE_PX: 40,
    _wireTickerSwipe(wrap, line) {
        if (this._swipeWired) return;
        this._swipeWired = true;
        let startX = 0, dragging = false, moved = false, pointerId = null;

        // Move/up are bound to window only while a drag is active (added on
        // pointerdown, torn down on pointerup/cancel) rather than relying on
        // Pointer Capture — besides tracking correctly if the pointer leaves
        // the ticker's own bounds mid-swipe, this sidesteps a real headless-
        // Chromium quirk confirmed while testing this: calling
        // setPointerCapture() from inside the pointerdown handler could
        // itself provoke an immediate synthetic `pointercancel` (clientX 0)
        // moments later, which read as a huge spurious swipe.
        const onMove = (e) => {
            if (!dragging || e.pointerId !== pointerId) return;
            const dx = e.clientX - startX;
            if (Math.abs(dx) > 6) moved = true;
            // Clamp so a long drag doesn't fling the headline fully offscreen
            // before release — it should feel like a rubber-banded nudge.
            const clamped = Math.max(-120, Math.min(120, dx));
            line.style.transform = `translateX(${clamped}px)`;
        };
        const endDrag = (e) => {
            if (!dragging || e.pointerId !== pointerId) return;
            dragging = false;
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', endDrag);
            window.removeEventListener('pointercancel', endDrag);
            const dx = e.clientX - startX;
            if (Math.abs(dx) >= this.SWIPE_PX) {
                // dx < 0 -> dragged left -> advance (dir 1); dx > 0 -> back (dir -1).
                this._manualNav(dx < 0 ? 1 : -1);
            } else {
                line.style.transition = `transform ${this.SLIDE_MS}ms cubic-bezier(.22,.9,.32,1)`;
                line.style.transform = 'translateX(0%)';
                this._resumeTicker();
            }
        };
        const onDown = (e) => {
            if (!this._tickerIncidents || this._tickerIncidents.length < 2) return;
            startX = e.clientX;
            dragging = true;
            moved = false;
            pointerId = e.pointerId;
            this._pauseTicker();
            line.style.transition = 'none';
            window.addEventListener('pointermove', onMove);
            window.addEventListener('pointerup', endDrag);
            window.addEventListener('pointercancel', endDrag);
        };
        wrap.addEventListener('pointerdown', onDown);
        // Capturing so this runs before the <a> follows its href — a real
        // drag (not a tap) must not also navigate to #threat-ledger.
        wrap.addEventListener('click', (e) => { if (moved) { e.preventDefault(); moved = false; } }, true);
    },

    _runProgress() {
        const progress = this._tickerProgress;
        if (!progress) return;
        progress.style.transition = 'none';
        progress.style.left = '-10%';
        void progress.offsetWidth; // force reflow so the next transition actually animates from the start
        progress.style.transition = `left ${this.HOLD_MS}ms linear`;
        progress.style.left = '105%';
    },

    // Pause on hover/focus — an auto-rotating feed that can't be paused to
    // actually read is a real accessibility miss (WCAG 2.2.2), not just a
    // nicety. Cancels whatever phase-timeout is pending; the in-flight CSS
    // transition (if any) still finishes on its own since it isn't tied to
    // the JS timer, so pausing never snaps the headline to a jarring
    // mid-slide stop.
    _pauseTicker() {
        this._paused = true;
        this._clearTickerTimer();
        if (this._tickerProgress) {
            const frozenLeft = getComputedStyle(this._tickerProgress).left;
            this._tickerProgress.style.transition = 'none';
            this._tickerProgress.style.left = frozenLeft;
        }
    },
    _resumeTicker() {
        if (!this._paused) return;
        this._paused = false;
        this._holdPhase();
    },

    _lessonHtml(lesson) {
        if (!lesson) return '';
        let tone = 'text-zinc-500';
        let note = lesson.prevention
            ? (lesson.covered_by ? 'already covered' : (lesson.out_of_scope ? 'out of scope' : 'coverage gap, noted'))
            : 'unclassified, investigated anyway';
        if (lesson.backtest && lesson.backtest.would_have_flagged === false) {
            tone = 'text-rose-400/80';
            note = 'model backtest miss';
        } else if (lesson.prevention && lesson.covered_by) {
            tone = 'text-emerald-500/70';
        }
        const title = lesson.prevention ? `${lesson.label}. Prevention: ${lesson.prevention}` : lesson.label;
        return `<div class="text-[10.5px] ${tone} mt-1 leading-relaxed" title="${escapeHtml(title)}">
            <i class="fa-solid fa-shield-halved text-[9px] mr-1"></i>${escapeHtml(lesson.label)}: ${escapeHtml(note)}</div>`;
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
        <div class="diff-row flex flex-col gap-1">
            <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1 flex items-center gap-1.5">
                    ${this._iconHtml(item.name, 'w-4 h-4')}<span class="text-zinc-100 text-sm truncate min-w-0">${escapeHtml(item.name)}</span>
                </div>
                <span class="shrink-0 px-2.5 py-1 text-xs ${sev.pill}">${fmtLoss(item.amount_usd_m)}</span>
            </div>
            <div class="text-zinc-500 text-xs leading-relaxed">${escapeHtml(item.technique || 'technique unspecified')} · ${escapeHtml(chains)}</div>
            ${this._lessonHtml(item.lesson)}
            <div class="flex items-center justify-between gap-3 mt-0.5">
                <div class="text-[10.5px] text-zinc-700 font-mono">${escapeHtml(item.date)} · ${escapeHtml(ago(item.date))}</div>
                <div class="flex items-center gap-3 shrink-0">
                    ${item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener" class="text-[10.5px] text-zinc-500 hover:text-zinc-300 hover:underline inline-flex items-center gap-1" title="Original incident source"><i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>Incident source</a>` : ''}
                    ${item.analysis_report ? `<a href="${REPORT_BLOB_BASE}${escapeHtml(item.analysis_report)}" target="_blank" rel="noopener" class="text-[10.5px] text-rose-400/80 hover:text-rose-400 hover:underline inline-flex items-center gap-1"><i class="fa-solid fa-magnifying-glass text-[9px]"></i>Full analysis</a>` : ''}
                </div>
            </div>
        </div>`;
    },

    _renderLedger() {
        const body = document.getElementById('threat-ledger-body');
        const updated = document.getElementById('threat-ledger-updated');
        const threatEl = document.getElementById('threat-ledger-threat');
        const sourceLink = document.getElementById('threat-ledger-source');
        if (!body) return;

        const data = this._data;

        if (!data) {
            body.innerHTML = `<div class="text-center py-10 text-zinc-500 text-xs">
                <i class="fa-solid fa-satellite-dish text-xl mb-2 opacity-50 block"></i>
                Live threat feed temporarily unavailable. Try again shortly.
            </div>`;
            if (updated) updated.textContent = 'unavailable';
            this._renderLedgerPagination(0);
            return;
        }

        const filtered = this._filteredSortedIncidents();
        const page = this._ledger.page;
        const pageItems = filtered.slice(page * LEDGER_PAGE_SIZE, (page + 1) * LEDGER_PAGE_SIZE);

        if (!filtered.length) {
            body.innerHTML = `<div class="text-center py-10 text-zinc-500 text-xs">
                <i class="fa-solid fa-shield-halved text-xl mb-2 opacity-50 block"></i>
                ${this._ledger.q || this._ledger.severity ? 'No incidents match this filter.' : "No incidents in the tracked feed's lookback window right now."}
            </div>`;
        } else {
            body.innerHTML = pageItems.map(i => this._ledgerRow(i)).join('');
            this._enhanceIcons(body);
        }
        this._renderLedgerPagination(filtered.length);

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
