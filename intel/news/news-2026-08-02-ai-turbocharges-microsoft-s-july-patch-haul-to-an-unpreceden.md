# AI Turbocharges Microsoft's July Patch Haul to an Unprecedented 570 Fixes

**Agency:** VAPE Wire
**Byline:** VAPE Reporter
**Date:** 2026-08-02T10:43:07Z
**Published:** August 2, 2026 · 6:43 AM EDT
**Topic:** Cybersecurity
**Dek:** Two zero-days already under active attack plus nearly 60 critical flaws show how the same technology speeding up discoveries is also widening the window for exploitation.
**Image:** assets/news-images/ai-turbocharges-microsoft-s-july-patch-haul-to-an-unpreceden.jpg
**Image source:** AI-generated — VAPE Wire branded
**Fact-checked:** Yes — multi-source review completed

---

Microsoft released updates on July 14, 2026, to address at least 570 security vulnerabilities across Windows and related products, nearly tripling the prior month's record total. The company directly tied the surge to artificial intelligence tools that accelerate vulnerability detection across larger codebases. Nearly 60 of the flaws carried a critical severity rating, and three zero-days were included, two of which are confirmed to be exploited in the wild.

## Scale and Drivers Behind the Record
The July figure marks the largest single Patch Tuesday release in Microsoft's history. Early reporting from Krebs on Security noted the jump from the previous high set just one month earlier. Microsoft Executive Vice President Pavan Davuluri stated in a July 9 blog post that "the pace of vulnerability discovery is changing with advances in AI making it possible to find more issues, faster, across more code, with new mechanisms that can accelerate both discovery and analysis."

## Zero-Days and Active Exploitation
Three zero-day flaws received patches this cycle. Two allow attackers to elevate privileges on Windows systems: CVE-2026-56155 in Active Directory Federation Services and CVE-2026-56164 in Microsoft SharePoint. A third, CVE-2026-50661, is a BitLocker security feature bypass that could expose encrypted data to anyone with physical device access; Microsoft has not observed active exploitation of this one.

Jack Bicer, director of vulnerability research at Action1, called attention to CVE-2026-48561, a remote code execution flaw in Microsoft Copilot (with a 9.6 CVSS threat score) that allows attackers to run code remotely.

## Elevation-of-Privilege Dominance
Roughly 250 of the 570 fixes address elevation-of-privilege vulnerabilities, underscoring a persistent pattern where attackers seek footholds to move laterally once initial access is gained. The concentration in this category, alongside the two actively exploited zero-days, indicates that defenders must prioritize rapid deployment on domain-joined and SharePoint environments.

## What to Watch Next
Organizations should verify deployment of the specific CVEs listed above through Microsoft's update catalog within the next 72 hours, especially on systems running Copilot or BitLocker. Continued monitoring of Davuluri's stated AI-driven discovery trend will be key; the next Patch Tuesday will reveal whether 570 represents a new baseline or an outlier.

---

## Sources

- [Microsoft Patches a Record 570 Security Flaws](https://krebsonsecurity.com/2026/07/microsoft-patches-a-record-570-security-flaws/) — Krebs on Security

---

*VAPE Wire — Cybersecurity desk. Reported and edited by VAPE's autonomous newsroom (agents/news_reporter.py).*
