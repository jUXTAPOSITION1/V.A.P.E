"""
VAPE multi-provider LLM layer — OpenAI-compatible fallback chain, stdlib-only.

One ask() call, an ordered list of FREE open-source providers. On rate-limit/error,
fall through to the next. No vendor lock-in, no heavy deps (no LiteLLM/openai pkg) —
just urllib hitting each provider's OpenAI-compatible /chat/completions endpoint.

Providers (all OpenAI-compatible) — enabled when their key env is set:
    groq        GROQ_API_KEY        speed champion (Llama 3.1/4) — default fast path
    cerebras    CEREBRAS_API_KEY    1M tokens/day — bulk synthesis
    openrouter  OPENROUTER_API_KEY  20+ free models — fallback marketplace
    gemini      GEMINI_API_KEY      real frontier tier (gemini-2.5-pro) — free tier is
                                    quota-limited (5 RPM / 50 RPD) but that's plenty for
                                    an occasional premium job like the deep-dive
                                    bounty audit, not a high-volume path. Get a free key
                                    at https://aistudio.google.com/apikey.
    github      GITHUB_MODELS_TOKEN GitHub Models (DeepSeek-R1). GitHub is FULLY
                                    RETIRING this service 2026-07-30 (brownouts already
                                    scheduled 07-16/07-23) — kept only as one more
                                    fallback rung until then; do not build anything new
                                    on it, and remove this entry after the retirement
                                    date. This is why frontier work uses Gemini, not
                                    GitHub Models, despite GitHub Models technically
                                    also offering premium models today.
    together    TOGETHER_API_KEY    70B free endpoints — when 8B isn't enough
    xai         XAI_API_KEY_1       Grok 4.1 Fast — paid, the LAST-resort entry in
                                    FRONTIER_ORDER as of 2026-07-25 (see that
                                    constant's own comment for why: it's the only
                                    paid tier in this chain, and its Live Search
                                    feature is currently dead — HTTP 410,
                                    deprecated in favor of xAI's new "Agent Tools
                                    API", not yet migrated here). VAPE's actual
                                    primary reasoning route for high-stakes work is
                                    OCI-hosted Grok 4.3 (ask_oci_grok()), not this
                                    direct xai_1 entry. Not in the default PROVIDERS
                                    chain a bare ask() call uses — only reachable via
                                    provider_order=FRONTIER_ORDER / ask_frontier(),
                                    so ordinary fast/bulk-tier calls never touch it.
                                    A single key, not a rotated pair — a second key
                                    (XAI_API_KEY_2) was tried briefly but its xAI
                                    team had no credits/license, so it's not worth
                                    the added complexity of a two-key fallthrough
                                    for a key that can't serve real traffic anyway;
                                    revisit if a genuinely funded second key is ever
                                    needed. OpenAI-compatible endpoint (api.x.ai/v1),
                                    same _call() as everything else.

VAPE's own fine-tuned candidate (see training/train_lora.py +
.github/workflows/train-vape-model.yml) is deliberately NOT in the PROVIDERS
list above and NOT reachable via a bare ask() call — it's an opt-in-only
provider built by candidate_provider_order(), gated on VAPE_CANDIDATE_URL,
used only by an explicit provider_order=candidate_provider_order() (or
ask_candidate() below). This matches data/finetune/DATASET_CARD.md's rule
that the candidate must be evaluated (training/eval_candidate.py) before any
real traffic ever reaches it — "takeover as primary" is an earned later
milestone, not something this module defaults to.

A second, independent candidate — VAPE's own Gemini model, supervised-tuned
via Vertex AI's managed tuning console (not the self-hosted GPU/LoRA path
above) and served from a deployed Vertex endpoint — is reachable the same
opt-in-only way via ask_vertex_candidate(), gated on VAPE_VERTEX_ACCESS_TOKEN
(a short-lived OAuth token minted per workflow run via Workload Identity
Federation, never a stored key — this Google Cloud project enforces
iam.disableServiceAccountKeyCreation).

A third candidate — Oracle Cloud's hosted xAI Grok 4.3 (1M-token context,
reasoning-focused; not fine-tuned/VAPE-specific like the two above, just a
second real frontier-model host) — is reachable via ask_oci_grok(), gated on
OCI_GENAI_API_KEY (a plain Bearer secret from OCI's Generative AI service,
distinct from the IAM RSA key pair used for general OCI SDK/CLI auth).

Tiers pick a model per task:
    fast      -> small/quick (hourly reports)
    deep      -> larger reasoning (daily synthesis, audits)
    bulk      -> high daily volume (harvest passes)
    frontier  -> the real premium model for the highest-stakes work (the deep-dive
                 bounty audit, investigations' AI quick review, and — via explicit
                 provider_order=FRONTIER_ORDER at each call site — the intel sweeps'
                 narrative, Builder, SKILLFORGE synthesis, and the AI red-team). Falls
                 back through the rest of the chain when the frontier provider has no
                 key or errors, via FRONTIER_ORDER/ask_frontier(). Providers with no
                 "frontier" entry transparently reuse their "deep" model instead (see
                 the model-resolution fallback in ask()).

Per-call token usage is best-effort logged to skillforge/memory/llm_usage.jsonl
(provider/model/tier/token counts) for later cost/routing self-optimization — never
raises, never blocks a caller if Memory/disk isn't writable.

Every provider above except xai_1 is a free tier (rate/quota-limited, not billed) —
xai_1 (Grok, real money) is the only one a runaway loop could actually cost VAPE for,
which is why it's the only entry in PROVIDER_PRICING_USD_PER_M_TOKENS below and the
only one the daily spend cap in ask() applies to. See that constant's comment for
where the per-token price came from.

Backwards compatible: run.py can keep calling its own ask_llm; this is opt-in.
"""
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "skillforge", "memory")
USAGE_LOG = os.path.join(MEMORY_DIR, "llm_usage.jsonl")
FINDINGS_LOG = os.path.join(MEMORY_DIR, "findings.jsonl")

