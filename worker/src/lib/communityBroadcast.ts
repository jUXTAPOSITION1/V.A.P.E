/**
 * community_intel_broadcast — VAPE's latest 6-hourly consolidated security +
 * market intel broadcast (agents/broadcast.py's real output, committed to
 * intel/broadcasts/broadcast-*.md on every run). Real gap this closes: this
 * offering has been listed (auto:true) and fulfilled via ACP
 * (agents/acp_fulfill.py::_community_broadcast()) since day one, but was
 * never x402-payable (x402:false) — this ports the exact same "find the
 * newest broadcast file" logic to the Worker, reading the public repo's own
 * committed content directly rather than duplicating any generation logic.
 */
const REPO = "jUXTAPOSITION1/V.A.P.E";
const BROADCASTS_DIR_API = `https://api.github.com/repos/${REPO}/contents/intel/broadcasts`;
// GitHub's Contents/REST API requires a User-Agent or rejects the request
// outright — unauthenticated calls against a public repo are otherwise fine,
// just subject to GitHub's stricter unauthenticated rate limit (60/hr/IP).
const UA = { "User-Agent": "VAPE-x402-worker/1.0", Accept: "application/vnd.github+json" };

export interface CommunityBroadcastResult {
  error?: string;
  note?: string;
  file?: string;
  content?: string;
}

export async function latestCommunityBroadcast(): Promise<CommunityBroadcastResult> {
  let listing: any;
  try {
    const r = await fetch(BROADCASTS_DIR_API, { headers: UA });
    if (!r.ok) return { error: `github_api_${r.status}`, note: "could not list intel/broadcasts/" };
    listing = await r.json();
  } catch (e: any) {
    return { error: String(e?.message || e) };
  }
  if (!Array.isArray(listing)) return { error: "unexpected_response", note: "intel/broadcasts/ listing was not an array" };

  // Only real consolidated broadcasts (agents/broadcast.py's own naming
  // convention, broadcast-YYYY-MM-DD-HH.md) — the directory also holds
  // x-thread-draft-*.md files (a separate, unrelated offering's drafts) that
  // sort lexicographically alongside them and must not be picked up here.
  const broadcasts = listing.filter((f: any) => typeof f?.name === "string" && /^broadcast-\d{4}-\d{2}-\d{2}-\d{2}\.md$/.test(f.name));
  if (!broadcasts.length) return { error: "no_broadcast_yet", note: "no broadcast generated yet" };

  // Filenames embed the UTC timestamp lexicographically (YYYY-MM-DD-HH), so
  // the newest file always sorts last — same ordering agents/acp_fulfill.py's
  // sorted(glob(...), reverse=True) relies on.
  broadcasts.sort((a: any, b: any) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  const latest = broadcasts[broadcasts.length - 1];
  if (!latest?.download_url) return { error: "no_download_url", note: `${latest?.name ?? "latest broadcast"} had no download_url` };

  try {
    const r = await fetch(latest.download_url, { headers: UA });
    if (!r.ok) return { error: `github_raw_${r.status}`, note: `could not fetch ${latest.name}` };
    const content = await r.text();
    return { file: latest.name, content };
  } catch (e: any) {
    return { error: String(e?.message || e) };
  }
}
