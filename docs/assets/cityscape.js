// VAPE Ave — a live, bird's-eye isometric map of VAPE's own real signals.
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
//   - Camera rotation (8 compass views, 45° apart) is a pure viewing
//     transform — it changes how the same real data is projected, never
//     what it says.
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

// ── Camera: 8-way rotation around downtown ──────────────────────────────
// A pure viewing transform, exactly like SimCity/tycoon-game camera
// rotation -- it changes which corner of the same real grid faces the
// viewer, never the underlying gridX/gridY a building actually has.
// Rotating around the real city's own footprint center (not the world's)
// keeps downtown centered in view at every angle. `rotation` is a
// continuous degree value (0-360, wrapping) so a compass drag/touch feels
// fluid; only the 8 multiples of 45 are ever treated as "rest" positions
// (footprint orientation and the terrain cache both snap to the nearest
// one), but the underlying rotation math is real trigonometry, not a
// 90°-only shortcut, so nothing looks discontinuous while dragging.
const CITY_BBOX = { minX: 0, maxX: 22, minY: 0, maxY: 18 }; // real buildings' footprint-inclusive extent
const CAMERA_PIVOT = { x: 11.5, y: 8.5 }; // The Foundry's own real footprint center -- the hub every road radiates from
const ROTATION_STOPS = [0, 45, 90, 135, 180, 225, 270, 315];
function nearestRotationStop(deg) {
    const n = ((deg % 360) + 360) % 360;
    return Math.round(n / 45) % 8 * 45;
}

