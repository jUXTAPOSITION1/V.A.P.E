// VAPE Wire — the breaking-headlines ticker and story grid between Platform
// Overview and the x402 Ledger. Two real, separately-written files back
// this: data/news-feed.json (agents/news_scan.py's raw headline discovery —
// Google News search + CoinGecko's news feed + one bounded web search, see
// that script's module docstring) drives the ticker; data/intel-index.json's
// "news" array (agents/build_intel_index.py::scan_news(), sourced from
// intel/news/*.md) drives the story grid below it. Editorial rule enforced
// upstream in news_scan.py, not here: crypto/blockchain headlines always
// occupy the ticker's leading slots, even over a more recent macro/stocks
// item — this file just renders whatever order it's handed.
const REPO = 'jUXTAPOSITION1/V.A.P.E';
const RAW = `https://raw.githubusercontent.com/${REPO}/main`;
const NEWS_FEED_URL = `${RAW}/data/news-feed.json`;
const INTEL_INDEX_URL = `${RAW}/data/intel-index.json`;
const PAGE_SIZE = 6;

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function ago(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    const s = (Date.now() - d) / 1e3;
    if (s < 3600) return Math.max(1, Math.floor(s / 60)) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

const NewsFeed = {
    _headlines: [],
    _stories: [],
    _rotateIdx: 0,
    _rotateTimer: null,
    _q: '', _topic: '',

    async init() {
        await Promise.all([this._loadTicker(), this._loadStories()]);
        this._renderTicker();
        this._wireControls();
        this._renderTopicFilter();
        this._renderGrid();
    },

    async refresh() {
        await this.init();
    },

    clearFilters() {
        this._q = '';
        this._topic = '';
        window.App?._pgReset?.('news-pg');
        this._renderTopicFilter();
        this._renderGrid();
    },

    async _loadTicker() {
        try {
            const res = await fetch(`${NEWS_FEED_URL}?t=${Date.now()}`);
            const data = await res.json();
            this._headlines = Array.isArray(data.headlines) ? data.headlines : [];
        } catch (e) {
            this._headlines = [];
        }
    },

    async _loadStories() {
        try {
            const res = await fetch(`${INTEL_INDEX_URL}?t=${Date.now()}`);
            const data = await res.json();
            this._stories = Array.isArray(data.news) ? data.news : [];
        } catch (e) {
            this._stories = [];
        }
    },

    // ── breaking-headlines ticker ──────────────────────────────────────────
    _tickerLineHtml(h) {
        const badgeCls = h.crypto
            ? 'text-[#60a5fa] border-[#60a5fa]/30 bg-[#60a5fa]/10'
            : 'text-zinc-400 border-white/15 bg-white/5';
        return `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] uppercase tracking-wide shrink-0 ${badgeCls}">${escapeHtml(h.topic || 'News')}</span>
                <span class="truncate">${escapeHtml(h.title)}</span>
                <span class="text-zinc-600 shrink-0 hidden sm:inline">— ${escapeHtml(h.source || '')}</span>`;
    },

    _renderTicker() {
        const wrap = document.getElementById('news-ticker-wrap');
        const line = document.getElementById('news-ticker-line');
        if (!wrap || !line) return;
        if (!this._headlines.length) {
            line.innerHTML = '<span class="text-zinc-600">No breaking headlines this cycle — the wire fills in as soon as one lands.</span>';
            return;
        }
        const paint = () => {
            const h = this._headlines[this._rotateIdx];
            line.style.opacity = '0';
            setTimeout(() => {
                line.innerHTML = `<a href="${escapeHtml(h.url)}" target="_blank" rel="noopener" class="flex items-center gap-2 min-w-0">${this._tickerLineHtml(h)}</a>`;
                line.style.opacity = '1';
            }, 180);
        };
        line.style.transition = 'opacity 180ms ease';
        paint();
        if (this._headlines.length < 2) return;

        const advance = () => {
            this._rotateIdx = (this._rotateIdx + 1) % this._headlines.length;
            paint();
        };
        const start = () => {
            this._clearTicker();
            this._rotateTimer = setInterval(advance, 4500);
        };
        wrap.addEventListener('mouseenter', () => this._clearTicker());
        wrap.addEventListener('mouseleave', start);
        wrap.addEventListener('focusin', () => this._clearTicker());
        wrap.addEventListener('focusout', start);
        start();
    },

    _clearTicker() {
        if (this._rotateTimer) { clearInterval(this._rotateTimer); this._rotateTimer = null; }
    },

    // ── VAPE Wire story grid ────────────────────────────────────────────────
    _wireControls() {
        const search = document.getElementById('news-search');
        if (search) {
            search.addEventListener('input', () => {
                this._q = search.value.trim().toLowerCase();
                window.App?._pgReset?.('news-pg');
                this._renderGrid();
            });
        }
        window.App?._pgWire?.('news-pg', PAGE_SIZE, () => this._renderGrid());
    },

    _renderTopicFilter() {
        const wrap = document.getElementById('news-topic-filter');
        if (!wrap) return;
        const topics = [...new Set(this._stories.map(s => s.topic).filter(Boolean))];
        wrap.innerHTML = topics.map(t => `
            <button type="button" data-topic="${escapeHtml(t)}"
                class="term-btn term-btn-sm ${this._topic === t ? 'term-btn-active' : ''}">${escapeHtml(t)}</button>
        `).join('');
        wrap.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                this._topic = this._topic === btn.dataset.topic ? '' : btn.dataset.topic;
                window.App?._pgReset?.('news-pg');
                this._renderTopicFilter();
                this._renderGrid();
            });
        });
    },

    _filtered() {
        let list = this._stories;
        if (this._topic) list = list.filter(s => s.topic === this._topic);
        if (this._q) {
            list = list.filter(s => `${s.title || ''} ${s.dek || ''} ${s.topic || ''}`.toLowerCase().includes(this._q));
        }
        return list;
    },

    _card(s) {
        const img = s.image || 'assets/logo-v-256.png';
        const isGenerated = (s.image_source || '').startsWith('AI-generated');
        return `
        <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener" class="news-card">
            <div class="news-card-img">
                <img src="${escapeHtml(img)}" alt="" loading="lazy"
                     onerror="this.src='assets/logo-v-256.png'; this.classList.add('news-card-img-fallback')">
                ${isGenerated ? '<span class="news-card-img-tag">AI illustration</span>' : ''}
            </div>
            <div class="news-card-body">
                <span class="news-card-topic">${escapeHtml(s.topic || 'News')}</span>
                <div class="news-card-title">${escapeHtml(s.title || '')}</div>
                <div class="news-card-dek">${escapeHtml(s.dek || '')}</div>
                <div class="news-card-meta">
                    <span>${escapeHtml(s.byline || 'VAPE Reporter')}</span>
                    <span>${ago(s.date)}</span>
                </div>
            </div>
        </a>`;
    },

    _renderGrid() {
        const el = document.getElementById('news-grid');
        if (!el) return;
        const filtered = this._filtered();
        const items = window.App?._pgSlice ? window.App._pgSlice('news-pg', filtered, PAGE_SIZE) : filtered.slice(0, PAGE_SIZE);
        el.innerHTML = items.length
            ? items.map(s => this._card(s)).join('')
            : '<div class="text-zinc-500 text-sm col-span-full">No stories match this filter yet — VAPE Wire publishes new coverage on a schedule.</div>';
    },
};

window.NewsFeed = NewsFeed;
document.addEventListener('DOMContentLoaded', () => NewsFeed.init());
