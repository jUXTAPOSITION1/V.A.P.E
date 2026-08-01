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
 * a transactional counter — plain KV has no compare-and-swap, so two
 * logJob() calls settling close together can still race. putWithVerifiedRetry()
 * below closes most of that gap (read back after every write, retry against
 * a fresh read if a concurrent write interleaved) without needing a Durable
 * Object — real added infra/cost this repo's low-ops philosophy doesn't
 * justify for a showcase feed. It narrows the race to "several attempts all
 * collide," not "closes it entirely" — the actual payment settlement (the
 * part that's real money) is handled entirely by the x402 facilitator,
 * never by this log.
 */

export interface KVLike {
  get(key: string, options?: { type?: "text" | "json" }): Promise<any>;
  put(key: string, value: string, options?: Record<string, unknown>): Promise<void>;
}

export interface JobRecord {
  id: string;
  ts: string;
  offering: string;
  address: string | null;
  chain_id: number;
  symbol: string | null;
  name: string | null;
  verdict: string | null;
  status: "settled" | "error";
  amount_usd: number;
  latency_ms: number | null;
  payer: string | null;
  tx_hash: string | null;
  network: string | null;
  error: string | null;
  // Which facilitator actually settled this payment (see
  // lib/facilitatorClient.ts's lastUsed) — absent on records logged before
  // the 50/50 VAPOR/CDP hybrid split shipped, and on any job that never
  // reached settlement.
  facilitator?: "vapor" | "cdp";
  // Set only by agents/x402_ledger_backfill.py — a real on-chain USDC
  // transfer reconstructed after the fact, from before VAPE_JOBS_KV_ID
  // existed, rather than something this Worker watched happen live. See
  // that script's docstring for why `offering`/`address`/`symbol`/etc. are
  // sometimes less precise (amount-inferred, occasionally ambiguous) for
  // these entries specifically.
  backfilled?: boolean;
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
  // Real achieved VAPOR/CDP split (see the 50/50 hybrid routing in
  // index.ts) — lets the site show the actual ratio rather than just the
  // intended one. Jobs logged before this field existed, or that never
  // reached settlement, aren't counted in either bucket.
  by_facilitator: Record<string, OfferingTotals>;
}

export interface DailyEntry {
  date: string;
  jobs: number;
  revenue_usd: number;
  // Unique paying wallets that day — derived on read from RECENT_JOBS (see
  // getStats() below), never persisted in DAILY_HISTORY itself, so it's
  // only as complete as RECENT_JOBS's own RECENT_CAP-bounded window (a day
  // past that window reports 0 rather than a guess). Optional because the
  // logJob() write path below never sets it — only getStats()'s returned
  // copy does.
  buyers?: number;
}

const RECENT_KEY = "RECENT_JOBS";
const TOTALS_KEY = "TOTALS";
const DAILY_HISTORY_KEY = "DAILY_HISTORY";
// Raised from 200: the site's Recent Jobs table (docs/assets/x402feed.js) is
// meant to hold VAPE's real job history end-to-end, Basescan-style, not just
// a shallow "last few" preview — 200 records was under two weeks of runway at
// real observed volume (~27 jobs/day per the live x402scan listing) before
// the oldest jobs silently fell off the end of this array.
// 10,000 records is still a single small KV value: each JobRecord serializes
// to roughly 400-500 bytes, so the whole array tops out around 4-5MB — well
// under Cloudflare KV's 25MB per-value ceiling, with the same 2-read-per-
// request cost as before (RECENT_KEY is one GET regardless of array length).
// At current volume this is well over a year of full per-job detail; TOTALS
// (all-time, never trimmed) still holds the true lifetime aggregate even
// once the oldest individual records eventually age out of this array.
const RECENT_CAP = 10000;
// ~13 months of daily entries — comfortably covers the site's longest
// chart view (1 year) with room to spare, while keeping this a single
// small KV value rather than one key per day. That per-day-key design
// (STATS_DAILY:<date>, one KV GET per requested day) is what this
// replaced: querying a 90-day range meant 90 parallel subrequests from a
// single Worker invocation, uncomfortably close to Cloudflare's
// documented free-plan cap of 50 subrequests per request — a 365-day
// view would have failed outright, not just been slow.
const DAILY_HISTORY_CAP = 400;

