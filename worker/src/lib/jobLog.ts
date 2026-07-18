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
}

const RECENT_KEY = "RECENT_JOBS";
const TOTALS_KEY = "TOTALS";
const DAILY_HISTORY_KEY = "DAILY_HISTORY";
const RECENT_CAP = 200;
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

export async function getStats(kv: KVLike | undefined, days = 30) {
  if (!kv) return null;
  // Exactly 2 KV reads regardless of `days` — the old design did one GET
  // per requested day, which meant a 90-day chart alone could approach
  // Cloudflare's 50-subrequest-per-request cap on the free plan.
  const [totals, dailyHistory] = await Promise.all([
    readJson<Totals>(kv, TOTALS_KEY, {
      jobs: 0, errors: 0, revenue_usd: 0, first_job_ts: null, last_job_ts: null, by_offering: {}, by_facilitator: {},
    }),
    readJson<DailyEntry[]>(kv, DAILY_HISTORY_KEY, []),
  ]);
  // Same migration guard as logJob() — real, already-stored KV data may
  // predate by_facilitator.
  totals.by_facilitator = totals.by_facilitator ?? {};
  const byDate = new Map(dailyHistory.map((d) => [d.date, d]));
  const now = new Date();
  const daily: DailyEntry[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const ds = new Date(now.getTime() - i * 86400000).toISOString().slice(0, 10);
    const found = byDate.get(ds);
    daily.push({ date: ds, jobs: found?.jobs ?? 0, revenue_usd: found?.revenue_usd ?? 0 });
  }
  return { totals, daily };
}
