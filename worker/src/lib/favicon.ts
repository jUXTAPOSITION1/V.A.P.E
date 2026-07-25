/**
 * VAPE's 32x32 icon, embedded as base64 so the Worker can serve /favicon.ico
 * itself with no redirect and no external fetch.
 *
 * Why this exists: x402scan's discovery spec asks a registered origin to
 * "serve a /favicon.ico at your API root to display an icon" — it's what the
 * explorer/marketplace renders next to the listing. A 302 to the GitHub Pages
 * copy would work in a browser but is not reliably followed by directory
 * crawlers, and a runtime fetch would make an unpaid discovery route depend on
 * a third-party host being up. Inlining 2.4KB avoids both.
 *
 * Source of truth is docs/assets/favicon-32.png (the same file ICON_URL in
 * index.ts points at, so the site, the x402 Bazaar `iconUrl` extension, and
 * this route all show the identical mark). Regenerate after changing that PNG:
 *   python3 -c "import base64;print(base64.b64encode(open('docs/assets/favicon-32.png','rb').read()).decode())"
 *
 * Served as image/png despite the .ico path: every browser and crawler
 * dispatches on Content-Type, not the extension, and PNG favicons have been
 * universally supported for years.
 */
const FAVICON_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAFXklEQVR4nLWWW3MURRTHz+me6d6ZWbJAggYQNBgEjEpZJaVg" +
  "uAYJYiAhAfRB/QyUD5Sfg/IbKEpMFsLVUiAEkoABuUghiRjLCiGCpkJ2w87O7sx0Hx8GVrK5EB44NU9T3efX//M/p2dQSBue" +
  "Z7Dnmh0AjHE0xhhDIgAARNCatCYAmjYDMoYTdulJAZjzMkWbDWkicUScNDcRESrfyxe9F9IpHAsjDxBRqbC6unrhggW+7wOi" +
  "EObt3r/6ewfyMBYoH6GYQUAmFwJKllVVVC572c8HgCCEGBoa6urq4tygSJSQtpC27ZQAwL59XxJRKpUaS6e1DjtOXah6obZ8" +
  "biUXQkonWhk9UjqGEOVzKt94cUt3xyWlw3R6LJVKEdHevV8AgO2URCsfmayUYsz4+psD/f39ruuOplKDg0NLX1+86LU55HOD" +
  "GTTeCQLi3NS+saSq/NUVi+4ODqVSo67r9vX1Hfj2O8ZNpVS0khWqKWPWvb8Hz507nygpiYpekiip2bbGy3nStIn0OADpmGn7" +
  "vl+zbbXjOIgIgIlEydmzHcP/3pMy9qg+E9u0pTWptAYAxpiX9TbVrp01x9IhFPmMiGGgZ801129ek816iMgYBkHY0pqE8W79" +
  "D1BKGWass7Ozt7fXsiwAyOXylZUVq9a86XqjnI9raM4N10u9W/32kiUV+VweAGzbvnnzt4sXLpoiVqhPsQIhRNZ9ePTYcce2" +
  "iQgREVnDzh0EqmgWiAhANzbVAxAiEpFlWUeOHM3lXNM0J1cAAFprRH7ocFsqneacI2Imk1m/Yd0rFZX5nFeoEmMsn/cqly6v" +
  "rn4/k3ER0TCMkZGRtrajyIwnp2wSgIxZv/fe6u6+EI/HtdZBEMwrK9teV0c65JwXAKRVQ/320tLSMAy11vG4c76zs7//tpSx" +
  "6QAAgIhEuqU1yRgDAESWy+UaGnYIaYVhGK0JgiBmOfX123OPZSFiS0sSQE+c+WKA1pob8vTp0wMDA1JKRMhmsytXvrXqnVV+" +
  "3uOccc4DP7f6vdVVVVVuNouIlhX7o//P9vazhimLjj8JgIiklA9Ghk+c/CEed4iIiGIx2dTUCECPW5B2794lhAACrbXjOCdO" +
  "nBxLPxBCFtp/SkAkApAlk4eyWY8xxhl33Wxt7ZaysnLf930/X16+cHPNpkwmg4ic80zGTSYPI7KJx58SIIR19cqVq1evOY6j" +
  "SedyucWLF23ZslmFeRX6Wz+sXfjSgnw+T0S2bV+6dPnGjV+FtGYKAADD4GHoHzrcJoSIBkIp1djUCMhMEdvV1BQEYdT+pmm2" +
  "tia1Cgo9VhQ46ScTEYPAnz9/wbmOM47jKKUQkTG2dt1G13Wv/NID0eQbxtjY2Lr1m4aHh03TnGjAlAqISMrY0N2BM2fa43FH" +
  "KRWGYSKR+OTjPffv3b3V22dZVhiGs+Lxn3469c/9ISknsXc6QEFJa+shpTRjjDHmum59/Q5EdvBgc5TRD/yJt9uMSlTQYXB+" +
  "6tSPK1Ys9zyPiBKJxI76ndevX798uWdeaenV69e2bv2IaKpP6tMUmKbpeZljx47HYjGlFBExhp9/9mlqdKS9/Wxi9uxkss3P" +
  "e6ZpTJNkOoDWGhk/3HZkdHTUNE3GWCbjbtiwfvbs0ubm71Op1PHjJ5AZ+onL+ZkBUlq3b/d1dXfbth0Eged5ZWVlddvrurq6" +
  "9u//6s6dO0JIPYW9UUznAQBwzr3sw6Zde1pbmtPpNAA4jvNzT09NzQecG2ras88IEOmwbWvjxo3RRQsEBNDRcd51M4ZhTNWd" +
  "zwAAACIKfO/JN6awGGNPzT5TACIwNu4mmElxopiuwwpB9AwZi+K5/13/Bw/SvUZ/LgkLAAAAAElFTkSuQmCC";
  "f955J5ulVVW32q3zm1u9ft/VZb5YBGFgrSVicV5E+2dH3cmk3elUdb3I8/8FaT0j6B8rT24AAAAASUVORK5CYII=";

function decode(b64: string): Uint8Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

// Decoded once per isolate at module load, not per request.
export const FAVICON_PNG: Uint8Array = decode(FAVICON_PNG_BASE64);
export const FAVICON_CONTENT_TYPE = "image/png";