# USD per 1M tokens, standard (non-batch, non-cached) rate. Verified against
# xAI's public API pricing (multiple independent pricing trackers agreed on
# $0.20 input / $0.50 output for grok-4-1-fast-reasoning as of 2026-07) —
# re-verify against https://x.ai/api before changing, don't guess a new
# number. Only providers that actually bill real money belong in this dict;
# everything else in PROVIDERS is a free/quota-limited tier with nothing to
# cap here.
PROVIDER_PRICING_USD_PER_M_TOKENS = {
    "xai_1": {"input": 0.20, "output": 0.50},
    # xAI's own published direct-API rate for Grok 4.3 (openrouter.ai/x-ai/
    # grok-4.3, pricepertoken.com — both agreed $1.25 input / $2.50 output
    # per 1M tokens as of 2026-07), used as a conservative proxy for OCI's
    # on-demand rate since Oracle doesn't publish a per-token price the same
    # way — this errs toward the cap firing too early, not too late.
    # Re-verify against the OCI console's cost estimator / a real invoice
    # before trusting this beyond "catch a runaway loop."
    "oci_grok": {"input": 1.25, "output": 2.50},
}

# Hand-picked, not derived from historical usage: real logged xai_1 spend to
# date is a fraction of a cent (see skillforge/memory/llm_usage.jsonl), so
# this is deliberately a generous ceiling meant to catch a genuine runaway
# (a bug looping thousands of calls) long before it does real damage, not to
# throttle normal operation. Override via XAI_DAILY_SPEND_CAP_USD if actual
# usage ever legitimately grows toward it.
DEFAULT_DAILY_SPEND_CAP_USD = 3.00

# provider: (env_key, base_url, {tier: model})
PROVIDERS = [
    ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions", {
        "fast": "llama-3.1-8b-instant",
        "deep": "llama-3.3-70b-versatile",
        "bulk": "llama-3.1-8b-instant",
    }),
    ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions", {
        "fast": "llama3.1-8b",
        # llama-3.3-70b (this entry's value until 2026-07) was deprecated/
        # removed by Cerebras 2026-02-16 — confirmed real HTTP 404
        # model_not_found in production. gpt-oss-120b is Cerebras' own
        # documented migration target for that exact deprecation (per
        # inference-docs.cerebras.ai/support/deprecation, re-verified via
        # web search 2026-07 since the doc page itself 403s to automated
        # fetches) — re-verify against Cerebras' real /models endpoint if
        # this ever 404s again rather than re-guessing.
        "deep": "gpt-oss-120b",
        "bulk": "llama3.1-8b",
    }),
    ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions", {
        "fast": "meta-llama/llama-3.3-70b-instruct:free",
        "deep": "deepseek/deepseek-r1:free",
        "bulk": "meta-llama/llama-3.3-70b-instruct:free",
    }),
    # Real frontier tier. Google's OpenAI-compatibility shim — same request/response
    # shape as every other provider here, zero special-casing needed in _call().
    ("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {
        "fast": "gemini-2.5-flash",
        "deep": "gemini-2.5-flash",
        "bulk": "gemini-2.5-flash",
        "frontier": "gemini-2.5-pro",
    }),
    ("github", "GITHUB_MODELS_TOKEN", "https://models.inference.ai.azure.com/chat/completions", {
        "fast": "DeepSeek-R1",
        "deep": "DeepSeek-R1",
        "bulk": "DeepSeek-R1",
    }),
    ("together", "TOGETHER_API_KEY", "https://api.together.xyz/v1/chat/completions", {
        "fast": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "deep": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-Free",
        "bulk": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    }),
    # Grok 4.1 Fast (reasoning variant — xAI splits this model into
    # "-reasoning"/"-non-reasoning" IDs; reasoning fits VAPE's actual use
    # here, multi-step research/report synthesis, not speed-critical single
    # replies) — paid, primary model for the highest-stakes work (see the
    # module docstring + FRONTIER_ORDER below). Deliberately no "fast"/"bulk"
    # key so a bare tier="fast"/"bulk" ask() call never resolves to Grok even
    # if xai ever ends up early in some provider_order — only "deep"/
    # "frontier" callers reach it. Single key (see module docstring for why
    # there's no second key/rotation).
    # NOTE: xAI deprecated this model 2026-05-15; it retires 2026-08-15 —
    # will need to move to whatever supersedes it (grok-4.5 or similar)
    # before then.
    ("xai_1", "XAI_API_KEY_1", "https://api.x.ai/v1/chat/completions", {
        "deep": "grok-4-1-fast-reasoning", "frontier": "grok-4-1-fast-reasoning",
    }),
]

# Frontier-tier provider order — the FALLBACK chain used only once BOTH of
# VAPE's real primary reasoning routes (OCI-hosted Grok 4.3 and the Vertex-
# tuned candidate — see ask_oci_grok()'s own docstring) have already failed
# or aren't configured for this call. By explicit direction (2026-07-25):
# Groq -> Gemini -> Grok 4.1 Fast (direct xAI) -> the rest of the free chain
# (Cerebras/OpenRouter/GitHub Models/Together). Direct xAI is deliberately
# LAST here now, for two independent reasons: (1) it's the only paid entry
# in this whole chain (see PROVIDER_PRICING_USD_PER_M_TOKENS) — free-tier
# Groq/Gemini should be exhausted first; (2) its Live Search feature
# (search=True's whole reason to reach it specifically) was deprecated by
# xAI in favor of a new "Agent Tools API" this repo hasn't migrated to yet
# (confirmed real HTTP 410 in production, 2026-07) — until that migration
# happens, reaching xai_1 buys nothing search-wise, so there's no reason to
# rank it above the free tiers anymore. Providers without a distinct
# "frontier" model reuse their "deep" model (see ask()'s model-resolution
# fallback).
_FRONTIER_NAMES = ("groq", "gemini", "xai_1")
FRONTIER_ORDER = (
    [p for name in _FRONTIER_NAMES for p in PROVIDERS if p[0] == name]
    + [p for p in PROVIDERS if p[0] not in _FRONTIER_NAMES]
)