function dateKey(iso: string): string {
  return iso.slice(0, 10); // YYYY-MM-DD
}

export async function readJson<T>(kv: KVLike, key: string, fallback: T): Promise<T> {
  try {
    const v = await kv.get(key, { type: "json" });
    return (v ?? fallback) as T;
  } catch {
    return fallback;
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Plain KV has no compare-and-swap, so two logJob() calls settling within
// the same few hundred ms (a burst of back-to-back paid requests, not an
// edge case in practice) can both read the same snapshot and the later
// put() silently clobbers the earlier one — previously undetected, this
// dropped real settled jobs from the feed/totals entirely rather than just
// under-counting a shared aggregate. Since this whole call already runs
// off the response path (via waitUntil), there's headroom to read back
// after writing and confirm THIS call's own update actually stuck, retrying
// against a fresh read if a concurrent write raced ahead of it. Not a true
// lock — two retries could still collide — but it turns a routine race
// into a rare one without standing up a Durable Object for a showcase feed.
const MAX_WRITE_ATTEMPTS = 8;
// Full jitter (AWS's term for it): the whole delay is randomized up to the
// exponential cap, not just added on top of a fixed base. A burst of
// several settlements landing at once retry on staggered, decorrelated
// schedules instead of a fixed cadence, so they don't all wake up and
// collide again in lockstep — this is what actually resolves an N-way
// pile-up within a handful of attempts rather than just spacing out a
// pairwise collision.
function fullJitterBackoff(attempt: number): number {
  return Math.random() * Math.min(1000, 40 * 2 ** attempt);
}

export async function putWithVerifiedRetry<T>(
  kv: KVLike,
  key: string,
  fallback: T,
  mutate: (current: T) => T
): Promise<void> {
  for (let attempt = 0; attempt < MAX_WRITE_ATTEMPTS; attempt++) {
    const current = await readJson<T>(kv, key, fallback);
    const serializedNext = JSON.stringify(mutate(current));
    await kv.put(key, serializedNext);
    // Re-read and compare verbatim: an exact match proves nothing landed in
    // between our read and our write. Any difference means a concurrent
    // writer's put() interleaved with ours — re-derive from its result
    // instead of blindly overwriting it again.
    const writtenBack = await readJson<T>(kv, key, fallback);
    if (JSON.stringify(writtenBack) === serializedNext) return;
    await sleep(fullJitterBackoff(attempt));
  }
  // Every attempt got clobbered by a concurrent write — extremely unlikely
  // at VAPE's real traffic volume. Give up silently rather than loop
  // forever; logJob()'s outer try/catch already treats logging failures as
  // non-fatal, cosmetic misses, never something a paying caller should see.
}

/**
 * Fire-and-forget: called via c.executionCtx.waitUntil() from the route
 * handler, so a KV hiccup never delays or fails the actual paid response.
 */
export async function logJob(kv: KVLike | undefined, record: JobRecord): Promise<void> {
  if (!kv) return;
  try {
    await putWithVerifiedRetry<JobRecord[]>(
      kv,
      RECENT_KEY,
      [],
      (recent) => [record, ...recent].slice(0, RECENT_CAP)
    );

    const emptyTotals: Totals = {
      jobs: 0, errors: 0, revenue_usd: 0, first_job_ts: null, last_job_ts: null, by_offering: {}, by_facilitator: {},
    };
    await putWithVerifiedRetry<Totals>(
      kv,
      TOTALS_KEY,
      emptyTotals,
      (totals) => {
        // Migration guard: real, already-stored KV data predates
        // by_facilitator, so a read of an existing key returns that older
        // shape verbatim (the fallback literal only applies when the key is
        // entirely absent) — never assume the field exists just because the
        // read succeeded.
        const next: Totals = {
          ...totals,
          by_offering: { ...totals.by_offering },
          by_facilitator: { ...(totals.by_facilitator ?? {}) },
        };
        next.jobs += 1;
        if (record.status === "error") next.errors += 1;
        else next.revenue_usd += record.amount_usd;
        next.first_job_ts = next.first_job_ts ?? record.ts;
        next.last_job_ts = record.ts;
        const off = next.by_offering[record.offering] ?? { count: 0, revenue_usd: 0 };
        const nextOff = { ...off, count: off.count + 1 };
        if (record.status === "settled") nextOff.revenue_usd += record.amount_usd;
        next.by_offering[record.offering] = nextOff;
        if (record.facilitator) {
          const fac = next.by_facilitator[record.facilitator] ?? { count: 0, revenue_usd: 0 };
          const nextFac = { ...fac, count: fac.count + 1 };
          if (record.status === "settled") nextFac.revenue_usd += record.amount_usd;
          next.by_facilitator[record.facilitator] = nextFac;
        }
        return next;
      }
    );

    const today = dateKey(record.ts);
    await putWithVerifiedRetry<DailyEntry[]>(
      kv,
      DAILY_HISTORY_KEY,
      [],
      (dailyHistory) => {
        const next = dailyHistory.map((d) => ({ ...d }));
        let entry = next.find((d) => d.date === today);
        if (!entry) {
          entry = { date: today, jobs: 0, revenue_usd: 0 };
          next.push(entry);
        }
        entry.jobs += 1;
        if (record.status === "settled") entry.revenue_usd += record.amount_usd;
        next.sort((a, b) => a.date.localeCompare(b.date));
        return next.slice(-DAILY_HISTORY_CAP);
      }
    );
  } catch {
    // Never let logging failure surface to a paying caller.
  }
}

export async function getFeed(kv: KVLike | undefined, limit = 50): Promise<JobRecord[]> {
  if (!kv) return [];
  const recent = await readJson<JobRecord[]>(kv, RECENT_KEY, []);
  return recent.slice(0, Math.max(1, Math.min(limit, RECENT_CAP)));
}

export type FeedSort = "ts_desc" | "ts_asc" | "amount_desc" | "amount_asc" | "latency_desc" | "latency_asc";

export interface FeedQuery {
  /** Case-insensitive substring match against offering/symbol/name/address/payer/tx_hash. */
  q?: string;
  offering?: string;
  status?: "settled" | "error";
  sort?: FeedSort;
  limit?: number;
  offset?: number;
}

export interface FeedPage {
  jobs: JobRecord[];
  /** Count after filtering, before pagination — what the UI paginates over. */
  total: number;
}

const SORTERS: Record<FeedSort, (a: JobRecord, b: JobRecord) => number> = {
  // RECENT_JOBS is already stored newest-first (logJob prepends), so ts_desc
  // is a pure passthrough — every other sort explicitly re-orders it.
  ts_desc: (a, b) => b.ts.localeCompare(a.ts),
  ts_asc: (a, b) => a.ts.localeCompare(b.ts),
  amount_desc: (a, b) => b.amount_usd - a.amount_usd,
  amount_asc: (a, b) => a.amount_usd - b.amount_usd,
  // Nulls (never measured, e.g. async/backfilled jobs) sort last regardless
  // of direction — "unknown latency" is not the same claim as "zero" or
  // "infinite" latency, so it shouldn't win either sort.
  latency_desc: (a, b) => (b.latency_ms ?? -1) - (a.latency_ms ?? -1),
  latency_asc: (a, b) => (a.latency_ms ?? Infinity) - (b.latency_ms ?? Infinity),
};

function matchesQuery(job: JobRecord, q: string): boolean {
  const haystack = [job.offering, job.symbol, job.name, job.address, job.payer, job.tx_hash, job.verdict]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

/**
 * Server-side search/filter/sort/paginate over the job feed. Safe to do this
 * way (rather than needing a real database) only because RECENT_JOBS is
 * already a single KV value fully read into memory for every /x402/feed
 * request — filtering and sorting an in-memory array of up to RECENT_CAP
 * records costs nothing extra over the read that already happens. This is the
 * server-side counterpart to a Basescan/Etherscan address-history table: the
 * client sends a page + filters, the server returns exactly that page plus
 * the total row count the filters produced, so pagination controls (page X
 * of Y) reflect the filtered set, not the unfiltered one.
 */
export async function queryFeed(kv: KVLike | undefined, query: FeedQuery): Promise<FeedPage> {
  if (!kv) return { jobs: [], total: 0 };
  const recent = await readJson<JobRecord[]>(kv, RECENT_KEY, []);

  let filtered = recent;
  if (query.status) filtered = filtered.filter((j) => j.status === query.status);
  if (query.offering) filtered = filtered.filter((j) => j.offering === query.offering);
  if (query.q) {
    const q = query.q.trim().toLowerCase();
    if (q) filtered = filtered.filter((j) => matchesQuery(j, q));
  }

  const sorter = SORTERS[query.sort ?? "ts_desc"] ?? SORTERS.ts_desc;
  // Only re-sort when a real order change is requested — the array is
  // already newest-first, so this skips a needless copy+sort on the by far
  // most common request (the default view, no explicit sort).
  const ordered = query.sort && query.sort !== "ts_desc" ? [...filtered].sort(sorter) : filtered;

  const total = ordered.length;
  const offset = Math.max(0, query.offset ?? 0);
  const limit = Math.max(1, Math.min(query.limit ?? 50, RECENT_CAP));
  return { jobs: ordered.slice(offset, offset + limit), total };
}

export async function getStats(kv: KVLike | undefined, days: number | "all" = 30) {
  if (!kv) return null;
  // 3 KV reads regardless of `days` — RECENT_JOBS is read alongside the
  // other two (not one-GET-per-day) purely to derive real unique-buyer
  // counts per day below; still nowhere near Cloudflare's 50-subrequest cap.
  const [totals, dailyHistory, recent] = await Promise.all([
    readJson<Totals>(kv, TOTALS_KEY, {
      jobs: 0, errors: 0, revenue_usd: 0, first_job_ts: null, last_job_ts: null, by_offering: {}, by_facilitator: {},
    }),
    readJson<DailyEntry[]>(kv, DAILY_HISTORY_KEY, []),
    readJson<JobRecord[]>(kv, RECENT_KEY, []),
  ]);
  const buyersByDate = new Map<string, Set<string>>();
  for (const job of recent) {
    const payer = job.payer?.toLowerCase();
    if (!payer) continue;
    const ds = dateKey(job.ts);
    if (!buyersByDate.has(ds)) buyersByDate.set(ds, new Set());
    buyersByDate.get(ds)!.add(payer);
  }
  // Same migration guard as logJob() — real, already-stored KV data may
  // predate by_facilitator.
  totals.by_facilitator = totals.by_facilitator ?? {};
  const byDate = new Map(dailyHistory.map((d) => [d.date, d]));
  const now = new Date();
  // "all" means every day DAILY_HISTORY actually retains (bounded by
  // DAILY_HISTORY_CAP, not literally infinite — first_job_ts on `totals`
  // remains the true never-trimmed all-time start date for anything older).
  // first_job_ts is authoritative because dailyHistory itself has no entry
  // at all for a day with zero jobs, so its own earliest key can understate
  // how far back activity actually goes on a sparse ledger.
  const spanDays = days === "all"
    ? Math.max(1, Math.min(
        DAILY_HISTORY_CAP,
        totals.first_job_ts
          ? Math.ceil((now.getTime() - new Date(totals.first_job_ts).getTime()) / 86400000) + 1
          : dailyHistory.length || 1,
      ))
    : days;
  const daily: DailyEntry[] = [];
  // True unique-payer count across the *whole* selected window — deliberately
  // not "sum of each day's buyers" (buyersByDate above), which would double
  // count any wallet that paid on more than one day in range.
  const rangeBuyers = new Set<string>();
  for (let i = spanDays - 1; i >= 0; i--) {
    const ds = new Date(now.getTime() - i * 86400000).toISOString().slice(0, 10);
    const found = byDate.get(ds);
    const dayBuyers = buyersByDate.get(ds);
    if (dayBuyers) for (const p of dayBuyers) rangeBuyers.add(p);
    daily.push({ date: ds, jobs: found?.jobs ?? 0, revenue_usd: found?.revenue_usd ?? 0, buyers: dayBuyers?.size ?? 0 });
  }
  return { totals, daily, range_buyers: rangeBuyers.size };
}
