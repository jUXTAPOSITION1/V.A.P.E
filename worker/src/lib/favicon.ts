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
  "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" +
  "L/72b8Jm+9vf+uZb3/gH7/Xzf/aV11//TLPTlro2hm1gq9q52jEbZlrN5+1mm4hg2NbODddGgY1H587XVRXHYRCGdVVZCzbG" +
  "AJ1O9/YHt7/211/d399fTMeBiQvRr3/9a+//6l2ybMKA2QKoysKYoNGIiqIYjIaVk26nN5mOrUK3N7eTZvLowcM8X8ZxZANb" +
  "V5WoMJlGM3r51Rs/+uGP/vRLb7z1jb//zf37ls36aBAa83f//h9/8MqNd27eLJaF805FODBJ0nB15Zy2Ot1WrzOejLnb7Vy5" +
  "sru9vbOYz4rVqiiKKApPnw7xcm57c/u5i6/94ed+cPNnSad14/r1a9de3Nna/P5Pfnr91VcvX97d3tkRcepFVcMozJdFVVbl" +
  "arXz/MWdnefa7ba99PyV0ZnhNE2fPHiwsbFhrI3jeBEEUFH1F59/3hr79OnTu/d+99a3/+3s+oaqztPp++/+stFIolAu7V65" +
  "t7dXLQtrA2NsVdX5YjGdTqMoSpLWczvP8e7uR4qimo7H2fjIOSeqxrANjHdy5tzG5vbW4w8fzeZpVRTv3br14cFBuVr95v33" +
  "ppPJ0eHTB/v3ev3ehc0tgbI1zIZAxWp59OHB8fGhiFy6fIVb7STLMl/XJm5F7TYzOSfMBKK14dA5Px4fF2W5fu78K5/85O7u" +
  "lbW13ksf/9jWzg4RZ/O5q91wNAzCEIDzLoyCqNkO4pY6Xa2W1gY2nU69R7e/1t9Yb7Q71TzzzkHIBiaKwtk0LfJlo9G8d2fv" +
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
