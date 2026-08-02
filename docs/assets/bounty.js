// Bounty Command Center — relocated off index.html onto its own page so the
// homepage stays lighter; this module owns everything the old
// #bounty-command-center section on index.html used to (telemetry, the live
// automation feed, matched Bounty Ops programs, VAPE's own audit track
// record). Ported near-verbatim from docs/assets/app.js (same fetches, same
// real sources: intel/bounty-radar/opportunities.json, intel/bounty-radar/
// bounty-ops/*.json, data/task-feed.json, intel/audits/hack-sweep-reports/)
// so behavior doesn't drift from what already shipped.
//
// docs/assets/hire.js's openBountyOps(slug) reads `App._bountyOpsList[slug]`
// off a global — this page doesn't load the full app.js (that drives the
// entire homepage), so `Bounty` is aliased onto `window.App` at the bottom
// of this file to satisfy that one lookup without touching hire.js at all.
const REPO = 'jUXTAPOSITION1/V.A.P.E';
const RAW = `https://raw.githubusercontent.com/${REPO}/main`;
const fmtUsd = n => n == null ? '…' : (n >= 1e9 ? '$' + (n / 1e9).toFixed(2) + 'B' : n >= 1e6 ? '$' + (n / 1e6).toFixed(1) + 'M' : '$' + Number(n).toLocaleString());

