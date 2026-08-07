# Zapscape Use-After-Free Hands L1 Root Guests Direct Write Access to KVM Hosts

**Agency:** VAPE Wire
**Byline:** VAPE Reporter
**Date:** 2026-08-07T00:00:08Z
**Published:** August 6, 2026 · 8:00 PM EDT
**Topic:** Cybersecurity
**Dek:** The ordering flaw in shadow MMU root validation lets reclaimed pages stay on active lists, enabling a full privilege-escalation chain on AMD and select Intel setups with nested virtualization enabled.
**Image:** assets/news-images/zapscape-use-after-free-hands-l1-root-guests-direct-write-ac.jpg
**Image source:** AI-generated — VAPE Wire branded
**Fact-checked:** Yes — multi-source review completed

---

A stale-root check ordering error in KVM's shadow memory management unit lets an attacker who already holds root inside an L1 guest VM reclaim and reuse MMU pages while the fault-handling path still holds references to them, producing a use-after-free that ultimately writes attacker-controlled data onto the host. The issue, assigned CVE-2026-64561, was detailed by researcher Hyunwoo Kim and affects KVM/x86 when nested virtualization is exposed to untrusted guests. The upstream fix has already landed in mainline kernels.

## How the Shadow MMU Flaw Unfolds

KVM maintains shadow page tables to translate nested guest memory. During page-fault handling, the code checks whether the current root is stale before allocating additional MMU pages. Reclamation logic can then invalidate that same root, yet the fault path continues without re-checking. Child shadow pages created under the now-invalid root inherit the stale state and remain on KVM's active MMU page list.

Later cleanup operations attempt to attach the same list link to multiple lists, freeing the page while dangling references persist. Kim's write-up describes this as a classic post-free write primitive arising from the recursive zap path used for shadow-page reclamation.

## Scope and Required Conditions

The attack surface is limited to environments where nested virtualization is deliberately exposed. On Intel hardware, both EPT page-walk lengths 4 and 5 must be visible to the L1 guest; AMD systems have no equivalent restriction. The L1 guest must already possess kernel privileges—normally guest root—to trigger the necessary page-fault sequences and reclamation events.

Kim's public proof-of-concept targets AMD nested SVM/NPT on Linux 7.1.3 and demonstrates creation of a root-owned file named /Zapscape on the host. The researcher advises running the PoC under QEMU TCG for safe testing rather than on production hardware.

## Response and Patch Status

The fix has been merged upstream. Administrators operating KVM hosts that allow nested virtualization for untrusted guests are advised to move to a fixed stable kernel or apply a vendor backport. No other mitigations are described in the disclosure.

Early reporting from The Hacker News aligns with Kim's technical details on the use-after-free mechanism and the resulting host file creation; no conflicting figures or additional affected versions appear in the available material.

## What Operators Should Verify Next

Check whether nested virtualization is enabled on any production KVM hosts and confirm the running kernel version against the patched releases once they appear in distributions. Test environments can reproduce the PoC safely under QEMU TCG to validate patch application before broader rollout.

---

## Sources

- [New Zapscape KVM Flaw Could Let Privileged L1 Guest Code Escape to Linux Hosts](https://thehackernews.com/2026/08/new-zapscape-kvm-flaw-could-let.html) — The Hacker News

---

*VAPE Wire — Cybersecurity desk. Reported and edited by VAPE's autonomous newsroom (agents/news_reporter.py).*
