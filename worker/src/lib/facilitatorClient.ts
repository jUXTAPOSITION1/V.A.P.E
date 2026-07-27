/**
 * Prefer-primary-fallback-to-secondary facilitator client. index.ts uses
 * this for a real 50/50 hybrid split between VAPOR (our own facilitator)
 * and CDP's hosted one: which one is "primary" is decided randomly per
 * request (see index.ts), not fixed — this class just guarantees that
 * whichever one is picked, a genuine infrastructure failure on it doesn't
 * take the payment down, by retrying against the other.
 *
 * This is safe to retry blindly on settle too: both VAPOR and CDP respond
 * 200 with `{ success: false, ... }` for a legitimate on-chain/business
 * rejection (insufficient balance, expired authorization, etc) — the
 * HTTPFacilitatorClient only throws for actual infrastructure failures
 * (network error, non-2xx, malformed JSON). And even if the primary
 * attempt secretly succeeded on-chain before erroring back to us, retrying
 * the identical payload against the other facilitator is still safe:
 * EIP-3009's nonce is one-time-use on-chain, so a second settle attempt
 * for an already-consumed authorization simply reverts (no double
 * payment) rather than re-charging the payer.
 */
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
 * request. This patches only the outgoing call to CDP specifically
 * (VAPOR is our own facilitator and already accepts whatever we send it)
 * by duplicating the v1-required fields onto the v2 requirements object
 * before it's serialized -- `resource`/`description` sourced from the
 * signed paymentPayload's own `resource` echo (present on a v2 payload per
 * PaymentPayloadV2Schema), `maxAmountRequired` duplicating `amount`. Never
 * touches scheme/network/asset/payTo/amount/the signature itself.
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

/**
 * Wraps a facilitator client's verify()/settle() so every outgoing call
 * gets the v1-compat fields above. Mutates and returns the same instance
 * (rather than a copy) so callers that read other properties off it
 * afterwards (e.g. withBazaar() reading .url/.createAuthHeaders, or
 * .extensions set later) keep working unchanged.
 */
export function withCdpV1RequirementsCompat<T extends FacilitatorClient>(client: T): T {
  const originalVerify = client.verify.bind(client);
  const originalSettle = client.settle.bind(client);
  client.verify = (paymentPayload, requirements) =>
    originalVerify(paymentPayload, addV1RequirementsCompat(requirements, paymentPayload));
  client.settle = (paymentPayload, requirements) =>
    originalSettle(paymentPayload, addV1RequirementsCompat(requirements, paymentPayload));
  return client;
}

export class FallbackFacilitatorClient implements FacilitatorClient {
  // Which facilitator actually handled the most recent call on this
  // instance — index.ts constructs a fresh instance per request, so this
  // is never stale/cross-request. Lets a caller log which facilitator
  // *really* settled a given payment (not just which one was picked as
  // primary), since a hybrid-split primary can still silently fail over.
  public lastUsed: "primary" | "fallback" = "primary";

  constructor(
    private readonly primary: FacilitatorClient,
    private readonly fallback: FacilitatorClient
  ) {}

  async verify(paymentPayload: PaymentPayload, paymentRequirements: PaymentRequirements): Promise<VerifyResponse> {
    try {
      const r = await this.primary.verify(paymentPayload, paymentRequirements);
      this.lastUsed = "primary";
      return r;
    } catch (err) {
      console.warn(`[x402] primary facilitator verify() failed, falling back: ${errMessage(err)}`);
      this.lastUsed = "fallback";
      return this.fallback.verify(paymentPayload, paymentRequirements);
    }
  }

  async settle(paymentPayload: PaymentPayload, paymentRequirements: PaymentRequirements): Promise<SettleResponse> {
    try {
      const r = await this.primary.settle(paymentPayload, paymentRequirements);
      this.lastUsed = "primary";
      return r;
    } catch (err) {
      console.warn(`[x402] primary facilitator settle() failed, falling back: ${errMessage(err)}`);
      this.lastUsed = "fallback";
      return this.fallback.settle(paymentPayload, paymentRequirements);
    }
  }

  async getSupported(): Promise<SupportedResponse> {
    try {
      const r = await this.primary.getSupported();
      this.lastUsed = "primary";
      return r;
    } catch (err) {
      console.warn(`[x402] primary facilitator getSupported() failed, falling back: ${errMessage(err)}`);
      this.lastUsed = "fallback";
      return this.fallback.getSupported();
    }
  }
}

function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
