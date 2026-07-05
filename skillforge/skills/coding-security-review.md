# Skill: Auditing Client-Side Code for Real, Concrete Vulnerabilities

**Tier:** coding · **Status:** active

## When to use
Whenever asked for "a security review" of a repo or site, and periodically on
any code that renders external or attacker-influenced data (on-chain token
metadata, wallet-extension-supplied data, API responses, user-submitted
issue/PR text). The goal is signal, not volume — a report full of theoretical
"could be an issue" noise trains nothing and gets ignored. Every finding
should be something you could demonstrate firing.

## Procedure (reproducible, grounded in this repo's real audit)

1. **Sweep by pattern, not by file.** Grep the whole tree for the small set
   of sink patterns that actually matter, rather than reading every file
   top to bottom:
   - `innerHTML|insertAdjacentHTML|document.write` in client JS — every hit
     is a potential XSS sink; the question is always "what data reaches this,
     and is it escaped."
   - `eval(|exec(|pickle.load|yaml.load(|subprocess.*shell=True` in Python —
     code-execution sinks.
   - `${{ github.event.(issue|pull_request|comment).* }}` inlined directly
     into a workflow `run:` block — GitHub Actions script injection. If it's
     already routed through `env:` first, it's safe; that's the one-line
     distinction that matters.
   - Hardcoded secret shapes (`sk-`, `ghp_`, `gsk_`, `-----BEGIN ... KEY-----`)
     across the whole tree.

2. **For every sink hit, trace the data backward to its origin — that's the
   whole job.** A hit isn't a finding until you know whether the value
   reaching it can ever be attacker-chosen. In this repo specifically:
   - On-chain token/NFT `name`/`symbol` fields are always attacker-chosen
     (anyone can mint a token with `name() = "<img src=x onerror=...>"`) —
     treat every render of on-chain metadata as a sink that needs escaping,
     full stop.
   - **EIP-6963 `announceProvider` events are a trust boundary most reviews
     miss.** `info.name`/`info.icon`/`info.uuid` are announced by *whatever
     browser extension dispatches the global `window` event* — a malicious
     or compromised extension can impersonate a real wallet with a crafted
     `info.icon` like `"><img src=x onerror=...>` and, if that string lands
     in `innerHTML` unescaped, break out of the `src="..."` attribute and
     execute in the page's own origin. This is a real, documented class of
     wallet-phishing risk in the dapp ecosystem, not a theoretical one.
   - A workflow input gated behind `issues: types: [labeled]` with a
     `label.name == 'vape-build'` check is *effectively* gated on write
     access (labeling is a maintainer action by default) — don't flag
     `github.event.issue.body` as freely attacker-controlled without also
     checking what actually triggers the workflow.
   - CLI args validated by a regex (`^0x[a-fA-F0-9]{40}$`) *before* being
     used to build a file path or shell argument close off path-traversal/
     injection at the source — check the validation exists and actually runs
     before the sink, not just that a regex constant is defined somewhere in
     the file.

3. **Don't stop at the first sink — check whether the *value itself* is
   ever validated, not just whether individual renders escape it.** The
   deeper bug in this repo's wallet-connect code wasn't only that popover
   HTML was unescaped — it was that `_bind()` accepted *any* string a
   provider returned as the connected "account" with zero format check, so
   that unvalidated string then fanned out into an `aria-label`, a Basescan
   `href`, and popover text across several call sites. Validating the shape
   once at the point of entry (`^0x[a-fA-F0-9]{40}$`) closes every downstream
   use in one place — cheaper and more durable than patching each render
   site individually, and it's the fix to prefer when a value has more than
   one consumer.

4. **Verify the fix by actually firing the payload, not just by reading the
   diff.** Headless Chromium lets you dispatch a fake trigger event and
   assert on the outcome directly:
   ```js
   window.dispatchEvent(new CustomEvent('eip6963:announceProvider', {
     detail: { info: { name: '<img src=x onerror="window.__xss=1">', ... }, provider: fakeProvider }
   }));
   // then assert window.__xss is still undefined after render
   ```
   A finding you can reproduce this way is a finding worth fixing immediately;
   one you can't concretely trigger is usually noise.

5. **Know the boundaries that are *not* bugs in this codebase**, so you
   don't waste a fix on something already handled by design:
   - `cors({ origin: "*" })` on the x402 worker is fine — there's no
     cookie/session auth to leak; the API is gated by signed payment headers,
     not origin trust.
   - `_is_safe_callback_url()` in `agents/deep_dive_audit.py` already blocks
     private/loopback/link-local/reserved/multicast resolved IPs before
     POSTing to a buyer-supplied callback URL — a real, intentionally-scoped
     SSRF guard, not a gap.
   - Static, repo-authored identifiers (offering names from
     `data/reputation.json`, generated from a fixed list in
     `agents/acp_fulfill.py`) don't need escaping when interpolated into an
     inline `onclick` — they're not externally controlled, unlike on-chain
     token metadata.

## Quality gates
- Every finding must name the exact sink (file:line) and the exact source of
  the attacker-controlled value, and be reproducible in a sandboxed browser
  or a unit-level repro — not just "this pattern looks risky."
- Prefer fixing at the value's point of entry when it has multiple
  downstream consumers, over patching every render site.
- Record both *what* was found and *how* it was found (the grep pattern, the
  trace) in `skillforge/memory/findings.jsonl` (the finding itself) and
  `skillforge/memory/build_log.jsonl` (the reusable method) — a finding
  fixed without a recorded method has to be rediscovered from scratch next
  time.

## Known limitations
- A single review pass over a large repo can't be exhaustive — this
  procedure optimizes for finding the highest-confidence, most-reachable
  issues in the areas most likely to have them (client-side rendering of
  external data, CI workflow triggers, subprocess/eval sinks), not for
  proving the absence of every possible bug class.
- Static review can't catch everything a live wallet/browser combination
  would surface (e.g. a specific in-app webview's quirks) — see the
  verification skill's "known limitations" for the same caveat.

_Written for skillforge/memory/build_log.jsonl's coding-education track —
see skillforge/memory/BUILD_LEDGER.md._
