// Site-wide search (search.html?q=<query>) — one client-side index built
// from data/intel-index.json, which already aggregates every real category
// this covers (agents/build_intel_index.py's scan_news/scan_investigations/
// scan_reports/scan_broadcasts/scan_tools): no separate fetch, no new data
// pipeline. Every result links to the real on-site reader where one exists
// (article.html for news, investigation.html for a dedicated investigation
// report) or straight to the real GitHub blob otherwise — same routing
// app.js's own Archive explorer already uses.
import { escapeHtml } from './report.js';
import { articleUrl } from './newswire.js';

const REPO = 'jUXTAPOSITION1/V.A.P.E';
const INTEL_INDEX_URL = `https://raw.githubusercontent.com/${REPO}/main/data/intel-index.json`;

const TYPE_META = {
    news: { label: 'VAPE Wire', icon: 'fa-newspaper' },
    investigation: { label: 'Investigation', icon: 'fa-magnifying-glass-chart' },
    report: { label: 'Report', icon: 'fa-file-shield' },
    broadcast: { label: 'Broadcast', icon: 'fa-tower-broadcast' },
    tool: { label: 'Tool', icon: 'fa-wrench' },
};

function ago(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    const s = (Date.now() - d) / 1e3;
    if (s < 3600) return Math.max(1, Math.floor(s / 60)) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

function shortAddr(a) { return (a && a.length > 12) ? a.slice(0, 6) + '…' + a.slice(-4) : (a || ''); }

// One dedicated investigation report (source==="report") reads on-site;
// the legacy catalog rows have no individual file of their own and keep
// linking out to the shared catalog blob — same rule app.js's Archive uses.
function investigationHref(item) {
    return item.file ? `investigation.html?file=${encodeURIComponent(item.file)}` : item.url;
}

// Normalizes every real record from intel-index.json into one flat,
// uniformly-shaped search entry: {type, title, sub, dateIso, href, external, text}.
function buildIndex(data) {
    const entries = [];
    (data.news || []).forEach(n => entries.push({
        type: 'news', title: n.title || n.file, sub: n.dek || n.topic || '',
        dateIso: n.date, href: articleUrl(n), external: false,
        text: [n.title, n.topic, n.dek, n.byline].filter(Boolean).join(' '),
    }));
    (data.investigations || []).forEach(i => {
        const sym = i.symbol || (i.title || '').match(/Investigation\s*[—-]\s*(.+)$/)?.[1]?.trim();
        entries.push({
            type: 'investigation', title: sym || shortAddr(i.target) || i.title || 'Investigation',
            sub: [i.verdict, i.score ? `${i.score}/100` : null, shortAddr(i.target)].filter(Boolean).join(' · '),
            dateIso: i.date, href: investigationHref(i), external: !i.file,
            text: [i.title, i.symbol, i.name, i.target, i.offering, i.key_finding, i.summary].filter(Boolean).join(' '),
        });
    });
    (data.reports || []).forEach(r => entries.push({
        type: 'report', title: r.title || r.file, sub: [r.type, r.threat].filter(Boolean).join(' · '),
        dateIso: r.date, href: r.url, external: true,
        text: [r.title, r.file, r.type, r.summary].filter(Boolean).join(' '),
    }));
    (data.broadcasts || []).forEach(b => entries.push({
        type: 'broadcast', title: b.title || b.file, sub: b.summary || '',
        dateIso: b.date, href: b.url, external: true,
        text: [b.title, b.file, b.summary].filter(Boolean).join(' '),
    }));
    (data.tools || []).forEach(t => entries.push({
        type: 'tool', title: t.name, sub: [t.tier, t.status, t.purpose].filter(Boolean).join(' · '),
        dateIso: null, href: t.url || '#', external: true,
        text: [t.name, t.tier, t.purpose, t.status].filter(Boolean).join(' '),
    }));
    return entries;
}

let ALL = [];
let activeType = '';

function resultRow(e) {
    const meta = TYPE_META[e.type];
    const when = e.dateIso ? ago(e.dateIso) : '';
    return `<a href="${escapeHtml(e.href)}"${e.external ? ' target="_blank" rel="noopener"' : ''} class="card-h diff-row flex items-start gap-3">
        <div class="w-9 flex items-start justify-center pt-0.5 shrink-0"><i class="fa-solid ${meta.icon} text-zinc-400 text-sm"></i></div>
        <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <span class="text-sm min-w-0 truncate">${escapeHtml(e.title)}</span>
                <span class="text-[10px] uppercase tracking-wide text-zinc-500 shrink-0">${escapeHtml(meta.label)}</span>
            </div>
            ${e.sub ? `<div class="text-[11px] text-zinc-500 mt-1 truncate">${escapeHtml(e.sub)}</div>` : ''}
            ${when ? `<div class="text-[10px] text-zinc-600 mt-1">${escapeHtml(when)}</div>` : ''}
        </div>
    </a>`;
}

function render(query) {
    const q = query.trim().toLowerCase();
    const statusEl = document.getElementById('search-status');
    const resultsEl = document.getElementById('search-results');

    let pool = activeType ? ALL.filter(e => e.type === activeType) : ALL;
    let matches = q ? pool.filter(e => e.text.toLowerCase().includes(q)) : pool;
    matches = matches.slice().sort((a, b) => {
        const da = a.dateIso ? new Date(a.dateIso) : null;
        const db = b.dateIso ? new Date(b.dateIso) : null;
        if (!da && !db) return 0;
        if (!da) return 1;
        if (!db) return -1;
        return db - da;
    });

    const CAP = 60;
    statusEl.textContent = q
        ? `${matches.length} result${matches.length === 1 ? '' : 's'} for "${query.trim()}"${matches.length > CAP ? ` (showing first ${CAP})` : ''}`
        : `${pool.length} item${pool.length === 1 ? '' : 's'} indexed. Type to search.`;
    resultsEl.innerHTML = matches.length
        ? matches.slice(0, CAP).map(resultRow).join('')
        : `<div class="text-zinc-500 text-sm py-8 text-center">No matches. Try a different ticker, address, or keyword.</div>`;
}

function renderFilters() {
    const counts = {};
    ALL.forEach(e => { counts[e.type] = (counts[e.type] || 0) + 1; });
    const filtersEl = document.getElementById('search-filters');
    const types = ['', ...Object.keys(TYPE_META).filter(t => counts[t])];
    filtersEl.innerHTML = types.map(t => {
        const label = t ? TYPE_META[t].label : 'All';
        const count = t ? counts[t] : ALL.length;
        const on = activeType === t;
        return `<button data-type="${t}" class="term-btn term-btn-sm ${on ? 'term-btn-active' : ''}">${escapeHtml(label)} <span class="opacity-60">${count}</span></button>`;
    }).join('');
    filtersEl.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
            activeType = btn.dataset.type;
            renderFilters();
            render(document.getElementById('search-input').value);
        });
    });
}

async function init() {
    const params = new URLSearchParams(window.location.search);
    const initialQuery = params.get('q') || '';
    const input = document.getElementById('search-input');
    input.value = initialQuery;

    try {
        const res = await fetch(`${INTEL_INDEX_URL}?t=${Date.now()}`);
        const data = await res.json();
        ALL = buildIndex(data);
    } catch (e) {
        document.getElementById('search-status').textContent = 'The search index is briefly unreachable — try again shortly.';
        document.getElementById('search-results').innerHTML = '';
        return;
    }

    renderFilters();
    render(initialQuery);

    let debounce;
    input.addEventListener('input', () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            const url = new URL(window.location.href);
            if (input.value.trim()) url.searchParams.set('q', input.value.trim());
            else url.searchParams.delete('q');
            history.replaceState(null, '', url);
            render(input.value);
        }, 150);
    });
}

document.addEventListener('DOMContentLoaded', init);
