// VAPE City — a live, bird's-eye isometric map of VAPE's own real signals.
// Every building is one real process this repo runs (data/city-state.json,
// written by agents/build_city_state.py from security-dashboard.json,
// attack-feed.json, intel-index.json, opportunities.json, and
// reputation.json); every moving "delivery truck" on the streets is one real
// settled x402 job, polled live from the same worker feed x402feed.js
// already reads. One module, two mount sizes — any element with
// `data-city-stage="compact"` or `data-city-stage="full"` on the current
// page gets its own live instance, so the exact same engine backs the small
// diorama inside #security-dashboard and the huge dedicated docs/city.html
// page with zero page-specific branching.
//
// Everything added on top of the real buildings/roads/vehicles is honest
// atmosphere, never a fabricated data surface:
//   - Road *layout* and the L-shaped street grid are a fixed display
//     choice, same as before, just rendered with a visible asphalt bed
//     instead of a near-invisible hairline.
//   - Camera rotation (4 compass views) is a pure viewing transform — it
//     changes how the same real data is projected, never what it says.
//   - Day/night (sky, sunsets, window lights, street lamps) is driven by
//     the viewer's own real local clock (`Date()`), not a simulated cycle.
//   - "Under construction" pulses only ever fire when a building's real
//     tier (agents/build_city_state.py's relative-percentile tier_for())
//     goes up between two live fetches — never a scripted animation.
//   - Zoning labels (Civic/Commercial/Industrial/Financial) are just a
//     human-readable grouping of each building's already-real `kind`
//     field, not a new data claim.
//   - Terrain + the two coastal piers are pure world scenery, deterministic
//     from a fixed seed, exactly like the ocean/mountain/farmland/vacant
//     tiles already were — never a road, never a data claim.
//
// Scene model vs. renderer are kept deliberately separate (buildings/roads/
// vehicles are plain data with grid positions; only the draw functions know
// about isometric projection, camera rotation, or canvas) so a future
// walkable 3D view can read the same data/city-state.json and swap in a
// different renderer without touching the data shape.

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

// A human-readable zoning grouping of the same real `kind` field above --
// not a new data source, just a SimCity-style label for what each real
// building already is.
const ZONE_FOR_KIND = {
    precinct: 'Civic · Public Safety',
    tower: 'Commercial · Contract Exchange',
    newsroom: 'Commercial · Media',
    watchtower: 'Civic · Infrastructure',
    mint: 'Financial District',
    foundry: 'Industrial · Fabrication',
    vault: 'Financial District',
    checkpoint: 'Infrastructure · Security Lane',
};

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

function buildingHeightPx(b) {
    return BASE_HEIGHT + (b.tier || 1) * TIER_UNIT;
}

// ── Camera: 4-way rotation around downtown ──────────────────────────────
// A pure viewing transform, exactly like SimCity/tycoon-game camera
// rotation -- it changes which corner of the same real grid faces the
// viewer, never the underlying gridX/gridY a building actually has.
// Rotating around the real city's own footprint center (not the world's)
// keeps downtown centered in view at every one of the 4 angles.
const CITY_BBOX = { minX: 0, maxX: 12, minY: 0, maxY: 9 }; // real buildings' footprint-inclusive extent
const CAMERA_PIVOT = { x: (CITY_BBOX.minX + CITY_BBOX.maxX) / 2, y: (CITY_BBOX.minY + CITY_BBOX.maxY) / 2 };

function rotateAroundPivot(gx, gy, rotation) {
    let dx = gx - CAMERA_PIVOT.x, dy = gy - CAMERA_PIVOT.y;
    const steps = ((rotation % 4) + 4) % 4;
    for (let i = 0; i < steps; i++) { const ndx = -dy, ndy = dx; dx = ndx; dy = ndy; }
    return { x: CAMERA_PIVOT.x + dx, y: CAMERA_PIVOT.y + dy };
}
function projectGrid(gx, gy, rotation) {
    const r = rotateAroundPivot(gx, gy, rotation);
    return gridToScreen(r.x, r.y);
}
function buildingAnchorGrid(b) {
    // Center point of a building's real footprint, ground level, BEFORE
    // camera rotation -- the one true position every angle rotates around.
    const [fw, fh] = b.footprint || [1, 1];
    return { x: b.gridX + fw / 2, y: b.gridY + fh / 2 };
}
function buildingAnchorInfo(b, rotation) {
    const g = buildingAnchorGrid(b);
    const r = rotateAroundPivot(g.x, g.y, rotation);
    return { grid: r, screen: gridToScreen(r.x, r.y) };
}

