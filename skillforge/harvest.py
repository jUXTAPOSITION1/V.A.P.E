#!/usr/bin/env python3
"""SKILLFORGE harvest — real-data intel collector. No LLM, no hypotheticals.
Sources:
  1. NVD CVE feed (smart-contract / Solidity / blockchain keywords), last 24h.
  2. Latest releases of registered tools (version drift detection).
Appends real entries to skillforge/memory/findings.jsonl and updates tool versions.
"""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = os.path.join(ROOT, "skillforge", "memory")
FINDINGS = os.path.join(MEM, "findings.jsonl")
REGISTRY = os.path.join(MEM, "tools-registry.json")

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "VAPE-SKILLFORGE"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def existing_refs():
    refs = set()
    if os.path.exists(FINDINGS):
        for line in open(FINDINGS):
            try: refs.add(json.loads(line).get("ref"))
            except: pass
    return refs

def append(entry):
    with open(FINDINGS, "a") as f:
        f.write(json.dumps(entry) + "\n")

def harvest_cves(seen):
    """NVD CVE API 2.0 — blockchain/solidity keywords, last 24h. Real data only."""
    out = []
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)
    for kw in ("smart contract", "solidity", "ethereum", "blockchain"):
        params = urllib.parse.urlencode({
            "keywordSearch": kw,
            "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "pubEndDate": end.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": 50,
        })
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?{params}"
        try:
            data = get(url, timeout=40)
        except Exception as e:
            print(f"[harvest] NVD {kw} fetch failed: {e}", file=sys.stderr)
            time.sleep(2); continue
        for v in data.get("vulnerabilities", []):
            cve = v.get("cve", {})
            cid = cve.get("id")
            ref = f"nvd:{cid}"
            if not cid or ref in seen: continue
            seen.add(ref)
            desc = next((d["value"] for d in cve.get("descriptions", []) if d.get("lang")=="en"), "")
            metrics = cve.get("metrics", {})
            sev = "UNKNOWN"
            for mk in ("cvssMetricV31","cvssMetricV30","cvssMetricV2"):
                if metrics.get(mk):
                    sev = metrics[mk][0].get("cvssData",{}).get("baseSeverity") \
                          or metrics[mk][0].get("baseSeverity","UNKNOWN")
                    break
            out.append({"ts": now(), "source": "nvd-cve", "severity": sev,
                        "target": cid, "summary": desc[:300], "ref": ref})
        time.sleep(1)  # respect NVD rate limit
    return out

def harvest_tool_releases(seen):
    """Check latest GitHub release tag for each registered tool; flag version drift."""
    out = []
    if not os.path.exists(REGISTRY): return out
    reg = json.load(open(REGISTRY))
    changed = False
    for tier, tools in reg.get("tiers", {}).items():
        for t in tools:
            repo = t.get("repo")
            if not repo: continue
            try:
                rel = get(f"https://api.github.com/repos/{repo}/releases/latest", timeout=20)
            except Exception:
                continue
            tag = rel.get("tag_name")
            if not tag: continue
            ref = f"release:{repo}:{tag}"
            prev = t.get("latest_release")
            if tag != prev:
                t["latest_release"] = tag
                changed = True
                if ref not in seen:
                    seen.add(ref)
                    out.append({"ts": now(), "source": "tool-release", "severity": "INFO",
                                "target": t["name"], "summary": f"{repo} new release {tag} (was {prev})",
                                "ref": ref})
            time.sleep(0.5)
    if changed:
        reg["updated"] = now()
        json.dump(reg, open(REGISTRY, "w"), indent=2)
    return out

def main():
    seen = existing_refs()
    n = 0
    for entry in harvest_cves(seen) + harvest_tool_releases(seen):
        append(entry); n += 1
    print(f"[harvest] appended {n} real entries at {now()}")

if __name__ == "__main__":
    main()
