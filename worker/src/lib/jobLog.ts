/**
 * In-house x402 job ledger — every real paid job VAPE fulfills gets logged
 * here, then surfaced by the site's live transaction feed (see
 * docs/assets/x402feed.js). Layered with real on-chain proof: each record
 * carries the actual settlement transaction hash from the x402 facilitator
 * (see index.ts's onAfterSettle hook), which the feed links straight to
 * Basescan — so every entry is independently checkable, not just a number
 * VAPE reports about itself.
 *
 * Storage: Cloudflare KV (binding `VAPE_JOBS`, wired in wrangler.toml only
 * once `VAPE_JOBS_KV_ID` is configured — see worker/README.md). Deliberately
 * NOT a Cloudflare-specific type here (no `@cloudflare/workers-types`
 * import) — this file lives under worker/src, which also runs unmodified on
 * Deno Deploy (see worker/README.md's "zero Cloudflare-specific code"
 * invariant); `KVLike` is a minimal duck-typed subset of the real
 * `KVNamespace` interface so both runtimes typecheck without an ambient
 * Cloudflare dependency. On Deno, `env.VAPE_JOBS` is simply never set, so
 * every function below is a no-op there — same graceful-degradation pattern
 * already used for every optional API key in this codebase.
 *
 * Trade-off, stated plainly: recent-jobs/stats use KV read-modify-write, not
 * a transactional counter — at VAPE's real traffic volume (paid jobs are not
 * high-frequency) the chance of two writes racing and one update being lost
 * is low and the consequence is cosmetic (an undercount), not a payment or
 * security issue. A Durable Object would close that gap but is real added
 * infra/cost this repo's low-ops philosophy doesn't justify for a showcase
 * feed — the actual payment settlement (the part that's real money) is
 * handled entirely by the x402 facilitator, never by this log.
 */

export interface KVLike {
  get(key: string, options?: { type?: "text" | "json" }): Promise<any>;
  put(key: string, value: string, options?: Record<string, unknown>): Promise<void>;
}

export interface JobRecord {
  id: string;
  ts: string;
  offering: string;
  address: string;
  chain_id: number;
  symbol: string | null;
  name: string | null;
  verdict: string | null;
  status: "settled" | "error";
  amount_usd: number;
  latency_ms: number;
  payer: string | null;
  tx_hash: string | null;
  network: string | null;
  error: string | null;
}

interface OfferingTotals {
  count: number;
  revenue_usd: number;
}

export interface Totals {
  jobs: number;
  errors: number;
  revenue_usd: number;
  first_job_ts: string | null;
  last_job_ts: string | null;
  by_offering: Record<string, OfferingTotals>;
}

interface DailyBucket {
  jobs: number;
  revenue_usd: number;
}

const RECENT_KEY = "RECENT_JOBS";
const TOTALS_KEY = "TOTALS";
const RECENT_CAP = 200;
const DAILY_PREFIX = "STATS_DAILY:";

function dateKey(iso: string): string {
  return iso.slice(0, 10); // YYYY-MM-DD
}

async function readJson<T>(kv: KVLike, key: string, fallback: T): Promise<T> {
  try {
    const v = await kv.get(key, { type: "json" });
    return (v ?? fallback) as T;
  } catch {
    return fallback;
  }
}

/**
 * Fire-and-forget: called via c.executionCtx.waitUntil() from the route
 * handler, so a KV hiccup never delays or fails the actual paid response.
 */
export async function logJob(kv: KVLike | undefined, record: JobRecord): Promise<void> {
  if (!kv) return;
  try {
    const recent = await readJson<JobRecord[]>(kv, RECENT_KEY, []);
    recent.unshift(record);
    await kv.put(RECENT_KEY, JSON.stringify(recent.slice(0, RECENT_CAP)));

    const totals = await readJson<Totals>(kv, TOTALS_KEY, {
      jobs: 0, errors: 0, revenue_usd: 0, first_job_ts: null, last_job_ts: null, by_offering: {},
    });
    totals.jobs += 1;
    if (record.status === "error") totals.errors += 1;
    else totals.revenue_usd += record.amount_usd;
    totals.first_job_ts = totals.first_job_ts ?? record.ts;
    totals.last_job_ts = record.ts;
    const off = totals.by_offering[record.offering] ?? { count: 0, revenue_usd: 0 };
    off.count += 1;
    if (record.status === "settled") off.revenue_usd += record.amount_usd;
    totals.by_offering[record.offering] = off;
    await kv.put(TOTALS_KEY, JSON.stringify(totals));

    const dKey = DAILY_PREFIX + dateKey(record.ts);
    const daily = await readJson<DailyBucket>(kv, dKey, { jobs: 0, revenue_usd: 0 });
    daily.jobs += 1;
    if (record.status === "settled") daily.revenue_usd += record.amount_usd;
    // 100 days is plenty for any chart window this feed will ever show, and
    // keeps a long-forgotten deploy from accumulating KV keys forever.
    await kv.put(dKey, JSON.stringify(daily), { expirationTtl: 60 * 60 * 24 * 100 });
  } catch {
    // Never let logging failure surface to a paying caller.
  }
}

export async function getFeed(kv: KVLike | undefined, limit = 50): Promise<JobRecord[]> {
  if (!kv) return [];
  const recent = await readJson<JobRecord[]>(kv, RECENT_KEY, []);
  return recent.slice(0, Math.max(1, Math.min(limit, RECENT_CAP)));
}

export async function getStats(kv: KVLike | undefined, days = 30) {
  if (!kv) return null;
  const totals = await readJson<Totals>(kv, TOTALS_KEY, {
    jobs: 0, errors: 0, revenue_usd: 0, first_job_ts: null, last_job_ts: null, by_offering: {},
  });
  const now = new Date();
  const dailyKeys: string[] = [];
  const dates: string[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 86400000);
    const ds = d.toISOString().slice(0, 10);
    dates.push(ds);
    dailyKeys.push(DAILY_PREFIX + ds);
  }
  const buckets = await Promise.all(dailyKeys.map((k) => readJson<DailyBucket>(kv, k, { jobs: 0, revenue_usd: 0 })));
  const daily = dates.map((date, i) => ({ date, jobs: buckets[i].jobs, revenue_usd: buckets[i].revenue_usd }));
  return { totals, daily };
}
