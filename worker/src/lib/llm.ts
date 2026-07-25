/**
 * Frontier-LLM client for the Worker/x402 side. Tries OCI-hosted Grok 4.3
 * first — the same primary reasoning route agents/llm.py::ask_oci_grok()
 * uses for every real Python call site (VAPE's actual "frontier" model,
 * by explicit 2026-07-19 direction) — falling back to Gemini/Groq only if
 * OCI_GENAI_API_KEY isn't configured or the call errors.
 *
 * Real, previously-live gap this closes (confirmed via a full-repo audit,
 * 2026-07-25): this file used to be permanently capped at Gemini->Groq —
 * dossier_check ($0.10) and website_review ($0.15), the x402 Worker's own
 * two paid LLM-backed offerings, NEVER reached OCI Grok, ever, regardless
 * of what every other real report-generating call site in this repo does.
 *
 * Vertex (agents/llm.py::ask_vertex_candidate(), the other half of VAPE's
 * real primary chain) is deliberately NOT ported here — its access token
 * is minted via GitHub Actions' WIF OIDC exchange
 * (google-github-actions/auth), which needs a refresh mechanism a
 * stateless Worker request can't run itself. OCI's API key is a plain,
 * static Bearer secret, so it ports directly as a Worker secret with no
 * such problem.
 *
 * OCI's OpenAI-compatible endpoint and Gemini/Groq's own OpenAI-compatible
 * endpoints share the same request/response shape (model/messages/
 * temperature/max_tokens in, choices[0].message.content out) — OCI just
 * needs its own function for the region-templated URL + optional
 * CompartmentId header, matching agents/llm.py::_call_oci_grok()'s exact
 * shape.
 */
export interface LlmEnv {
  OCI_GENAI_API_KEY?: string;
  OCI_COMPARTMENT_OCID?: string;
  OCI_REGION?: string;
  OCI_GROK_MODEL?: string;
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

const OCI_DEFAULT_REGION = "us-ashburn-1";
const OCI_DEFAULT_MODEL = "xai.grok-4.3";

async function callOci(env: LlmEnv, system: string, user: string, maxTokens: number,
                        temperature: number, timeoutMs: number): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const region = env.OCI_REGION || OCI_DEFAULT_REGION;
    const model = env.OCI_GROK_MODEL || OCI_DEFAULT_MODEL;
    const url = `https://inference.generativeai.${region}.oci.oraclecloud.com/20231130/actions/v1/chat/completions`;
    const headers: Record<string, string> = {
      Authorization: `Bearer ${env.OCI_GENAI_API_KEY}`,
      "Content-Type": "application/json",
    };
    if (env.OCI_COMPARTMENT_OCID) headers.CompartmentId = env.OCI_COMPARTMENT_OCID;
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model,
        messages: [{ role: "system", content: system }, { role: "user", content: user }],
        temperature, max_tokens: maxTokens,
      }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`oci_grok HTTP ${res.status}`);
    const data: any = await res.json();
    const text = data?.choices?.[0]?.message?.content;
    if (typeof text !== "string") throw new Error("oci_grok: no content in response");
    return text;
  } finally {
    clearTimeout(timer);
  }
}

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

/** Try OCI Grok 4.3 first, then Gemini, then Groq. Never throws — mirrors
 * agents/llm.py::ask_safe()'s "never raises" contract, since dossier_check/
 * website_review must degrade, not 500, when no LLM key is configured. */
export async function askFrontier(env: LlmEnv, system: string, user: string,
                                   opts: { maxTokens?: number; temperature?: number; timeoutMs?: number } = {}): Promise<FrontierResult> {
  const maxTokens = opts.maxTokens ?? 400;
  const temperature = opts.temperature ?? 0.3;
  const timeoutMs = opts.timeoutMs ?? 25000;
  const errors: string[] = [];

  if (env.OCI_GENAI_API_KEY) {
    try {
      const text = await callOci(env, system, user, maxTokens, temperature, timeoutMs);
      return { available: true, provider: "oci_grok", text: text.trim() };
    } catch (e: any) {
      errors.push(`oci_grok: ${e?.message || e}`);
    }
  }

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
      : "no LLM provider key set (need OCI_GENAI_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY)",
  };
}
