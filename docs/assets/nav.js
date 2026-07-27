// Tiny, self-contained mobile-nav toggle for news.html/article.html — these
// pages deliberately don't load app.js (see newspage.js's comment for why),
// so this duplicates just the nav-toggle slice of app.js's own bottom-level
// wiring rather than pulling in the whole file.
document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.getElementById('nav-menu-toggle');
    const navPanel = document.getElementById('nav-menu-panel');
    if (!navToggle || !navPanel) return;
    const OPEN = ['visible', 'opacity-100', 'scale-100', 'translate-y-0', 'pointer-events-auto'];
    const CLOSED = ['invisible', 'opacity-0', 'scale-[0.98]', '-translate-y-1', 'pointer-events-none'];
    const navBars = document.getElementById('nav-menu-bars');
    const navClose = document.getElementById('nav-menu-close');
    const setOpen = (open) => {
        navPanel.classList.remove(...(open ? CLOSED : OPEN));
        navPanel.classList.add(...(open ? OPEN : CLOSED));
        navToggle.setAttribute('aria-expanded', String(open));
        navBars?.classList.toggle('hidden', open);
        navClose?.classList.toggle('hidden', !open);
    };
    navToggle.addEventListener('click', () => setOpen(navPanel.classList.contains('invisible')));
    navPanel.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setOpen(false)));
    document.addEventListener('click', (e) => {
        if (!navPanel.classList.contains('invisible') && !navPanel.contains(e.target) && !navToggle.contains(e.target)) setOpen(false);
    });
});
