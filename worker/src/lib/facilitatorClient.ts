import type { FacilitatorClient } from "@x402/core/server";
import type { PaymentPayload, PaymentRequirements, SettleResponse, SupportedResponse, VerifyResponse } from "@x402/core/types";

/**
 * Confirmed via a live settle rejection during the 2026-07-27 transaction
 * outage: CDP's real /verify and /settle endpoints reject a v2
 * paymentRequirements body with HTTP 400 "invalid request body",
 * fieldErrors.paymentRequirements: ["Invalid input: expected string,
 * received undefined", ...] -- two (or more) required-string violations.
 * @x402/core (2.18.0 and 2.19.0 both, so this isn't a version-bump
 * regression) hardcodes x402Version to 2 with no config to opt back into
 * v1, and v2's PaymentRequirements schema simply has no `resource`,
 * `description`, or `maxAmountRequired` fields -- exactly the three
 * required strings v1's schema has that v2 doesn't. CDP's schema still
 * appears to validate against the v1 shape for these fields even for a v2
 * request. This duplicates the v1-required fields onto the outgoing
 * requirements object before it's serialized -- `resource`/`description`
 * sourced from the signed paymentPayload's own `resource` echo (present on
 * a v2 payload per PaymentPayloadV2Schema), `maxAmountRequired` duplicating
 * `amount`. Never touches scheme/network/asset/payTo/amount/the signature
 * itself.
 */
function addV1RequirementsCompat(
  requirements: PaymentRequirements,
  paymentPayload: PaymentPayload
): PaymentRequirements {
  if (paymentPayload.x402Version !== 2 || "resource" in requirements) {
    return requirements;
  }
  const resourceInfo = (paymentPayload as { resource?: { url?: string; description?: string } }).resource;
  const amount = (requirements as { amount?: string }).amount;
  return {
    ...requirements,
    resource: resourceInfo?.url ?? "",
    description: resourceInfo?.description ?? "",
    maxAmountRequired: amount ?? "0",
  } as PaymentRequirements;
}

/** Same BigInt-safe serialization @x402/core's own HTTPFacilitatorClient uses internally. */
function toJsonSafe(obj: unknown): unknown {
  return JSON.parse(JSON.stringify(obj, (_, v) => (typeof v === "bigint" ? v.toString() : v)));
}

/**
 * A from-scratch FacilitatorClient for CDP, used in place of
 * @x402/core's own HTTPFacilitatorClient.
 *
 * Why this exists instead of wrapping/monkeypatching HTTPFacilitatorClient's
 * verify()/settle(): that was tried first (duplicate the v1-compat fields
 * onto the requirements object passed to the real client's methods) and,
 * separately, tested with an unconditional sentinel throw replacing the
 * method body entirely -- confirmed via a live deploy (a temporary build
 * marker on "/" proved the new code was genuinely live) that neither
 * change ever altered the observed settlement error by even one character,
 * across multiple real $0.01 job attempts. That means whatever object
 * ends up invoked for a real settle() was not the instance being patched --
 * despite @x402/core's own source showing only two `.settle(` call sites in
 * the whole dependency tree, both of which trace back to the exact
 * `resourceServer`/`facilitatorClient` this file constructs. Rather than
 * keep reverse-engineering an opaque, unexplained non-effect, this
 * implements verify/settle/getSupported directly against CDP's REST API
 * (the same three endpoints HTTPFacilitatorClient itself calls, using the
 * same request/response shapes and the same createAuthHeaders mechanism),
 * so there is no wrapped instance to fail to intercept -- this class *is*
 * the whole call. It also surfaces CDP's full rejection body (up to 2000
 * chars) instead of @x402/core's internal 200-char responseExcerpt(),
 * which was making this bug harder to diagnose than it needed to be.
 */
export class DirectCdpFacilitatorClient implements FacilitatorClient {
  constructor(
    private readonly url: string,
    private readonly createAuthHeaders?: () => Promise<{
      verify: Record<string, string>;
      settle: Record<string, string>;
      supported: Record<string, string>;
    }>
  ) {}

  private async headersFor(op: "verify" | "settle" | "supported"): Promise<Record<string, string>> {
    if (!this.createAuthHeaders) return {};
    const all = await this.createAuthHeaders();
    return all[op] ?? {};
  }

  private async call(
    op: "verify" | "settle",
    paymentPayload: PaymentPayload,
    requirements: PaymentRequirements
  ): Promise<VerifyResponse | SettleResponse> {
    const patched = addV1RequirementsCompat(requirements, paymentPayload);
    const headers = {
      "Content-Type": "application/json",
      ...(await this.headersFor(op)),
    };
    const response = await fetch(`${this.url}/${op}`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        x402Version: paymentPayload.x402Version,
        paymentPayload: toJsonSafe(paymentPayload),
        paymentRequirements: toJsonSafe(patched),
      }),
    });
    const text = await response.text();
    if (!response.ok) {
      throw new Error(`CDP direct ${op} failed (${response.status}): ${text.slice(0, 2000)}`);
    }
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(`CDP direct ${op} returned non-JSON (${response.status}): ${text.slice(0, 2000)}`);
    }
    return data as VerifyResponse | SettleResponse;
  }

  async verify(paymentPayload: PaymentPayload, requirements: PaymentRequirements): Promise<VerifyResponse> {
    return this.call("verify", paymentPayload, requirements) as Promise<VerifyResponse>;
  }

  async settle(paymentPayload: PaymentPayload, requirements: PaymentRequirements): Promise<SettleResponse> {
    return this.call("settle", paymentPayload, requirements) as Promise<SettleResponse>;
  }

  async getSupported(): Promise<SupportedResponse> {
    const headers = await this.headersFor("supported");
    const response = await fetch(`${this.url}/supported`, { method: "GET", headers });
    const text = await response.text();
    if (!response.ok) {
      throw new Error(`CDP direct getSupported failed (${response.status}): ${text.slice(0, 2000)}`);
    }
    return JSON.parse(text) as SupportedResponse;
  }
}
