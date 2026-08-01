// VAPE Wire full article reader (article.html?file=<intel/news/*.md filename>).
// Fetches the real markdown file straight from GitHub (the same raw-content
// path every other data fetch on this site already uses) and renders it as
// a real, full-page article — reuses report.js's own markdown renderer
// rather than shipping a second one.
import { escapeHtml, simpleMarkdownToHtml } from './report.js';
import { NEWS_DIR_RAW } from './newswire.js';

// Mirrors agents/build_intel_index.py::_field() -- pulls a '**Label:**
// value' line out of the raw markdown VAPE's own report writer emits.
function field(text, label) {
    const re = new RegExp(`\\*?\\*?${label}\\*?\\*?\\s*[:：]\\s*(.+)`, 'i');
    const m = text.match(re);
    return m ? m[1].trim().replace(/^\*+|\*+$/g, '').trim() : null;
}

function firstHeading(text) {
    for (const line of text.split('\n')) {
        const s = line.trim();
        if (s.startsWith('#')) return s.replace(/^#+\s*/, '').trim();
    }
    return null;
}

// Strips the leading "# Headline" + metadata block (everything before the
// first "---" rule) so the body renderer only ever sees the actual story
// (body + Sources + closing line) — never the frontmatter lines duplicated
// as a stray heading/paragraph. Rejoins the remaining sections with a blank
// line rather than a literal "---" (simpleMarkdownToHtml has no <hr> rule,
// so a bare "---" would otherwise render as visible dashes).
function bodyAfterFrontmatter(text) {
    const parts = text.split(/^---$/m);
    return parts.length > 1 ? parts.slice(1).join('\n\n').trim() : text;
}

function renderError(msg) {
    document.getElementById('article-root').innerHTML = `
        <div class="text-center py-20">
            <i class="fa-solid fa-newspaper text-2xl mb-3 opacity-40 block"></i>
            <div class="text-zinc-400 text-sm">${escapeHtml(msg)}</div>
            <a href="news.html" class="term-btn term-btn-sm inline-block mt-5">&larr; Back to VAPE Wire</a>
        </div>`;
}

async function init() {
    const file = new URLSearchParams(window.location.search).get('file');
    if (!file || !/^[\w.-]+\.md$/.test(file)) {
        renderError('No article specified.');
        return;
    }
    let text;
    try {
        const res = await fetch(`${NEWS_DIR_RAW}/${encodeURIComponent(file)}?t=${Date.now()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        text = await res.text();
    } catch (e) {
        renderError('This story could not be loaded — it may have been moved or the archive is briefly unreachable.');
        return;
    }

    const headline = firstHeading(text) || 'Untitled';
    const byline = field(text, 'Byline') || 'VAPE Reporter';
    const agency = field(text, 'Agency') || 'VAPE Wire';
    const dateStr = field(text, 'Published') || field(text, 'Date');
    const topic = field(text, 'Topic');
    const dek = field(text, 'Dek');
    const image = field(text, 'Image');
    const factChecked = field(text, 'Fact-checked');

    document.title = `${headline} — VAPE Wire`;
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc && dek) metaDesc.setAttribute('content', dek);

    const bodyHtml = simpleMarkdownToHtml(bodyAfterFrontmatter(text));

    document.getElementById('article-root').innerHTML = `
        <a href="news.html" class="text-xs text-zinc-500 hover:text-zinc-200 transition inline-flex items-center gap-1.5 mb-6">
            <i class="fa-solid fa-arrow-left text-[10px]"></i> Back to VAPE Wire
        </a>
        ${image ? `<div class="article-hero"><img src="${escapeHtml(image)}" alt="" onerror="this.parentElement.remove()"></div>` : ''}
        ${topic ? `<span class="news-card-topic mb-3">${escapeHtml(topic)}</span>` : ''}
        <h1 class="article-headline">${escapeHtml(headline)}</h1>
        ${dek ? `<p class="article-dek">${escapeHtml(dek)}</p>` : ''}
        <div class="article-byline">
            <span><i class="fa-solid fa-feather-pointed text-[10px] mr-1"></i>${escapeHtml(agency)} — ${escapeHtml(byline)}</span>
            ${dateStr ? `<span>${escapeHtml(dateStr)}</span>` : ''}
            ${factChecked ? `<span title="${escapeHtml(factChecked)}"><i class="fa-solid fa-circle-check text-[10px] mr-1 ${factChecked.startsWith('Yes') ? 'text-emerald-400' : 'text-zinc-500'}"></i>${factChecked.startsWith('Yes') ? 'Fact-checked' : 'Not independently reviewed'}</span>` : ''}
        </div>
        <article class="article-body">${bodyHtml}</article>
    `;
}

document.addEventListener('DOMContentLoaded', init);