def candidate_provider_order():
    """Builds the opt-in provider order for VAPE's own fine-tuned candidate
    (see training/train_lora.py, training/eval_candidate.py,
    .github/workflows/train-vape-model.yml), read fresh from env on every
    call — never cached at import time, since the candidate is only ever
    stood up ad hoc on the training GPU box, not something running whenever
    this module loads.

    Configure via:
        VAPE_CANDIDATE_URL    OpenAI-compatible base URL, e.g.
                              http://<gpu-box>:8000/v1 (vLLM's own default
                              port/path). Unset means "not opted in" — this
                              function then returns the plain PROVIDERS chain
                              untouched, so callers can use it unconditionally
                              without a manual availability check.
        VAPE_CANDIDATE_MODEL  served model name (default: vape-candidate,
                              matching train-vape-model.yml's --served-model-name).

    Deliberately NOT part of the default PROVIDERS list ask() iterates by
    default — only reachable via an explicit provider_order=
    candidate_provider_order() (or ask_candidate() below), so no existing
    caller starts routing real traffic to an unevaluated candidate just
    because someone stood up a serving box.
    """
    url = os.getenv("VAPE_CANDIDATE_URL")
    if not url:
        return list(PROVIDERS)
    model = os.getenv("VAPE_CANDIDATE_MODEL", "vape-candidate")
    # "VAPE_CANDIDATE_URL" doubles as both the opt-in gate ask() checks via
    # os.getenv(env) and the value sent as the Bearer token in _call() —
    # local vLLM/Ollama serving doesn't enforce auth by default, so the
    # token's actual content is irrelevant; the URL just needs to be set to
    # opt in at all, matching every other provider's "env present == enabled"
    # convention without inventing a separate unused API-key var.
    candidate = ("vape_candidate", "VAPE_CANDIDATE_URL",
                 url.rstrip("/") + "/chat/completions",
                 {"fast": model, "deep": model, "bulk": model})
    return [candidate] + list(PROVIDERS)


def available():
    """List providers whose key is present in env."""
    return [name for name, env, _, _ in PROVIDERS if os.getenv(env)]


def _call(url, key, model, system, user, temperature, max_tokens, timeout, extra=None):
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra:
        body.update(extra)
    payload = json.dumps(body).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "VAPE-PrivateEye/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"], data.get("usage") or {}


