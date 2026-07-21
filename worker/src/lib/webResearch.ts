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

// ── minimal, portable HTML tokenizer ────────────────────────────────────────
// worker/src runs on BOTH Cloudflare Workers and Deno (worker/deno/deno-entry.ts
// — see worker/README.md's "Cloudflare + Deno Deploy" section: "src/index.ts
// has zero Cloudflare-specific code"), so Cloudflare's own HTMLRewriter global
// isn't usable here — Deno's `deno check` has no declaration for it. This is
// a real, hand-written single-pass tokenizer instead: it never re-scans
// already-consumed input (unlike an iterative regex replace, which is exactly
// the "incomplete multi-character sanitization" class of bug CodeQL flags —
// e.g. stripping "<script>" once from "<scr<script>ipt>" leaves a new,
// unintended "<script>ipt>"), same guarantee Python's stdlib
// html.parser.HTMLParser gives agents/investigate.py's own _TextExtractor.
// script/style are read as HTML5's real "raw text" elements — their content
// is never itself tokenized, only scanned forward for the literal closing
// tag, exactly like a real browser parser (not a heuristic guess).
interface TagToken { type: "open" | "close"; name: string; attrs: Record<string, string>; selfClosing?: boolean; }
interface TextToken { type: "text"; text: string; }
type HtmlToken = TagToken | TextToken;

const RAW_TEXT_TAGS = new Set(["script", "style"]);
const ATTR_RE = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*(?:=\s*("([^"]*)"|'([^']*)'|[^\s"'=<>`]+))?/g;
const NAMED_ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };

function decodeEntities(s: string): string {
  return s.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (whole, ent: string) => {
    if (ent[0] === "#") {
      const isHex = ent[1] === "x" || ent[1] === "X";
      const code = parseInt(ent.slice(isHex ? 2 : 1), isHex ? 16 : 10);
      return Number.isFinite(code) ? String.fromCodePoint(code) : whole;
    }
    return NAMED_ENTITIES[ent] ?? whole;
  });
}

function tokenizeHtml(html: string): HtmlToken[] {
  const tokens: HtmlToken[] = [];
  const n = html.length;
  let i = 0;
  while (i < n) {
    const lt = html.indexOf("<", i);
    if (lt === -1) { tokens.push({ type: "text", text: html.slice(i) }); break; }
    if (lt > i) tokens.push({ type: "text", text: html.slice(i, lt) });
    if (html.startsWith("<!--", lt)) {
      const end = html.indexOf("-->", lt + 4);
      i = end === -1 ? n : end + 3;
      continue;
    }
    if (html[lt + 1] === "!" || html[lt + 1] === "?") {
      const end = html.indexOf(">", lt);
      i = end === -1 ? n : end + 1;
      continue;
    }
    const isClose = html[lt + 1] === "/";
    const nameStart = isClose ? lt + 2 : lt + 1;
    const nameMatch = /^[a-zA-Z][a-zA-Z0-9]*/.exec(html.slice(nameStart));
    if (!nameMatch) { tokens.push({ type: "text", text: "<" }); i = lt + 1; continue; }
    const name = nameMatch[0].toLowerCase();
    const gt = html.indexOf(">", nameStart + name.length);
    if (gt === -1) { i = n; break; }
    const rawAttrs = html.slice(nameStart + name.length, gt);
    const selfClosing = /\/\s*$/.test(rawAttrs);
    const attrs: Record<string, string> = {};
    if (!isClose) {
      ATTR_RE.lastIndex = 0;
      let am: RegExpExecArray | null;
      while ((am = ATTR_RE.exec(rawAttrs))) {
        if (!am[1]) continue;
        attrs[am[1].toLowerCase()] = am[3] ?? am[4] ?? am[2] ?? "";
      }
    }
    tokens.push(isClose ? { type: "close", name, attrs: {} } : { type: "open", name, attrs, selfClosing });
    i = gt + 1;
    if (!isClose && RAW_TEXT_TAGS.has(name) && !selfClosing) {
      const closeRe = new RegExp(`</${name}\\s*>`, "i");
      const rest = html.slice(i);
      const cm = closeRe.exec(rest);
      if (cm) {
        if (cm.index > 0) tokens.push({ type: "text", text: rest.slice(0, cm.index) });
        tokens.push({ type: "close", name, attrs: {} });
        i += cm.index + cm[0].length;
      } else {
        tokens.push({ type: "text", text: rest });
        i = n;
      }
    }
  }
  return tokens;
}

/** Visible text only — script/style content is skipped via real tag-depth
 * tracking (see tokenizeHtml's raw-text handling above), never re-scanned. */