// ── Day/night: driven by the viewer's own real local clock, never a
// simulated or fabricated cycle -- reload at 2pm and it's day; reload at
// 2am and it's night, exactly like the wall clock says.
function dayPhase() {
    const d = new Date();
    return (d.getHours() * 60 + d.getMinutes()) / 1440;
}
function isNight(phase) { return phase < 0.24 || phase > 0.83; }
function _lerpColorHex(a, b, f) {
    const pa = parseInt(a.replace('#', ''), 16), pb = parseInt(b.replace('#', ''), 16);
    const ar = (pa >> 16) & 255, ag = (pa >> 8) & 255, ab = pa & 255;
    const br = (pb >> 16) & 255, bg = (pb >> 8) & 255, bb = pb & 255;
    const r = Math.round(ar + (br - ar) * f), g = Math.round(ag + (bg - ag) * f), bl = Math.round(ab + (bb - ab) * f);
    return `rgb(${r},${g},${bl})`;
}
// phase: 0/1 = midnight, 0.25 = ~6am, 0.5 = noon, 0.75 = ~6pm.
const SKY_STOPS = [
    { t: 0.00, top: '#04040a', bot: '#0b0e1c' },
    { t: 0.20, top: '#04040a', bot: '#0b0e1c' },
    { t: 0.27, top: '#2b3a63', bot: '#e8895f' }, // sunrise
    { t: 0.35, top: '#5f8fd9', bot: '#f3c98a' },
    { t: 0.50, top: '#3f7fd6', bot: '#bcd8f5' }, // noon
    { t: 0.68, top: '#4a72c9', bot: '#e8a35f' },
    { t: 0.76, top: '#3a3466', bot: '#e0673f' }, // sunset
    { t: 0.85, top: '#12142c', bot: '#3a2444' },
    { t: 1.00, top: '#04040a', bot: '#0b0e1c' },
];
function skyGradientStops(phase) {
    for (let i = 0; i < SKY_STOPS.length - 1; i++) {
        const a = SKY_STOPS[i], b = SKY_STOPS[i + 1];
        if (phase >= a.t && phase <= b.t) {
            const f = (phase - a.t) / (b.t - a.t || 1);
            return { top: _lerpColorHex(a.top, b.top, f), bot: _lerpColorHex(a.bot, b.bot, f) };
        }
    }
    return { top: SKY_STOPS[0].top, bot: SKY_STOPS[0].bot };
}

