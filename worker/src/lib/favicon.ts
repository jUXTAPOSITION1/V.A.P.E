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
 * Source of truth is docs/assets/favicon-32.png — but NOT a plain resize of
 * icon-512.png. That larger asset has a thin, low-contrast purple accent
 * stripe (~40px of a 512px canvas, already close in luminance to the
 * near-black background) framing one stroke of the V. At 512/192/180px that
 * stripe reads fine, but downscaling straight to 32x16 cannot preserve ~1px
 * of that low-contrast detail — every resampler (LANCZOS included) blends it
 * into a soft gray halo around the glyph edges, which is exactly the
 * fuzziness reported against the version x402scan was showing. Fixed by
 * flattening icon-512.png to solid two-tone (off-white glyph on near-black,
 * thresholded on max-channel luminance, no gradient) BEFORE downsampling —
 * the small sizes trade the accent stripe for a crisp edge once there's no
 * sub-pixel gradient left for the resize to alias. Regenerate after changing
 * the source:
 *   python3 -c "
 *   from PIL import Image; import numpy as np, base64
 *   src = Image.open('docs/assets/icon-512.png').convert('RGB')
 *   arr = np.array(src).astype(int); lum = arr.max(axis=2)
 *   flat = np.zeros_like(arr)
 *   flat[lum > 140] = [230,230,230]; flat[lum <= 140] = [6,7,10]
 *   flat_im = Image.fromarray(flat.astype('uint8'), 'RGB')
 *   flat_im.resize((32,32), Image.LANCZOS).save('docs/assets/favicon-32.png')
 *   print(base64.b64encode(open('docs/assets/favicon-32.png','rb').read()).decode())"
 *
 * Served as image/png despite the .ico path: every browser and crawler
 * dispatches on Content-Type, not the extension, and PNG favicons have been
 * universally supported for years.
 */
const FAVICON_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAFGElEQVR4nLVWa09UZxB+L+c992VpQLDBaGM0xjSKXzCxERRBpKjc" +
  "FmMa+yPaJm1/h+lvaGvdXblYtFEXA4iRCGKkVSo1JqVqVS676577Oe/0w8EFlmXFpE72y57MzDPP3N7BoqSiDynkg3pHCAlr0Agh" +
  "hAAAQghjzDnnnL/TRWmr1QDYtnJrbakky6HlRoIxti0ToTVxiJKG0LIVDmuAMQ5878jRo9u2bXNdFwHIsjx1//7v09MCEzfiQQjx" +
  "PLe2trZ2/37bthFGoijNzc2NDA9TgS1HJkqqKKmqVoYQ+va77wEgk8lks1kAuHr1N0yoJOuhzvqfJGuUslRqCACy2WwmkwGAr77+" +
  "BiGkamWhzgoDz3Wrq6uHh4c0TQuCACEkimLLibbpB/clWV1PghBi22Zd3cErg5dN08QYC4KQyWQajhxbWJhnTAwZLHcRAEiy/OLF" +
  "P8PDI9FoFGOMECorK4vFugA4IUWajRCCgHd3d2mahjHGGEej0VTq5utXLyRppXKFlvFEMgyfUmqa5sm2Nj0SdV03hFxdW8dxouUV" +
  "n7e2GoZBKcUYe54bTyQQWqO5AhAEAROV0dFbDx8+UlUVACzL2rNnd+PRRt+zC0gQQgLfaWo6tmvXTtu2AUBV1enpP8bvjDNRDkMs" +
  "woAxZplv+vsHFEUJk44x7jnTXRAUQihs+p5Yd5gJzrksy319/bZtMMaKMwj1MKZ9/QPpdFoQBEJILmccaWjY8clOx7byWSKEOI61" +
  "a/ee+vrDuVyOEMIYW1hY6OsfwEQoaIdCAElW/px5ODZ2W9d1zrnrulVVVe3tpzj3KaV5AOB+R8fpysoKz/M457quj4yOPnkyK0lK" +
  "KQCEECEYgMfjiTDphBDHcbo6O0VR9n0/1PE8T5LVzo4Oy1qpTfxiAgHHhblcBxAEnArS9Rupp0+fyrKMMTYM48CB2rq6g65jUUop" +
  "pZ5rHzp0aN++T8P2VxRldvavoaGbApOLjEvBfwCQJGlp8fXglavhxHHOJUmK9XQjBG/LAGd6YuEoBUGgqurg4GA2uySK4vrFVWSC" +
  "OOcIk2Sy1zTNMGTDMFpPtFRUVruO67pO9daa48ebw/JSSnO5N4lkL8ak6MoqDiCKyr17kxMTE5qmAYDjODu2b2853uz7duC7rSda" +
  "ampqHMcBAF3Xx8fvTk8/ENeVd0MAhJAg0MB3k5d6RXF5lQacx2LdCBHGpJ6emO/7hBDOuSAI8USSB16+xwoEF30yw7nfuvXjkeGh" +
  "SCTi+z7GmBDy2eEG0zAnJ8bz3tPpdH1D4/z8PGOs6MtRnAEASJL8/NnfqdSQpmmcc9/3o9HoF2fPvvz32czMjKIonufpun7t2vVX" +
  "L5+v3m6bAsjLxXgiCJbDN02zs7MdY/LjTxdEUUQIu657MR5utw1fveIpyvOglKRuXNu7d69pmgBQXh493d41NTU1OXG3qmrLxMRk" +
  "a2sbWj9dm2TAGLMto69/QJblt7uPfHnuXCa9mEqlIpFI8lKv61qCIJRwUgqAc44J7evrX1xcZIwRQgzDaGpqLP+o4ucLvywtLV2+" +
  "/Csmwurl/N4AkqTMPn48emtMVRXP80zL3LKl8tTJk2NjY+fP/zA3NyeK0jvOjtKXHaXUMt90dcWSyXg2m0UIRSL67dt3mpqbKWWl" +
  "Y98UQMhDVdX6+sOEEASAMAaAkZHRcJGUDn9TAAghAPBca/UXJir5a+5/AMAIkbWbYDPJCaVUh+UF3sdjgXzw6/o/hjmrm1Wq3aEA" +
  "AAAASUVORK5CYII=";

function decode(b64: string): Uint8Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

// Decoded once per isolate at module load, not per request.
export const FAVICON_PNG: Uint8Array = decode(FAVICON_PNG_BASE64);
export const FAVICON_CONTENT_TYPE = "image/png";
