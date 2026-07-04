/**
 * CDP (Coinbase Developer Platform) Bearer JWT generation for authenticating
 * against a mainnet x402 facilitator. Ported from @coinbase/cdp-sdk's real
 * `generateJwt` (src/auth/utils/jwt.ts) rather than depending on the full SDK
 * package, which pulls in axios + Solana packages unrelated to this one
 * function and unnecessary weight/risk in a Workers bundle. Uses `jose`
 * (the same JWT library the SDK itself uses) and native Web Crypto/base64
 * instead of Node's `Buffer`, so it needs no `nodejs_compat` polyfill.
 *
 * Supports both CDP key formats: EC (PEM, ES256) and Ed25519 (base64, EdDSA).
 */
import { SignJWT, importPKCS8, importJWK } from "jose";

function randomNonceHex(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function buildEcJwt(privateKeyPem: string, keyId: string, claims: Record<string, unknown>, now: number, expiresIn: number) {
  const ecKey = await importPKCS8(privateKeyPem, "ES256");
  return new SignJWT(claims)
    .setProtectedHeader({ alg: "ES256", kid: keyId, typ: "JWT", nonce: randomNonceHex() })
    .setIssuedAt(now)
    .setNotBefore(now)
    .setExpirationTime(now + expiresIn)
    .sign(ecKey);
}

async function buildEdwardsJwt(privateKeyB64: string, keyId: string, claims: Record<string, unknown>, now: number, expiresIn: number) {
  const decoded = base64ToBytes(privateKeyB64);
  if (decoded.length !== 64) throw new Error("Invalid Ed25519 key length (expected 64 bytes: 32 seed + 32 public)");
  const seed = decoded.subarray(0, 32);
  const publicKey = decoded.subarray(32);
  const jwk = { kty: "OKP", crv: "Ed25519", d: bytesToBase64Url(seed), x: bytesToBase64Url(publicKey) };
  const key = await importJWK(jwk, "EdDSA");
  return new SignJWT(claims)
    .setProtectedHeader({ alg: "EdDSA", kid: keyId, typ: "JWT", nonce: randomNonceHex() })
    .setIssuedAt(now)
    .setNotBefore(now)
    .setExpirationTime(now + expiresIn)
    .sign(key);
}

/** True if `str` parses as a PEM EC private key jose can import for ES256. */
async function isEcKey(str: string): Promise<boolean> {
  try {
    await importPKCS8(str, "ES256");
    return true;
  } catch {
    return false;
  }
}

export async function generateCdpJwt(opts: {
  apiKeyId: string;
  apiKeySecret: string;
  requestMethod: string;
  requestHost: string;
  requestPath: string;
  expiresIn?: number;
}): Promise<string> {
  if (!opts.apiKeyId) throw new Error("CDP apiKeyId is required");
  if (!opts.apiKeySecret) throw new Error("CDP apiKeySecret is required");

  const now = Math.floor(Date.now() / 1000);
  const expiresIn = opts.expiresIn ?? 120;
  const claims = {
    sub: opts.apiKeyId,
    iss: "cdp",
    uris: [`${opts.requestMethod} ${opts.requestHost}${opts.requestPath}`],
  };

  if (await isEcKey(opts.apiKeySecret)) {
    return buildEcJwt(opts.apiKeySecret, opts.apiKeyId, claims, now, expiresIn);
  }
  // Not a recognized EC PEM key — try Ed25519 (base64, 64 bytes); buildEdwardsJwt
  // throws its own clear error if that format check fails too.
  return buildEdwardsJwt(opts.apiKeySecret, opts.apiKeyId, claims, now, expiresIn);
}
