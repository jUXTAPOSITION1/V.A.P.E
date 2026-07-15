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
