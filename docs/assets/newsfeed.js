// Home-page VAPE Wire teaser — a small preview of the latest stories,
// sitting between Platform Overview and the x402 Ledger. The breaking-
// headlines ticker that used to live here has moved to the top of the page
// (attackfeed.js's combined live-feed ticker, explicit direction
// 2026-08-01) — this file's only job now is the story tiles. The full,
// searchable/filterable archive lives on its own page (news.html, rendered
// by newspage.js) — this file intentionally only ever shows a handful of
// tiles and points readers there.
import { fetchStories, storyCardHtml } from './newswire.js';

const TEASER_COUNT = 3;

const NewsFeed = {
    async init() {
        const stories = await fetchStories();
        this._renderTeaser(stories);
    },

    async refresh() {
        await this.init();
    },

    _renderTeaser(stories) {
        const el = document.getElementById('news-grid');
        if (!el) return;
        const items = stories.slice(0, TEASER_COUNT);
        el.innerHTML = items.length
            ? items.map(storyCardHtml).join('')
            : '<div class="text-zinc-500 text-sm col-span-full">No stories published yet — VAPE Wire publishes new coverage on a schedule.</div>';
    },
};

window.NewsFeed = NewsFeed;
document.addEventListener('DOMContentLoaded', () => NewsFeed.init());
