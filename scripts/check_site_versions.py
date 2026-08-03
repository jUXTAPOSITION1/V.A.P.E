#!/usr/bin/env python3
"""Checks docs/ for pinned CDN package versions against each package's real
latest npm release.

Dependabot only sees package.json/lockfiles — it has no visibility into
version strings hardcoded into CDN URLs inside static HTML/JS, which is how
docs/ (GitHub Pages) pulls jsPDF, Font Awesome, and the @x402/* client SDK
used by hire.js. This closes that specific gap; it is not a replacement for
Dependabot (see .github/dependabot.yml for the real package-manager side).

Each TRACKED entry's regex extracts whatever version is currently on disk
rather than assuming a fixed prior value, so a bump applied by one run
never makes the next run's baseline stale.

Same-major bumps (patch/minor) are rewritten in place automatically, since
semver's contract says those shouldn't break a call site. A major-version
jump is only reported (via version-review-needed.json, surfaced by
version-currency.yml as a tracking issue) — a CDN vendor library's public
API can change across majors and there is no compiler here to catch a
broken call site in a page-relative <script> tag, so that needs a human to
check actual usage before bumping.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = r"(\d+\.\d+\.\d+)"

TRACKED = [
    {
        "file": REPO_ROOT / "docs/assets/hire.js",
        "package": "@x402/evm",
        "pattern": re.compile(r"@x402/evm@" + VERSION_RE),
    },
    {
        "file": REPO_ROOT / "docs/assets/hire.js",
        "package": "@x402/fetch",
        "pattern": re.compile(r"@x402/fetch@" + VERSION_RE),
    },
    {
        "file": REPO_ROOT / "docs/index.html",
        "package": "jspdf",
        "pattern": re.compile(r"cdn\.jsdelivr\.net/npm/jspdf@" + VERSION_RE),
    },
    {
        # Font Awesome moved from the cdnjs CDN to a locally vendored copy
        # at some point -- docs/index.html's own <link> has referenced
        # assets/fontawesome/css/all.min.css (no version string at all)
        # ever since, so the old cdnjs-URL pattern below could never match
        # again and just kept filing the same unfixable review issue. The
        # vendored file's own real version banner (present in every Font
        # Awesome release) is the one signal left to track the actual
        # installed version against npm's latest.
        "file": REPO_ROOT / "docs/assets/fontawesome/css/all.min.css",
        "package": "@fortawesome/fontawesome-free",
        "pattern": re.compile(r"Font Awesome Free " + VERSION_RE),
        # This banner is just a label on already-downloaded files (css +
        # webfonts) -- rewriting it in place would claim a newer version
        # while shipping the old assets. Every bump here needs a human to
        # actually re-vendor the files, so route it straight to manual
        # review regardless of whether it's a same-major bump.
        "vendored": True,
    },
]


def latest_version(pkg: str) -> str:
    url = f"https://registry.npmjs.org/{pkg}/latest"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.load(resp)["version"]


def major(version: str) -> str:
    return version.split(".", 1)[0]


def main() -> int:
    applied = []
    needs_review = []

    for entry in TRACKED:
        pkg, path, pattern = entry["package"], entry["file"], entry["pattern"]
        text = path.read_text()
        matches = list(pattern.finditer(text))
        if not matches:
            needs_review.append({
                "file": str(path.relative_to(REPO_ROOT)),
                "package": pkg,
                "reason": "pattern not found in file — TRACKED entry is out of date",
            })
            continue
        # A package can be imported at more than one call site (hire.js does
        # this for its status-check vs. pay flows) — every occurrence must
        # be on the same pin, or this repo already has silent drift that
        # needs a human to look at, not an automated bump.
        currents = {m.group(1) for m in matches}
        if len(currents) > 1:
            needs_review.append({
                "file": str(path.relative_to(REPO_ROOT)),
                "package": pkg,
                "reason": f"occurrences already disagree on version: {sorted(currents)}",
            })
            continue
        current = matches[0].group(1)

        try:
            latest = latest_version(pkg)
        except Exception as exc:  # network hiccup, package renamed, etc.
            print(f"WARN: could not check {pkg}: {exc}", file=sys.stderr)
            continue

        if latest == current:
            continue

        result = {"file": str(path.relative_to(REPO_ROOT)), "package": pkg, "old": current, "latest": latest}

        if entry.get("vendored"):
            result["reason"] = "vendored files, not a CDN URL — needs a human to re-download and replace them"
            needs_review.append(result)
            continue

        if major(latest) != major(current):
            result["reason"] = "major version bump — needs manual review of call sites"
            needs_review.append(result)
            continue

        new_text = pattern.sub(lambda m: m.group(0).replace(current, latest), text)
        path.write_text(new_text)
        applied.append(result)

    if applied:
        print("Applied same-major bumps:")
        for e in applied:
            print(f"  {e['file']}: {e['package']} {e['old']} -> {e['latest']}")
    if needs_review:
        print("Needs manual review (major bump or pattern mismatch):")
        for e in needs_review:
            print(f"  {e['file']}: {e['package']} {e.get('old', '?')} -> {e.get('latest', '?')} ({e['reason']})")
    if not applied and not needs_review:
        print("Everything tracked is already current.")

    review_path = REPO_ROOT / "version-review-needed.json"
    if needs_review:
        review_path.write_text(json.dumps(needs_review, indent=2))
    elif review_path.exists():
        review_path.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
