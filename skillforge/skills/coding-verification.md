# Skill: Verifying a Change Before Calling It Done

**Tier:** coding · **Status:** active

## When to use
Before every commit that touches code — not after review flags a problem.
Verification is cheap; a bug shipped to `main` and caught by a user (or by
CodeQL, or by a broken page) is expensive.

## Procedure (reproducible, grounded in this repo's real checks)

1. **Syntax first, always — it's nearly free.**
   - Python: `python3 -m py_compile <file>.py` catches syntax errors;
     `python3 -c "import <module>"` additionally catches import-time errors
     (a bad top-level import, a circular import) that `py_compile` alone
     misses.
   - JavaScript: `node --check <file>.js` — works even for `type="module"`
     files despite Node not executing them as modules, since `--check` only
     parses.

2. **Structural checks for generated/hand-edited markup.** For
   `docs/index.html`: no duplicate `id` attributes (breaks
   `document.getElementById` callers silently — the first match wins, later
   ones are dead), and balanced `<section>`/`<div>`/`<footer>` tag counts. A
   short Python regex pass catches both in under a second and has caught
   real mistakes in this repo's history (an unclosed div from a large
   multi-edit session).

3. **Runtime check with a headless browser for anything touching the live
   site's JS.** Serve `docs/` locally (`python3 -m http.server`), load it in
   headless Chromium, and listen for `pageerror` events (uncaught exceptions)
   — not just `console` errors, which include expected noise like blocked
   external network calls in a sandboxed environment. A clean `pageerror`
   list means the JS parsed and executed without throwing, which `node
   --check` alone can't confirm (it doesn't execute anything).

4. **Feed realistic mock data through render functions when you can't hit
   the real network.** A sandboxed test environment often can't reach
   external APIs — that doesn't mean the *rendering logic* is untestable.
   Call the render function directly with a hand-built object shaped like
   the real API response (see how Archive-card overflow was checked this
   session: `App._intel = {...realistic shape...}; App._renderIntel();`
   then measure `el.scrollWidth > el.clientWidth` on the rendered cards) —
   this exercises the actual template code without needing the network.

5. **Know what a sandbox limitation looks like, so you don't chase a ghost
   bug.** If every element on a page reports being ~1024px wide in a
   viewport of 375px, and the "wide" elements are all `<img>` tags with
   Tailwind sizing classes, check whether Tailwind's CDN script itself
   could load — if the sandbox blocks outbound requests to
   `cdn.tailwindcss.com`, none of the sizing utilities apply and every image
   falls back to its raw intrinsic pixel size. That's a sandbox artifact,
   not a production bug — confirm by checking whether the *same* utility
   classes render correctly in production (they do, if the rest of the site
   already uses them successfully elsewhere).

6. **Verify the deploy, not just the merge.** See the git-workflow skill's
   step 6 — a green merge is not the same as a live, working site.

## Quality gates
- Every check in steps 1–3 should be automatable in under a minute — if a
  verification step takes long enough that it feels worth skipping, that's
  a sign to make it faster (a targeted script), not to skip it.
- A verification pass that only checks "does it look plausible" is not a
  verification pass — it needs a concrete, falsifiable check (an exit code,
  a boolean, a specific error list), not a vibe.

## Known limitations
- None of this replaces an actual human (or a real user) exercising the
  feature in a real browser against the real deployed site — headless
  smoke tests catch crashes and gross layout breakage, not subjective
  design quality or edge cases only a real wallet/browser combination would
  surface (e.g. an in-app webview blocking a specific API).

_Written for skillforge/memory/build_log.jsonl's coding-education track —
see skillforge/memory/BUILD_LEDGER.md._
