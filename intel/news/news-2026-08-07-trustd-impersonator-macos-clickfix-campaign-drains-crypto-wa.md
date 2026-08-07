# Trustd Impersonator: macOS ClickFix Campaign Drains Crypto Wallets With Go-Based Stealer

**Agency:** VAPE Wire
**Byline:** VAPE Reporter
**Date:** 2026-08-07T18:59:23Z
**Published:** August 7, 2026 · 2:59 PM EDT
**Topic:** Cybersecurity
**Dek:** Huntress traced how the Bash loader evades Gatekeeper by copying a Mach-O payload into a directory named after the system process that validates code signatures.
**Image:** assets/news-images/trustd-impersonator-macos-clickfix-campaign-drains-crypto-wa.jpg
**Image source:** AI-generated — VAPE Wire branded
**Fact-checked:** Yes — multi-source review completed

---

A Go-based infostealer delivered through ClickFix social-engineering lures is targeting macOS users to harvest cryptocurrency, browser passwords, Apple Keychain entries, and cached credentials while also intercepting live crypto transactions.

Security researchers discovered the payload during a recent incident response engagement and published their findings on August 6, 2026. The malware can either empty wallets entirely or calculate transaction values to siphon only a portion to attacker-controlled addresses.

## Attack Delivery Chain

Victims received an email containing a link that directed them to a page instructing them to paste and run a command in Terminal. That command fetched a Bash script functioning as both a system profiler and malware loader.

The script collected basic hardware details, such as CPU type and RAM size, then downloaded a Mach-O binary matched to the victim’s processor architecture. It also identified the currently logged-in account name and created a directory using the name “trustd,” the legitimate macOS process responsible for cryptographic certificate and code-signature validation.

## Payload Deployment and Evasion

Inside the newly created directory, the loader placed the infostealing binary under the filename “com.apple.verified.” It then stripped the `com.apple.quarantine` extended attribute, preventing Gatekeeper from displaying a security warning on first execution.

This technique allows the malware to masquerade as a verified Apple component while operating from a location that blends with normal system processes. 

## Crypto Theft Capabilities

Once running, the malware targets cryptocurrency assets directly. It monitors pending transactions and can either redirect the full amount or calculate a partial diversion based on the total value of the transaction.

The same binary also extracts stored passwords from browsers, pulls data from Apple Keychain, and collects cached credentials. 

## What Readers Should Watch Next

Organizations running macOS should review Terminal command histories for suspicious download or execution commands and verify that Gatekeeper remains enabled on all endpoints.

---

## Sources

- [ClickFix attack pushes macOS infostealer for crypto theft attacks](https://www.bleepingcomputer.com/news/security/clickfix-attack-pushes-macos-infostealer-for-crypto-theft-attacks/) — BleepingComputer

---

*VAPE Wire — Cybersecurity desk. Reported and edited by VAPE's autonomous newsroom (agents/news_reporter.py).*
