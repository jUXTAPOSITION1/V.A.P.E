"""
VAPE Critic — a deterministic, same-cycle consistency check on score()'s own
output, run immediately after every investigation.

Complements agents/review_ledger.py's retrospective drift check (which
re-investigates old verdicts on a schedule to catch the REAL WORLD changing
under a stale verdict) with an immediate STRUCTURAL check: does this
investigation's own reasons/positive_signals/verdict/score actually agree
with the raw evidence that produced them, and with score()'s own declared
invariants (verdict/score bands, the legitimacy cap)?

Rule-based only — matches this repo's "rule-based first, LLM only when
reasoning is required" design law. A reason string drifting out of sync
with the flag() that produced it, a verdict/score band mismatch, a cap not
applied — these are structural facts checkable without any model call, not
judgment calls. This is NOT a verdict re-judge: it never mutates
score/verdict/reasons. It only surfaces, into Memory + the report, cases
where an investigation contradicts itself, so a real generation-time bug
gets noticed the moment it happens instead of relying solely on
review_ledger.py's later drift detection to catch something changed.

Never raises: any internal error in the critic itself must not sink an
investigation — this is defense-in-depth, not a load-bearing gate.
"""
try:
    from skillforge.memory.retriever import append_to_memory
except Exception:
    append_to_memory = None


def _verdict_for_score(s):
    return "PROCEED" if s >= 80 else ("CAUTION" if s >= 50 else "REJECT")


def verify(gp, verif, s, verdict, reasons, positive_signals):
    """Deterministically re-check score()'s output against its own raw
    inputs and its own declared invariants. Returns {"ok": bool, "issues": [str]}
    — never raises."""
    issues = []
    try:
        reason_text = " | ".join(reasons)
        signal_text = " | ".join(positive_signals)

        # 1. Verdict/score band invariant.
        expected = _verdict_for_score(s)
        if expected != verdict:
            issues.append(f"verdict/score mismatch: score {s} implies {expected}, got {verdict}")

        # 2. Score bounds.
        if not (0 <= s <= 100):
            issues.append(f"score out of bounds: {s}")

        # 3. Honeypot grounding.
        is_honeypot = str(gp.get("is_honeypot")) == "1"
        reason_claims_honeypot = "HONEYPOT detected" in reason_text
        if is_honeypot != reason_claims_honeypot:
            issues.append(f"honeypot mismatch: gp.is_honeypot={gp.get('is_honeypot')!r} "
                          f"but honeypot-reason present={reason_claims_honeypot}")

        # 4. Verification grounding.
        verified = verif.get("verified")
        if "Contract source UNVERIFIED" in reason_text and verified is not False:
            issues.append(f"unverified-reason present but verif.verified={verified!r}")
        if "Custom verified source" in signal_text and verified is not True:
            issues.append(f"verified-signal present but verif.verified={verified!r}")

        # 5. Ownership-renounced grounding.
        owner = (gp.get("owner_address") or "").lower()
        zero_addr = "0x0000000000000000000000000000000000000000"
        owner_present = bool(owner) and owner != zero_addr
        if "Ownership renounced" in signal_text and owner_present:
            issues.append(f"renounced-signal present but owner_address={gp.get('owner_address')!r}")
        if "Owner not renounced" in reason_text and not owner_present:
            issues.append("owner-not-renounced reason present but owner_address is empty/burn")

        # 6. Legitimacy cap invariant — mirrors score()'s own cap exactly.
        if len(positive_signals) == 0 and s > 55:
            issues.append(f"no positive signals but score {s} exceeds the 55 cap")
        elif len(positive_signals) == 1 and s > 70:
            issues.append(f"only one positive signal but score {s} exceeds the 70 cap")
    except Exception as e:
        issues.append(f"critic internal error (non-fatal): {e}")

    return {"ok": not issues, "issues": issues}


def log_finding(target, chain, sym, issues):
    """Best-effort: surface a real consistency failure into Memory so it's
    visible to self_improve.py / a human, not just printed to a CI log that
    scrolls away. No-op (not an error) when Memory isn't wired or nothing
    was found."""
    if not append_to_memory or not issues:
        return
    try:
        append_to_memory(
            category="lesson",
            title=f"Critic flagged {sym} ({target[:10]}) — {len(issues)} consistency issue(s)",
            content="; ".join(issues)[:1800],
            source="agents/critic.py",
            tags=["critic", "self-audit", "consistency"],
            confidence=0.9,
            metadata={"target": target, "chain": str(chain), "issues": issues},
        )
    except Exception as e:
        print(f"[critic] memory log failed: {e}")
