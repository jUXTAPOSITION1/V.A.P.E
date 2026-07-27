#!/usr/bin/env python3
"""Read-only diagnostic: fetches 402index.io's own docs page from a real,
unrestricted-egress environment (GitHub Actions), so the exact claim/verify
request/response shape can be confirmed from source rather than guessed at.

Why this exists: 402index.io/api-docs returns HTTP 403 to automated fetchers
from the dev sandbox this repo is normally edited in (confirmed directly,
2026-07-27) -- CI's real egress is the only way to read it. This mirrors the
same "confirm from a real network path via CI, not sandbox guesswork"
pattern already used for agents/x402_directory_register.py's own documented
POST /api/v1/register schema and diag_x402_payload.py's CDP debugging.

Prints the full page text (docs) plus a best-effort scan for any of a few
plausible OpenAPI/spec JSON paths, so the claim/verify flow referenced in
agents/x402_directory_register.py's module docstring
("402index.io domain verification") can actually be implemented against a
confirmed real schema instead of a fabricated one.
"""
import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (VAPE-diagnostic/1.0; +https://github.com/jUXTAPOSITION1/V.A.P.E)"}


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:
        return 0, str(e)


print("=== GET https://402index.io/api-docs ===")
code, body = _get("https://402index.io/api-docs")
print(f"HTTP {code}, {len(body)} bytes\n")
print(body)

print("\n\n=== Candidate structured-spec endpoints ===")
for path in ("/api/openapi.json", "/openapi.json", "/api-docs.json", "/api/v1/openapi.json", "/api/docs.json"):
    code, body = _get(f"https://402index.io{path}")
    print(f"\n--- {path}: HTTP {code} ({len(body)} bytes) ---")
    if code == 200:
        try:
            print(json.dumps(json.loads(body), indent=2)[:8000])
        except Exception:
            print(body[:2000])

print("\n\n=== Existing listing check: GET /api/v1 (root, for any claim-related hints in a listing/search response) ===")
code, body = _get("https://402index.io/api/v1/search?q=VAPE")
print(f"HTTP {code}, {len(body)} bytes")
print(body[:4000])
