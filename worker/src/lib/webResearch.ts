/**
 * Web search + scrape for the Worker/x402 side — TypeScript equivalent of
 * skillforge/research.py's provider router (Tavily -> Brave -> keyless
 * fallback for search; Firecrawl -> keyless fetch for scrape).
 *
 * skillforge/research.py drives its paid providers through a local MCP
 * server process (skillforge/mcp_client.py) — that mechanism doesn't exist
 * in a Cloudflare Worker (no subprocess/MCP protocol support), so this
 * calls each provider's plain REST API directly with fetch(). Deliberately
 * narrower than the Python router: Bright Data and Apify's real REST
 * contracts (as opposed to their MCP tool wrappers) weren't confirmed
 * against primary sources, so scrape here is Firecrawl -> keyless only,
 * same "real, not guessed" standard as everywhere else in this repo. No
 * quota guard either (skillforge/research.py's MONTHLY_QUOTA is a durable
 * file-backed counter — the Worker has no equivalent durable store wired
 * up); each provider's own account-level rate limit is the real backstop.
 */
export interface ResearchEnv {
  TAVILY_API_KEY?: string;
  BRAVE_API_KEY?: string;
  FIRECRAWL_API_KEY?: string;
}

export interface SearchResult {
  provider: string;
  results: Array<{ title: string; url: string; snippet: string }>;
  degraded?: boolean;
}

async function tavilySearch(apiKey: string, query: string, maxResults: number): Promise<SearchResult> {
  const res = await fetch("https://api.tavily.com/search", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ query, max_results: maxResults }),
  });
  if (!res.ok) throw new Error(`tavily HTTP ${res.status}`);
  const data: any = await res.json();
  const rows: any[] = Array.isArray(data?.results) ? data.results : [];
  return { provider: "tavily", results: rows.map((r) => ({ title: r.title || "", url: r.url || "", snippet: (r.content || "").slice(0, 200) })) };
}

async function braveSearch(apiKey: string, query: string, maxResults: number): Promise<SearchResult> {
  const url = `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}&count=${maxResults}`;
  const res = await fetch(url, { headers: { Accept: "application/json", "X-Subscription-Token": apiKey } });
  if (!res.ok) throw new Error(`brave HTTP ${res.status}`);
  const data: any = await res.json();
  const rows: any[] = Array.isArray(data?.web?.results) ? data.web.results : [];
  return { provider: "brave-search", results: rows.map((r) => ({ title: r.title || "", url: r.url || "", snippet: (r.description || "").slice(0, 200) })) };
}

// Keyless fallback — DDG HTML scrape only (skillforge/research.py also tries
// several SearXNG instances first; simplified here to one real, documented
// fallback rather than porting a multi-instance list unverified for Workers).
async function ddgSearch(query: string, maxResults: number): Promise<SearchResult> {
  try {
    const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
    const res = await fetch(url, { headers: { "User-Agent": "VAPE-PrivateEye/1.0" } });
    if (!res.ok) throw new Error(`ddg HTTP ${res.status}`);
    const body = await res.text();
    const results: Array<{ title: string; url: string; snippet: string }> = [];
    const re = /result__a"\s+href="([^"]+)"[^>]*>(.*?)<\/a>/gs;
    let m: RegExpExecArray | null;
    while ((m = re.exec(body)) && results.length < maxResults) {
      const href = m[1].replace(/&amp;/g, "&");
      const title = m[2].replace(/<[^>]+>/g, "").trim();
      let realUrl = href;
      try {
        const parsed = new URL(href.startsWith("//") ? `https:${href}` : href);
        realUrl = parsed.searchParams.get("uddg") || href;
      } catch { /* keep raw href */ }
      results.push({ title, url: decodeURIComponent(realUrl), snippet: "" });
    }
    return { provider: "ddg-keyless", results, degraded: results.length === 0 };
  } catch {
    return { provider: "keyless", results: [], degraded: true };
  }
}

export async function webSearch(env: ResearchEnv, query: string, maxResults = 5): Promise<SearchResult> {
  if (env.TAVILY_API_KEY) {
    try { return await tavilySearch(env.TAVILY_API_KEY, query, maxResults); } catch { /* fall through */ }
  }
  if (env.BRAVE_API_KEY) {
    try { return await braveSearch(env.BRAVE_API_KEY, query, maxResults); } catch { /* fall through */ }
  }
  return ddgSearch(query, maxResults);
}

export interface ScrapeResult {
  provider: string;
  content: string | null;
}

async function firecrawlScrape(apiKey: string, url: string): Promise<ScrapeResult> {
  const res = await fetch("https://api.firecrawl.dev/v2/scrape", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ url, formats: ["markdown"] }),
  });
  if (!res.ok) throw new Error(`firecrawl HTTP ${res.status}`);
  const data: any = await res.json();
  return { provider: "firecrawl", content: data?.data?.markdown ?? null };
}

async function keylessFetch(url: string): Promise<ScrapeResult> {
  try {
    const res = await fetch(url, { headers: { "User-Agent": "VAPE-PrivateEye/1.0" } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    const text = html.replace(/<script[\s\S]*?<\/script>/gi, "").replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    return { provider: "fetch-keyless", content: text.slice(0, 8000) };
  } catch {
    return { provider: "fetch-keyless", content: null };
  }
}

export async function webScrape(env: ResearchEnv, url: string): Promise<ScrapeResult> {
  if (env.FIRECRAWL_API_KEY) {
    try { return await firecrawlScrape(env.FIRECRAWL_API_KEY, url); } catch { /* fall through */ }
  }
  return keylessFetch(url);
}
