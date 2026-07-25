/**
 * Triggers a GitHub Actions workflow_dispatch to run a real, multi-step job that
 * can't fit inside a Worker's request/response window — specifically the
 * bounty_deep_dive offering's actual audit (recon + Slither + a frontier-model
 * source review), which genuinely takes minutes, not the sub-second turnaround
 * every other x402 route here returns.
 *
 * Needs a fine-grained PAT scoped to this repo with "Actions: write" +
 * "Contents: read" — Workers have no equivalent of the GITHUB_TOKEN Actions
 * injects into its own workflow runs, so this is a real, separate secret:
 *   wrangler secret put GH_DISPATCH_TOKEN
 */
const REPO = "jUXTAPOSITION1/V.A.P.E";

export interface DispatchResult {
  ok: boolean;
  status: number;
  body: string;
}

export async function dispatchDeepDiveAudit(
  token: string,
  address: string,
  chain: string,
  callbackUrl?: string,
): Promise<DispatchResult> {
  const inputs: Record<string, string> = { address, chain };
  if (callbackUrl) inputs.callback_url = callbackUrl;

  const res = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/deep-dive-bounty.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "vape-x402-worker/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ ref: "main", inputs }),
    },
  );
  // GitHub returns 204 No Content on a successful dispatch — no run ID is
  // handed back synchronously (dispatch is fire-and-forget by design), so
  // job tracking is via the worker's own KV job record (index.ts's jobId ->
  // /scan/bounty_deep_dive/callback -> /status polling) or the optional
  // callback_url webhook — never a public repo commit (a paid buyer's PoC
  // is never committed to this public repo).
  const body = res.status === 204 ? "" : await res.text().catch(() => "");
  return { ok: res.status === 204, status: res.status, body };
}

export interface ExternalAuditDispatchArgs {
  owner: string;
  repo: string;
  ref?: string;
  programName?: string;
  paths?: string;
  callbackUrl?: string;
}

/** Sibling of dispatchDeepDiveAudit() for a source-repo target instead of an
 * on-chain address (e.g. Move/Sui or any external bounty-program repo) —
 * same fire-and-forget REST dispatch shape, targeting
 * agents/external_audit.py via .github/workflows/external-bounty-audit.yml. */
export async function dispatchExternalBountyAudit(
  token: string,
  args: ExternalAuditDispatchArgs,
): Promise<DispatchResult> {
  const inputs: Record<string, string> = { owner: args.owner, repo: args.repo };
  if (args.ref) inputs.ref = args.ref;
  if (args.programName) inputs.program_name = args.programName;
  if (args.paths) inputs.paths = args.paths;
  if (args.callbackUrl) inputs.callback_url = args.callbackUrl;

  const res = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/external-bounty-audit.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "vape-x402-worker/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ ref: "main", inputs }),
    },
  );
  const body = res.status === 204 ? "" : await res.text().catch(() => "");
  return { ok: res.status === 204, status: res.status, body };
}
