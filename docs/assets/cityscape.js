// VAPE City — a live, bird's-eye isometric map of VAPE's own real signals.
// Every building is one real process this repo runs (data/city-state.json,
// written by agents/build_city_state.py from security-dashboard.json,
// attack-feed.json, intel-index.json, opportunities.json, and
// reputation.json); every road is a fixed layout choice, never a data
// claim; every moving "delivery truck" on the streets is one real settled
// x402 job, polled live from the same worker feed x402feed.js already
// reads. One module, two mount sizes — any element with
// `data-city-stage="compact"` or `data-city-stage="full"` on the current
// page gets its own live instance, so the exact same engine backs the
// small diorama inside #security-dashboard and the huge dedicated
// docs/city.html page with zero page-specific branching.
//
// Scene model vs. renderer are kept deliberately separate (buildings/roads/
// vehicles are plain data with grid positions; only the draw functions know
// about isometric projection or canvas) so a future walkable 3D view can
// read the same data/city-state.json and swap in a different renderer
// without touching the data shape.

const CITY_STATE_URL = 'https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/data/city-state.json';
// Not every page mounting this module also loads app.js (which sets
// WORKER_BASE as a side effect) -- city.html doesn't need app.js at
// all, so this module carries the same worker origin x402feed.js/app.js
// already hardcode, and only falls back to it when nothing set the global.
const WORKER_BASE = window.WORKER_BASE || 'https://vape-x402.vapex402.workers.dev';

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// data/city-state.json's `link` fields are all repository-controlled
// constants today (see agents/build_city_state.py's LAYOUT/build_landmarks),
// but that file is fetched over the network from a mutable branch --
// escapeHtml alone stops an attribute breakout, not a javascript:/data:
// scheme landing in href. Only relative paths/anchors and explicit http(s)
// pass through.
function safeHref(url) {
    const s = String(url ?? '').trim();
    if (/^(https?:)?\/\//i.test(s)) return s;
    if (/^[a-z][a-z0-9+.-]*:/i.test(s)) return '';
    return s;
}

// Cached -- the render loop calls this tens of times per frame at ~30fps,
// and every one of these tokens is a static :root value that never changes
// after first paint.
const _cssVarCache = new Map();
function cssVar(name) {
    if (!_cssVarCache.has(name)) {
        _cssVarCache.set(name, getComputedStyle(document.documentElement).getPropertyValue(name).trim());
    }
    return _cssVarCache.get(name);
}

// Canvas's `font` setter parses its value as a CSS <'font'> shorthand and
// silently ignores anything containing var() (per the HTML spec, "property-
// independent style sheet syntax" isn't allowed there) -- so `ctx.font =
// '...var(--font-sans)...'` never actually applies and just keeps whatever
// font canvas already had. Resolve the custom property to a real value once
// and build the shorthand from that instead.
let _canvasFontFamily = null;
function canvasFontFamily() {
    if (_canvasFontFamily === null) {
        _canvasFontFamily = cssVar('--font-sans') || 'sans-serif';
    }
    return _canvasFontFamily;
}

// One vocabulary for every building kind: status -> color. Shared across
// both toggleable layers' "Health" mode and every alert-glow decision,
// mirroring securitydashboard.js's own sevColor() single-source pattern.
function statusColor(status) {
    if (status === 'ok') return cssVar('--sev-low');
    if (status === 'warn') return cssVar('--sev-medium');
    if (status === 'alert') return cssVar('--sev-critical');
    return cssVar('--sev-info');
}

// Landmark kind -> its own identity hue (the "Overview" layer). Checkpoints
// (the 10 automated lanes) have no individual kind identity worth a distinct
// color -- their status IS the signal -- so they always render by status,
// in both layers.
const KIND_VAR = {
    precinct: '--city-precinct', tower: '--city-tower', newsroom: '--city-newsroom',
    watchtower: '--city-watchtower', mint: '--city-mint', foundry: '--city-foundry', vault: '--city-vault',
};
function kindColor(kind) {
    const v = KIND_VAR[kind];
    return v ? cssVar(v) : cssVar('--sev-info');
}

// Terrain hues are their own ramp -- deliberately not part of the 7
// validated building-identity colors above (different job: quiet backdrop,
// not a categorical data set shown side-by-side).
const TERRAIN_KIND_VAR = {
    ocean: '--city-terrain-ocean', mountain: '--city-terrain-mountain',
    farmland: '--city-terrain-farmland', vacant: '--city-terrain-vacant',
};
function terrainColor(kind) {
    return cssVar(TERRAIN_KIND_VAR[kind]) || '#232329';
}

// Isometric projection constants -- 2:1 tile ratio, the standard web
// isometric convention (screen dx/dy are half the tile's width/height per
// grid step) that keeps the math to four multiplies, no trig.
const TILE_W = 64, TILE_H = 32;
const TIER_UNIT = 15, BASE_HEIGHT = 18;

function gridToScreen(gx, gy) {
    return { x: (gx - gy) * (TILE_W / 2), y: (gx + gy) * (TILE_H / 2) };
}

function buildingAnchor(b) {
    // Screen point at the center of a building's footprint, ground level.
    const [fw, fh] = b.footprint || [1, 1];
    return gridToScreen(b.gridX + fw / 2, b.gridY + fh / 2);
}

function buildingHeightPx(b) {
    return BASE_HEIGHT + (b.tier || 1) * TIER_UNIT;
}

// ── The surrounding world (full mode only) — ocean, mountains, farmland,
// vacant land around the real-data city. Deliberately client-side and NOT
// part of data/city-state.json: unlike every building/road/vehicle above,
// terrain traces to no real signal at all, so it stays out of the
// aggregator's "every number here is real" contract entirely. It's the
// same kind of presentational, non-data choice as the fixed road layout,
// just bigger -- and it's fully deterministic (a fixed seed, not
// Math.random()) so the world reads as one stable place across visits,
// never a randomly different backdrop.
const WORLD_BOUNDS = { minX: -40, maxX: 60, minY: -40, maxY: 53 };
const CITY_BBOX = { minX: 0, maxX: 12, minY: 0, maxY: 9 }; // real buildings' footprint-inclusive extent
const VACANT_MARGIN = 3; // tiles of guaranteed "room to grow" ring around downtown
const TERRAIN_SEED = 402019;

function _hash(n, seed) {
    const x = Math.sin(n * 12.9898 + seed * 78.233) * 43758.5453;
    return x - Math.floor(x);
}
function _valueNoise1D(x, seed) {
    const i = Math.floor(x), f = x - i;
    const a = _hash(i, seed), b = _hash(i + 1, seed);
    const t = f * f * (3 - 2 * f); // smoothstep
    return a + (b - a) * t;
}
// Two octaves so region edges (coastlines, mountain foothills) wobble
// organically instead of reading as a ruler-straight boundary.
function _wobble(x, seedOffset) {
    return (_valueNoise1D(x / 6, TERRAIN_SEED + seedOffset) - 0.5) * 6
        + (_valueNoise1D(x / 2.4, TERRAIN_SEED + seedOffset + 1) - 0.5) * 2;
}

// Pure function of (gx, gy) + the fixed seed above -- same biome every
// load, no canvas/DOM access, mirrors this module's own "scene model is
// plain data" discipline. Returns null inside the real city's own
// footprint (buildings own that ground, no terrain tile is drawn there).
function biomeAt(gx, gy) {
    const insideCity = gx >= CITY_BBOX.minX && gx <= CITY_BBOX.maxX && gy >= CITY_BBOX.minY && gy <= CITY_BBOX.maxY;
    if (insideCity) return null;
    const insideMargin = gx >= CITY_BBOX.minX - VACANT_MARGIN && gx <= CITY_BBOX.maxX + VACANT_MARGIN
        && gy >= CITY_BBOX.minY - VACANT_MARGIN && gy <= CITY_BBOX.maxY + VACANT_MARGIN;
    if (insideMargin) return 'vacant'; // guaranteed room to grow, regardless of the macro region below
    const u = gx - gy, v = gx + gy; // the same two axes gridToScreen already projects on
    if (v < -30 + _wobble(u, 10)) return 'ocean';
    if (v > 78 + _wobble(u, 20)) return 'mountain';
    if (u < -49 + _wobble(v, 30)) return 'farmland';
    return 'vacant';
}

// Real offering-name -> building-id routing for live x402 "delivery truck"
// vehicles. The offering name itself is real (worker/src/lib/jobLog.ts's
// JobRecord.offering); which building visually receives it is a display
// choice, same category as the fixed road layout below -- not a data claim.
const OFFERING_TARGET = [
    [/invest|dossier|wallet|profile/i, 'precinct-investigations'],
    [/audit|exploit|deep_dive|redteam|contract/i, 'foundry'],
    [/bounty/i, 'tower-bounty'],
    [/news|article|broadcast/i, 'newsroom'],
    [/threat|attack|incident/i, 'watchtower-threat'],
];
function targetForOffering(offering) {
    const s = String(offering || '');
    for (const [re, id] of OFFERING_TARGET) if (re.test(s)) return id;
    return 'foundry';
}

const CityScape = {
    _cityState: null,
    _instances: [],
    // The world is identical (same fixed seed) for every 'full' instance,
    // so it's built once and shared rather than per-instance state.
    _terrainCanvas: null,
    _terrainOrigin: null,

    async init() {
        const stages = document.querySelectorAll('[data-city-stage]');
        if (!stages.length) return;
        try {
            const res = await fetch(`${CITY_STATE_URL}?t=${Math.floor(Date.now() / 300000)}`);
            if (!res.ok) throw new Error(`city-state ${res.status}`);
            this._cityState = await res.json();
        } catch (e) {
            this._cityState = null;
        }
        this._renderUpdated();
        stages.forEach(el => this._mount(el));
    },

    _renderUpdated() {
        const el = document.getElementById('city-updated');
        if (!el) return;
        const ts = this._cityState && this._cityState.generated_at;
        const d = ts && new Date(ts);
        el.textContent = d && !isNaN(d) ? `updated ${d.toLocaleString()}` : 'city state unavailable this cycle';
    },

    _mount(el) {
        const mode = el.dataset.cityStage === 'full' ? 'full' : 'compact';
        const canvas = document.createElement('canvas');
        canvas.className = 'city-canvas';
        el.appendChild(canvas);

        const inst = {
            el, canvas, ctx: canvas.getContext('2d'), mode,
            buildings: [], roads: [], hitboxes: [],
            scale: mode === 'full' ? 1 : 0.72,
            offsetX: 0, offsetY: 0,
            layer: 'overview',
            selected: null,
            vehicles: [], ambient: [], oceanGlints: [],
            lastX402: new Set(),
            lastFrame: 0,
            visible: true,
        };
        this._instances.push(inst);

        // Only the full page ever shows the wider world -- the compact
        // diorama stays exactly the tightly-cropped city glance it always
        // was (no terrain build cost on a widely-embedded small widget).
        if (mode === 'full') {
            if (!this._terrainCanvas) this._buildTerrainCache();
            inst.oceanGlints = Array.from({ length: 10 }, () => this._spawnOceanGlint());
        }

        if (this._cityState) this._loadCity(inst, this._cityState);
        this._wireInteraction(inst);
        this._resize(inst);
        new ResizeObserver(() => this._resize(inst)).observe(el);
        // The compact stage sits inside a long page -- scrolled past, it has
        // no reason to keep clearing/repainting ~30 times a second.
        new IntersectionObserver(([entry]) => { inst.visible = entry.isIntersecting; }, { rootMargin: '100px' }).observe(el);
        requestAnimationFrame(t => this._frame(inst, t));

        if (WORKER_BASE) {
            this._pollX402(inst);
            setInterval(() => this._pollX402(inst), mode === 'full' ? 25000 : 60000);
        }
    },

    _loadCity(inst, city) {
        inst.buildings = (city.buildings || []).map(b => ({ ...b, anchor: buildingAnchor(b) }));
        inst.roads = (city.roads || []).map(([fromId, toId]) => {
            const from = inst.buildings.find(b => b.id === fromId);
            const to = inst.buildings.find(b => b.id === toId);
            return from && to ? { from, to } : null;
        }).filter(Boolean);
        inst.ambient = inst.roads.length ? Array.from({ length: 6 }, (_, i) => ({
            road: inst.roads[i % inst.roads.length],
            t: Math.random(),
            speed: 0.00012 + Math.random() * 0.00008,
            dir: Math.random() < 0.5 ? 1 : -1,
        })) : [];
        this._renderStatStrip(inst, city);
        this._renderA11yList(inst);
    },

    // Screen-reader-only equivalent of the canvas -- the dataviz
    // accessibility requirement ("a table view exists") without visually
    // duplicating the map for sighted users, same pattern as
    // securitydashboard.js's _renderLanesA11yList().
    _renderA11yList(inst) {
        const list = inst.el.parentElement && inst.el.parentElement.querySelector('[data-city-a11y]');
        if (!list) return;
        list.innerHTML = inst.buildings.map(b => {
            const stat = b.stat_primary && b.stat_primary.value != null
                ? `, ${escapeHtml(b.stat_primary.label)}: ${escapeHtml(b.stat_primary.value)}` : '';
            return `<li>${escapeHtml(b.title)}: ${escapeHtml(b.status)}${stat}</li>`;
        }).join('');
    },

    _renderStatStrip(inst, city) {
        const strip = inst.el.querySelector('.city-stat-strip');
        if (!strip) return;
        const ds = city.district_stats || {};
        strip.innerHTML = `
            <span class="stat"><b>${ds.lanes_passing ?? '…'}/${ds.lanes_total ?? '…'}</b>lanes</span>
            <span class="stat"><b>${(ds.buildings_total ?? inst.buildings.length).toLocaleString()}</b>buildings</span>
            ${ds.overall_threat_level ? `<span class="stat"><b>${escapeHtml(ds.overall_threat_level)}</b>threat</span>` : ''}
        `;
    },

    // ── Interaction: pointer-based drag/pinch/zoom + click-to-inspect ──────
    _wireInteraction(inst) {
        const { el, canvas } = inst;
        const pointers = new Map();
        let pinchStartDist = 0, pinchStartScale = 1;
        let dragStart = null;
        let moved = false;

        // Full mode's floor is low enough that zooming all the way out
        // reveals the entire ~100x93-tile world, not just downtown; compact
        // never shows the world at all, so its floor is unchanged.
        const clampScale = s => Math.max(inst.mode === 'full' ? 0.07 : 0.5, Math.min(2.6, s));

        canvas.addEventListener('pointerdown', (e) => {
            canvas.setPointerCapture(e.pointerId);
            pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
            moved = false;
            if (pointers.size === 1) {
                dragStart = { x: e.clientX, y: e.clientY, offX: inst.offsetX, offY: inst.offsetY };
            } else if (pointers.size === 2) {
                const [a, b] = [...pointers.values()];
                pinchStartDist = Math.hypot(a.x - b.x, a.y - b.y) || 1;
                pinchStartScale = inst.scale;
            }
        });
        canvas.addEventListener('pointermove', (e) => {
            if (!pointers.has(e.pointerId)) return;
            pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
            if (pointers.size === 2) {
                const [a, b] = [...pointers.values()];
                const dist = Math.hypot(a.x - b.x, a.y - b.y) || 1;
                inst.scale = clampScale(pinchStartScale * (dist / pinchStartDist));
                moved = true;
            } else if (dragStart) {
                // moved is tracked in every mode (a compact-stage drag must
                // not be misread as a tap by the click handler below); only
                // 'full' mode actually pans the camera with it.
                if (Math.abs(e.clientX - dragStart.x) + Math.abs(e.clientY - dragStart.y) > 4) moved = true;
                if (inst.mode === 'full') {
                    inst.offsetX = dragStart.offX + (e.clientX - dragStart.x);
                    inst.offsetY = dragStart.offY + (e.clientY - dragStart.y);
                }
            }
        });
        const endPointer = (e) => {
            pointers.delete(e.pointerId);
            if (pointers.size === 0) dragStart = null;
        };
        canvas.addEventListener('pointerup', endPointer);
        canvas.addEventListener('pointercancel', endPointer);

        if (inst.mode === 'full') {
            canvas.addEventListener('wheel', (e) => {
                e.preventDefault();
                const factor = e.deltaY < 0 ? 1.1 : 0.9;
                inst.scale = clampScale(inst.scale * factor);
            }, { passive: false });
            canvas.addEventListener('dblclick', (e) => { inst.scale = clampScale(inst.scale * 1.4); });
        }

        canvas.addEventListener('click', (e) => {
            if (moved) return;
            const rect = canvas.getBoundingClientRect();
            this._handleClick(inst, e.clientX - rect.left, e.clientY - rect.top);
        });

        const layerBtns = inst.el.querySelectorAll('[data-city-layer]');
        layerBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                inst.layer = btn.dataset.cityLayer;
                layerBtns.forEach(b => b.classList.toggle('is-active', b === btn));
            });
        });
        const zoomIn = inst.el.querySelector('[data-city-zoom="in"]');
        const zoomOut = inst.el.querySelector('[data-city-zoom="out"]');
        const zoomReset = inst.el.querySelector('[data-city-zoom="reset"]');
        if (zoomIn) zoomIn.addEventListener('click', () => { inst.scale = clampScale(inst.scale * 1.25); });
        if (zoomOut) zoomOut.addEventListener('click', () => { inst.scale = clampScale(inst.scale * 0.8); });
        // A one-tap way back to downtown after zooming/panning out to see
        // the wider world -- only meaningful in 'full' mode.
        if (zoomReset) zoomReset.addEventListener('click', () => { inst.scale = 1; inst.offsetX = 0; inst.offsetY = 0; });
    },

    _handleClick(inst, px, py) {
        const w = inst.canvas.clientWidth, h = inst.canvas.clientHeight;
        const originX = w / 2 + inst.offsetX, originY = h * 0.32 + inst.offsetY;
        let hit = null;
        // hitboxes are pushed in painter's-algorithm (back-to-front) draw
        // order, and generous hit-box padding means neighbors overlap --
        // walk it in reverse so an overlapping click resolves to whichever
        // building was actually drawn on top.
        for (let i = inst.hitboxes.length - 1; i >= 0; i--) {
            const box = inst.hitboxes[i];
            const dx = (px - (originX + box.x * inst.scale)) / inst.scale;
            const dy = (py - (originY + box.y * inst.scale)) / inst.scale;
            if (Math.abs(dx) < box.hw && Math.abs(dy) < box.hh) { hit = box.building; break; }
        }
        if (hit) this._showDetail(inst, hit);
        else this._hideDetail(inst);
    },

    _showDetail(inst, b) {
        inst.selected = b.id;
        let card = inst.el.querySelector('.city-detail-card');
        if (!card) {
            card = document.createElement('div');
            card.className = 'city-detail-card';
            inst.el.appendChild(card);
        }
        const color = b.kind === 'checkpoint' ? statusColor(b.status) : kindColor(b.kind);
        const rows = [];
        if (b.stat_primary && b.stat_primary.value != null) {
            rows.push(`<div class="city-detail-row"><span>${escapeHtml(b.stat_primary.label)}</span><b>${escapeHtml(b.stat_primary.value)}</b></div>`);
        } else if (b.live_only) {
            rows.push(`<div class="city-detail-row"><span>status</span><b>${inst.mintLive ? 'live' : '…'}</b></div>`);
        }
        (b.stat_secondary || []).forEach(s => {
            if (s.value == null) return;
            rows.push(`<div class="city-detail-row"><span>${escapeHtml(s.label)}</span><b>${escapeHtml(s.value)}</b></div>`);
        });
        card.innerHTML = `
            <div class="city-detail-title">
                <span class="dot" style="background:${color}"></span>
                <span>${escapeHtml(b.title)}</span>
                <button type="button" class="city-detail-close" data-close>Close ✕</button>
            </div>
            ${rows.join('') || '<div class="city-detail-row"><span>No data this cycle.</span></div>'}
            ${safeHref(b.link) ? `<a class="city-detail-link" href="${escapeHtml(safeHref(b.link))}">Open <i class="fa-solid fa-arrow-right text-[9px]"></i></a>` : ''}
        `;
        card.style.display = 'block';
        // Position near the building, clamped inside the stage.
        const box = inst.hitboxes.find(h => h.building.id === b.id);
        const w = inst.el.clientWidth, h = inst.el.clientHeight;
        if (box) {
            const originX = w / 2 + inst.offsetX, originY = h * 0.32 + inst.offsetY;
            let left = originX + box.x * inst.scale - 100;
            let top = originY + box.y * inst.scale - 70;
            left = Math.max(6, Math.min(w - 226, left));
            top = Math.max(6, Math.min(h - 140, top));
            card.style.left = `${left}px`;
            card.style.top = `${top}px`;
        }
        card.querySelector('[data-close]').addEventListener('click', (e) => { e.stopPropagation(); this._hideDetail(inst); });
    },

    _hideDetail(inst) {
        inst.selected = null;
        const card = inst.el.querySelector('.city-detail-card');
        if (card) card.style.display = 'none';
    },

    // ── Live x402 settlements -> moving delivery vehicles ───────────────────
    async _pollX402(inst) {
        try {
            const r = await fetch(`${WORKER_BASE}/x402/feed?limit=6`, { signal: AbortSignal.timeout(8000) });
            const data = await r.json();
            const jobs = Array.isArray(data.jobs) ? data.jobs : Array.isArray(data) ? data : [];
            inst.mintLive = jobs.length > 0;
            const mint = inst.buildings.find(b => b.id === 'mint-x402');
            const nextMintStatus = inst.mintLive ? 'ok' : 'unknown';
            if (mint && mint.status !== nextMintStatus) {
                mint.status = nextMintStatus;
                this._renderA11yList(inst); // the sr-only list is the canvas's declared text equivalent -- keep it in sync
            }
            jobs.forEach(job => {
                const key = job.tx_hash || job.id;
                if (!key || inst.lastX402.has(key) || job.status !== 'settled') return;
                inst.lastX402.add(key);
                this._spawnVehicle(inst, 'mint-x402', targetForOffering(job.offering), {
                    offering: job.offering, amount_usd: job.amount_usd, tx_hash: job.tx_hash,
                });
            });
            if (inst.lastX402.size > 200) inst.lastX402 = new Set([...inst.lastX402].slice(-100));
        } catch (e) { /* mint building just stays in its 'unknown' state this cycle */ }
    },

    _spawnVehicle(inst, fromId, toId, meta) {
        const from = inst.buildings.find(b => b.id === fromId);
        const to = inst.buildings.find(b => b.id === toId);
        if (!from || !to) return;
        inst.vehicles.push({ from, to, t: 0, meta, speed: 0.00035 });
    },

    // ── Render loop ──────────────────────────────────────────────────────────
    _resize(inst) {
        const dpr = Math.min(2, window.devicePixelRatio || 1);
        const w = inst.el.clientWidth, h = inst.el.clientHeight;
        inst.canvas.width = Math.max(1, Math.round(w * dpr));
        inst.canvas.height = Math.max(1, Math.round(h * dpr));
        inst.canvas.style.width = `${w}px`;
        inst.canvas.style.height = `${h}px`;
        inst.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    },

    _frame(inst, t) {
        if (inst.visible && t - inst.lastFrame > 33) { // ~30fps cap, mobile-friendly
            inst.lastFrame = t;
            // An uncaught throw here would stop this rAF chain from ever
            // rescheduling itself, freezing the canvas for the rest of the
            // page session -- degrade to a static frame instead.
            try {
                this._advance(inst);
                this._draw(inst);
            } catch (e) {
                console.error('[CityScape] frame', e);
            }
        }
        requestAnimationFrame(tt => this._frame(inst, tt));
    },

    _advance(inst) {
        inst.ambient.forEach(a => {
            a.t += a.speed * a.dir * 16;
            if (a.t > 1 || a.t < 0) { a.dir *= -1; a.t = Math.max(0, Math.min(1, a.t)); }
        });
        inst.vehicles.forEach(v => { v.t += v.speed * 16; });
        inst.vehicles = inst.vehicles.filter(v => v.t < 1);
    },

    _draw(inst) {
        const { ctx } = inst;
        const w = inst.canvas.clientWidth, h = inst.canvas.clientHeight;
        ctx.clearRect(0, 0, w, h);
        if (!inst.buildings.length) {
            ctx.fillStyle = '#52525b';
            ctx.font = `12px ${canvasFontFamily()}, sans-serif`;
            ctx.textAlign = 'center';
            ctx.fillText('Syncing city state…', w / 2, h / 2);
            return;
        }
        ctx.save();
        ctx.translate(w / 2 + inst.offsetX, h * 0.32 + inst.offsetY);
        ctx.scale(inst.scale, inst.scale);

        if (this._terrainCanvas) ctx.drawImage(this._terrainCanvas, this._terrainOrigin.x, this._terrainOrigin.y);
        this._drawOceanGlints(inst);
        this._drawRoads(inst);
        this._drawAmbient(inst);
        inst.hitboxes = [];
        // Painter's algorithm: back-to-front by (gridX+gridY) so nearer
        // buildings correctly occlude farther ones.
        const ordered = [...inst.buildings].sort((a, b) => (a.gridX + a.gridY) - (b.gridX + b.gridY));
        ordered.forEach(b => this._drawBuilding(inst, b));
        this._drawVehicles(inst);

        ctx.restore();
    },

    _drawRoads(inst) {
        const { ctx } = inst;
        ctx.strokeStyle = 'rgba(255,255,255,0.09)';
        ctx.lineWidth = 9;
        ctx.lineCap = 'round';
        inst.roads.forEach(r => {
            ctx.beginPath();
            ctx.moveTo(r.from.anchor.x, r.from.anchor.y);
            ctx.lineTo(r.to.anchor.x, r.to.anchor.y);
            ctx.stroke();
        });
        ctx.strokeStyle = 'rgba(255,255,255,0.16)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 5]);
        inst.roads.forEach(r => {
            ctx.beginPath();
            ctx.moveTo(r.from.anchor.x, r.from.anchor.y);
            ctx.lineTo(r.to.anchor.x, r.to.anchor.y);
            ctx.stroke();
        });
        ctx.setLineDash([]);
    },

    _lerp(a, b, t) { return a + (b - a) * t; },

    _drawAmbient(inst) {
        const { ctx } = inst;
        inst.ambient.forEach(a => {
            const x = this._lerp(a.road.from.anchor.x, a.road.to.anchor.x, a.t);
            const y = this._lerp(a.road.from.anchor.y, a.road.to.anchor.y, a.t);
            ctx.beginPath();
            ctx.arc(x, y - 3, 2, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(228,228,231,0.5)';
            ctx.fill();
        });
    },

    _drawVehicles(inst) {
        const { ctx } = inst;
        inst.vehicles.forEach(v => {
            const x = this._lerp(v.from.anchor.x, v.to.anchor.x, v.t);
            const y = this._lerp(v.from.anchor.y, v.to.anchor.y, v.t);
            ctx.save();
            ctx.beginPath();
            ctx.arc(x, y - 4, 4, 0, Math.PI * 2);
            ctx.fillStyle = cssVar('--city-mint') || '#008300';
            ctx.shadowColor = ctx.fillStyle;
            ctx.shadowBlur = 8;
            ctx.fill();
            ctx.restore();
        });
    },

    _drawBuilding(inst, b) {
        const { ctx } = inst;
        const [fw, fh] = b.footprint || [1, 1];
        const hw = (fw * TILE_W) / 2, hh = (fh * TILE_H) / 2;
        const H = buildingHeightPx(b);
        const { x: cx, y: cy } = b.anchor;
        const isCheckpoint = b.kind === 'checkpoint';
        const base = isCheckpoint || inst.layer === 'health' ? statusColor(b.status) : kindColor(b.kind);
        const alert = b.status === 'alert';

        const top = { x: cx, y: cy - hh - H };
        const right = { x: cx + hw, y: cy - H };
        const bottom = { x: cx, y: cy + hh - H };
        const left = { x: cx - hw, y: cy - H };
        const rightBase = { x: cx + hw, y: cy };
        const bottomBase = { x: cx, y: cy + hh };
        const leftBase = { x: cx - hw, y: cy };

        if (alert) {
            ctx.save();
            ctx.shadowColor = base;
            ctx.shadowBlur = 16;
        }

        // Left face (darker), right face (mid), top face (brightest).
        ctx.fillStyle = this._shade(base, -0.35);
        ctx.beginPath();
        ctx.moveTo(left.x, left.y); ctx.lineTo(bottom.x, bottom.y);
        ctx.lineTo(bottomBase.x, bottomBase.y); ctx.lineTo(leftBase.x, leftBase.y);
        ctx.closePath(); ctx.fill();

        ctx.fillStyle = this._shade(base, -0.15);
        ctx.beginPath();
        ctx.moveTo(right.x, right.y); ctx.lineTo(bottom.x, bottom.y);
        ctx.lineTo(bottomBase.x, bottomBase.y); ctx.lineTo(rightBase.x, rightBase.y);
        ctx.closePath(); ctx.fill();

        ctx.fillStyle = base;
        ctx.beginPath();
        ctx.moveTo(top.x, top.y); ctx.lineTo(right.x, right.y);
        ctx.lineTo(bottom.x, bottom.y); ctx.lineTo(left.x, left.y);
        ctx.closePath(); ctx.fill();

        ctx.strokeStyle = 'rgba(0,0,0,0.35)';
        ctx.lineWidth = 1;
        ctx.stroke();

        if (alert) ctx.restore();

        // A small initial-letter mark on the top face for landmarks (not
        // checkpoints -- 10 tiny identical marks would just be noise at
        // this scale). Canvas text can't render Font Awesome's ligature
        // glyphs, so this stays a plain letter rather than a broken icon.
        if (!isCheckpoint && inst.mode === 'full') {
            ctx.fillStyle = 'rgba(9,9,11,0.55)';
            ctx.font = `600 11px ${canvasFontFamily()}, sans-serif`;
            ctx.textAlign = 'center';
            ctx.fillText(String(b.title || '?').charAt(0), top.x, top.y + 4);
        }

        inst.hitboxes.push({ building: b, x: cx, y: cy - H / 2, hw: hw + 6, hh: hh + H / 2 + 6 });
    },

    _shade(hex, amt) {
        const h = (hex || '#71717a').replace('#', '');
        if (h.length !== 6) return hex;
        const n = parseInt(h, 16);
        let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
        const f = c => Math.max(0, Math.min(255, Math.round(c + (amt < 0 ? c * amt : (255 - c) * amt))));
        r = f(r); g = f(g); b = f(b);
        return `rgb(${r},${g},${b})`;
    },

    // ── The surrounding world (built once, shared by every 'full' instance)
    _buildTerrainCache() {
        const { minX, maxX, minY, maxY } = WORLD_BOUNDS;
        // Screen-space bounding box of the whole world under gridToScreen,
        // plus a small slack margin for mountain-peak extrusion.
        const xMin = (minX - maxY) * (TILE_W / 2) - 40;
        const xMax = (maxX - minY) * (TILE_W / 2) + 40;
        const yMin = (minX + minY) * (TILE_H / 2) - 40;
        const yMax = (maxX + maxY) * (TILE_H / 2) + 40;
        const w = Math.ceil(xMax - xMin), h = Math.ceil(yMax - yMin);

        const cvs = typeof OffscreenCanvas !== 'undefined'
            ? new OffscreenCanvas(w, h)
            : Object.assign(document.createElement('canvas'), { width: w, height: h });
        const ctx = cvs.getContext('2d');

        // Same back-to-front diagonal order as _draw()'s building sort, so
        // overlapping mountain-peak extrusions occlude correctly.
        for (let sum = minX + minY; sum <= maxX + maxY; sum++) {
            const gxLo = Math.max(minX, sum - maxY), gxHi = Math.min(maxX, sum - minY);
            for (let gx = gxLo; gx <= gxHi; gx++) {
                const gy = sum - gx;
                const biome = biomeAt(gx, gy);
                if (biome) this._drawTerrainTile(ctx, biome, gx, gy, -xMin, -yMin);
            }
        }
        this._terrainCanvas = cvs;
        this._terrainOrigin = { x: xMin, y: yMin };
    },

    _drawTerrainTile(ctx, biome, gx, gy, dx, dy) {
        const g = gridToScreen(gx + 0.5, gy + 0.5);
        const cx = g.x + dx, cy = g.y + dy;
        const hw = TILE_W / 2, hh = TILE_H / 2;
        const color = terrainColor(biome);
        // Mountains are the one terrain type with height -- kept short
        // (8-24px, vs. buildings' 33-78px) so they read as backdrop, never
        // competing with a real tier-4 landmark. A little per-tile noise
        // keeps a mountain range from looking like a flat plateau.
        const H = biome === 'mountain' ? 8 + Math.round(_valueNoise1D(gx * 7 + gy * 3, TERRAIN_SEED + 99) * 16) : 0;

        const top = { x: cx, y: cy - hh - H };
        const right = { x: cx + hw, y: cy - H };
        const bottom = { x: cx, y: cy + hh - H };
        const left = { x: cx - hw, y: cy - H };

        if (H > 0) {
            const rightBase = { x: cx + hw, y: cy }, bottomBase = { x: cx, y: cy + hh }, leftBase = { x: cx - hw, y: cy };
            ctx.fillStyle = this._shade(color, -0.35);
            ctx.beginPath();
            ctx.moveTo(left.x, left.y); ctx.lineTo(bottom.x, bottom.y);
            ctx.lineTo(bottomBase.x, bottomBase.y); ctx.lineTo(leftBase.x, leftBase.y);
            ctx.closePath(); ctx.fill();

            ctx.fillStyle = this._shade(color, -0.15);
            ctx.beginPath();
            ctx.moveTo(right.x, right.y); ctx.lineTo(bottom.x, bottom.y);
            ctx.lineTo(bottomBase.x, bottomBase.y); ctx.lineTo(rightBase.x, rightBase.y);
            ctx.closePath(); ctx.fill();
        }

        // Cheap "tilled row" alternation for farmland; flat fill otherwise.
        ctx.fillStyle = biome === 'farmland' && (gx + gy) % 2 === 0 ? this._shade(color, -0.08) : color;
        ctx.beginPath();
        ctx.moveTo(top.x, top.y); ctx.lineTo(right.x, right.y);
        ctx.lineTo(bottom.x, bottom.y); ctx.lineTo(left.x, left.y);
        ctx.closePath(); ctx.fill();

        ctx.strokeStyle = 'rgba(0,0,0,0.12)';
        ctx.lineWidth = 1;
        if (biome === 'vacant') ctx.setLineDash([3, 3]); // a surveyed, undeveloped lot -- never a building
        ctx.stroke();
        if (biome === 'vacant') ctx.setLineDash([]);
    },

    // A handful of drifting glints on the ocean -- pure atmosphere, same
    // drifting-dot technique as _drawAmbient's road particles, just seeded
    // to ocean coordinates instead of roads.
    _spawnOceanGlint() {
        for (let i = 0; i < 40; i++) {
            const gx = Math.round(WORLD_BOUNDS.minX + Math.random() * (WORLD_BOUNDS.maxX - WORLD_BOUNDS.minX));
            const gy = Math.round(WORLD_BOUNDS.minY + Math.random() * (WORLD_BOUNDS.maxY - WORLD_BOUNDS.minY));
            if (biomeAt(gx, gy) === 'ocean') {
                const { x, y } = gridToScreen(gx, gy);
                return { x, y, phase: Math.random() * Math.PI * 2, speed: 0.0006 + Math.random() * 0.0004 };
            }
        }
        return { x: 0, y: (WORLD_BOUNDS.minX + WORLD_BOUNDS.minY) * (TILE_H / 2) + 40, phase: 0, speed: 0.0008 };
    },

    _drawOceanGlints(inst) {
        if (!inst.oceanGlints.length) return;
        const { ctx } = inst;
        const t = performance.now();
        inst.oceanGlints.forEach(g => {
            const alpha = 0.15 + 0.15 * (0.5 + 0.5 * Math.sin(g.phase + t * g.speed));
            ctx.beginPath();
            ctx.arc(g.x, g.y, 2, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(180, 210, 230, ${alpha.toFixed(2)})`;
            ctx.fill();
        });
    },
};

window.CityScape = CityScape;
document.addEventListener('DOMContentLoaded', () => CityScape.init());
