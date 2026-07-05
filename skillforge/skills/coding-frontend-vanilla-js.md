# Skill: Building the Zero-Build Frontend (docs/)

**Tier:** coding · **Status:** active

## When to use
Any change to `docs/index.html` or `docs/assets/*.js` — the site has no
bundler, no build step, no npm install. Every file is served exactly as
written, straight from GitHub Pages. That constraint shapes every pattern
below; violate it and the site breaks for real visitors with no build to
catch the mistake first.

## Procedure (reproducible, grounded in this repo's real frontend)

1. **Know which script-loading mode a file needs before writing it.**
   `docs/assets/app.js` is a classic `<script>` (no `type="module"`) because
   its top-level consts need to be visible the old way; `wallet.js`,
   `profile.js`, `report.js`, `hire.js` are `type="module"` because they
   `import`/`export` between each other (see `docs/assets/icons.js` being
   imported directly into `report.js` and `profile.js`). Mixing this up
   produces a silent `ReferenceError` at runtime, not a build error — always
   check the `<script>` tag in `docs/index.html` before assuming a file can
   `import`.

2. **Escape everything that touches `innerHTML`, always, at the sink.**
   Every JS file in `docs/assets/` defines its own local `escapeHtml()` and
   applies it to any attacker-influenced string (a token's on-chain `name()`,
   a wallet-supplied address, a worker's JSON response) right before it goes
   into a template literal that becomes `innerHTML`. See the CodeQL fix in
   this repo's history: an `href="${basescanUrl(addr)}"` without
   `escapeHtml()` around the *whole* computed URL — not just the visible
   text — was flagged even though runtime validation made it currently safe.
   Escape at the sink regardless of what the caller guarantees upstream.

3. **Never guess an icon/logo URL — use the tiered resolver.** See
   `docs/assets/icons.js`'s three tiers (hand-verified table → address-keyed
   CDN → exact-name match against a live authoritative list) and the
   dedicated build_log entry on this exact pattern. A wrong guess is worse
   than no icon.

4. **Remember `position:absolute` needs a real positioned ancestor.**
   Anything appended to `document.body` and positioned `absolute` resolves
   against the top of the whole document, not the viewport — invisible after
   scrolling. Use `getBoundingClientRect()` + `position:fixed` for anything
   body-appended (`docs/assets/wallet.js`'s `_placeNearAnchor()`), or make
   sure the real intended ancestor (e.g. a `sticky` nav) is what receives the
   absolutely-positioned child.

5. **Design cards to wrap, not to guess a safe max length.** A `flex
   items-center justify-between` row with one `shrink-0` badge and one
   "joined with · " text string has nowhere to shrink to if the string is
   long — it either truncates unpredictably or overflows the card. Use small
   independent chips in a `flex flex-wrap` container instead (see
   `App._metaChips()` in `app.js`) so a long line wraps onto a second row
   instead of forcing width.

6. **Bump the cache-buster version on every JS file you touch.**
   `docs/index.html` has an explicit comment above the script tags: GitHub
   Pages and in-app wallet webviews cache aggressively, and a shipped fix
   that a stale cache still hides looks identical to "not fixed yet." Bump
   only the files you actually changed — bumping unrelated ones is harmless
   but adds noise to the diff.

7. **Test with a headless browser, but know what the sandbox can't tell
   you.** `node --check file.js` catches syntax errors; a headless-Chromium
   pass (Playwright, `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`) catches
   runtime errors (`pageerror` events) even when outbound network calls to
   Tailwind's CDN or external APIs are blocked by the build sandbox — those
   show up as `console` resource-load errors, not `pageerror`s, and can be
   filtered out. A real layout/overflow check needs Tailwind's CSS to have
   actually loaded, which the sandbox can't guarantee — trust the JS-error
   check fully, treat a sandboxed visual check as informative but not proof.

## Quality gates
- `node --check` on every changed `.js` file.
- A Python (or equivalent) structural pass on `docs/index.html`: no
  duplicate `id` attributes, and `<section>`/`<div>`/`<footer>` open/close
  counts balanced — a single unclosed `<div>` silently breaks every section
  below it with no error anywhere.
- No new external API call site without checking it's either free/keyless
  (like DexScreener's public endpoints) or already proxied through
  `WORKER_BASE` (for anything needing a server-side key, like CoinGecko
  pricing through `/prices`).

## Known limitations
- There is no linter or type checker wired into CI for this frontend by
  design (zero-build) — `node --check` only catches syntax errors, not logic
  bugs. That's why the manual overflow/render checks above matter more here
  than they would in a bundled, typed frontend.

_Written for skillforge/memory/build_log.jsonl's coding-education track —
see skillforge/memory/BUILD_LEDGER.md._
