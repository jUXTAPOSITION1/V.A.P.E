/**
 * Frontier-LLM client for the Worker/x402 side — TypeScript port of
 * agents/llm.py's ask_frontier(), scoped down to the two providers this
 * repo's own docs already frame as the real chain ("a frontier-tier model
 * (Gemini 2.5 Pro, Groq fallback)" — see worker/README.md,
 * agents/deep_dive_audit.py). The Python version tries five OpenAI-
 * compatible providers; porting all five here would need Worker secrets for
 * providers nothing on the x402 side has ever asked for. Gemini + Groq
 * covers the documented "real chain" without inventing new scope.
 *
 * Both providers speak the same OpenAI-compatible /chat/completions shape,
 * so one _call() covers both — identical pattern to agents/llm.py's _call().
 */
export interface LlmEnv {
  GEMINI_API_KEY?: string;
  GROQ_API_KEY?: string;
}

interface Provider {
  name: string;
  envKey: keyof LlmEnv;
  url: string;
  model: string;
}

const PROVIDERS: Provider[] = [
  {
    name: "gemini",
    envKey: "GEMINI_API_KEY",
    url: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    model: "gemini-2.5-pro",
  },
  {
    name: "groq",
    envKey: "GROQ_API_KEY",
    url: "https://api.groq.com/openai/v1/chat/completions",
    model: "llama-3.3-70b-versatile",
  },
];

async function callProvider(p: Provider, apiKey: string, system: string, user: string,
                             maxTokens: number, temperature: number, timeoutMs: number): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(p.url, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: p.model,
        messages: [{ role: "system", content: system }, { role: "user", content: user }],
        temperature, max_tokens: maxTokens,
      }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`${p.name} HTTP ${res.status}`);
    const data: any = await res.json();
    const text = data?.choices?.[0]?.message?.content;
    if (typeof text !== "string") throw new Error(`${p.name}: no content in response`);
    return text;
  } finally {
    clearTimeout(timer);
  }
}

export interface FrontierResult {
  available: boolean;
  provider?: string;
  text?: string;
  note?: string;
}

/** Try Gemini first, then Groq. Never throws — mirrors agents/llm.py::ask_safe()'s
 * "never raises" contract, since dossier_check must degrade, not 500, when no
 * LLM key is configured. */
export async function askFrontier(env: LlmEnv, system: string, user: string,
                                   opts: { maxTokens?: number; temperature?: number; timeoutMs?: number } = {}): Promise<FrontierResult> {
  const maxTokens = opts.maxTokens ?? 400;
  const temperature = opts.temperature ?? 0.3;
  const timeoutMs = opts.timeoutMs ?? 25000;
  const errors: string[] = [];
  for (const p of PROVIDERS) {
    const key = env[p.envKey];
    if (!key) continue;
    try {
      const text = await callProvider(p, key, system, user, maxTokens, temperature, timeoutMs);
      return { available: true, provider: p.name, text: text.trim() };
    } catch (e: any) {
      errors.push(`${p.name}: ${e?.message || e}`);
    }
  }
  return {
    available: false,
    note: errors.length
      ? `LLM unavailable this call: ${errors.join("; ")}`
      : "no LLM provider key set (need GEMINI_API_KEY or GROQ_API_KEY)",
  };
}
