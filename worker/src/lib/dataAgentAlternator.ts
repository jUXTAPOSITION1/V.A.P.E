/**
 * Deterministic CDP/VAPOR alternation for DATA AGENT's own hires
 * (agents/data_agent.py, tagged X-VAPE-Client: data-agent) — every other
 * traffic class still gets the random 50/50 split in index.ts. DATA AGENT
 * runs on a fixed, low-volume cadence (2 hires/hour), so a coin flip could
 * easily string together a long run that never touches one side; a
 * persisted, race-safe alternator guarantees VAPOR gets genuine, regular
 * settlement volume from VAPE's own traffic rather than leaving it to
 * chance. Reuses jobLog.ts's putWithVerifiedRetry so concurrent invocations
 * (overlapping requests) still hand out each side exactly once per pair,
 * not two of the same in a row.
 *
 * One logical x402 payment is actually TWO separate HTTP requests hitting
 * this same alternator: the initial unpaid request that gets the 402
 * challenge, then the real paid retry carrying X-PAYMENT once the client
 * signs. index.ts calls this once per incoming request, so advancing on
 * both meant every hire consumed exactly 2 flips — which cancel out
 * (flip(flip(s)) === s) and reset the state right back to where it started
 * before the next hire. The result: the unpaid leg and the paid/settling
 * leg always differed from each other (as designed), but the SETTLING leg
 * specifically never actually rotated between hires — it stayed pinned to
 * whichever side won that parity from the very first call, forever. Only
 * the leg that carries a real payment now advances the persisted state;
 * the free challenge leg peeks the current value without mutating it,
 * since facilitator identity is a server-side implementation detail the
 * 402 challenge itself never exposes to the payer either way.
 */
import { KVLike, putWithVerifiedRetry, readJson } from "./jobLog";

const ALTERNATOR_KEY = "DATA_AGENT_ALTERNATOR";

interface AlternatorState {
  nextPrimary: "cdp" | "vapor";
}

const DEFAULT_STATE: AlternatorState = { nextPrimary: "cdp" };

export async function nextDataAgentFacilitator(
  kv: KVLike | undefined,
  options: { advance?: boolean } = {}
): Promise<"cdp" | "vapor"> {
  if (!kv) return "cdp";
  if (options.advance === false) {
    const current = await readJson<AlternatorState>(kv, ALTERNATOR_KEY, DEFAULT_STATE);
    return current.nextPrimary;
  }
  let chosen: "cdp" | "vapor" = "cdp";
  await putWithVerifiedRetry<AlternatorState>(
    kv,
    ALTERNATOR_KEY,
    DEFAULT_STATE,
    (current) => {
      chosen = current.nextPrimary;
      return { nextPrimary: current.nextPrimary === "cdp" ? "vapor" : "cdp" };
    }
  );
  return chosen;
}
