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
                                    an occasional premium job like the 24h deep-dive
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
    xai         XAI_API_KEY_1       Grok 4.1 Fast — paid, primary model for VAPE's
                                    highest-stakes work (see FRONTIER_ORDER below).
                                    Not in the default PROVIDERS chain a bare ask()
                                    call uses — only reachable via provider_order=
                                    FRONTIER_ORDER / ask_frontier(), so ordinary
                                    fast/bulk-tier calls never touch it and stay on
                                    the free chain, matching the operating policy:
                                    Grok for reports/investigations/the $50 x402
                                    audit/intel/Builder/SKILLFORGE; Groq/Gemini for
                                    everything else. A single key, not a rotated
                                    pair — a second key (XAI_API_KEY_2) was tried
                                    briefly but its xAI team had no credits/license,
                                    so it's not worth the added complexity of a
                                    two-key fallthrough for a key that can't serve
                                    real traffic anyway; revisit if a genuinely
                                    funded second key is ever needed.
                                    OpenAI-compatible endpoint (api.x.ai/v1), same
                                    _call() as everything else.

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

Tiers pick a model per task:
    fast      -> small/quick (hourly reports)
    deep      -> larger reasoning (daily synthesis, audits)
    bulk      -> high daily volume (harvest passes)
    frontier  -> the real premium model for the highest-stakes work (the 24h deep-dive
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
        "deep": "llama-3.3-70b",
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

# Frontier-tier provider order — VAPE's "smart LLM" chain for the highest-stakes
# work: Grok 4.1 Fast -> Groq -> Gemini -> the rest of the free chain
# (Cerebras/OpenRouter/GitHub Models/Together — VAPE's own "local/custom" free
# fallback tier; there's no separate self-hosted model wired in yet, so this
# honestly IS that tier today). Providers without a distinct "frontier" model
# reuse their "deep" model (see ask()'s model-resolution fallback).
_FRONTIER_NAMES = ("xai_1", "groq", "gemini")
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


def _call(url, key, model, system, user, temperature, max_tokens, timeout):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
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
        timeout=45, retries_per_provider=2, provider_order=None):
    """
    Try each provider with a key, in order, until one succeeds.

    provider_order overrides the default PROVIDERS order — use FRONTIER_ORDER
    (or pass tier="frontier" via ask_frontier() below) to try Grok 4.1 Fast
    first. A provider with no model mapped for `tier` falls back to its own
    "deep" model, then "fast" — so providers that don't define a distinct
    "frontier" model still work, just at their normal tier.

    Returns (text, provider_name). Raises RuntimeError only if ALL fail/absent.
    """
    errors = []
    for name, env, url, models in (provider_order or PROVIDERS):
        key = os.getenv(env)
        if not key:
            continue
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
                txt, usage = _call(url, key, model, system, user, temperature, max_tokens, timeout)
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


def ask_frontier(system, user, **kw):
    """ask() pinned to the frontier tier + FRONTIER_ORDER: Grok 4.1 Fast
    first (key 1, then key 2), Groq/Gemini/the rest of the chain as fallback."""
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
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "systemInstruction": {"parts": [{"text": system}]},
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


def ask_vertex_candidate(system, user, *, temperature=0.7, max_tokens=2048, timeout=45):
    """Calls VAPE's Vertex AI supervised-tuned Gemini model directly (see
    the Vertex AI Tuning console job that produced it) if
    VAPE_VERTEX_ACCESS_TOKEN is set this run, falling back to the normal
    free chain (ask()) if it's unset or the call errors — same "opt-in,
    never silently primary" posture as ask_candidate()'s self-hosted-GPU
    path above; this is a second, independently-hosted candidate, not a
    replacement for it. Call this ONLY for explicit comparison/evaluation
    work, not production report/investigation/sweep code paths."""
    if os.getenv("VAPE_VERTEX_ACCESS_TOKEN"):
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
    return ask(system, user, tier="fast", temperature=temperature, max_tokens=max_tokens, timeout=timeout)


def ask_safe(system, user, **kw):
    """Never raises — returns (text_or_error_string, provider_or_None)."""
    try:
        return ask(system, user, **kw)
    except Exception as e:
        return (f"[llm unavailable: {e}]", None)


if __name__ == "__main__":
    print("providers with keys:", available() or "(none)")
    if available():
        txt, prov = ask_safe("You are a test.", "Reply with the single word: OK", tier="fast", max_tokens=10)
        print(f"[{prov}] {txt!r}")
    else:
        print("set GROQ_API_KEY (or CEREBRAS/OPENROUTER/GEMINI/GITHUB_MODELS/TOGETHER/XAI_API_KEY_1) "
              "to test a live call")
        sys.exit(0)