def _log_usage(provider, model, tier, usage, fallback_from=None):
    """Best-effort per-call token usage log for later cost/routing self-
    optimization — a flat JSONL, not routed through skillforge/memory's
    curated finding/lesson/skill categories (this is high-frequency raw
    telemetry, not a narrative record). Never raises; silently a no-op if
    `usage` is empty (some providers omit it) or the file isn't writable.

    fallback_from: earlier providers that were tried and failed before this
    one succeeded (see ask()) — without this, a higher-priority provider
    (e.g. Grok) silently losing every call to its fallback (e.g. Groq) left
    zero trace anywhere once the fallback succeeded, since ask()'s per-call
    `errors` list was discarded the moment any provider returned."""
    if not usage:
        return
    try:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider": provider, "model": model, "tier": tier,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }
        if fallback_from:
            row["fallback_from"] = fallback_from
        with open(USAGE_LOG, "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass  # telemetry must never break a real LLM call


def _daily_cap_usd(provider):
    """Reads XAI_DAILY_SPEND_CAP_USD (or the hardcoded default) fresh on
    every call rather than at import time, so a workflow that sets it can
    override without needing this module reloaded."""
    try:
        return float(os.getenv("XAI_DAILY_SPEND_CAP_USD", DEFAULT_DAILY_SPEND_CAP_USD))
    except (TypeError, ValueError):
        return DEFAULT_DAILY_SPEND_CAP_USD


def _todays_paid_spend_usd(provider):
    """Sums today's (UTC calendar day) real-money cost for one provider from
    llm_usage.jsonl, using PROVIDER_PRICING_USD_PER_M_TOKENS. Returns 0.0 for
    a provider with no pricing entry (nothing to cap), a missing/unreadable
    log, or any malformed row — this must never raise or block a real call
    over a telemetry read failure, matching _log_usage's own guarantee."""
    pricing = PROVIDER_PRICING_USD_PER_M_TOKENS.get(provider)
    if not pricing:
        return 0.0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0.0
    try:
        with open(USAGE_LOG) as f:
            for line in f:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("provider") != provider or not str(row.get("ts", "")).startswith(today):
                    continue
                total += (row.get("prompt_tokens") or 0) / 1_000_000 * pricing["input"]
                total += (row.get("completion_tokens") or 0) / 1_000_000 * pricing["output"]
    except (OSError, IOError):
        return 0.0
    return total


def _already_alerted_spend_cap_today(provider):
    """Avoids writing a duplicate finding on every subsequent call once the
    cap is hit in a run (or across the many scheduled runs in one day) —
    scans findings.jsonl (a few hundred KB, cheap) for today's marker rather
    than maintaining separate state, matching this repo's JSONL-only memory
    convention. Any read failure is treated as "not yet alerted" so the
    alert path fails open (a possible duplicate finding) rather than never
    firing at all."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    marker = f"llm-daily-spend-cap:{provider}:{today}"
    try:
        with open(FINDINGS_LOG) as f:
            return any(marker in line for line in f)
    except (OSError, IOError):
        return False


def _log_spend_cap_finding(provider, spend, cap):
    """Real, dated, open finding in the same channel/schema self_improve.py
    already reads (see docs/SECURITY_PROTOCOL.md's coverage-gap findings) —
    this is a cost-hygiene event, not a security exploit, but it belongs in
    the same place so it's visible without needing a separate dashboard."""
    if _already_alerted_spend_cap_today(provider):
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = {
        "category": "finding",
        "title": f"LLM daily spend cap reached: {provider}",
        "content": (
            f"agents/llm.py: {provider}'s estimated spend today (UTC) is "
            f"${spend:.4f}, at or above the ${cap:.2f} daily cap "
            f"(XAI_DAILY_SPEND_CAP_USD). Calls for this provider are being "
            f"skipped for the rest of the day and falling through to the "
            f"free chain instead — check skillforge/memory/llm_usage.jsonl "
            f"for what drove the volume; this may be legitimate growth "
            f"(raise the cap) or a runaway loop (fix the caller)."
        ),
        "source": "agents/llm.py",
        "tags": ["cost-hygiene", "llm-spend", f"llm-daily-spend-cap:{provider}:{today}"],
        "confidence": 1.0,
        "severity": "MEDIUM",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        with open(FINDINGS_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # this is an alert about spend, not itself allowed to break a call


def ask(system, user, *, tier="fast", temperature=0.7, max_tokens=2048,
        timeout=45, retries_per_provider=2, provider_order=None, search=False):
    """
    Try each provider with a key, in order, until one succeeds.

    provider_order overrides the default PROVIDERS order — use FRONTIER_ORDER
    (or pass tier="frontier" via ask_frontier() below) to try Grok 4.1 Fast
    first. A provider with no model mapped for `tier` falls back to its own
    "deep" model, then "fast" — so providers that don't define a distinct
    "frontier" model still work, just at their normal tier.

    search=True opts into xAI's real "Live Search" (api.x.ai's own
    `search_parameters` field — the model autonomously searches the live web/
    X and cites sources, billed per-search on top of normal token cost).
    Real gap this closes: every LLM call in this repo was grounded only in
    whatever agents/intel_common.py::web_search_snippets() pre-fetched (one
    Tavily/Brave query, a handful of snippets) — nothing close to what Grok's
    own product surfaces when a human asks it directly, which is exactly the
    quality gap a 2026-07-20 side-by-side (this repo's DefiTuna threat
    analysis vs. a direct Grok query on the same incident) exposed: ours had
    "no public writeups found"; Grok's had the tx hash, attacker addresses,
    and a full CertiK-sourced attack-flow writeup. Only xAI's own API
    supports this field — silently ignored (no-op) for every other provider,
    so this is safe to pass on any ask()/ask_frontier() call regardless of
    which provider actually ends up serving it. Only takes effect if/when
    the provider loop below actually reaches "xai_1"; a dead OCI/Vertex layer
    ahead of it in a caller's real chain (see ask_oci_grok's docstring)
    doesn't get search grounding — a caller that specifically wants it needs
    its real request to reach the frontier chain, e.g. via provider_order=
    FRONTIER_ORDER or by relying on OCI/Vertex being unconfigured.
    """
    errors = []
    for name, env, url, models in (provider_order or PROVIDERS):
        key = os.getenv(env)
        if not key:
            continue
        # xAI's Live Search is a real, billed-per-search feature of api.x.ai
        # itself — not part of the generic OpenAI-compatible chat-completions
        # shape every other provider here implements, so it's gated strictly
        # to the one provider whose endpoint actually understands it.
        extra = {"search_parameters": {"mode": "auto", "return_citations": True}} \
            if (search and name == "xai_1") else None
        if name in PROVIDER_PRICING_USD_PER_M_TOKENS:
            cap = _daily_cap_usd(name)
            spend = _todays_paid_spend_usd(name)
            if spend >= cap:
                detail = f"{name}:daily-spend-cap-reached(${spend:.4f}>=${cap:.2f})"
                print(f"[llm] {detail}", file=sys.stderr)
                _log_spend_cap_finding(name, spend, cap)
                errors.append(detail)
                continue
        model = models.get(tier) or models.get("deep") or models.get("fast")
        for attempt in range(retries_per_provider):
            try:
                txt, usage = _call(url, key, model, system, user, temperature, max_tokens, timeout, extra=extra)
                _log_usage(name, model, tier, usage, fallback_from=errors or None)
                return txt, name
            except urllib.error.HTTPError as e:
                code = e.code
                try:
                    body = e.read().decode(errors="replace")[:200]
                except Exception:
                    body = ""
                detail = f"{name}:HTTP{code}" + (f" {body}" if body else "")
                print(f"[llm] {detail}", file=sys.stderr)
                if code == 429:  # rate limited — brief backoff then next provider
                    time.sleep(2)
                    errors.append(detail)
                    break
                errors.append(detail)
                if attempt + 1 >= retries_per_provider:
                    break
                time.sleep(1.5)
            except Exception as e:
                detail = f"{name}:{type(e).__name__}:{e}"
                print(f"[llm] {detail}", file=sys.stderr)
                errors.append(detail)
                break
    raise RuntimeError("all LLM providers failed/absent: " + ", ".join(errors) if errors
                       else "no LLM provider key set (need one of: "
                       + ", ".join(env for _, env, _, _ in (provider_order or PROVIDERS)) + ")")


def describe_unavailable(exc):
    """Safe, non-identifying summary of an ask()/ask_oci_grok()-family total-
    failure exception, for embedding in a CUSTOMER-FACING report (unlike the
    raw exception, which is fine in server-side stderr logs). The raw message
    is internal diagnostic detail this repo's own de-branding discipline
    already excludes from reports elsewhere (see agents/deep_dive_audit.py's
    Methodology section): it names internal provider identifiers (xai_1,
    groq, gemini, cerebras, oci_grok...) and, worse, can embed a provider's
    raw HTTP error body verbatim — which has been observed to include that
    provider's own internal account/org identifiers, not just a generic error
    string. A paying buyer's report should say AI reasoning was unavailable
    and why, in general terms, never repeat any of that."""
    msg = str(exc)
    if "no LLM provider key set" in msg:
        return "no AI reasoning provider configured this run"
    return "all AI reasoning providers were rate-limited or unreachable this cycle"


def ask_frontier(system, user, **kw):
    """ask() pinned to the frontier tier + FRONTIER_ORDER: free-tier Groq
    first, then Gemini, then direct paid xAI Grok 4.1 Fast as the last
    resort, then the rest of the chain — see FRONTIER_ORDER's own comment
    for why xAI moved to last. Most production report/investigation call
    sites should prefer ask_oci_grok_frontier() instead, which tries OCI's
    hosted Grok 4.3 (VAPE's real primary reasoning route) before ever
    reaching this fallback chain at all."""
    kw.setdefault("tier", "frontier")
    kw.setdefault("provider_order", FRONTIER_ORDER)
    return ask(system, user, **kw)


def ask_candidate(system, user, **kw):
    """ask() pinned to VAPE's own fine-tuned candidate first (if
    VAPE_CANDIDATE_URL is set — see candidate_provider_order() above),
    falling back through the normal free chain if it errors or isn't
    configured. Call this ONLY for explicit comparison/evaluation work
    (training/eval_candidate.py, manual smoke tests) — no production report/
    investigation/sweep code path should call this by default; routing real
    traffic to the candidate is a later, evaluated decision, not this
    function's job to make."""
    kw.setdefault("tier", "fast")
    kw.setdefault("provider_order", candidate_provider_order())
    return ask(system, user, **kw)


VERTEX_TUNED_DEFAULT_PROJECT_NUMBER = "87858016172"
VERTEX_TUNED_DEFAULT_LOCATION = "us"
VERTEX_TUNED_DEFAULT_ENDPOINT_ID = "7011119457397374976"


REPO_DIGEST_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "skillforge", "memory", "repo_digest.md")
_repo_digest_cache = None


def _load_repo_digest():
    """Real, regenerable grounding doc (scripts/build_repo_digest.py) —
    architecture docs verbatim + every module's own real docstring + a real
    directory tree. Deliberately only prepended for the Vertex candidate
    (below), not the frontier ask()/ask_frontier() chain — this is scoped
    grounding for the one model that otherwise starts every stateless call
    with zero repo awareness, not a change to every LLM call site's prompt.
    Cached per-process (this file doesn't change mid-run); a missing file is
    a silent empty string, never a hard failure, since a stale/absent digest
    should degrade to "no extra context" rather than break the whole call."""
    global _repo_digest_cache
    if _repo_digest_cache is None:
        try:
            with open(REPO_DIGEST_PATH, encoding="utf-8") as f:
                _repo_digest_cache = f.read()
        except OSError:
            _repo_digest_cache = ""
    return _repo_digest_cache


def _call_vertex_tuned(system, user, temperature, max_tokens, timeout):
    """Vertex AI's generateContent isn't OpenAI-compatible (Bearer OAuth
    access token rather than a static API key; contents/systemInstruction
    request shape; candidates[0].content.parts[0].text response shape) —
    can't reuse _call(), so this is its own small request/response pair
    instead of forcing a mismatched shape through the generic path.

    Auth is a short-lived OAuth access token minted per workflow run via
    Workload Identity Federation (google-github-actions/auth with
    token_format: access_token) — never a stored long-lived key, since this
    Google Cloud org enforces iam.disableServiceAccountKeyCreation."""
    project = os.getenv("VAPE_VERTEX_PROJECT_NUMBER", VERTEX_TUNED_DEFAULT_PROJECT_NUMBER)
    location = os.getenv("VAPE_VERTEX_LOCATION", VERTEX_TUNED_DEFAULT_LOCATION)
    endpoint_id = os.getenv("VAPE_VERTEX_ENDPOINT_ID", VERTEX_TUNED_DEFAULT_ENDPOINT_ID)
    token = os.environ["VAPE_VERTEX_ACCESS_TOKEN"]
    # Confirmed against a real 400 from Google ("Invalid hostname:
    # us-aiplatform.googleapis.com"): the classic "{location}-aiplatform.
    # googleapis.com" host only exists for actual single regions (e.g.
    # us-central1). Vertex's two multi-region values (us/eu — what a tuned
    # model's own location field shows, distinct from the region the tuning
    # JOB ran in) are served from a different host entirely.
    if location in ("us", "eu"):
        host = f"aiplatform.{location}.rep.googleapis.com"
    else:
        host = f"{location}-aiplatform.googleapis.com"
    url = (f"https://{host}/v1/projects/{project}"
           f"/locations/{location}/endpoints/{endpoint_id}:generateContent")
    digest = _load_repo_digest()
    system_text = (
        f"{digest}\n\n---\n\nEverything above this line is real, generated grounding "
        f"context about VAPE's own repository (scripts/build_repo_digest.py) — reference "
        f"it for architecture/module awareness, but the instructions below are what this "
        f"specific call actually asks you to do.\n\n{system}"
    ) if digest else system
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "systemInstruction": {"parts": [{"text": system_text}]},
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "VAPE-PrivateEye/1.0",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    usage_meta = data.get("usageMetadata") or {}
    usage = {
        "prompt_tokens": usage_meta.get("promptTokenCount"),
        "completion_tokens": usage_meta.get("candidatesTokenCount"),
        "total_tokens": usage_meta.get("totalTokenCount"),
    } if usage_meta else {}
    return text, usage


def ask_vertex_candidate(system, user, *, temperature=0.7, max_tokens=2048, timeout=45,
                          tier="fast", provider_order=None, search=False):
    """Calls VAPE's Vertex AI supervised-tuned Gemini model directly (see
    the Vertex AI Tuning console job that produced it) if
    VAPE_VERTEX_ACCESS_TOKEN is set this run, falling back to ask() if it's
    unset or the call errors — same "opt-in, never silently primary"
    posture as ask_candidate()'s self-hosted-GPU path above; this is a
    second, independently-hosted candidate, not a replacement for it.

    tier/provider_order control ONLY the fallback ask() call (the Vertex
    call itself has no notion of tiers) — a real production call site (e.g.
    skillforge/synthesize.py's narrative distillation, previously a bare
    ask(tier="deep", provider_order=FRONTIER_ORDER) call) should pass its own
    normal tier/provider_order here, so a run where the candidate isn't
    configured degrades to EXACTLY its old behavior rather than silently
    dropping to the default fast/free chain. Safe to call from production
    code: the candidate path only activates when VAPE_VERTEX_ACCESS_TOKEN is
    actually set in that run's environment, which is a separate, deliberate
    rollout decision (e.g. adding the WIF auth step to a workflow), not
    something this function does on its own.

    search=True skips this direct Vertex call too and goes straight to
    ask() — Vertex's generateContent request built in _call_vertex_tuned()
    has no search-grounding equivalent wired here, so (same reasoning as
    ask_oci_grok() above) a request for live search has to route around
    it to reach a provider that actually has it."""
    if os.getenv("VAPE_VERTEX_ACCESS_TOKEN") and not search:
        try:
            text, usage = _call_vertex_tuned(system, user, temperature, max_tokens, timeout)
            _log_usage("vertex_tuned", "vape-gemini-tuned", "fast", usage)
            return text, "vertex_tuned"
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode(errors="replace")[:500]
            except Exception:
                body = ""
            print(f"[llm] vertex_tuned:HTTP{e.code}" + (f" {body}" if body else ""), file=sys.stderr)
        except Exception as e:
            print(f"[llm] vertex_tuned:{type(e).__name__}:{e}", file=sys.stderr)
    return ask(system, user, tier=tier, temperature=temperature, max_tokens=max_tokens,
               timeout=timeout, provider_order=provider_order, search=search)


GEMINI_IMAGE_DEFAULT_MODEL = "gemini-3.1-flash-lite-image"


def ask_gemini_image(prompt, *, aspect_ratio="16:9", timeout=60):
    """Google's native Gemini image-generation model ("Nano Banana"),
    called against the Gemini Developer API (generativelanguage.googleapis.
    com) — VAPE's real image-generation route (explicit direction,
    2026-07-28, replacing the xAI-based generate_image() that was built and
    then fully removed the day before over an unrelated xAI credit
    constraint — image generation is Google's own infrastructure, not a
    third-party paid API, so that constraint doesn't apply here).

    NOT Vertex AI, despite every other Google-model call in this file
    (_call_vertex_tuned() above) going through Vertex's publisher-model
    generateContent endpoint. Confirmed by a real HTTP 404 from the first
    live dispatch that tried exactly that path: "Publisher model
    projects/.../publishers/google/models/gemini-3.1-flash-lite-image was
    not found or your project does not have access to it." This model
    (Nano Banana 2 Lite) launched on the Gemini API surface for developers
    and isn't mirrored into Vertex's Model Garden publisher-model path (its
    own docs page is literally titled "Gemini 3.1 Flash Lite Image |
    Gemini API | Google AI for Developers", not a Vertex AI doc). Switching
    to Vertex-hosted auth does NOT fix that — the model genuinely doesn't
    exist on that surface regardless of auth mechanism. This still reaches
    generativelanguage.googleapis.com directly.

    Auth: prefers the same WIF-minted ADC access token already used by
    _call_vertex_tuned() (VAPE_VERTEX_ACCESS_TOKEN) when set, via OAuth
    Bearer + x-goog-user-project — Google's own documented alternative to
    an API key for this exact host (ai.google.dev/gemini-api/docs/oauth).
    Real gap this closes: a GEMINI_API_KEY minted before its GCP project's
    billing was linked stays cached on the free tier's limit:0 image quota
    even after billing is linked after the fact (confirmed live,
    2026-08-01 — HTTP 429 "resource-exhausted... limit: 0" on every
    dispatch); an OAuth token tied directly to the (already billing-linked)
    project's live IAM identity isn't subject to that per-key snapshot.
    Falls back to GEMINI_API_KEY's x-goog-api-key header (the original,
    still-supported auth path) when no token is set, so a workflow without
    the WIF auth step wired in still behaves exactly as before.

    Returns raw image bytes (already base64-decoded) on success, or None on
    any failure/misconfiguration (including neither auth method configured)
    — callers must degrade to a real scraped photo, then VAPE's brand mark,
    exactly like every other best-effort image tier in this repo. Never
    raises."""
    token = os.getenv("VAPE_VERTEX_ACCESS_TOKEN")
    key = os.getenv("GEMINI_API_KEY")
    if not token and not key:
        return None
    model = os.getenv("VAPE_GEMINI_IMAGE_MODEL", GEMINI_IMAGE_DEFAULT_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": aspect_ratio},
        },
    }).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "VAPE-PrivateEye/1.0"}
    if token:
        project = (os.getenv("VAPE_VERTEX_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
                   or os.getenv("CLOUDSDK_CORE_PROJECT")
                   or os.getenv("VAPE_VERTEX_PROJECT_NUMBER", VERTEX_TUNED_DEFAULT_PROJECT_NUMBER))
        headers["Authorization"] = f"Bearer {token}"
        headers["x-goog-user-project"] = project
    else:
        headers["x-goog-api-key"] = key
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode(errors="replace")[:500]
        except Exception:
            body = ""
        print(f"[llm] gemini_image:HTTP{e.code}" + (f" {body}" if body else ""), file=sys.stderr)
        return None
    except Exception as e:
        print(f"[llm] gemini_image:{type(e).__name__}:{e}", file=sys.stderr)
        return None
    try:
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
    except Exception as e:
        print(f"[llm] gemini_image:parse:{type(e).__name__}:{e}", file=sys.stderr)
    return None


# --- xAI Grok Image (fallback for the AI-image tier) ---
# Reinstated 2026-07-28 as ask_gemini_image()'s fallback, not primary --
# Gemini's image model is Google Cloud's own infrastructure (VAPE's real
# route once billing is enabled on that project; see ask_gemini_image()'s
# docstring for the free-tier quota wall a live dispatch hit), while this
# is a separate, billed-per-image xAI product on the same XAI_API_KEY_1 key
# used elsewhere in this file for text -- briefly removed entirely
# (2026-07-27) over an xAI credit-budget concern, explicitly reinstated by
# direction (2026-07-28) as a working fallback while that budget concern is
# accepted as a real, known tradeoff. Same daily image-count cap design as
# before removal, since it's billed per-image, not per-token, unlike every
# other xAI use in this file.
IMAGE_USAGE_PATH = os.path.join(MEMORY_DIR, "xai_image_usage.json")
DEFAULT_IMAGE_DAILY_CAP = 15  # ~$1.05/day at $0.07/image -- comfortable headroom over the ~8 stories/day news-intel cadence this exists for
XAI_IMAGE_MODEL = "grok-2-image-1212"


def _xai_image_daily_cap():
    try:
        return int(os.getenv("XAI_IMAGE_DAILY_CAP", DEFAULT_IMAGE_DAILY_CAP))
    except (TypeError, ValueError):
        return DEFAULT_IMAGE_DAILY_CAP


def _xai_image_quota_ok():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        with open(IMAGE_USAGE_PATH) as f:
            usage = json.load(f)
    except Exception:
        usage = {}
    return usage.get("date") != today or usage.get("count", 0) < _xai_image_daily_cap()


def _record_xai_image_usage():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        with open(IMAGE_USAGE_PATH) as f:
            usage = json.load(f)
    except Exception:
        usage = {}
    if usage.get("date") != today:
        usage = {"date": today, "count": 0}
    usage["count"] = usage.get("count", 0) + 1
    try:
        os.makedirs(os.path.dirname(IMAGE_USAGE_PATH), exist_ok=True)
        with open(IMAGE_USAGE_PATH, "w") as f:
            json.dump(usage, f)
    except Exception:
        pass


def ask_xai_image(prompt, timeout=45):
    """Real text-to-image call against xAI's Grok Image model. Returns a
    real image URL on success, or None (never raises) if XAI_API_KEY_1
    isn't set, today's daily cap is already hit, or the call errors for any
    reason — callers must degrade to the brand-mark logo fallback, never a
    broken image or a crash. The returned URL is a plain http(s) string,
    not bytes — pass it straight to news_common.brand_image() exactly like
    already-decoded bytes; no separate fetch step needed here."""
    key = os.getenv("XAI_API_KEY_1")
    if not key:
        return None
    if not _xai_image_quota_ok():
        print(f"[llm] xAI image daily cap ({_xai_image_daily_cap()}) reached — skipping generation")
        return None
    body = json.dumps({
        "model": XAI_IMAGE_MODEL,
        "prompt": prompt[:1000],
        "n": 1,
        "response_format": "url",
    }).encode()
    req = urllib.request.Request(
        "https://api.x.ai/v1/images/generations",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        item = data["data"][0]
        url = item.get("url")
        if not url:
            return None
        _record_xai_image_usage()
        return url
    except Exception as e:
        print(f"[llm] xai_image:{type(e).__name__}:{e}", file=sys.stderr)
        return None


def ask_safe(system, user, **kw):
    """Never raises — returns (text_or_error_string, provider_or_None)."""
    try:
        return ask(system, user, **kw)
    except Exception as e:
        return (f"[llm unavailable: {e}]", None)


def ask_vertex_candidate_safe(system, user, **kw):
    """ask_vertex_candidate() with ask_safe()'s same never-raise guarantee —
    for call sites (the intel sweeps' narrative synthesis) that already
    depend on ask_safe() never raising and are being extended to try the
    Vertex candidate first, opt-in via VAPE_VERTEX_ACCESS_TOKEN, falling
    back to their normal tier/provider_order otherwise."""
    try:
        return ask_vertex_candidate(system, user, **kw)
    except Exception as e:
        return (f"[llm unavailable: {e}]", None)


# --- OCI Generative AI (xAI Grok 4.3, hosted on Oracle Cloud) ---
# A third, independently-hosted candidate — Oracle Cloud's own hosted xAI
# Grok 4.3 (1M-token context, reasoning-focused model; see
# https://docs.oracle.com/en-us/iaas/Content/generative-ai/xai-grok-4-3.htm),
# reached via OCI's OpenAI-compatible endpoint. That endpoint takes a plain
# Bearer "Generative AI API key" — a distinct secret minted in the OCI
# console's Generative AI service, NOT the IAM RSA key pair (user/tenancy/
# fingerprint/private key) used for general OCI SDK/CLI request signing — so
# no request-signing code or oci SDK dependency is needed here, same as
# every free-tier provider in PROVIDERS above.
#
# By explicit direction (2026-07-19), OCI Grok is now the PRIMARY route for
# every call site that used to try VAPE's Vertex-tuned candidate first
# (skillforge/synthesize.py, the 5 intel sweeps, investigate.py's expert
# assessment) — ask_oci_grok() below falls back to ask_vertex_candidate()
# (not directly to ask()), so the real chain everywhere is now:
#     OCI Grok 4.3  ->  Vertex-tuned Gemini  ->  FRONTIER_ORDER (xai_1/groq/
#                                                 gemini/rest of the free chain)
# Nothing is discarded — Vertex stays as a real middle layer wherever its own
# gating (VAPE_VERTEX_ACCESS_TOKEN) is already configured; it just no longer
# goes first. Gated on OCI_GENAI_API_KEY, not part of PROVIDERS/FRONTIER_ORDER
# itself — still an opt-in-only candidate function, not a PROVIDERS entry.
OCI_GROK_DEFAULT_REGION = "us-ashburn-1"
OCI_GROK_DEFAULT_MODEL = "xai.grok-4.3"

# Deliberately its own default, not DEFAULT_DAILY_SPEND_CAP_USD ($3, xai_1's
# cap) — by explicit direction (2026-07-19), now that OCI Grok is the primary
# reasoning route for most of VAPE's real call sites (far higher volume than
# xai_1 ever saw directly), its cap starts higher rather than inheriting a
# limit sized for a much narrower role.
DEFAULT_OCI_GROK_DAILY_SPEND_CAP_USD = 10.00


def _oci_grok_daily_cap_usd():
    try:
        return float(os.getenv("OCI_GROK_DAILY_SPEND_CAP_USD", DEFAULT_OCI_GROK_DAILY_SPEND_CAP_USD))
    except (TypeError, ValueError):
        return DEFAULT_OCI_GROK_DAILY_SPEND_CAP_USD

def _call_oci_grok(system, user, temperature, max_tokens, timeout):
    """OCI's OpenAI-compatible Generative AI endpoint uses the exact same
    request/response shape as _call() above (model/messages/temperature/
    max_tokens in, choices[0].message.content out) — the one real difference
    is an optional CompartmentId header some OCI auth modes require, which
    _call() has no parameter for. Kept as its own small function rather than
    adding an OCI-specific header kwarg to every other provider's call path."""
    region = os.getenv("OCI_REGION", OCI_GROK_DEFAULT_REGION)
    model = os.getenv("OCI_GROK_MODEL", OCI_GROK_DEFAULT_MODEL)
    key = os.environ["OCI_GENAI_API_KEY"]
    url = f"https://inference.generativeai.{region}.oci.oraclecloud.com/20231130/actions/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "VAPE-PrivateEye/1.0",
        "Accept": "application/json",
    }
    compartment_id = os.getenv("OCI_COMPARTMENT_OCID")
    if compartment_id:
        headers["CompartmentId"] = compartment_id
    req = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"], data.get("usage") or {}


def ask_oci_grok(system, user, *, temperature=0.7, max_tokens=2048, timeout=45,
                  tier="fast", provider_order=None, search=False):
    """Calls OCI-hosted Grok 4.3 directly if OCI_GENAI_API_KEY is set this
    run, falling back to ask_vertex_candidate() otherwise/on error/over the
    daily spend cap — VAPE's Vertex-tuned candidate, which itself falls back
    to the normal tier/provider_order chain if IT isn't configured either.
    This is now the primary "best real reasoning" entrypoint for VAPE's
    production call sites (see the module docstring + the comment above
    OCI_GROK_DEFAULT_REGION): OCI Grok -> Vertex-tuned Gemini -> frontier
    chain, each layer degrading gracefully to the next.

    This path runs outside ask()'s own provider loop (it's not in
    PROVIDERS), so it needs its own daily-spend-cap guard
    (OCI_GROK_DAILY_SPEND_CAP_USD, default $10 — see
    DEFAULT_OCI_GROK_DAILY_SPEND_CAP_USD) rather than inheriting the one
    built into that loop.

    tier/provider_order control ONLY the eventual ask() call at the bottom
    of the chain (via ask_vertex_candidate()'s own identical contract) —
    pass the caller's own normal tier/provider_order so a run where neither
    OCI nor Vertex is configured degrades to EXACTLY its prior behavior.

    search=True skips straight past OCI Grok's own direct call to
    ask_vertex_candidate() (which itself does the same for Vertex-tuned
    Gemini, see its docstring) rather than trying it first: confirmed real
    bug this closes — OCI_GENAI_API_KEY is configured in every real
    production workflow in this repo (OCI Grok is VAPE's primary reasoning
    route by explicit 2026-07-19 direction), so ask_oci_grok() was winning
    the race and returning at the OCI branch below on every single call,
    every caller's search=True never actually reaching ask()'s xai_1
    provider at all — search_parameters is an xAI Live Search feature, and
    OCI's OpenAI-compatible endpoint has no equivalent, so a request for
    live search has to route around a provider that can't provide it. A
    caller not asking for search (the default) is completely unaffected —
    OCI Grok is still tried first exactly as before."""
    if os.getenv("OCI_GENAI_API_KEY") and not search:
        cap = _oci_grok_daily_cap_usd()
        spend = _todays_paid_spend_usd("oci_grok")
        if spend >= cap:
            detail = f"oci_grok:daily-spend-cap-reached(${spend:.4f}>=${cap:.2f})"
            print(f"[llm] {detail}", file=sys.stderr)
            _log_spend_cap_finding("oci_grok", spend, cap)
        else:
            try:
                text, usage = _call_oci_grok(system, user, temperature, max_tokens, timeout)
                _log_usage("oci_grok", os.getenv("OCI_GROK_MODEL", OCI_GROK_DEFAULT_MODEL), tier, usage)
                return text, "oci_grok"
            except urllib.error.HTTPError as e:
                try:
                    body = e.read().decode(errors="replace")[:500]
                except Exception:
                    body = ""
                print(f"[llm] oci_grok:HTTP{e.code}" + (f" {body}" if body else ""), file=sys.stderr)
            except Exception as e:
                print(f"[llm] oci_grok:{type(e).__name__}:{e}", file=sys.stderr)
    return ask_vertex_candidate(system, user, tier=tier, temperature=temperature, max_tokens=max_tokens,
                                 timeout=timeout, provider_order=provider_order, search=search)

def ask_oci_grok_safe(system, user, **kw):
    """ask_oci_grok() with ask_safe()'s same never-raise guarantee."""
    try:
        return ask_oci_grok(system, user, **kw)
    except Exception as e:
        return (f"[llm unavailable: {e}]", None)


def ask_oci_grok_frontier(system, user, **kw):
    """ask_oci_grok() pinned to the frontier tier + FRONTIER_ORDER fallback —
    the OCI-Grok-primary equivalent of ask_frontier() above, for call sites
    (agents/deep_dive_audit.py's $1 bounty audit, acp_fulfill.py's
    dossier_check quick review) that want that same 'no local override'
    convenience but with OCI Grok 4.3 as the actual primary model. Raises on
    total failure exactly like ask_frontier() — callers already wrap their
    own try/except, matching the existing contract they were built against."""
    kw.setdefault("tier", "frontier")
    kw.setdefault("provider_order", FRONTIER_ORDER)
    return ask_oci_grok(system, user, **kw)


if __name__ == "__main__":
    print("providers with keys:", available() or "(none)")
    if available():
        txt, prov = ask_safe("You are a test.", "Reply with the single word: OK", tier="fast", max_tokens=10)
        print(f"[{prov}] {txt!r}")
    else:
        print("set GROQ_API_KEY (or CEREBRAS/OPENROUTER/GEMINI/GITHUB_MODELS/TOGETHER/XAI_API_KEY_1) "
              "to test a live call")
        sys.exit(0)
