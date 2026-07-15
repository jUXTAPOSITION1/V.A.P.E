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
 */
import { KVLike, putWithVerifiedRetry } from "./jobLog";

const ALTERNATOR_KEY = "DATA_AGENT_ALTERNATOR";

interface AlternatorState {
  nextPrimary: "cdp" | "vapor";
}

export async function nextDataAgentFacilitator(kv: KVLike | undefined): Promise<"cdp" | "vapor"> {
  if (!kv) return "cdp";
  let chosen: "cdp" | "vapor" = "cdp";
  await putWithVerifiedRetry<AlternatorState>(
    kv,
    ALTERNATOR_KEY,
    { nextPrimary: "cdp" },
    (current) => {
      chosen = current.nextPrimary;
      return { nextPrimary: current.nextPrimary === "cdp" ? "vapor" : "cdp" };
    }
  );
  return chosen;
}
