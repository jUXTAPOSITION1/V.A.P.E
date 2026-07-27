#!/usr/bin/env python3
"""Read-only(-ish) diagnostic: captures the EXACT outgoing x402 PaymentPayload
DATA AGENT's real signing wallet produces, right before the x402 SDK sends it
to CDP's facilitator.

Why this exists: CDP's /settle endpoint has been rejecting real payments with
two different errors -- some with "Facilitator settle failed (400): invalid
request body" (a schema mismatch inside `paymentPayload` itself), others with
"Facilitator settle failed (402): a valid payment method is required". The
worker's response only ever surfaces CDP's own (often truncated) error text,
never the payload that provoked it. This monkeypatches
x402ClientSync.create_payment_payload (the exact call the SDK's own
x402HTTPAdapter makes right before signing+sending) to print the full
payload as JSON, so the actual wire-level content -- scheme, network, payTo,
asset, the signed authorization -- is visible for the first time, rather than
guessed at from CDP's own truncated error strings.

Spends one real $0.01 job (same as any other DATA AGENT hire) -- this is not
free, but it's the only way to see the real payload short of a packet
capture.
"""
import json
import sys

sys.path.insert(0, ".")

from x402 import x402ClientSync  # noqa: E402

_original = x402ClientSync.create_payment_payload


def _logged_create_payment_payload(self, payment_required, resource=None, extensions=None):
    payload = _original(self, payment_required, resource=resource, extensions=extensions)
    try:
        print("[diag] outgoing PaymentPayload:")
        print(json.dumps(json.loads(payload.model_dump_json(by_alias=True, exclude_none=False)), indent=2))
    except Exception as e:
        print(f"[diag] could not serialize payload for logging: {e}")
        print(f"[diag] repr: {payload!r}")
    return payload


x402ClientSync.create_payment_payload = _logged_create_payment_payload

from agents import data_agent  # noqa: E402

session = data_agent._build_session("data-agent")
if session is None:
    print("[diag] _build_session() returned None -- check DATA_AGENT_PRIVATE_KEY / wallet match")
    sys.exit(1)

deliverable, paid = data_agent.hire(session, "chain_overview", {})
print(f"[diag] paid={paid} deliverable={deliverable}")