const Bounty = {
    _esc(t) { return (t || '').replace(/[<>&"']/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;' }[c])); },
    _ago(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        if (isNaN(d)) return iso;
        const s = (Date.now() - d) / 1e3;
        if (s < 3600) return Math.max(1, Math.floor(s / 60)) + 'm ago';
        if (s < 86400) return Math.floor(s / 3600) + 'h ago';
        return Math.floor(s / 86400) + 'd ago';
    },
    _set(id, v) { const e = document.getElementById(id); if (!e) return; e.classList.remove('skeleton'); e.textContent = v; },

    // ── Generic client-side pagination (identical contract to app.js's own
    // _pgWire/_pgSlice/_pgReset — same "Showing X–Y of Z / Page N of M /
    // Prev/Next" footer convention used everywhere else on the site). ─────
    _pg: {},
    _pgWire(key, pageSize, onChange) {
        if (this._pg[key]) return;
        this._pg[key] = { page: 0, pageSize, onChange };
        const prev = document.getElementById(key + '-prev');
        const next = document.getElementById(key + '-next');
        if (prev) prev.addEventListener('click', () => { const st = this._pg[key]; st.page = Math.max(0, st.page - 1); st.onChange(); });
        if (next) next.addEventListener('click', () => { const st = this._pg[key]; st.page += 1; st.onChange(); });
    },
    _pgReset(key) { if (this._pg[key]) this._pg[key].page = 0; },
    _pgSlice(key, items, pageSize) {
        const st = this._pg[key];
        const size = pageSize || (st && st.pageSize) || 10;
        const total = items.length;
        const pages = Math.max(1, Math.ceil(total / size));
        let page = st ? st.page : 0;
        if (page > pages - 1) { page = pages - 1; if (st) st.page = page; }
        const countEl = document.getElementById(key + '-count');
        const pageEl = document.getElementById(key + '-page');
        const prev = document.getElementById(key + '-prev');
        const next = document.getElementById(key + '-next');
        if (countEl) countEl.textContent = total ? `Showing ${page * size + 1}–${Math.min(total, (page + 1) * size)} of ${total}` : 'No entries match this filter.';
        if (pageEl) pageEl.textContent = `Page ${page + 1} of ${pages}`;
        if (prev) prev.disabled = page <= 0;
        if (next) next.disabled = page + 1 >= pages;
        return items.slice(page * size, (page + 1) * size);
    },

    // Telemetry strip + live automation feed + VAPE's own audit track record.
    async bountyCommand() {
        try {
            const data = await (await fetch(`${RAW}/intel/bounty-radar/opportunities.json?t=` + Date.now())).json();
            const list = Array.isArray(data) ? data : [];
            const liveStatuses = new Set(['live', 'active']);
            const live = list.filter(o => liveStatuses.has((o.status || '').toLowerCase())).length;
            const platforms = new Set(list.map(o => o.platform).filter(Boolean));
            this._set('bcc-total', list.length.toLocaleString());
            this._set('bcc-live', live.toLocaleString());
            this._set('bcc-platforms', platforms.size);
            const updated = document.getElementById('bcc-updated');
            if (updated) updated.textContent = 'radar synced ' + new Date().toLocaleTimeString();
        } catch (e) {
            const updated = document.getElementById('bcc-updated');
            if (updated) updated.textContent = 'radar telemetry unavailable';
        }

        const taskFeedEl = document.getElementById('bcc-task-feed');
        const synthesisEl = document.getElementById('bcc-task-synthesis');
        const KIND_META = {
            investigation: ['fa-magnifying-glass-chart', '#60a5fa'],
            'bounty-radar': ['fa-satellite-dish', '#60a5fa'],
            audit: ['fa-file-shield', '#60a5fa'],
            broadcast: ['fa-tower-broadcast', '#a1a1aa'],
            reputation: ['fa-chart-line', '#a1a1aa'],
            sweep: ['fa-broom', '#a1a1aa'],
            'data-agent': ['fa-database', '#a1a1aa'],
            build: ['fa-code-merge', '#a1a1aa'],
            automation: ['fa-gears', '#a1a1aa'],
        };
        try {
            const feed = await (await fetch(`${RAW}/data/task-feed.json?t=` + Date.now())).json();
            const tasks = Array.isArray(feed.tasks) ? feed.tasks : [];
            this._set('bcc-tasks', tasks.length);
            if (synthesisEl) synthesisEl.textContent = feed.synthesis || '';
            if (!tasks.length) throw 0;
            this._taskFeedItems = tasks;
            this._taskFeedKindMeta = KIND_META;
            this._wireTaskFeedControls();
            this._renderTaskFeed();
        } catch (e) {
            if (taskFeedEl) taskFeedEl.innerHTML = '<div class="text-zinc-500 text-sm">No recent automated activity recorded.</div>';
            this._set('bcc-tasks', 0);
        }

        const auditEl = document.getElementById('bcc-audit-list');
        try {
            const items = await (await fetch(`https://api.github.com/repos/${REPO}/contents/intel/audits/hack-sweep-reports`)).json();
            const files = (Array.isArray(items) ? items : []).filter(f => f.name.endsWith('.md'))
                .map(f => {
                    const stopped = /-STOPPED/.test(f.name);
                    const m = f.name.match(/(\d{4}-\d{2}-\d{2})/);
                    const base = f.name.replace(/\.md$/, '').replace(/-STOPPED/, '').replace(/^(audit|lead|hack-sweep)-/, '').replace(/-\d{4}-\d{2}-\d{2}$/, '');
                    return { name: base.replace(/-/g, ' '), stopped, date: m ? m[1] : '', url: f.html_url, isAudit: !stopped };
                })
                .sort((a, b) => b.date.localeCompare(a.date));
            this._set('bcc-audits', files.filter(f => f.isAudit).length);
            if (!files.length) throw 0;
            this._auditFiles = files;
            this._wireAuditListControls();
            this._renderAuditList();
        } catch (e) {
            if (auditEl) auditEl.innerHTML = '<div class="text-zinc-500 text-sm">No audits filed yet. <a class="text-zinc-400 hover:underline" href="https://github.com/' + REPO + '/tree/main/intel/audits/hack-sweep-reports" target="_blank">Browse the audit ledger</a>.</div>';
        }
    },

    _taskFeedItems: [], _taskFeedKindMeta: {}, _taskFeedQuery: '',
    _wireTaskFeedControls() {
        if (this._taskFeedWired) return;
        this._taskFeedWired = true;
        const search = document.getElementById('bcc-task-search');
        if (search) search.addEventListener('input', () => {
            this._taskFeedQuery = search.value.trim().toLowerCase();
            this._pgReset('bcc-task-pg');
            this._renderTaskFeed();
        });
        this._pgWire('bcc-task-pg', 8, () => this._renderTaskFeed());
    },
    _renderTaskFeed() {
        const taskFeedEl = document.getElementById('bcc-task-feed');
        if (!taskFeedEl) return;
        let tasks = this._taskFeedItems;
        if (this._taskFeedQuery) tasks = tasks.filter(t => (t.message || '').toLowerCase().includes(this._taskFeedQuery) || (t.kind || '').toLowerCase().includes(this._taskFeedQuery));
        const items = this._pgSlice('bcc-task-pg', tasks, 8);
        taskFeedEl.innerHTML = items.length ? items.map(t => {
            const [icon, col] = this._taskFeedKindMeta[t.kind] || this._taskFeedKindMeta.automation || ['fa-gears', '#a1a1aa'];
            return `
            <a href="${t.url || '#'}" target="_blank" rel="noopener" class="card-h diff-row flex items-center gap-3">
                <i class="fa-solid ${icon} w-4 text-center shrink-0" style="color:${col}"></i>
                <div class="min-w-0 flex-1 text-xs text-zinc-300 truncate">${this._esc(t.message || '')}</div>
                <div class="text-[10px] text-zinc-500 shrink-0">${this._ago(t.date)}</div>
            </a>`;
        }).join('') : '<div class="text-zinc-500 text-sm">No automated activity matches this filter.</div>';
    },

    _auditFiles: [], _auditQuery: '',
    _wireAuditListControls() {
        if (this._auditWired) return;
        this._auditWired = true;
        const search = document.getElementById('bcc-audit-search');
        if (search) search.addEventListener('input', () => {
            this._auditQuery = search.value.trim().toLowerCase();
            this._pgReset('bcc-audit-pg');
            this._renderAuditList();
        });
        this._pgWire('bcc-audit-pg', 8, () => this._renderAuditList());
    },
    _renderAuditList() {
        const auditEl = document.getElementById('bcc-audit-list');
        if (!auditEl) return;
        let files = this._auditFiles;
        if (this._auditQuery) files = files.filter(f => f.name.includes(this._auditQuery));
        const items = this._pgSlice('bcc-audit-pg', files, 8);
        auditEl.innerHTML = items.length ? items.map(f => `
                <a href="${f.url}" target="_blank" class="card-h diff-row block">
                    <div class="flex items-center justify-between gap-2 mb-1.5">
                        <i class="fa-solid ${f.stopped ? 'fa-ban text-zinc-500' : 'fa-file-shield text-[#60a5fa]'}"></i>
                        <span class="text-[10px] ${f.stopped ? 'text-zinc-500' : 'text-[#60a5fa]'}">${f.stopped ? 'Lead stopped' : 'Audit filed'}</span>
                    </div>
                    <div class="text-xs leading-snug capitalize">${this._esc(f.name)}</div>
                    <div class="text-[10px] text-zinc-500 mt-1">${f.date}</div>
                </a>`).join('') : '<div class="text-zinc-500 text-sm">No audits match this filter.</div>';
    },

    // Bounty Ops: real, checklist-tracked programs written by
    // agents/bounty_ops.py to intel/bounty-radar/bounty-ops/*.json.
    _bountyOpsPromise: null,
    async _loadBountyOps() {
        if (this._bountyOpsPromise) return this._bountyOpsPromise;
        this._bountyOpsPromise = (async () => {
            try {
                const items = await (await fetch(`https://api.github.com/repos/${REPO}/contents/intel/bounty-radar/bounty-ops`)).json();
                const files = (Array.isArray(items) ? items : []).filter(f => f.name.endsWith('.json') && f.name !== 'INDEX.json');
                const entries = await Promise.all(files.map(f =>
                    fetch(`${RAW}/intel/bounty-radar/bounty-ops/${f.name}?t=` + Date.now()).then(r => r.json()).catch(() => null)
                ));
                const map = {};
                entries.filter(Boolean).forEach(e => {
                    const slug = (e.name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
                    map[slug] = e;
                });
                return map;
            } catch (e) { return {}; }
        })();
        return this._bountyOpsPromise;
    },

    _bountyOpsData: [], _bountyOpsMap: {}, _bountyOpsList: {}, _bountyOpsQuery: '',
    async bounties() {
        const el = document.getElementById('bounties');
        const searchEl = document.getElementById('bounty-ops-search');
        try {
            let data = await (await fetch(`${RAW}/intel/bounty-radar/opportunities.json?t=` + Date.now())).json();
            if (!Array.isArray(data)) data = [];
            data = data.filter(b => b.track === 'bounty' && b.vapeFit === true)
                       .sort((a, b) => (b.bountyFitScore || 0) - (a.bountyFitScore || 0)).slice(0, 30);
            if (!data.length) throw 0;
            const opsMap = await this._loadBountyOps();
            this._bountyOpsData = data;
            this._bountyOpsMap = opsMap;
            this._bountyOpsList = {};
            data.forEach(b => {
                const slug = (b.name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
                this._bountyOpsList[slug] = b;
            });
            if (searchEl) {
                searchEl.classList.remove('hidden');
                searchEl.oninput = () => {
                    this._bountyOpsQuery = searchEl.value.trim().toLowerCase();
                    this._pgReset('bounty-ops-pg');
                    this._renderBounties();
                };
            }
            this._pgWire('bounty-ops-pg', 6, () => this._renderBounties());
            this._renderBounties();
        } catch (e) {
            if (el) el.innerHTML = `<div class="text-zinc-500 text-sm">No live bounty program in scope right now. <a class="text-zinc-400 hover:underline" href="https://github.com/${REPO}/tree/main/intel/bounty-radar" target="_blank">Browse intel</a>.</div>`;
            if (searchEl) searchEl.classList.add('hidden');
        }
    },
    _renderBounties() {
        const el = document.getElementById('bounties');
        if (!el) return;
        const opsMap = this._bountyOpsMap;
        let data = this._bountyOpsData;
        if (this._bountyOpsQuery) {
            const q = this._bountyOpsQuery;
            data = data.filter(b => `${b.name || ''} ${b.platform || ''} ${(b.tags || []).join(' ')}`.toLowerCase().includes(q));
        }
        const items = this._pgSlice('bounty-ops-pg', data, 6);
        el.innerHTML = items.length ? items.map(b => {
            const slug = (b.name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
            const ops = opsMap[slug];
            const done = ops ? (ops.checklist || []).filter(i => i.done).length : 0;
            const total = ops ? (ops.checklist || []).length : 0;
            return `
            <div class="diff-row">
                <div class="flex items-start justify-between gap-2">
                    <div class="text-sm leading-snug">${this._esc(b.name || 'Unknown')}</div>
                    <div class="text-zinc-100 shrink-0">${b.prizeUsd ? fmtUsd(b.prizeUsd) : '…'}</div>
                </div>
                <div class="text-xs text-zinc-500 mt-2">${this._esc(b.platform || '')} ${b.status ? '· ' + this._esc(b.status) : ''}</div>
                ${b.vapeFitReason ? `<div class="text-[10px] text-[#60a5fa]/80 mt-1.5"><i class="fa-solid fa-check-circle"></i> ${this._esc(b.vapeFitReason)}</div>` : ''}
                ${(b.tags || []).slice(0, 4).map(t => `<span class="inline-block text-[10px] mr-2 mt-2 text-zinc-500">${this._esc(t)}</span>`).join('')}
                ${ops ? `<div class="mt-2 pt-2 border-t border-white/5 flex items-center justify-between text-[10px] text-zinc-500">
                    <span><i class="fa-solid fa-list-check"></i> Bounty Ops tracked${total ? ` · ${done}/${total} checklist` : ''}</span>
                    ${ops.vapeReportUrl ? `<span><i class="fa-solid fa-file-shield"></i> VAPE report</span>` : ''}
                </div>` : ''}
                <div class="mt-2.5 pt-2.5 border-t border-white/5 flex items-center gap-3">
                    <a href="${b.url || '#'}" target="_blank" class="text-[11px] text-zinc-500 hover:underline"><i class="fa-solid fa-arrow-up-right-from-square"></i> View program</a>
                    <button onclick="Hire.openBountyOps('${slug}')" class="text-[11px] text-[#60a5fa]/90 hover:underline"><i class="fa-solid fa-bolt"></i> Hire VAPE for this bounty</button>
                </div>
            </div>`;
        }).join('') : '<div class="text-zinc-500 text-sm">No bounty programs match this filter.</div>';
    },

    init() {
        Promise.allSettled([this.bountyCommand(), this.bounties()]);
    },
};

window.App = Bounty; // hire.js::openBountyOps() reads App._bountyOpsList — see module comment above.
document.addEventListener('DOMContentLoaded', () => Bounty.init());
