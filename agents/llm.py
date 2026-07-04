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

Tiers pick a model per task:
    fast      -> small/quick (hourly reports)
    deep      -> larger reasoning (daily synthesis, audits)
    bulk      -> high daily volume (harvest passes)
    frontier  -> real premium model (gemini-2.5-pro) for the highest-stakes work (the
                 24h deep-dive bounty audit). Falls back through the rest of the chain —
                 Groq's "deep" model included — when the frontier provider has no key or
                 errors, via FRONTIER_ORDER/ask_frontier(). Providers with no "frontier"
                 entry transparently reuse their "deep" model instead (see the
                 model-resolution fallback in ask()).

Backwards compatible: run.py can keep calling its own ask_llm; this is opt-in.
"""
import json
import os
import time
import urllib.request
import urllib.error

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
]

# Frontier-tier provider order: try the real premium model (Gemini 2.5 Pro) first, then
# fall through the normal chain — Groq's "deep" model is the first real fallback,
# exactly matching "frontier model, Groq as the fallback for now." Providers without a
# distinct "frontier" model reuse their "deep" model (see ask()'s model-resolution
# fallback), so this list is just PROVIDERS with gemini moved to the front.
FRONTIER_ORDER = (
    [p for p in PROVIDERS if p[0] == "gemini"]
    + [p for p in PROVIDERS if p[0] != "gemini"]
)


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
    return data["choices"][0]["message"]["content"]


def ask(system, user, *, tier="fast", temperature=0.7, max_tokens=2048,
        timeout=45, retries_per_provider=2, provider_order=None):
    """
    Try each provider with a key, in order, until one succeeds.

    provider_order overrides the default PROVIDERS order — use FRONTIER_ORDER
    (or pass tier="frontier" via ask_frontier() below) to try GitHub Models'
    real openai/gpt-4o first. A provider with no model mapped for `tier`
    falls back to its own "deep" model, then "fast" — so providers that don't
    define a distinct "frontier" model still work, just at their normal tier.

    Returns (text, provider_name). Raises RuntimeError only if ALL fail/absent.
    """
    errors = []
    for name, env, url, models in (provider_order or PROVIDERS):
        key = os.getenv(env)
        if not key:
            continue
        model = models.get(tier) or models.get("deep") or models.get("fast")
        for attempt in range(retries_per_provider):
            try:
                txt = _call(url, key, model, system, user, temperature, max_tokens, timeout)
                return txt, name
            except urllib.error.HTTPError as e:
                code = e.code
                if code == 429:  # rate limited — brief backoff then next provider
                    time.sleep(2)
                    errors.append(f"{name}:429")
                    break
                errors.append(f"{name}:HTTP{code}")
                if attempt + 1 >= retries_per_provider:
                    break
                time.sleep(1.5)
            except Exception as e:
                errors.append(f"{name}:{type(e).__name__}")
                break
    raise RuntimeError("all LLM providers failed/absent: " + ", ".join(errors) if errors
                       else "no LLM provider key set (need one of: "
                       + ", ".join(env for _, env, _, _ in (provider_order or PROVIDERS)) + ")")


def ask_frontier(system, user, **kw):
    """ask() pinned to the frontier tier + FRONTIER_ORDER: real openai/gpt-4o via
    GitHub Models first, Groq (and the rest of the chain) as the fallback."""
    kw.setdefault("tier", "frontier")
    kw.setdefault("provider_order", FRONTIER_ORDER)
    return ask(system, user, **kw)


def ask_safe(system, user, **kw):
    """Never raises — returns (text_or_error_string, provider_or_None)."""
    try:
        return ask(system, user, **kw)
    except Exception as e:
        return (f"[llm unavailable: {e}]", None)


if __name__ == "__main__":
    import sys
    print("providers with keys:", available() or "(none)")
    if available():
        txt, prov = ask_safe("You are a test.", "Reply with the single word: OK", tier="fast", max_tokens=10)
        print(f"[{prov}] {txt!r}")
    else:
        print("set GROQ_API_KEY (or CEREBRAS/OPENROUTER/GITHUB_MODELS/TOGETHER) to test a live call")
        sys.exit(0)
