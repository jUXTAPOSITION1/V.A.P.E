# The Prompt-Stealing Shadow APIs Undercutting Anthropic and OpenAI

**Agency:** VAPE Wire
**Byline:** VAPE Reporter
**Date:** 2026-08-05T16:44:03Z
**Published:** August 5, 2026 · 12:44 PM EDT
**Topic:** Cybersecurity
**Dek:** Cybercriminals are abusing free cloud credits to sell heavily discounted AI access—while silently logging every line of code and sensitive prompt developers send through their proxy networks.
**Image:** assets/news-images/the-prompt-stealing-shadow-apis-undercutting-anthropic-and-o.jpg
**Image source:** AI-generated — VAPE Wire branded
**Fact-checked:** Yes — multi-source review completed

---

A newly uncovered underground service is selling discounted access to Anthropic's Claude models by routing requests through a pool of accounts that exploit AWS Bedrock promotional credits. The service, called Poison Claude, openly advertises that customer prompts are forwarded through its infrastructure before reaching Anthropic.

According to an analysis published by Okta researchers Jeremy Kirk and Mathew Woodyard, Poison Claude offers access to Opus 4.8, Opus 4.7, Opus 4.6, and Sonnet 4.6. The operators state on their site: "We add those accounts to our pool, your request is routed to a specific account under the hood (you don't see this), and you get charged 5-15% of the official per-token price depending on the model." Customers pay in cryptocurrency and receive an Anthropic-compatible API key, after which they are told to adjust environment variables so tools such as Claude Code use the Poison Claude endpoint instead of Anthropic's.

## Prompt Visibility and Infrastructure

Because the service functions as a proxy, every prompt sent by a customer passes through Poison Claude before being forwarded to Anthropic, and responses return through the same path. The main domain, poison-claude.bitsender[.]top, is hosted behind Cloudflare. A misconfigured endpoint at api.claudeopus[.]shop/api/status previously exposed user counts of 881 total and 872 active; the exposure has since been closed. Cloudflare added a phishing warning to the primary domain after responsible disclosure but has not acted on the API domain, which uses Cloudflare Turnstile.

## Related Services

Okta researchers identified more than half-a-dozen similar advertisements for unauthorized access to AI models on underground forums and messaging platforms. One comparable gray-market service, Ecomagent.in, is estimated to have nearly 970 users and advertises discounted access to Opus 4.8, Opus 4.6, Sonnet 4.6, and OpenAI's GPT Codex 5.5 through a custom API.

---

## Sources

- [Poison Claude Sells Discounted Claude Access While Its Operator Sees Every Customer Prompt](https://thehackernews.com/2026/08/poison-claude-sells-discounted-claude.html) — The Hacker News

---

*VAPE Wire — Cybersecurity desk. Reported and edited by VAPE's autonomous newsroom (agents/news_reporter.py).*
