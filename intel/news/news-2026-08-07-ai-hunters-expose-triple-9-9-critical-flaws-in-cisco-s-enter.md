# AI Hunters Expose Triple 9.9 Critical Flaws in Cisco's Enterprise SD-WAN and IOS XE

**Agency:** VAPE Wire
**Byline:** VAPE Reporter
**Date:** 2026-08-07T10:03:38Z
**Published:** August 7, 2026 · 6:03 AM EDT
**Topic:** Cybersecurity
**Dek:** A sweeping internal audit powered by frontier AI models uncovers 12 severe vulnerabilities in core routing infrastructure before attackers can weaponize them.
**Image:** assets/news-images/ai-hunters-expose-triple-9-9-critical-flaws-in-cisco-s-enter.jpg
**Image source:** AI-generated — VAPE Wire branded
**Fact-checked:** Yes — multi-source review completed

---

Cisco has issued a security advisory patching 12 vulnerabilities across its Catalyst SD-WAN and IOS XE software, including three CVSS 9.9 bugs. The flaws were discovered during an internal security review using existing testing processes as well as frontier AI models. None are known to be actively exploited.

The vulnerabilities affect Cisco Catalyst SD-WAN Software regardless of device configuration, and Cisco IOS XE Software when running in autonomous or controller mode.

## SD-WAN vulnerabilities

The three CVSS 9.9 issues in Catalyst SD-WAN Software are:

- CVE-2026-20303: improper input validation (including path traversal)
- CVE-2026-20304: improper access control
- CVE-2026-20310: improper link resolution before file access

Additional SD-WAN issues include CVE-2026-20312 (CVSS 8.8, cleartext storage of sensitive information) and CVE-2026-20313 (CVSS 7.7, improper validation of specified quantity in input).

Fixed releases: 20.9.10, 20.12.8.1, 20.15.6, 20.18.4, and 26.1.2. Versions earlier than 20.9 require migration to a fixed release.

## IOS XE vulnerabilities

IOS XE Software received patches for improper access control, buffer overflow/out-of-bounds write, improper control of a resource through its lifetime, incorrect calculation (including integer overflow/underflow/truncation), and insufficient control flow management. The listed CVEs are CVE-2026-20267 (CVSS 9.0), CVE-2026-20268 (CVSS 8.6), CVE-2026-20269 (CVSS 8.6), CVE-2026-20270 (CVSS 8.6), and CVE-2026-20271 (CVSS 8.6).

## Recommended actions

Cisco advises applying the updates. Administrators should identify devices running the affected versions in the listed modes and deploy the fixed releases.

---

## Sources

- [Cisco Patches 12 SD-WAN and IOS XE Flaws, Including Three 9.9 CVSS Score Bugs](https://thehackernews.com/2026/08/cisco-patches-12-sd-wan-and-ios-xe.html) — The Hacker News

---

*VAPE Wire — Cybersecurity desk. Reported and edited by VAPE's autonomous newsroom (agents/news_reporter.py).*
