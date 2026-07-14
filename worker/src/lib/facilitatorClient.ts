/**
 * Prefer-primary-fallback-to-secondary facilitator client. VAPE's paid
 * offerings are real revenue, so a VAPOR outage (VAPOR is self-hosted on a
 * single Oracle Cloud instance, not a redundant multi-region service like
 * CDP's) must never take the worker's payment path down with it — every
 * verify/settle/getSupported call tries VAPOR first and only falls back to
 * CDP's hosted facilitator if the VAPOR call itself throws.
 *
 * This is safe to retry blindly on settle too: VAPOR always responds 200
 * with `{ success: false, ... }` for a legitimate on-chain/business
 * rejection (insufficient balance, expired authorization, etc) — the
 * HTTPFacilitatorClient only throws for actual infrastructure failures
 * (network error, non-2xx, malformed JSON). And even if VAPOR's primary
 * attempt secretly succeeded on-chain before erroring back to us, retrying
 * the identical payload against CDP is still safe: EIP-3009's nonce is
 * one-time-use on-chain, so a second settle attempt for an
 * already-consumed authorization simply reverts (no double payment) rather
 * than re-charging the payer.
 */
import type { FacilitatorClient } from "@x402/core/server";
import type { PaymentPayload, PaymentRequirements, SettleResponse, SupportedResponse, VerifyResponse } from "@x402/core/types";

export class FallbackFacilitatorClient implements FacilitatorClient {
  constructor(
    private readonly primary: FacilitatorClient,
    private readonly fallback: FacilitatorClient
  ) {}

  async verify(paymentPayload: PaymentPayload, paymentRequirements: PaymentRequirements): Promise<VerifyResponse> {
    try {
      return await this.primary.verify(paymentPayload, paymentRequirements);
    } catch (err) {
      console.warn(`[x402] primary facilitator verify() failed, falling back: ${errMessage(err)}`);
      return this.fallback.verify(paymentPayload, paymentRequirements);
    }
  }

  async settle(paymentPayload: PaymentPayload, paymentRequirements: PaymentRequirements): Promise<SettleResponse> {
    try {
      return await this.primary.settle(paymentPayload, paymentRequirements);
    } catch (err) {
      console.warn(`[x402] primary facilitator settle() failed, falling back: ${errMessage(err)}`);
      return this.fallback.settle(paymentPayload, paymentRequirements);
    }
  }

  async getSupported(): Promise<SupportedResponse> {
    try {
      return await this.primary.getSupported();
    } catch (err) {
      console.warn(`[x402] primary facilitator getSupported() failed, falling back: ${errMessage(err)}`);
      return this.fallback.getSupported();
    }
  }
}

function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