function rotateAroundPivot(gx, gy, rotationDeg) {
    const rad = (rotationDeg * Math.PI) / 180;
    const cos = Math.cos(rad), sin = Math.sin(rad);
    const dx = gx - CAMERA_PIVOT.x, dy = gy - CAMERA_PIVOT.y;
    return { x: CAMERA_PIVOT.x + dx * cos - dy * sin, y: CAMERA_PIVOT.y + dx * sin + dy * cos };
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
const WORLD_BOUNDS = { minX: -75, maxX: 115, minY: -75, maxY: 100 };
// Bounds on the per-rotation terrain cache: a hard pixel cap per canvas
// (downscaled physically, stretched back to logical size on composite) and
// an LRU cap on how many rotation stops stay resident at once. Both exist
// purely to keep canvas memory bounded on mobile -- neither changes what
// the terrain looks like at rest, only how much of it stays cached.
const TERRAIN_CACHE_MAX_PIXELS = 6_000_000;
const TERRAIN_CACHE_MAX_STOPS = 2;
const VACANT_MARGIN = 5; // tiles of guaranteed "room to grow" ring around downtown
const TERRAIN_SEED = 402019;
// A handful of fixed "park" tiles just outside downtown, in the vacant
// margin ring -- pure world scenery (same non-data category as everything
// else in this terrain layer), not derived from any real signal.
const PARK_TILES = new Set([
    '-3,3', '-2,3', '-3,4', '-2,4',
    '24,3', '25,3', '24,4', '25,4',
    '11,21', '12,21', '11,22', '12,22',
]);

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
// organically instead of reading as a ruler-straight boundary. Scaled up
// alongside the wider city/world so the coastline's waviness stays
// proportional instead of looking finicky against the bigger map.
function _wobble(x, seedOffset) {
    return (_valueNoise1D(x / 11, TERRAIN_SEED + seedOffset) - 0.5) * 10
        + (_valueNoise1D(x / 4.5, TERRAIN_SEED + seedOffset + 1) - 0.5) * 3.5;
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
    if (v < -55 + _wobble(u, 10)) return 'ocean';
    if (v > 145 + _wobble(u, 20)) return 'mountain';
    if (u < -90 + _wobble(v, 30)) return 'farmland';
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

// Real event-driven "service vehicles" — agents/build_city_state.py's
// recent_events (one real timestamped entry per investigation/article/
// bounty-lead/incident, straight from the same 4 files every landmark
// building already reads). Each type dispatches from the Foundry hub to
// its own real building, and borrows that building's own already-validated
// identity hue -- no new colors, no new data claim.
const EVENT_TARGET = {
    investigation: 'precinct-investigations',
    news: 'newsroom',
    bounty: 'tower-bounty',
    threat: 'watchtower-threat',
};
const EVENT_COLOR_VAR = {
    investigation: '--city-precinct',
    news: '--city-newsroom',
    bounty: '--city-tower',
    threat: '--city-watchtower',
};

const CityScape = {
    _cityState: null,
    _instances: [],
    // The world is identical (same fixed seed) for every 'full' instance,
    // so it's built once per rotation stop and shared rather than
    // per-instance state. Keyed by one of the 8 ROTATION_STOPS degree
    // values (not the continuously-dragged inst.rotation) since rebuilding
    // ~30k terrain tiles every animation frame mid-drag would be far too
    // expensive -- the terrain only re-renders once a drag/arrow settles.
    _terrainCache: {},
    _terrainOrigin: {},
    _terrainCacheOrder: [], // LRU order, oldest first -- see TERRAIN_CACHE_MAX_STOPS

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
            rotation: 0, terrainRotation: 0,
            layer: 'overview',
            selected: null,
            vehicles: [], ambient: [], oceanGlints: [],
            lastX402: new Set(),
            lastEvents: new Set(), eventsSeeded: false,
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
        // _loadCity replaces every building object wholesale on each 90s
        // refresh -- the real-event light-balls a building has already
        // absorbed this session (see _advance's vehicle-arrival handling)
        // have to be carried forward by id, or they'd vanish every reload.
        const prevContained = new Map(inst.buildings.map(b => [b.id, b.contained]));
        inst.buildings = (city.buildings || []).map(b => {
            const prev = prevTier.get(b.id);
            const upgraded = prev != null && (b.tier || 1) > prev;
            return { ...b, _upgradeUntil: upgraded ? performance.now() + 6000 : 0, contained: prevContained.get(b.id) || [] };
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

        // Real event-driven dispatch vehicles -- seeded silently on this
        // instance's first load (never replays the aggregator's whole
        // recent-events history the moment the page opens); only a
        // genuinely new event id after that spawns a vehicle, same
        // discipline as _pollX402's lastX402 dedup above.
        const events = city.recent_events || [];
        if (!inst.eventsSeeded) {
            events.forEach(e => inst.lastEvents.add(e.id));
            inst.eventsSeeded = true;
        } else {
            events.forEach(e => {
                if (!e.id || inst.lastEvents.has(e.id)) return;
                inst.lastEvents.add(e.id);
                const target = EVENT_TARGET[e.type];
                if (target) this._spawnVehicle(inst, 'foundry', target, { kind: e.type, label: e.label, verdict: e.verdict, amount_usd_m: e.amount_usd_m });
            });
        }
        if (inst.lastEvents.size > 300) inst.lastEvents = new Set([...inst.lastEvents].slice(-150));

        this._computeGroundCells(inst);
        this._renderStatStrip(inst, city);
        this._renderA11yList(inst);
    },

    // Every downtown grid cell not already a real building's footprint or
    // a real road's own corridor -- computed fresh from this instance's
    // actual buildings/roads (not hardcoded), so it stays correct if the
    // real layout ever changes. Cached on the instance and only recomputed
    // when _loadCity reloads, since _drawDowntownGround below redraws these
    // every frame (downtown is ~400 cells at most -- cheap either way, but
    // no reason to recompute occupancy 30 times a second).
    _computeGroundCells(inst) {
        const key = (x, y) => `${x},${y}`;
        const occupied = new Set();
        inst.buildings.forEach(b => {
            const [fw, fh] = b.footprint || [1, 1];
            for (let dx = 0; dx < fw; dx++) for (let dy = 0; dy < fh; dy++) occupied.add(key(b.gridX + dx, b.gridY + dy));
        });
        inst.roads.forEach(r => {
            const [fromG, elbowG, toG] = this._roadPathGrid(r);
            const xLo = Math.floor(Math.min(fromG.x, elbowG.x)), xHi = Math.ceil(Math.max(fromG.x, elbowG.x));
            for (let x = xLo; x <= xHi; x++) occupied.add(key(x, Math.round(fromG.y)));
            const yLo = Math.floor(Math.min(elbowG.y, toG.y)), yHi = Math.ceil(Math.max(elbowG.y, toG.y));
            for (let y = yLo; y <= yHi; y++) occupied.add(key(Math.round(elbowG.x), y));
        });
        const cells = [];
        for (let gx = CITY_BBOX.minX; gx <= CITY_BBOX.maxX; gx++) {
            for (let gy = CITY_BBOX.minY; gy <= CITY_BBOX.maxY; gy++) {
                if (occupied.has(key(gx, gy))) continue;
                const h = _hash(gx * 13.7 + gy * 5.3, TERRAIN_SEED + 201);
                const feature = h < 0.02 ? 'fountain' : h < 0.09 ? 'park' : h < 0.13 ? 'diner' : h < 0.22 ? 'bench' : null;
                cells.push({ gx, gy, feature });
            }
        }
        inst.groundCells = cells;
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
        let pinchStartAngle = 0, pinchStartRotation = 0;
        let dragStart = null;
        let moved = false;

        // Full mode's floor is low enough that zooming all the way out
        // reveals the entire ~100x93-tile world, not just downtown; compact
        // never shows the world at all, so its floor is unchanged.
        const clampScale = s => Math.max(inst.mode === 'full' ? 0.07 : 0.5, Math.min(2.6, s));
        const pointerAngleDeg = (a, b) => Math.atan2(b.y - a.y, b.x - a.x) * (180 / Math.PI);

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
                pinchStartAngle = pointerAngleDeg(a, b);
                pinchStartRotation = inst.rotation;
            }
        });
        canvas.addEventListener('pointermove', (e) => {
            if (!pointers.has(e.pointerId)) return;
            pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
            if (pointers.size === 2) {
                const [a, b] = [...pointers.values()];
                const dist = Math.hypot(a.x - b.x, a.y - b.y) || 1;
                inst.scale = clampScale(pinchStartScale * (dist / pinchStartDist));
                // Two-finger twist (the mobile analog of the desktop compass
                // drag below) -- the same real-time pointer-angle delta a
                // map app's rotate gesture uses, only meaningful in 'full'
                // mode since compact has no rotation controls at all.
                if (inst.mode === 'full') {
                    const angleDelta = pointerAngleDeg(a, b) - pinchStartAngle;
                    inst.rotation = ((pinchStartRotation + angleDelta) % 360 + 360) % 360;
                    this._syncCompassDial(inst);
                }
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
            const wasTwoFinger = pointers.size === 2;
            pointers.delete(e.pointerId);
            if (pointers.size === 0) {
                dragStart = null;
            } else if (pointers.size === 1) {
                // A finger lifted mid-gesture (e.g. out of a pinch/twist) --
                // re-seed from where the remaining pointer actually is, so
                // the next pointermove measures a delta from now instead of
                // jumping by the full distance travelled during the gesture.
                const [p] = [...pointers.values()];
                dragStart = { x: p.x, y: p.y, offX: inst.offsetX, offY: inst.offsetY };
            } else if (pointers.size === 2) {
                // Dropped from 3 fingers back to 2 -- re-seed the pinch/twist
                // baselines the same way pointerdown does, so scale and
                // rotation don't jump from now-stale values.
                const [a, b] = [...pointers.values()];
                pinchStartDist = Math.hypot(a.x - b.x, a.y - b.y) || 1;
                pinchStartScale = inst.scale;
                pinchStartAngle = pointerAngleDeg(a, b);
                pinchStartRotation = inst.rotation;
            }
            // The twist gesture just ended -- settle on the nearest of the
            // 8 rotation stops, same as releasing the desktop compass dial.
            if (wasTwoFinger && pointers.size < 2 && inst.mode === 'full') {
                inst.rotation = nearestRotationStop(inst.rotation);
                inst.terrainRotation = inst.rotation;
                this._syncCompassDial(inst);
            }
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
        // A one-tap way back to downtown after zooming/panning/rotating out
        // to see the wider world -- only meaningful in 'full' mode.
        if (zoomReset) zoomReset.addEventListener('click', () => {
            inst.scale = 1; inst.offsetX = 0; inst.offsetY = 0;
            inst.rotation = 0; inst.terrainRotation = 0;
            this._syncCompassDial(inst);
        });

        // ── Camera rotation: a compass dial you drag/touch (mouse on
        // desktop, a finger on mobile -- Pointer Events unify both with one
        // code path) plus two step arrows, 8 stops (45°) around downtown.
        // A pure viewing transform, never a change to any building's real
        // gridX/gridY. Lives on its own small dial element rather than the
        // main canvas so it never fights with canvas drag-to-pan.
        const dial = inst.el.querySelector('[data-city-rotate-dial]');
        const rotateCCW = inst.el.querySelector('[data-city-rotate="ccw"]');
        const rotateCW = inst.el.querySelector('[data-city-rotate="cw"]');
        const stepRotate = dir => {
            const next = nearestRotationStop(inst.rotation) + dir * 45;
            inst.rotation = ((next % 360) + 360) % 360;
            inst.terrainRotation = inst.rotation;
            this._syncCompassDial(inst);
        };
        if (rotateCCW) rotateCCW.addEventListener('click', () => stepRotate(-1));
        if (rotateCW) rotateCW.addEventListener('click', () => stepRotate(1));
        if (dial) {
            let dragging = false, startX = 0, startRotation = 0;
            const ROTATE_SENSITIVITY = 0.7; // degrees per pixel of horizontal drag
            dial.addEventListener('pointerdown', (e) => {
                dial.setPointerCapture(e.pointerId);
                dragging = true;
                startX = e.clientX;
                startRotation = inst.rotation;
                dial.classList.add('is-dragging');
            });
            dial.addEventListener('pointermove', (e) => {
                if (!dragging) return;
                const deg = startRotation + (e.clientX - startX) * ROTATE_SENSITIVITY;
                inst.rotation = ((deg % 360) + 360) % 360;
                this._syncCompassDial(inst);
            });
            const endDrag = () => {
                if (!dragging) return;
                dragging = false;
                dial.classList.remove('is-dragging');
                inst.rotation = nearestRotationStop(inst.rotation);
                inst.terrainRotation = inst.rotation;
                this._syncCompassDial(inst);
            };
            dial.addEventListener('pointerup', endDrag);
            dial.addEventListener('pointercancel', endDrag);
        }
        this._syncCompassDial(inst);
    },

    // Rotates the compass dial's own needle to match inst.rotation -- a
    // cheap DOM style update, not part of the canvas render loop.
    _syncCompassDial(inst) {
        const needle = inst.el.querySelector('[data-city-rotate-dial] .city-compass-needle');
        if (needle) needle.style.transform = `translate(-50%, -100%) rotate(${inst.rotation}deg)`;
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
                    kind: 'x402', offering: job.offering, amount_usd: job.amount_usd, tx_hash: job.tx_hash,
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
        // A vehicle that reaches its real destination doesn't just vanish --
        // it's absorbed as one colored light-ball contained inside that
        // building (see _drawBuilding's translucent fill), the same real
        // job/report the vehicle always represented, now piled up on
        // arrival instead of disappearing.
        inst.vehicles.forEach(v => {
            if (v.t < 1) return;
            const b = inst.buildings.find(x => x.id === v.to.id);
            if (!b) return;
            if (!b.contained) b.contained = [];
            b.contained.push({ color: this._ballColorForVehicle(v), enteredAt: performance.now() });
            if (b.contained.length > 60) b.contained.shift();
        });
        inst.vehicles = inst.vehicles.filter(v => v.t < 1);
    },

    // A real-event vehicle's color once it's absorbed into its destination
    // building -- reuses whatever real severity signal that event type
    // actually carries (an investigation's real verdict, an incident's real
    // dollar loss), falling back to the destination's own identity hue
    // where no honest severity concept exists (news, bounty leads, x402
    // settlements are just "delivered," not pass/fail).
    _ballColorForVehicle(v) {
        const meta = v.meta || {};
        if (meta.kind === 'investigation') {
            const verdict = String(meta.verdict || '').toUpperCase();
            if (verdict === 'REJECT') return cssVar('--sev-critical');
            if (verdict === 'CAUTION') return cssVar('--sev-medium');
            if (verdict === 'PROCEED') return cssVar('--sev-low');
            return cssVar('--sev-info');
        }
        if (meta.kind === 'threat') {
            const amt = typeof meta.amount_usd_m === 'number' ? meta.amount_usd_m : 0;
            return amt >= 5 ? cssVar('--sev-critical') : cssVar('--sev-medium');
        }
        if (meta.kind === 'x402') return cssVar('--city-mint') || '#008300';
        const colorVar = EVENT_COLOR_VAR[meta.kind];
        return colorVar ? cssVar(colorVar) : cssVar('--sev-info');
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

        // Terrain is cached per rotation *stop* (built lazily the first
        // time that stop is viewed) -- gated on this instance's own mode so
        // a compact instance never inherits the full-world backdrop. Keyed
        // by inst.terrainRotation (snapped), not the continuously-dragged
        // inst.rotation, so a mid-drag frame reuses the last-settled
        // terrain image instead of rebuilding ~30k tiles every frame.
        //
        // The whole scene has to read as one rigid world turning together,
        // not a city spinning in place over a static backdrop -- so while
        // a drag/twist is live (inst.rotation !== inst.terrainRotation),
        // the cached image is spun by the outstanding angle around
        // CAMERA_PIVOT's own screen point (which this projection always
        // maps to the same pixel regardless of rotation, so it's the
        // correct pivot). A plain screen rotation isn't pixel-identical to
        // this isometric projection's real grid-then-project math (the 2:1
        // tile aspect makes that a shear, not a similarity transform), but
        // it's a fine live approximation for the terrain's own backdrop;
        // the instant the gesture ends, terrainRotation snaps to match and
        // the true re-projected cache takes over, pixel-correct again.
        if (inst.mode === 'full') {
            if (!this._terrainCache[inst.terrainRotation]) this._buildTerrainCache(inst.terrainRotation);
            else this._touchTerrainCache(inst.terrainRotation);
            const tc = this._terrainCache[inst.terrainRotation], origin = this._terrainOrigin[inst.terrainRotation];
            if (tc && origin) {
                const liveDelta = inst.rotation - inst.terrainRotation;
                if (Math.abs(liveDelta) > 0.05) {
                    // Rotating a rectangular cached image around the pivot
                    // sweeps its corners away from where they used to cover
                    // the viewport, so a wedge outside the swept rectangle
                    // can peek through during the live drag. A flat vacant-
                    // toned fallback fill first means that wedge reads as
                    // more backdrop, never a hard black gap, at any hour.
                    ctx.fillStyle = terrainColor('vacant');
                    ctx.fillRect(-8000, -8000, 16000, 16000);
                    const pivot = gridToScreen(CAMERA_PIVOT.x, CAMERA_PIVOT.y);
                    ctx.save();
                    ctx.translate(pivot.x, pivot.y);
                    ctx.rotate((liveDelta * Math.PI) / 180);
                    ctx.translate(-pivot.x, -pivot.y);
                    ctx.drawImage(tc, origin.x, origin.y, origin.w, origin.h);
                    ctx.restore();
                } else {
                    ctx.drawImage(tc, origin.x, origin.y, origin.w, origin.h);
                }
            }
            this._drawOceanGlints(inst);
        }
        this._drawDowntownGround(inst, phase);
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

    // Downtown ground fill -- every real building/road already has its own
    // real footprint, but the gaps between them had no ground tile at all
    // (bare canvas). Filled with plain pavement, plus a deterministic
    // scatter of parks/fountains/diners/benches -- all pure atmosphere,
    // same non-data category as the roadside trees and outer-world terrain,
    // computed fresh from this instance's own cells (not a static image,
    // since downtown is cheap enough to redraw live every frame at ~400
    // cells, unlike the much larger surrounding world).
    _drawDowntownGround(inst, phase) {
        const { ctx } = inst;
        const night = inst.mode === 'full' && isNight(phase);
        const hw = TILE_W / 2, hh = TILE_H / 2;
        (inst.groundCells || []).forEach(({ gx, gy, feature }) => {
            const r = rotateAroundPivot(gx + 0.5, gy + 0.5, inst.rotation);
            const { x: cx, y: cy } = gridToScreen(r.x, r.y);
            ctx.beginPath();
            ctx.moveTo(cx, cy - hh); ctx.lineTo(cx + hw, cy); ctx.lineTo(cx, cy + hh); ctx.lineTo(cx - hw, cy);
            ctx.closePath();
            ctx.fillStyle = feature === 'park' ? '#213b28' : '#212126';
            ctx.fill();
            ctx.strokeStyle = 'rgba(0,0,0,0.18)';
            ctx.lineWidth = 1;
            ctx.stroke();

            if (feature === 'park') {
                [[-6, -2], [5, 1], [0, -6], [-2, 5]].forEach(([ox, oy]) => this._drawTreeGlyph(ctx, cx + ox, cy + oy, 0.8));
            } else if (feature === 'fountain') {
                this._drawFountain(ctx, cx, cy);
            } else if (feature === 'diner') {
                this._drawDiner(ctx, cx, cy, night);
            } else if (feature === 'bench') {
                this._drawBench(ctx, cx, cy);
            }
        });
    },

    _drawFountain(ctx, cx, cy) {
        const t = performance.now();
        ctx.save();
        ctx.strokeStyle = 'rgba(180,190,200,0.5)';
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.ellipse(cx, cy, 9, 4.5, 0, 0, Math.PI * 2); ctx.stroke();
        const glint = 0.35 + 0.25 * Math.sin(t / 400);
        ctx.fillStyle = `rgba(150,200,235,${glint.toFixed(2)})`;
        ctx.beginPath(); ctx.ellipse(cx, cy, 6.5, 3.2, 0, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = 'rgba(210,225,240,0.6)';
        ctx.beginPath(); ctx.arc(cx, cy - 1, 1.4, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
    },

    _drawDiner(ctx, cx, cy, night) {
        ctx.save();
        const hw = 9, hh = 6, H = 12;
        const top = { x: cx, y: cy - hh - H }, right = { x: cx + hw, y: cy - H };
        const bottom = { x: cx, y: cy + hh - H }, left = { x: cx - hw, y: cy - H };
        const rightBase = { x: cx + hw, y: cy }, bottomBase = { x: cx, y: cy + hh }, leftBase = { x: cx - hw, y: cy };
        ctx.fillStyle = '#7a4030';
        ctx.beginPath(); ctx.moveTo(left.x, left.y); ctx.lineTo(bottom.x, bottom.y); ctx.lineTo(bottomBase.x, bottomBase.y); ctx.lineTo(leftBase.x, leftBase.y); ctx.closePath(); ctx.fill();
        ctx.fillStyle = '#9a5138';
        ctx.beginPath(); ctx.moveTo(right.x, right.y); ctx.lineTo(bottom.x, bottom.y); ctx.lineTo(bottomBase.x, bottomBase.y); ctx.lineTo(rightBase.x, rightBase.y); ctx.closePath(); ctx.fill();
        ctx.fillStyle = night ? '#ffe6a8' : '#c96a4a';
        ctx.beginPath(); ctx.moveTo(top.x, top.y); ctx.lineTo(right.x, right.y); ctx.lineTo(bottom.x, bottom.y); ctx.lineTo(left.x, left.y); ctx.closePath(); ctx.fill();
        ctx.strokeStyle = 'rgba(0,0,0,0.3)'; ctx.lineWidth = 1; ctx.stroke();
        if (night) { ctx.fillStyle = 'rgba(255,224,150,0.9)'; ctx.shadowColor = 'rgba(255,210,140,0.7)'; ctx.shadowBlur = 4; ctx.fillRect(cx + hw * 0.1, cy - H * 0.55, 2, 2); ctx.fillRect(cx + hw * 0.5, cy - H * 0.4, 2, 2); ctx.shadowBlur = 0; }
        ctx.restore();
    },

    _drawBench(ctx, cx, cy) {
        ctx.save();
        ctx.translate(cx, cy - 1);
        ctx.fillStyle = '#5b4a3a';
        ctx.fillRect(-5, -1.5, 10, 1.6);
        ctx.fillRect(-4.5, 0.5, 1.2, 2.5);
        ctx.fillRect(3.3, 0.5, 1.2, 2.5);
        ctx.restore();
    },

    // Road *hierarchy* -- real landmark spokes (Investigations, Bounty Ops,
    // Newsroom, Watchtower, Mint, Vault) render as wide avenues; the 10
    // uniform lane-checkpoint spokes render as narrower streets. This is a
    // real structural fact already in data/city-state.json (which building
    // a road's other end actually is), not a fabricated road-class dataset.
    _drawRoads(inst, phase) {
        const { ctx } = inst;
        const lit = inst.mode === 'full' && isNight(phase);
        const activity = inst.layer === 'activity';
        const strokePath = (pts, width, style) => {
            ctx.strokeStyle = style;
            ctx.lineWidth = width;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.beginPath();
            pts.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
            ctx.stroke();
        };
        // Relative to the busiest real road this cycle (log-scaled, since
        // real per-building counts here span two orders of magnitude --
        // e.g. 14 self-built tools vs. 1,413 sealed findings) so the
        // overlay stays a genuine comparison instead of nearly every
        // landmark clamping to the same saturated maximum.
        const activityPeak = activity ? Math.max(1, ...inst.roads.map(r =>
            r.to.stat_primary && typeof r.to.stat_primary.value === 'number' ? r.to.stat_primary.value : 0)) : 1;
        inst.roads.forEach(r => {
            const isAvenue = r.to.kind !== 'checkpoint';
            const pts = this._roadPathScreen(r, inst.rotation);
            let bedWidth = isAvenue ? 13 : 8.5;
            let curbWidth = isAvenue ? 16 : 10.5;
            let curbAlpha = 0.10;
            // "Activity" data layer -- an honest SimCity-style overlay: real
            // per-building volume (the same stat_primary already shown in
            // that building's own detail card) brightens/widens the road
            // reaching it. No pollution/land-value layer exists here because
            // VAPE has no real signal for either -- this is the one real
            // per-connection volume we actually have.
            if (activity) {
                const v = r.to.stat_primary && typeof r.to.stat_primary.value === 'number' ? r.to.stat_primary.value : 0;
                const norm = Math.min(1, Math.log1p(v) / Math.log1p(activityPeak));
                bedWidth = 6 + norm * 11;
                curbWidth = bedWidth + 3;
                curbAlpha = 0.08 + norm * 0.4;
            }
            strokePath(pts, curbWidth + 6, '#2b2b31'); // sidewalk -- a visible paved border, not bare ground, alongside every road
            strokePath(pts, curbWidth, `rgba(255,255,255,${curbAlpha.toFixed(2)})`); // curb / edge glow
            strokePath(pts, bedWidth, '#20202a'); // asphalt bed -- this is the fix for "can't see the roads"
            ctx.setLineDash(isAvenue ? [5, 5] : [3, 6]);
            strokePath(pts, isAvenue ? 1.6 : 1, lit ? 'rgba(255,224,150,0.55)' : 'rgba(255,255,255,0.32)'); // centerline
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

    // Real settled x402 jobs and real dispatched events -- bigger, glowing,
    // and visually distinct from the ambient gray traffic above. Color
    // comes from the real destination building's own kind (x402 stays
    // mint-green, matching The Mint's own identity hue); threat-dispatch
    // "emergency" vehicles also get a flashing red/cyan beacon, the one
    // SimCity service-vehicle detail this module borrows outright since
    // it's just a rendering flourish on an already-real incident.
    _drawVehicles(inst) {
        const { ctx } = inst;
        inst.vehicles.forEach(v => {
            const p = this._pointAlongRoadPath({ from: v.from, to: v.to }, v.t, inst.rotation);
            const kind = (v.meta && v.meta.kind) || 'x402';
            const colorVar = EVENT_COLOR_VAR[kind];
            const color = colorVar ? cssVar(colorVar) : (cssVar('--city-mint') || '#008300');
            ctx.save();
            ctx.translate(p.x, p.y - 5);
            ctx.fillStyle = color;
            ctx.shadowColor = color;
            ctx.shadowBlur = kind === 'threat' ? 14 : 10;
            ctx.beginPath();
            if (ctx.roundRect) ctx.roundRect(-5, -3, 10, 6, 2); else ctx.rect(-5, -3, 10, 6);
            ctx.fill();
            if (kind === 'threat') {
                const flash = Math.sin(performance.now() / 90) > 0;
                ctx.fillStyle = flash ? '#ff3d78' : '#2dd4ee';
                ctx.shadowBlur = 0;
                ctx.beginPath(); ctx.arc(0, -4, 1.5, 0, Math.PI * 2); ctx.fill();
            }
            ctx.restore();
        });
    },

    _drawBuilding(inst, b, phase) {
        const { ctx } = inst;
        let [fw, fh] = b.footprint || [1, 1];
        // A rotated camera swaps which grid axis reads as "wide" on screen,
        // so a building's own footprint has to swap with it to keep its
        // real width/depth ratio intact. Snapped to the nearest 90°
        // quadrant (not continuous) since a rectangular footprint only
        // has two honest orientations -- during a drag this "pops" once
        // per quadrant crossing rather than smoothly stretching, which
        // reads better than a distorted footprint mid-turn.
        const quadrant = Math.round(inst.rotation / 90) % 4;
        if (quadrant % 2 !== 0) { [fw, fh] = [fh, fw]; }
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

        // Ground shadow -- every building (checkpoints included) gets one,
        // the cheapest single fix for "looks like a block floating on the
        // grid" rather than a real object standing on real ground.
        ctx.save();
        ctx.globalAlpha = 0.28;
        ctx.fillStyle = '#000';
        ctx.beginPath();
        ctx.ellipse(cx, cy + hh * 0.2, hw * 0.95, hh * 0.6, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

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

        // Real facade -- a proper window grid fitted to both visible faces
        // (not just a couple of hardcoded dots), day or night, on every
        // landmark. This is the actual fix for "buildings just look like
        // colored blocks": a lit/glazed grid reads as a real facade at a
        // glance in a way a flat color never does.
        if (!isCheckpoint) {
            this._drawFacadeWindows(ctx, left, bottom, bottomBase, leftBase, H, hw, hh, night);
            this._drawFacadeWindows(ctx, right, bottom, bottomBase, rightBase, H, hw, hh, night);
            // A small dark entrance at street level on the near corner.
            ctx.fillStyle = 'rgba(0,0,0,0.5)';
            ctx.fillRect(cx - 2.5, cy + hh * 0.55 - 6, 5, 6);
        }
        // Checkpoints (the 10 automated-lane markers) double as real
        // downtown intersections -- an always-visible traffic-light pole,
        // plus a warm streetlamp glow layered on top at night.
        if (isCheckpoint) {
            this._drawTrafficLight(ctx, cx, cy, H);
            if (night) {
                ctx.beginPath();
                ctx.arc(cx, cy - H - 5, 2.6, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(255,230,150,0.9)';
                ctx.shadowColor = 'rgba(255,220,140,0.85)';
                ctx.shadowBlur = 10;
                ctx.fill();
                ctx.shadowBlur = 0;
            }
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

        // Rooftop silhouette per real building *kind* -- a smokestack for
        // the Foundry, an antenna for the Precinct, a dish for the
        // Newsroom, a beacon for the Watchtower, a dome for the Vault, a
        // sign frame for Bounty Ops, a coin disc for the Mint. `kind` is
        // already-real data; which small shape represents it is a display
        // choice, same category as its identity color.
        if (!isCheckpoint) this._drawRoofIcon(ctx, b.kind, top);

        // Real-tier "wealth" detailing -- build_city_state.py's tier_for()
        // relative-percentile tier is this module's one honest analog of
        // SimCity's wealth-driven material progression: a real tier-1
        // building stays plain, a real tier-4 building earns the glass-
        // curtain-wall streak and rooftop spire, exactly as much extra
        // detail as its real relative volume actually earned.
        if (!isCheckpoint) this._drawWealthDetailing(ctx, b.tier || 1, cx, cy, top, right, hw, H);

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

    _drawWealthDetailing(ctx, tier, cx, cy, top, right, hw, H) {
        if (tier >= 2) {
            // Thin bright roofline trim -- the first step up from bare
            // blockwork.
            ctx.strokeStyle = 'rgba(255,255,255,0.22)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(top.x, top.y); ctx.lineTo(right.x, right.y);
            ctx.stroke();
        }
        if (tier >= 3) {
            // A glass curtain-wall streak on the sunlit face.
            ctx.save();
            ctx.globalAlpha = 0.24;
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.moveTo(right.x - hw * 0.15, right.y + 4);
            ctx.lineTo(right.x + hw * 0.05, right.y + 4);
            ctx.lineTo(cx + hw * 0.35, cy - H * 0.15);
            ctx.lineTo(cx + hw * 0.15, cy - H * 0.15);
            ctx.closePath(); ctx.fill();
            ctx.restore();
        }
        if (tier >= 4) {
            // A rooftop spire -- the skyline mark of a real tier-4 landmark.
            ctx.strokeStyle = 'rgba(255,255,255,0.55)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(top.x, top.y); ctx.lineTo(top.x, top.y - 10);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(top.x, top.y - 11, 1.4, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,255,255,0.75)';
            ctx.fill();
        }
    },

    // Tiles a real window grid across an isometric face quadrilateral via
    // bilinear interpolation between its 4 real corners -- so every window
    // actually sits flush on the face instead of floating near it. Day
    // glazing is a muted blue-gray pane; night swaps to a warm lit color
    // with a soft glow, same look _drawBuildingWindows used to hardcode in
    // only two spots.
    _drawFacadeWindows(ctx, topNear, topFar, bottomFar, bottomNear, H, hw, hh, night) {
        const rows = Math.max(2, Math.round(H / 13));
        const cols = Math.max(1, Math.round(Math.max(hw, hh) / 11));
        const color = night ? 'rgba(255,214,120,0.9)' : 'rgba(196,214,230,0.32)';
        if (night) { ctx.shadowColor = 'rgba(255,200,120,0.55)'; ctx.shadowBlur = 2.5; }
        ctx.fillStyle = color;
        for (let r = 0; r < rows; r++) {
            const v = (r + 0.35) / rows;
            const nearX = this._lerp(topNear.x, bottomNear.x, v), nearY = this._lerp(topNear.y, bottomNear.y, v);
            const farX = this._lerp(topFar.x, bottomFar.x, v), farY = this._lerp(topFar.y, bottomFar.y, v);
            for (let c = 0; c < cols; c++) {
                const u = (c + 0.5) / cols;
                const x = this._lerp(nearX, farX, u), y = this._lerp(nearY, farY, u);
                ctx.fillRect(x - 1.1, y - 1.3, 2.2, 2.6);
            }
        }
        ctx.shadowBlur = 0;
    },

    _drawRoofIcon(ctx, kind, top) {
        ctx.save();
        ctx.lineWidth = 1;
        if (kind === 'foundry') {
            ctx.fillStyle = 'rgba(20,16,14,0.55)';
            ctx.fillRect(top.x - 6, top.y - 10, 3, 10);
            ctx.fillRect(top.x, top.y - 7, 3, 7);
        } else if (kind === 'precinct') {
            ctx.strokeStyle = 'rgba(255,255,255,0.45)';
            ctx.beginPath(); ctx.moveTo(top.x, top.y); ctx.lineTo(top.x, top.y - 9); ctx.stroke();
            ctx.fillStyle = 'rgba(255,255,255,0.55)';
            ctx.fillRect(top.x, top.y - 9, 6, 3.5);
        } else if (kind === 'newsroom') {
            ctx.strokeStyle = 'rgba(255,255,255,0.5)';
            ctx.beginPath(); ctx.arc(top.x - 3, top.y - 5, 3.2, Math.PI, Math.PI * 1.85); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(top.x - 3, top.y - 5); ctx.lineTo(top.x - 3, top.y - 1); ctx.stroke();
        } else if (kind === 'watchtower') {
            ctx.strokeStyle = 'rgba(255,255,255,0.55)';
            ctx.beginPath(); ctx.moveTo(top.x, top.y); ctx.lineTo(top.x, top.y - 12); ctx.stroke();
            ctx.beginPath(); ctx.arc(top.x, top.y - 13, 2, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,120,120,0.85)'; ctx.fill();
        } else if (kind === 'vault') {
            ctx.fillStyle = 'rgba(255,255,255,0.28)';
            ctx.beginPath(); ctx.arc(top.x, top.y - 1, 5.5, Math.PI, 0); ctx.closePath(); ctx.fill();
        } else if (kind === 'tower') {
            ctx.strokeStyle = 'rgba(255,255,255,0.45)';
            ctx.strokeRect(top.x - 6, top.y - 9, 12, 5.5);
        } else if (kind === 'mint') {
            ctx.fillStyle = 'rgba(255,255,255,0.32)';
            ctx.beginPath(); ctx.arc(top.x, top.y - 4, 4, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = 'rgba(0,0,0,0.3)'; ctx.stroke();
        }
        ctx.restore();
    },

    // A tiny deterministic tree glyph -- pure atmosphere, the same
    // non-data category as the ambient traffic/pedestrian particles
    // already in this file. Used both scattered through the surrounding
    // terrain and alongside real downtown streets.
    _drawTreeGlyph(ctx, x, y, s) {
        ctx.save();
        ctx.translate(x, y);
        ctx.scale(s, s);
        ctx.fillStyle = 'rgba(10,8,6,0.3)';
        ctx.beginPath(); ctx.ellipse(0, 1.5, 3.4, 1.4, 0, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#5b3a24';
        ctx.fillRect(-0.6, -3, 1.2, 4.5);
        ctx.fillStyle = '#2f6b3a';
        ctx.beginPath(); ctx.arc(0, -6, 3.4, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#3d8a4b';
        ctx.beginPath(); ctx.arc(-1.2, -7.3, 2.1, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
    },

    // A real traffic-light pole at each lane-checkpoint "intersection" --
    // pure atmosphere, always visible (not just at night), same non-data
    // category as the trees/benches/fountains above.
    _drawTrafficLight(ctx, cx, cy, H) {
        ctx.save();
        ctx.strokeStyle = 'rgba(50,50,56,0.9)';
        ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.moveTo(cx, cy - H); ctx.lineTo(cx, cy - H - 14); ctx.stroke();
        ctx.fillStyle = '#1c1c22';
        ctx.fillRect(cx - 2.3, cy - H - 22, 4.6, 9);
        const colors = ['#ff3d40', '#ffd23d', '#2dd45a'];
        colors.forEach((c, i) => {
            ctx.beginPath();
            ctx.arc(cx, cy - H - 19.7 + i * 3, 1, 0, Math.PI * 2);
            ctx.fillStyle = c;
            ctx.fill();
        });
        ctx.restore();
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
        const wLogical = Math.max(1, Math.ceil(xMax - xMin)), hLogical = Math.max(1, Math.ceil(yMax - yMin));
        // WORLD_BOUNDS spans ~190x175 tiles -- the 0°/90° stops alone would
        // otherwise allocate an ~70-megapixel (~280MB) canvas apiece with no
        // upper bound, easily exhausting canvas memory on mobile. Downscale
        // the *physical* canvas (via a single ctx.scale() below, so every
        // existing draw call below needs zero coordinate changes) and
        // stretch it back to logical size on composite -- soft, but this is
        // a static, never-crisp-at-that-distance backdrop layer anyway.
        const scale = Math.min(1, Math.sqrt(TERRAIN_CACHE_MAX_PIXELS / (wLogical * hLogical)));
        const w = Math.max(1, Math.round(wLogical * scale)), h = Math.max(1, Math.round(hLogical * scale));

        const cvs = typeof OffscreenCanvas !== 'undefined'
            ? new OffscreenCanvas(w, h)
            : Object.assign(document.createElement('canvas'), { width: w, height: h });
        const ctx = cvs.getContext('2d');
        if (scale < 1) ctx.scale(scale, scale);

        tiles.forEach(t => this._drawTerrainTile(ctx, t.biome, t.rx, t.ry, -xMin, -yMin, t.gx, t.gy));
        this._findBridgeSpots(tiles).forEach(spot => this._drawBridge(ctx, spot, rotation, -xMin, -yMin));
        this._drawExitRoads(ctx, rotation, -xMin, -yMin);

        this._cacheTerrain(rotation, cvs, { x: xMin, y: yMin, w: wLogical, h: hLogical });
    },

    // LRU eviction -- even pixel-capped, each cached canvas can be tens of
    // MB, so keep at most TERRAIN_CACHE_MAX_STOPS resident rather than
    // accumulating one per rotation stop ever viewed in a session.
    _cacheTerrain(rotation, canvas, origin) {
        if (!this._terrainCacheOrder) this._terrainCacheOrder = [];
        this._terrainCache[rotation] = canvas;
        this._terrainOrigin[rotation] = origin;
        this._touchTerrainCache(rotation);
        while (this._terrainCacheOrder.length > TERRAIN_CACHE_MAX_STOPS) {
            const evict = this._terrainCacheOrder.shift();
            delete this._terrainCache[evict];
            delete this._terrainOrigin[evict];
        }
    },

    _touchTerrainCache(rotation) {
        if (!this._terrainCacheOrder) this._terrainCacheOrder = [];
        const idx = this._terrainCacheOrder.indexOf(rotation);
        if (idx !== -1) this._terrainCacheOrder.splice(idx, 1);
        this._terrainCacheOrder.push(rotation);
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

        // Trees + parks -- pure world scenery, same non-data category as
        // the rest of this terrain layer. A handful of fixed tiles near
        // downtown are designated parks (denser trees + a green tint,
        // clearly distinct from a plain surveyed-vacant lot); everywhere
        // else gets a light, deterministic sprinkle so the world doesn't
        // read as bare dirt.
        if (biome === 'vacant' || biome === 'farmland') {
            if (PARK_TILES.has(`${ogx},${ogy}`)) {
                ctx.save();
                ctx.globalAlpha = 0.4;
                ctx.fillStyle = '#2c5c33';
                ctx.beginPath();
                ctx.moveTo(top.x, top.y); ctx.lineTo(right.x, right.y);
                ctx.lineTo(bottom.x, bottom.y); ctx.lineTo(left.x, left.y);
                ctx.closePath(); ctx.fill();
                ctx.restore();
                [[-7, -2], [6, 1], [0, -7], [-2, 5]].forEach(([ox, oy]) => this._drawTreeGlyph(ctx, cx + ox, cy + oy, 1.05));
            } else {
                const seedVal = _hash(ogx * 13.7 + ogy * 5.3, TERRAIN_SEED + 77);
                const threshold = biome === 'farmland' ? 0.05 : 0.15;
                if (seedVal < threshold) this._drawTreeGlyph(ctx, cx + (seedVal / threshold) * 14 - 7, cy - 2, 0.85);
            }
        }
    },

    // Two fixed roads out of town -- purely structural world scenery, same
    // non-data category as the fixed road layout itself, just extended
    // past the city limits: one heads due west along the real street
    // grid's own Main Street row out to a small marina on the coast, the
    // other heads south out of town and tapers into open land.
    _drawExitRoads(ctx, rotation, dx, dy) {
        const project = (gx, gy) => {
            const r = rotateAroundPivot(gx, gy, rotation);
            const s = gridToScreen(r.x, r.y);
            return { x: s.x + dx, y: s.y + dy };
        };
        const strokeLine = (p1, p2, width, style, dash) => {
            ctx.save();
            ctx.strokeStyle = style;
            ctx.lineWidth = width;
            ctx.lineCap = 'round';
            if (dash) ctx.setLineDash(dash);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
            ctx.restore();
        };

        const marinaA = project(0, CAMERA_PIVOT.y), marinaB = project(-70, CAMERA_PIVOT.y);
        strokeLine(marinaA, marinaB, 11, '#20202a');
        strokeLine(marinaA, marinaB, 1.4, 'rgba(255,255,255,0.28)', [5, 6]);
        this._drawMarina(ctx, project(-66, CAMERA_PIVOT.y));

        // A county road tapering south into open land -- shrinking segments
        // instead of one long stroke so it visually fades rather than
        // stopping dead at a hard edge.
        for (let i = 0; i < 6; i++) {
            const p0 = project(CAMERA_PIVOT.x, CITY_BBOX.maxY + i * 5);
            const p1 = project(CAMERA_PIVOT.x, CITY_BBOX.maxY + (i + 1) * 5);
            strokeLine(p0, p1, 9, `rgba(32,32,42,${(0.85 - i * 0.13).toFixed(2)})`);
        }
    },

    _drawMarina(ctx, at) {
        ctx.save();
        ctx.translate(at.x, at.y);
        ctx.strokeStyle = '#8a8a94';
        ctx.lineWidth = 6;
        ctx.beginPath(); ctx.moveTo(-15, 0); ctx.lineTo(15, 0); ctx.stroke();
        ctx.lineWidth = 4;
        ctx.beginPath(); ctx.moveTo(0, -9); ctx.lineTo(0, 9); ctx.stroke();
        [[-9, -4], [8, 3], [-3, 6]].forEach(([bx, by]) => {
            ctx.save();
            ctx.translate(bx, by);
            ctx.fillStyle = '#e8ddb0';
            ctx.beginPath();
            if (ctx.roundRect) ctx.roundRect(-4, -2, 8, 4, 1.5); else ctx.rect(-4, -2, 8, 4);
            ctx.fill();
            ctx.restore();
        });
        ctx.restore();
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
