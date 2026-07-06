"""
VAPE ledger self-review — periodically re-checks its OWN past verdicts
against fresh real data, so it can tell where it was accurate and where it
wasn't. This is how the pass/caution/fail lists (agents/investigate.py's
ledger.json + fail/caution/pass-list.md) become a growing, self-correcting
database instead of a write-once log nobody ever looks at again.

Does not duplicate any recon/scoring logic: it picks WHICH addresses are
most overdue for a re-check (oldest-last-checked within a category first),
then calls the real agents/investigate.py::investigate(address, force=True)
for each — the exact same pipeline a hired/deep-dive re-check would use.
Drift (the verdict materially changed) is logged as a real Memory finding;
no drift just refreshes last_investigated so the sampling naturally rotates
through the whole list over repeated runs instead of hammering the same
handful of addresses.

Usage:
  python agents/review_ledger.py --categories pass,caution --sample 5
  python agents/review_ledger.py --categories fail --sample 5
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import investigate as inv  # noqa: E402

try:
    from skillforge.memory.retriever import append_to_memory
except Exception:
    append_to_memory = None

REVIEWS_DIR = os.path.join(inv.ROOT, "intel", "investigations", "reviews")

VERDICT_RANK = {"REJECT": 0, "CAUTION": 1, "PROCEED": 2}


def _sample(category, n):
    ledger = inv._load_ledger()
    candidates = [(addr, e) for addr, e in ledger.items() if e.get("last_verdict") == category]
    candidates.sort(key=lambda kv: kv[1].get("last_investigated", ""))  # oldest-checked first
    return candidates[:n]


def _drift_severity(old_verdict, new_verdict):
    old_rank, new_rank = VERDICT_RANK.get(old_verdict, 1), VERDICT_RANK.get(new_verdict, 1)
    if new_rank == old_rank:
        return None
    # Verdict got WORSE (a past PROCEED/CAUTION is now riskier) is the more
    # actionable direction — someone may still be relying on the old verdict.
    return "worsened" if new_rank < old_rank else "improved"


def review_category(category, sample_size):
    results = []
    for addr, old_entry in _sample(category, sample_size):
        old_verdict, old_score = old_entry.get("last_verdict"), old_entry.get("last_score")
        try:
            r = inv.investigate(old_entry.get("address", addr), old_entry.get("chain", "8453"), force=True)
        except Exception as e:
            # Defense in depth: a real crash in one address's re-check (e.g.
            # the write_report() emoji-NameError this session found and
            # fixed) used to kill this entire batch before it reached
            # _update_ledger() for ANY sampled address — including the ones
            # that succeeded before the crash. One address's real failure
            # should cost that address a re-check this cycle, not the
            # whole self-review run.
            print(f"[review_ledger] {old_entry.get('address', addr)} re-check crashed, skipping: {e}")
            continue
        if r.get("error") or r.get("skipped"):
            continue
        new_verdict, new_score = r["verdict"], r["score"]
        drift = _drift_severity(old_verdict, new_verdict)
        results.append({
            "address": old_entry.get("address", addr), "symbol": r.get("symbol"),
            "old_verdict": old_verdict, "old_score": old_score,
            "new_verdict": new_verdict, "new_score": new_score,
            "drift": drift, "report": r.get("report"),
        })
        if drift and append_to_memory:
            try:
                append_to_memory(
                    category="lesson",
                    title=f"Ledger review: {r.get('symbol')} drifted {old_verdict}→{new_verdict} "
                          f"({old_score}→{new_score}/100)",
                    content=f"Self-review of a past {old_verdict} verdict for {old_entry.get('address', addr)} "
                            f"found the current real data now scores {new_verdict} ({new_score}/100) — "
                            f"drift: {drift}. Original verdict stood since {old_entry.get('first_investigated')}.",
                    source="agents/review_ledger.py",
                    tags=["self-review", "ledger", category.lower(), drift],
                    confidence=0.85,
                    metadata={"address": old_entry.get("address", addr), "old_verdict": old_verdict,
                              "new_verdict": new_verdict, "old_score": old_score, "new_score": new_score},
                )
            except Exception as e:
                print(f"[review_ledger] could not log drift lesson: {e}")
    return results


def main():
    ap = argparse.ArgumentParser(description="VAPE ledger self-review")
    ap.add_argument("--categories", default="pass,caution",
                     help="comma list of pass,caution,fail (default: pass,caution)")
    ap.add_argument("--sample", type=int, default=5, help="max addresses re-checked per category")
    args = ap.parse_args()

    name_to_verdict = {"pass": "PROCEED", "caution": "CAUTION", "fail": "REJECT"}
    categories = [name_to_verdict[c.strip().lower()] for c in args.categories.split(",") if c.strip().lower() in name_to_verdict]

    os.makedirs(REVIEWS_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REVIEWS_DIR, f"review-{stamp}.md")

    all_results = {}
    for cat in categories:
        all_results[cat] = review_category(cat, args.sample)

    lines = [f"# VAPE Ledger Self-Review — {datetime.now(timezone.utc).isoformat()}", ""]
    total_drift = 0
    for cat, results in all_results.items():
        lines.append(f"## {cat} ({len(results)} re-checked)")
        if not results:
            lines.append("- Nothing on record in this category yet.")
        for r in results:
            status = f"DRIFT ({r['drift']})" if r["drift"] else "held"
            total_drift += 1 if r["drift"] else 0
            lines.append(f"- **{r['symbol']}** `{r['address']}` — {r['old_verdict']} {r['old_score']} → "
                          f"{r['new_verdict']} {r['new_score']} — {status}")
        lines.append("")
    lines.append(f"## Verdict\n{'Real drift found in ' + str(total_drift) + ' case(s) — see skillforge/memory/lessons.jsonl.' if total_drift else 'No verdict drift this cycle across the sampled addresses.'}")

    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[review_ledger] cycle complete ({total_drift} drift). Report: {os.path.relpath(report_path, inv.ROOT)}")


if __name__ == "__main__":
    main()