function extractText(html: string): string {
  let depth = 0;
  let out = "";
  for (const tok of tokenizeHtml(html)) {
    if (tok.type === "open" && RAW_TEXT_TAGS.has(tok.name) && !tok.selfClosing) { depth++; continue; }
    if (tok.type === "close" && RAW_TEXT_TAGS.has(tok.name)) { depth = Math.max(0, depth - 1); continue; }
    if (tok.type === "text" && depth === 0) out += tok.text;
  }
  return decodeEntities(out);
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
    let depth = 0; // >0 while inside a matched <a class="result__a">
    let currentHref: string | null = null;
    let currentTitle = "";
    for (const tok of tokenizeHtml(body)) {
      if (tok.type === "open" && tok.name === "a") {
        const classes = (tok.attrs["class"] || "").split(/\s+/);
        if (depth === 0 && classes.includes("result__a")) {
          depth = 1;
          currentHref = tok.attrs["href"] || null;
          currentTitle = "";
        } else if (depth > 0) {
          depth++; // nested <a> — real HTML disallows this, defensive only
        }
      } else if (tok.type === "close" && tok.name === "a" && depth > 0) {
        depth--;
        if (depth === 0) {
          if (currentHref && results.length < maxResults) {
            let realUrl = currentHref;
            try {
              const parsed = new URL(currentHref.startsWith("//") ? `https:${currentHref}` : currentHref);
              realUrl = parsed.searchParams.get("uddg") || currentHref;
            } catch { /* keep raw href */ }
            results.push({ title: decodeEntities(currentTitle).trim(), url: decodeURIComponent(realUrl), snippet: "" });
          }
          currentHref = null;
          currentTitle = "";
        }
      } else if (tok.type === "text" && depth > 0) {
        currentTitle += tok.text;
      }
      if (results.length >= maxResults && depth === 0) break;
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

// SSRF guard for keylessFetch below — the one scrape path that's a raw
// fetch() FROM this Worker, unlike firecrawlScrape (Firecrawl's own
// infrastructure does that fetch, out of this repo's control either way).
// Blocks the well-known direct SSRF vectors: loopback, RFC1918 private
// ranges, link-local (which covers the 169.254.169.254 cloud-metadata
// address specifically), and other reserved/multicast ranges — on both the
// literal hostname (IP-literal URLs) and, best-effort, on whatever the
// Worker runtime resolves at fetch time isn't inspectable here (Workers
// exposes no DNS-resolution API), so a hostname that only resolves to a
// private address at request time (DNS rebinding) is a known residual gap,
// same class of limitation as most fetch-a-user-URL features on this
// platform. Re-applied to every redirect hop by keylessFetch's manual
// redirect loop below, since a same-origin-looking initial URL can still
// redirect to a private target.
function isBlockedHost(hostname: string): boolean {
  const h = hostname.toLowerCase();
  if (h === "localhost" || h.endsWith(".localhost")) return true;
  // IPv4 literal ranges.
  const m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (m) {
    const [a, b] = [Number(m[1]), Number(m[2])];
    if (a === 127) return true; // loopback
    if (a === 10) return true; // RFC1918
    if (a === 172 && b >= 16 && b <= 31) return true; // RFC1918
    if (a === 192 && b === 168) return true; // RFC1918
    if (a === 169 && b === 254) return true; // link-local incl. cloud metadata 169.254.169.254
    if (a === 0) return true; // "this network"
    if (a >= 224) return true; // multicast/reserved (224-255)
  }
  // IPv6 loopback/link-local/unique-local literals (bracketed form already
  // stripped of brackets by URL.hostname).
  if (h === "::1" || h.startsWith("fe80:") || h.startsWith("fc") || h.startsWith("fd")) return true;
  return false;
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
    let current = url;
    // Manual redirect handling (redirect: "manual") so each hop is
    // re-validated against isBlockedHost before being followed — a public-
    // looking initial URL redirecting to a private target would otherwise
    // bypass the check fetch()'s default "follow" behavior does silently.
    for (let hop = 0; hop < 5; hop++) {
      const parsed = new URL(current);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") throw new Error("blocked: non-http(s) redirect target");
      if (isBlockedHost(parsed.hostname)) throw new Error("blocked: private/reserved network target");
      const res = await fetch(current, { headers: { "User-Agent": "VAPE-PrivateEye/1.0" }, redirect: "manual" });
      if (res.status >= 300 && res.status < 400) {
        const loc = res.headers.get("location");
        if (!loc) throw new Error(`redirect with no Location (HTTP ${res.status})`);
        current = new URL(loc, current).toString();
        continue;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const html = await res.text();
      const cleaned = extractText(html).replace(/\s+/g, " ").trim();
      return { provider: "fetch-keyless", content: cleaned.slice(0, 8000) };
    }
    throw new Error("too many redirects");
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