// ── The surrounding world (full mode only) — ocean, mountains, farmland,
// vacant land around the real-data city. Deliberately client-side and NOT
// part of data/city-state.json: unlike every building/road/vehicle above,
// terrain traces to no real signal at all, so it stays out of the
// aggregator's "every number here is real" contract entirely. It's the
// same kind of presentational, non-data choice as the road layout, just
// bigger -- and it's fully deterministic (a fixed seed, not Math.random())
// so the world reads as one stable place across visits, never a randomly
// different backdrop.
const WORLD_BOUNDS = { minX: -40, maxX: 60, minY: -40, maxY: 53 };
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
// Deliberately independent of camera rotation -- a mountain stays a
// mountain no matter which way you're looking at the city from.
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
    // so it's built once per rotation angle and shared rather than
    // per-instance state. Keyed by rotation (0-3) since rotating the camera
    // re-projects every tile onto a different patch of screen space.
    _terrainCache: {},
    _terrainOrigin: {},

    async init() {
        const stages = document.querySelectorAll('[data-city-stage]');
        if (!stages.length) return;
        await this._fetchCityState();
        this._renderUpdated();
        stages.forEach(el => this._mount(el));
        // Real tier/status changes (a lane recovering, a building's relative
        // rank shifting) should surface as a live "under construction"
        // pulse without a page reload -- the URL's own 5-minute timestamp
        // bucket already caps this to a genuinely fresh fetch server-side.
        setInterval(() => this._refreshCityState(), 90000);
    },

    async _fetchCityState() {
        try {
            const res = await fetch(`${CITY_STATE_URL}?t=${Math.floor(Date.now() / 300000)}`);
            if (!res.ok) throw new Error(`city-state ${res.status}`);
            this._cityState = await res.json();
        } catch (e) {
            this._cityState = null;
        }
    },

    async _refreshCityState() {
        await this._fetchCityState();
        this._renderUpdated();
        if (this._cityState) this._instances.forEach(inst => this._loadCity(inst, this._cityState));
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
            rotation: 0,
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
            if (!this._terrainCache[0]) this._buildTerrainCache(0);
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
        // A building's real tier only ever rises when build_city_state.py's
        // relative-percentile tier_for() genuinely ranks it higher this
        // cycle -- that's the one and only trigger for the "upgrading"
        // pulse drawn in _drawBuilding. prevTier is empty on first load, so
        // nothing pulses on initial paint, only on a real change afterward.
        const prevTier = new Map(inst.buildings.map(b => [b.id, b.tier]));
        inst.buildings = (city.buildings || []).map(b => {
            const prev = prevTier.get(b.id);
            const upgraded = prev != null && (b.tier || 1) > prev;
            return { ...b, _upgradeUntil: upgraded ? performance.now() + 6000 : 0 };
        });
        inst.roads = (city.roads || []).map(([fromId, toId]) => {
            const from = inst.buildings.find(b => b.id === fromId);
            const to = inst.buildings.find(b => b.id === toId);
            return from && to ? { from, to } : null;
        }).filter(Boolean);
        inst.ambient = inst.roads.length ? Array.from({ length: 10 }, (_, i) => ({
            road: inst.roads[i % inst.roads.length],
            t: Math.random(),
            speed: 0.00012 + Math.random() * 0.00008,
            dir: Math.random() < 0.5 ? 1 : -1,
            kind: Math.random() < 0.7 ? 'car' : 'pedestrian',
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

    // ── Interaction: pointer-based drag/pinch/zoom/rotate + click-to-inspect
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
        const rotateBtn = inst.el.querySelector('[data-city-rotate]');
        if (zoomIn) zoomIn.addEventListener('click', () => { inst.scale = clampScale(inst.scale * 1.25); });
        if (zoomOut) zoomOut.addEventListener('click', () => { inst.scale = clampScale(inst.scale * 0.8); });
        // A one-tap way back to downtown after zooming/panning/rotating out
        // to see the wider world -- only meaningful in 'full' mode.
        if (zoomReset) zoomReset.addEventListener('click', () => { inst.scale = 1; inst.offsetX = 0; inst.offsetY = 0; inst.rotation = 0; });
        // Rotates the camera 90° at a time around downtown, SimCity-style --
        // a pure viewing transform, never a change to any building's real
        // gridX/gridY.
        if (rotateBtn) rotateBtn.addEventListener('click', () => { inst.rotation = (inst.rotation + 1) % 4; });
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
        const zone = ZONE_FOR_KIND[b.kind];
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
            ${zone ? `<div class="city-detail-zone">${escapeHtml(zone)}</div>` : ''}
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

        const phase = dayPhase();
        // Sky is drawn in plain screen space (before translate/scale) so it
        // always fills the viewport regardless of pan/zoom/rotation --
        // compact mode keeps its existing static CSS backdrop instead.
        if (inst.mode === 'full') {
            const sky = skyGradientStops(phase);
            const grad = ctx.createLinearGradient(0, 0, 0, h);
            grad.addColorStop(0, sky.top);
            grad.addColorStop(1, sky.bot);
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, w, h);
        }

        ctx.save();
        ctx.translate(w / 2 + inst.offsetX, h * 0.32 + inst.offsetY);
        ctx.scale(inst.scale, inst.scale);

        // Terrain is cached per rotation angle (built lazily the first time
        // that angle is viewed) -- gated on this instance's own mode so a
        // compact instance never inherits the full-world backdrop.
        if (inst.mode === 'full') {
            if (!this._terrainCache[inst.rotation]) this._buildTerrainCache(inst.rotation);
            const tc = this._terrainCache[inst.rotation], origin = this._terrainOrigin[inst.rotation];
            if (tc && origin) ctx.drawImage(tc, origin.x, origin.y);
            this._drawOceanGlints(inst);
        }
        this._drawRoads(inst, phase);
        this._drawAmbient(inst, phase);
        inst.hitboxes = [];
        // Painter's algorithm: back-to-front by the *rotated* grid depth, so
        // nearer buildings correctly occlude farther ones at every camera
        // angle, not just the default one.
        const ordered = [...inst.buildings].sort((a, b) => {
            const ga = buildingAnchorInfo(a, inst.rotation).grid, gb = buildingAnchorInfo(b, inst.rotation).grid;
            return (ga.x + ga.y) - (gb.x + gb.y);
        });
        ordered.forEach(b => this._drawBuilding(inst, b, phase));
        this._drawVehicles(inst);

        ctx.restore();
    },

    // The two-segment L-shaped grid path (screen space) a road actually
    // takes between two real buildings -- a fixed display choice, never a
    // data claim, but a genuine street grid instead of an as-the-crow-flies
    // line, and correctly re-projected at whichever camera angle is active.
    _roadPathGrid(r) {
        const fromG = buildingAnchorGrid(r.from), toG = buildingAnchorGrid(r.to);
        const elbowG = { x: toG.x, y: fromG.y };
        return [fromG, elbowG, toG];
    },
    _roadPathScreen(r, rotation) {
        return this._roadPathGrid(r).map(g => projectGrid(g.x, g.y, rotation));
    },
    // A point t (0-1) of the way along that same L-shaped path, for traffic/
    // pedestrians/real x402 vehicles to walk without cutting corners off-road.
    _pointAlongRoadPath(road, t, rotation) {
        const [fromG, elbowG, toG] = this._roadPathGrid(road);
        const len1 = Math.abs(elbowG.x - fromG.x), len2 = Math.abs(toG.y - elbowG.y);
        const total = len1 + len2;
        let gx, gy;
        if (total === 0) { gx = fromG.x; gy = fromG.y; }
        else {
            const d = Math.max(0, Math.min(1, t)) * total;
            if (d <= len1) {
                const f = len1 ? d / len1 : 0;
                gx = fromG.x + (elbowG.x - fromG.x) * f; gy = fromG.y;
            } else {
                const f = len2 ? (d - len1) / len2 : 0;
                gx = elbowG.x; gy = elbowG.y + (toG.y - elbowG.y) * f;
            }
        }
        return projectGrid(gx, gy, rotation);
    },

    _drawRoads(inst, phase) {
        const { ctx } = inst;
        const lit = inst.mode === 'full' && isNight(phase);
        const strokePath = (pts, width, style) => {
            ctx.strokeStyle = style;
            ctx.lineWidth = width;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.beginPath();
            pts.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
            ctx.stroke();
        };
        inst.roads.forEach(r => {
            const pts = this._roadPathScreen(r, inst.rotation);
            strokePath(pts, 13, 'rgba(255,255,255,0.10)'); // curb / edge glow
            strokePath(pts, 10.5, '#20202a'); // asphalt bed -- this is the fix for "can't see the roads"
            ctx.setLineDash([4, 6]);
            strokePath(pts, 1.2, lit ? 'rgba(255,224,150,0.55)' : 'rgba(255,255,255,0.32)'); // centerline
            ctx.setLineDash([]);
        });
    },

    _lerp(a, b, t) { return a + (b - a) * t; },

    // Ambient traffic + pedestrians -- pure atmosphere (same non-data
    // category this module has always used for its drifting road
    // particles), now rendered as small cars/pedestrians walking the real
    // street grid instead of bare dots, and warmed under streetlight at
    // night.
    _drawAmbient(inst, phase) {
        const { ctx } = inst;
        const lit = inst.mode === 'full' && isNight(phase);
        inst.ambient.forEach(a => {
            const p = this._pointAlongRoadPath(a.road, a.t, inst.rotation);
            if (a.kind === 'pedestrian') {
                ctx.beginPath();
                ctx.arc(p.x, p.y - 2, 1.6, 0, Math.PI * 2);
                ctx.fillStyle = lit ? 'rgba(255,224,170,0.75)' : 'rgba(228,228,231,0.6)';
                ctx.fill();
            } else {
                ctx.save();
                ctx.translate(p.x, p.y - 4);
                ctx.fillStyle = lit ? '#3a3a44' : '#4b4b58';
                ctx.beginPath();
                if (ctx.roundRect) ctx.roundRect(-4, -2.5, 8, 5, 1.5); else ctx.rect(-4, -2.5, 8, 5);
                ctx.fill();
                if (lit) {
                    ctx.fillStyle = 'rgba(255,235,180,0.9)';
                    ctx.beginPath(); ctx.arc(3.3, 0, 1, 0, Math.PI * 2); ctx.fill();
                }
                ctx.restore();
            }
        });
    },

    // Real settled x402 jobs -- bigger, glowing, mint-green, and visually
    // distinct from the ambient gray traffic above.
    _drawVehicles(inst) {
        const { ctx } = inst;
        inst.vehicles.forEach(v => {
            const p = this._pointAlongRoadPath({ from: v.from, to: v.to }, v.t, inst.rotation);
            ctx.save();
            ctx.translate(p.x, p.y - 5);
            ctx.fillStyle = cssVar('--city-mint') || '#008300';
            ctx.shadowColor = ctx.fillStyle;
            ctx.shadowBlur = 10;
            ctx.beginPath();
            if (ctx.roundRect) ctx.roundRect(-5, -3, 10, 6, 2); else ctx.rect(-5, -3, 10, 6);
            ctx.fill();
            ctx.restore();
        });
    },

    _drawBuilding(inst, b, phase) {
        const { ctx } = inst;
        let [fw, fh] = b.footprint || [1, 1];
        // A rotated camera swaps which grid axis reads as "wide" on screen,
        // so a building's own footprint has to swap with it to keep its
        // real width/depth ratio intact from every angle.
        if (inst.rotation % 2 === 1) { [fw, fh] = [fh, fw]; }
        const hw = (fw * TILE_W) / 2, hh = (fh * TILE_H) / 2;
        const H = buildingHeightPx(b);
        const { x: cx, y: cy } = buildingAnchorInfo(b, inst.rotation).screen;
        const isCheckpoint = b.kind === 'checkpoint';
        const base = isCheckpoint || inst.layer === 'health' ? statusColor(b.status) : kindColor(b.kind);
        const alert = b.status === 'alert';
        const night = inst.mode === 'full' && isNight(phase);

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

        // Lit windows at real local night-time -- deterministic pattern (no
        // Math.random() in the render loop, which would flicker every
        // frame), gated to landmarks so 10 tiny identical checkpoint marks
        // don't turn into 10 tiny identical light grids at this scale.
        if (night && !isCheckpoint) this._drawBuildingWindows(ctx, cx, cy, hw, H);
        // Checkpoints (the 10 automated-lane markers) get a streetlamp glow
        // instead -- they're spread through downtown like real intersections.
        if (night && isCheckpoint) {
            ctx.beginPath();
            ctx.arc(cx, cy - H - 5, 2.6, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,230,150,0.9)';
            ctx.shadowColor = 'rgba(255,220,140,0.85)';
            ctx.shadowBlur = 10;
            ctx.fill();
            ctx.shadowBlur = 0;
        }

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

        // "Under construction" pulse -- fires only when _loadCity just saw
        // this building's real tier rise between two live fetches.
        if (b._upgradeUntil && performance.now() < b._upgradeUntil) {
            const pulse = 0.4 + 0.4 * Math.sin(performance.now() / 180);
            ctx.save();
            ctx.strokeStyle = `rgba(255,255,255,${pulse.toFixed(2)})`;
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 3]);
            ctx.beginPath();
            ctx.moveTo(top.x, top.y); ctx.lineTo(right.x, right.y);
            ctx.lineTo(bottom.x, bottom.y); ctx.lineTo(left.x, left.y);
            ctx.closePath(); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = `rgba(255,255,255,${pulse.toFixed(2)})`;
            ctx.font = `600 9px ${canvasFontFamily()}, sans-serif`;
            ctx.textAlign = 'center';
            ctx.fillText('▲ upgrading', top.x, top.y - 8);
            ctx.restore();
        }

        inst.hitboxes.push({ building: b, x: cx, y: cy - H / 2, hw: hw + 6, hh: hh + H / 2 + 6 });
    },

    _drawBuildingWindows(ctx, cx, cy, hw, H) {
        const rows = Math.max(2, Math.round(H / 14));
        ctx.fillStyle = 'rgba(255, 214, 120, 0.85)';
        ctx.shadowColor = 'rgba(255,200,120,0.6)';
        ctx.shadowBlur = 3;
        for (let r = 0; r < rows; r++) {
            const fy = cy - H + 8 + r * ((H - 14) / Math.max(1, rows - 1));
            if (r % 2 === 0) ctx.fillRect(cx - hw * 0.55 - 1, fy - 1, 2, 2);
            if ((r + 1) % 2 === 0) ctx.fillRect(cx + hw * 0.5 - 1, fy - 1, 2, 2);
        }
        ctx.shadowBlur = 0;
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

    // ── The surrounding world (built once per camera angle, shared by every
    // 'full' instance) ───────────────────────────────────────────────────────
    _buildTerrainCache(rotation) {
        const { minX, maxX, minY, maxY } = WORLD_BOUNDS;
        const tiles = [];
        for (let gx = minX; gx <= maxX; gx++) {
            for (let gy = minY; gy <= maxY; gy++) {
                const biome = biomeAt(gx, gy);
                if (!biome) continue;
                const rp = rotateAroundPivot(gx, gy, rotation);
                tiles.push({ gx, gy, biome, rx: rp.x, ry: rp.y, depth: rp.x + rp.y });
            }
        }
        // Back-to-front by the *rotated* diagonal so mountain-peak
        // extrusions occlude correctly at every camera angle.
        tiles.sort((a, b) => a.depth - b.depth);

        let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
        tiles.forEach(t => {
            const { x, y } = gridToScreen(t.rx, t.ry);
            if (x < xMin) xMin = x; if (x > xMax) xMax = x;
            if (y < yMin) yMin = y; if (y > yMax) yMax = y;
        });
        xMin -= 40; xMax += 40; yMin -= 40; yMax += 60; // slack for mountain extrusion + pier decks
        const w = Math.max(1, Math.ceil(xMax - xMin)), h = Math.max(1, Math.ceil(yMax - yMin));

        const cvs = typeof OffscreenCanvas !== 'undefined'
            ? new OffscreenCanvas(w, h)
            : Object.assign(document.createElement('canvas'), { width: w, height: h });
        const ctx = cvs.getContext('2d');

        tiles.forEach(t => this._drawTerrainTile(ctx, t.biome, t.rx, t.ry, -xMin, -yMin, t.gx, t.gy));
        this._findBridgeSpots(tiles).forEach(spot => this._drawBridge(ctx, spot, rotation, -xMin, -yMin));

        this._terrainCache[rotation] = cvs;
        this._terrainOrigin[rotation] = { x: xMin, y: yMin };
    },

    _drawTerrainTile(ctx, biome, rx, ry, dx, dy, ogx, ogy) {
        const g = gridToScreen(rx + 0.5, ry + 0.5);
        const cx = g.x + dx, cy = g.y + dy;
        const hw = TILE_W / 2, hh = TILE_H / 2;
        const color = terrainColor(biome);
        // Mountains are the one terrain type with height -- kept short
        // (8-24px, vs. buildings' 33-78px) so they read as backdrop, never
        // competing with a real tier-4 landmark. Height/pattern noise keys
        // off the tile's true (unrotated) grid position so a given mountain
        // looks the same physical shape from every camera angle.
        const H = biome === 'mountain' ? 8 + Math.round(_valueNoise1D(ogx * 7 + ogy * 3, TERRAIN_SEED + 99) * 16) : 0;

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
        ctx.fillStyle = biome === 'farmland' && (ogx + ogy) % 2 === 0 ? this._shade(color, -0.08) : color;
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

    // Two short, fixed, deterministic piers wherever the seeded coastline
    // happens to form a narrow ocean strait -- pure world scenery, same
    // non-data category as the terrain it sits on, never a road.
    _findBridgeSpots(tiles) {
        const key = (x, y) => `${x},${y}`;
        const byKey = new Map(tiles.map(t => [key(t.gx, t.gy), t.biome]));
        const spots = [];
        const claimed = new Set();
        for (const t of tiles) {
            if (t.biome !== 'ocean' || claimed.has(key(t.gx, t.gy))) continue;
            const north = byKey.get(key(t.gx, t.gy - 1));
            const mid1 = byKey.get(key(t.gx, t.gy + 1));
            const mid2 = byKey.get(key(t.gx, t.gy + 2));
            const south = byKey.get(key(t.gx, t.gy + 3));
            if (north && north !== 'ocean' && mid1 === 'ocean' && mid2 === 'ocean' && south && south !== 'ocean') {
                spots.push({ gx: t.gx, gyStart: t.gy - 1, gyEnd: t.gy + 3 });
                for (let k = -1; k <= 3; k++) claimed.add(key(t.gx, t.gy + k));
                if (spots.length >= 2) break;
            }
        }
        return spots;
    },

    _drawBridge(ctx, spot, rotation, dx, dy) {
        const a = rotateAroundPivot(spot.gx + 0.5, spot.gyStart, rotation);
        const b = rotateAroundPivot(spot.gx + 0.5, spot.gyEnd, rotation);
        const pa = gridToScreen(a.x, a.y), pb = gridToScreen(b.x, b.y);
        ctx.save();
        ctx.translate(dx, dy);
        ctx.strokeStyle = '#8a8a94';
        ctx.lineWidth = 7;
        ctx.lineCap = 'butt';
        ctx.beginPath(); ctx.moveTo(pa.x, pa.y - 6); ctx.lineTo(pb.x, pb.y - 6); ctx.stroke();
        ctx.strokeStyle = '#5f5f68';
        ctx.lineWidth = 2;
        ctx.setLineDash([2, 3]);
        ctx.beginPath(); ctx.moveTo(pa.x, pa.y - 6); ctx.lineTo(pb.x, pb.y - 6); ctx.stroke();
        ctx.setLineDash([]);
        [0.2, 0.5, 0.8].forEach(f => {
            const px = pa.x + (pb.x - pa.x) * f, py = pa.y + (pb.y - pa.y) * f;
            ctx.strokeStyle = '#4a4a52';
            ctx.lineWidth = 2.5;
            ctx.beginPath(); ctx.moveTo(px, py - 6); ctx.lineTo(px, py + 3); ctx.stroke();
        });
        ctx.restore();
    },

    // A handful of drifting glints on the ocean -- pure atmosphere, same
    // drifting-dot technique as _drawAmbient's road particles, just seeded
    // to ocean coordinates instead of roads. Stored as grid coordinates (not
    // pre-projected screen points) so they re-project correctly at whichever
    // camera angle is active.
    _spawnOceanGlint() {
        for (let i = 0; i < 40; i++) {
            const gx = Math.round(WORLD_BOUNDS.minX + Math.random() * (WORLD_BOUNDS.maxX - WORLD_BOUNDS.minX));
            const gy = Math.round(WORLD_BOUNDS.minY + Math.random() * (WORLD_BOUNDS.maxY - WORLD_BOUNDS.minY));
            if (biomeAt(gx, gy) === 'ocean') {
                return { gx, gy, phase: Math.random() * Math.PI * 2, speed: 0.0006 + Math.random() * 0.0004 };
            }
        }
        return { gx: WORLD_BOUNDS.minX, gy: WORLD_BOUNDS.minY, phase: 0, speed: 0.0008 };
    },

    _drawOceanGlints(inst) {
        if (!inst.oceanGlints.length) return;
        const { ctx } = inst;
        const t = performance.now();
        inst.oceanGlints.forEach(g => {
            const alpha = 0.15 + 0.15 * (0.5 + 0.5 * Math.sin(g.phase + t * g.speed));
            const { x, y } = projectGrid(g.gx, g.gy, inst.rotation);
            ctx.beginPath();
            ctx.arc(x, y, 2, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(180, 210, 230, ${alpha.toFixed(2)})`;
            ctx.fill();
        });
    },
};

window.CityScape = CityScape;
document.addEventListener('DOMContentLoaded', () => CityScape.init());
