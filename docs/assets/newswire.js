// Shared VAPE Wire helpers — imported by newsfeed.js (the teaser ticker +
// preview tiles on the main site, above the x402 ledger), newspage.js (the
// full VAPE Wire news page's grid), and article.js (the individual article
// reader). One copy of the fetch/format/render logic instead of three
// diverging ones. Two real, separately-written source files back
// everything here: data/news-feed.json (agents/news_scan.py's headline
// discovery) and data/intel-index.json's "news" array
// (agents/build_intel_index.py::scan_news(), sourced from intel/news/*.md).
export const REPO = 'jUXTAPOSITION1/V.A.P.E';
export const RAW = `https://raw.githubusercontent.com/${REPO}/main`;
export const NEWS_FEED_URL = `${RAW}/data/news-feed.json`;
export const INTEL_INDEX_URL = `${RAW}/data/intel-index.json`;
export const NEWS_DIR_RAW = `${RAW}/intel/news`;

export function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export function ago(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    const s = (Date.now() - d) / 1e3;
    if (s < 3600) return Math.max(1, Math.floor(s / 60)) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

export async function fetchTicker() {
    try {
        const res = await fetch(`${NEWS_FEED_URL}?t=${Date.now()}`);
        const data = await res.json();
        return Array.isArray(data.headlines) ? data.headlines : [];
    } catch (e) {
        return [];
    }
}

export async function fetchStories() {
    try {
        const res = await fetch(`${INTEL_INDEX_URL}?t=${Date.now()}`);
        const data = await res.json();
        return Array.isArray(data.news) ? data.news : [];
    } catch (e) {
        return [];
    }
}

// Every VAPE Wire story links to its own reader page (article.html), not
// straight to a GitHub blob — see article.js for the full-page renderer.
export function articleUrl(story) {
    return `article.html?file=${encodeURIComponent(story.file)}`;
}

// ── breaking-headlines ticker (shared by index.html + news.html) ──────────
function tickerLineHtml(h) {
    const badgeCls = h.crypto
        ? 'text-[#60a5fa] border-[#60a5fa]/30 bg-[#60a5fa]/10'
        : 'text-zinc-400 border-white/15 bg-white/5';
    return `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] uppercase tracking-wide shrink-0 ${badgeCls}">${escapeHtml(h.topic || 'News')}</span>
            <span class="truncate">${escapeHtml(h.title)}</span>
            <span class="text-zinc-600 shrink-0 hidden sm:inline">— ${escapeHtml(h.source || '')}</span>`;
}

// Wires an auto-rotating headline ticker into `#${idPrefix}-wrap` /
// `#${idPrefix}-line` (matching the id pattern both index.html and
// news.html use). Returns nothing; safe to call once per page load.
export function wireTicker(headlines, idPrefix = 'news-ticker') {
    const wrap = document.getElementById(`${idPrefix}-wrap`);
    const line = document.getElementById(`${idPrefix}-line`);
    if (!wrap || !line) return;
    if (!headlines.length) {
        line.innerHTML = '<span class="text-zinc-600">No breaking headlines this cycle — the wire fills in as soon as one lands.</span>';
        return;
    }
    let idx = 0, timer = null;
    const paint = () => {
        const h = headlines[idx];
        line.style.opacity = '0';
        setTimeout(() => {
            line.innerHTML = `<a href="${escapeHtml(h.url)}" target="_blank" rel="noopener" class="flex items-center gap-2 min-w-0">${tickerLineHtml(h)}</a>`;
            line.style.opacity = '1';
        }, 180);
    };
    line.style.transition = 'opacity 180ms ease';
    paint();
    if (headlines.length < 2) return;
    const clear = () => { if (timer) { clearInterval(timer); timer = null; } };
    const start = () => { clear(); timer = setInterval(() => { idx = (idx + 1) % headlines.length; paint(); }, 4500); };
    wrap.addEventListener('mouseenter', clear);
    wrap.addEventListener('mouseleave', start);
    wrap.addEventListener('focusin', clear);
    wrap.addEventListener('focusout', start);
    start();
}

// ── tiny self-contained pagination (news.html doesn't load app.js — see
// newspage.js's own comment on why — so this can't reuse App._pgWire/
// _pgSlice; same idea, much smaller) ────────────────────────────────────
export function wirePager(page, onChange) {
    const prev = document.getElementById('news-pg-prev');
    const next = document.getElementById('news-pg-next');
    if (prev) prev.addEventListener('click', () => { page.n = Math.max(0, page.n - 1); onChange(); });
    if (next) next.addEventListener('click', () => { page.n += 1; onChange(); });
}

export function renderPage(page, items, pageSize) {
    const total = items.length;
    const pages = Math.max(1, Math.ceil(total / pageSize));
    if (page.n > pages - 1) page.n = pages - 1;
    const countEl = document.getElementById('news-pg-count');
    const pageEl = document.getElementById('news-pg-page');
    const prev = document.getElementById('news-pg-prev');
    const next = document.getElementById('news-pg-next');
    if (countEl) countEl.textContent = total ? `Showing ${page.n * pageSize + 1}–${Math.min(total, (page.n + 1) * pageSize)} of ${total}` : 'No entries match this filter.';
    if (pageEl) pageEl.textContent = `Page ${page.n + 1} of ${pages}`;
    if (prev) prev.disabled = page.n <= 0;
    if (next) next.disabled = page.n + 1 >= pages;
    return items.slice(page.n * pageSize, (page.n + 1) * pageSize);
}

// ── story tile (shared by the home teaser and the full news.html grid) ────
export function storyCardHtml(s) {
    const img = s.image || 'assets/logo-v-256.png';
    const isGenerated = (s.image_source || '').startsWith('AI-generated');
    return `
    <a href="${escapeHtml(articleUrl(s))}" class="news-card">
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
}
