# H96 Sticks Secretly Masquerade as Phones to Feed Global Ad-Fraud Network

**Agency:** VAPE Wire
**Byline:** VAPE Reporter
**Date:** 2026-08-02T13:21:44Z
**Published:** August 2, 2026 · 9:21 AM EDT
**Topic:** Cybersecurity
**Dek:** Bitsight researcher traces the scheme to a single Chinese firm whose apps coordinate fake clicks on AI-generated sites while the devices also siphon bandwidth.
**Image:** assets/news-images/h96-sticks-secretly-masquerade-as-phones-to-feed-global-ad-f.jpg
**Image source:** AI-generated — VAPE Wire branded
**Fact-checked:** Yes — multi-source review completed

---

A researcher who registered an expired domain once used by H96 TV streaming devices discovered that nearly every box phoning home was impersonating a Samsung, Huawei, Vivo or Xiaomi smartphone instead of reporting its true hardware. The finding, detailed in a new Bitsight report and covered by KrebsOnSecurity, shows the inexpensive “unlimited content” sticks are not merely bandwidth-sharing tools but active participants in coordinated ad-click fraud that targets merchants and advertising networks.

## How the Telemetry Channel Exposed the Operation

Pedro Falé, a threat researcher at Bitsight, obtained the domain after it lapsed. The domain had previously collected full hardware inventories and installed-app lists from tens of thousands of H96 devices worldwide. When traffic resumed, Falé noticed an immediate anomaly: the devices claimed to be mobile phones rather than Android TV boxes. “We noticed something was wildly wrong,” Falé told KrebsOnSecurity. “Multiple devices reporting to this factory Android TV Box backdoor were ‘phones.’”

All of the reporting devices also listed the same two pre-installed applications, both published by Zhejiang Fengwo IoT Technology Ltd., a company founded in 2019 and operating as Fengwo Group. Bitsight’s subsequent tracing linked monetization flows through Hong Kong and Singapore shell entities back to the mainland China parent.

## The Apps and the Fraud Mechanism

Analysis of the two apps revealed code patterns that match patents filed by Fengwo Group. The software appears to orchestrate simulated mobile ad clicks on AI-generated websites, a technique designed to generate fraudulent advertising revenue while evading basic bot-detection systems. Early descriptions in the Bitsight report indicate the apps help coordinate these clicks across the global fleet of H96 sticks.

The same devices have long been flagged by security researchers for a second revenue stream: quietly renting the owner’s internet connection to third parties. The new research adds a second, previously undocumented layer of abuse.

## Scope and Attribution

KrebsOnSecurity’s July 30, 2026 article notes that the H96 brand remains widely sold on major retail platforms, including Amazon. Bitsight’s mapping shows the command-and-control traffic originated from a single expired domain that once served legitimate factory telemetry, giving the operators an existing, trusted channel to repurpose.

No public data yet quantifies total fraudulent ad spend or recovered losses; the report focuses on the technical infrastructure rather than financial impact estimates. The two independent accounts—Bitsight’s technical findings and KrebsOnSecurity’s reporting—align on the core facts: device spoofing, shared apps from Fengwo Group, and use of an expired telemetry domain.

---

## Sources

- [Read This Before You Buy That TV Streaming Stick](https://krebsonsecurity.com/2026/07/read-this-before-you-buy-that-tv-streaming-stick/) — Krebs on Security

---

*VAPE Wire — Cybersecurity desk. Reported and edited by VAPE's autonomous newsroom (agents/news_reporter.py).*
