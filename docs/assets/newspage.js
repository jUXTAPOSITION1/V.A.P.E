// VAPE Wire — the full news archive page (news.html): the same
// breaking-headlines ticker as the home-page teaser, plus every published
// story, searchable and filterable by topic. Deliberately does NOT load
// docs/assets/app.js — that file's bottom-level DOMContentLoaded handler
// wires dozens of main-site-only element ids with no existence guards on
// several of them (e.g. `document.getElementById('hunt-target').addEventListener(...)`),
// so loading it on a page that lacks those ids throws partway through and
// silently kills everything after it in that handler, including this
// page's own nav toggle. This page brings its own tiny pagination
// (newswire.js::wirePager/renderPage) instead.
import { fetchTicker, fetchStories, wireTicker, storyCardHtml, wirePager, renderPage } from './newswire.js';

const PAGE_SIZE = 9;

const NewsPage = {
    _stories: [],
    _q: '', _topic: '',
    _page: { n: 0 },

    async init() {
        const [headlines, stories] = await Promise.all([fetchTicker(), fetchStories()]);
        wireTicker(headlines, 'news-ticker');
        this._stories = stories;
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
        this._page.n = 0;
        const search = document.getElementById('news-search');
        if (search) search.value = '';
        this._renderTopicFilter();
        this._renderGrid();
    },

    _wireControls() {
        const search = document.getElementById('news-search');
        if (search) {
            search.addEventListener('input', () => {
                this._q = search.value.trim().toLowerCase();
                this._page.n = 0;
                this._renderGrid();
            });
        }
        wirePager(this._page, () => this._renderGrid());
    },

    _renderTopicFilter() {
        const wrap = document.getElementById('news-topic-filter');
        if (!wrap) return;
        const topics = [...new Set(this._stories.map(s => s.topic).filter(Boolean))];
        wrap.innerHTML = topics.map(t => `
            <button type="button" data-topic="${t.replace(/"/g, '&quot;')}"
                class="term-btn term-btn-sm ${this._topic === t ? 'term-btn-active' : ''}">${t}</button>
        `).join('');
        wrap.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                this._topic = this._topic === btn.dataset.topic ? '' : btn.dataset.topic;
                this._page.n = 0;
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

    _renderGrid() {
        const el = document.getElementById('news-grid');
        if (!el) return;
        const items = renderPage(this._page, this._filtered(), PAGE_SIZE);
        el.innerHTML = items.length
            ? items.map(storyCardHtml).join('')
            : '<div class="text-zinc-500 text-sm col-span-full">No stories match this filter yet. New coverage publishes on a schedule.</div>';
    },
};

window.NewsPage = NewsPage;
document.addEventListener('DOMContentLoaded', () => NewsPage.init());
