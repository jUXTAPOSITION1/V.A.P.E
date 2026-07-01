# MCP Integration Guide — GitHub + Twitter + Web

> Model Context Protocol (MCP) tools extend VAPE's capabilities. Everything MCP returns flows into Memory and triggers downstream actions.

---

## What is MCP?

**MCP (Model Context Protocol)** is a standard for LLMs to safely access external tools and services. In V.A.P.E., MCP tools act as **sensors and actuators**:

- **Sensors:** GitHub issues, Twitter mentions, CVE feeds
- **Actuators:** Create PRs, post alerts, trigger workflows

All MCP calls are:
- ✅ Logged comprehensively (audit trail)
- ✅ Rate-limited (respect API quotas)
- ✅ Stored in Memory automatically
- ✅ Validated before use

---

## Available MCP Tools

### 1. GitHub MCP
Read repo metadata, search issues, create PRs, list files.

**Operations:**
- `search_issues(repo, query, limit)` — search GitHub issues
- `get_file(repo, path, ref)` — fetch a file
- `list_repo_files(repo, path)` — list directory contents
- `create_issue(repo, title, body, labels)` — open an issue

**Usage Example:**
```python
from skillforge.mcp.integration import mcp_manager, MCPTool

# Builder: search for similar security tools
result = mcp_manager.call(
    MCPTool.GITHUB,
    "search_issues",
    {
        "repo": "jUXTAPOSITION1/V.A.P.E",
        "query": "security vulnerability fix",
        "limit": 5,
    }
)

if result:
    for issue in result["issues"]:
        print(f"#{issue['number']}: {issue['title']}")
```

**Requirements:**
- `GITHUB_TOKEN` env var (GitHub Personal Access Token)
- Minimal scopes: `public_repo`, `read:org`

---

### 2. Twitter/X MCP
Monitor mentions, search tweets, analyze sentiment.

**Operations:**
- `search_tweets(query, limit)` — search recent tweets
- `get_mentions(username, limit)` — get mentions of a user

**Usage Example:**
```python
from skillforge.mcp.integration import mcp_manager, MCPTool

# MCP: monitor for security threats on Twitter
result = mcp_manager.call(
    MCPTool.TWITTER,
    "search_tweets",
    {
        "query": "Base blockchain exploit OR vulnerability",
        "limit": 20,
    }
)

if result:
    print(f"Sentiment: {result['sentiment']}")
    for tweet in result["tweets"]:
        print(f"  - {tweet['text'][:80]}...")
```

**Requirements:**
- `TWITTER_BEARER_TOKEN` env var (X/Twitter API v2 Bearer Token)
- Access to v2 API (tweets, search)

---

## Integration Patterns

### Pattern 1: Builder Uses GitHub MCP
```python
from skillforge.mcp.integration import mcp_manager, MCPTool

# Before generating a tool, check if it already exists as a PR/issue
existing = mcp_manager.call(
    MCPTool.GITHUB,
    "search_issues",
    {
        "repo": "jUXTAPOSITION1/V.A.P.E",
        "query": "exploit simulator",
        "limit": 5,
    }
)

if existing and len(existing["issues"]) > 0:
    print(f"⚠️  Similar tool already proposed in issue #{existing['issues'][0]['number']}")
    # Don't generate, reuse instead
else:
    print("✅ Safe to generate new tool")
    # Proceed with generation
```

### Pattern 2: Vape Uses Twitter MCP for Threat Detection
```python
from skillforge.mcp.integration import mcp_manager, MCPTool

# Periodically check Twitter for security threats
threats = mcp_manager.call(
    MCPTool.TWITTER,
    "search_tweets",
    {
        "query": "@based_vape OR Base blockchain security",
        "limit": 50,
    }
)

if threats and threats["sentiment"] == "bearish":
    print("🚨 Crisis detected on Twitter!")
    # Trigger defensive analysis
    append_to_memory("social_events", {
        "platform": "x",
        "threat_level": "bearish",
        "tweets": len(threats["tweets"]),
    }, source="mcp.twitter", tags=["crisis"])
```

### Pattern 3: Builder Creates PR via MCP
```python
from skillforge.mcp.integration import mcp_manager, MCPTool

# After generating and validating tool, create issue asking for review
mcp_manager.call(
    MCPTool.GITHUB,
    "create_issue",
    {
        "repo": "jUXTAPOSITION1/V.A.P.E",
        "title": "[Builder Generated] New exploit simulator tool",
        "body": """Auto-generated tool for exploit simulation.

Code: [see PR #XXX]
Confidence: 92%
Tests: passing

Please review and merge if acceptable.""",
        "labels": ["builder", "auto-generated", "requires-review"],
    }
)
```

---

## Workflow: MCP → Memory → Action

```
Twitter detects exploit mention
  ↓
MCP fetches tweets, analyzes sentiment
  ↓
Result stored in Memory (social_events)
  ↓
Vape queries Memory: "recent bearish signals?"
  ↓
Found crisis → trigger defensive analysis
  ↓
Generate report, auto-create PR if critical
```

---

## Setup Instructions

### 1. GitHub Token (for Builder + Detective)
```bash
# Generate token at https://github.com/settings/tokens
# Scopes needed: public_repo, read:org
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
```

### 2. Twitter Bearer Token (for social signals)
```bash
# Apply for X API v2 access at https://developer.twitter.com
# Once approved, generate a Bearer Token
export TWITTER_BEARER_TOKEN="AAAAAAAAAAAAAAAAAAAAAA..."
```

### 3. Update .env.example
```bash
# Add to .env.example:
GITHUB_TOKEN=your_github_personal_access_token
TWITTER_BEARER_TOKEN=your_x_api_bearer_token
```

---

## Monitoring & Debugging

### Check MCP Rate Limits
```python
from skillforge.mcp.integration import mcp_manager

# Inside any module:
rate_status = mcp_manager.rate_limits
print(f"GitHub calls this hour: {rate_status['github']['calls']}")
print(f"Twitter calls this hour: {rate_status['twitter']['calls']}")
```

### View MCP Calls in Memory
```python
from skillforge.memory.retriever import search_memory

# Search for all MCP calls
results = search_memory("", source_filter="mcp.github")  # once added
for r in results:
    print(f"{r['timestamp']}: {r['operation']}")
```

---

## Rate Limits & Quotas

| Tool | Limit | Window |
|------|-------|--------|
| GitHub API | 60 (unauthenticated) / 5000 (authenticated) | per hour |
| Twitter v2 | 450 | per 15 minutes |

**Current config:** 100 calls per hour per tool (conservative, can be tuned).

---

## Security & Best Practices

1. **Never hardcode tokens** — Always use env vars
2. **Validate all MCP results** — Treat external data as untrusted
3. **Log everything** — Full audit trail in logs + Memory
4. **Rate limit gracefully** — Backoff and retry on 429
5. **Store results in Memory** — Auto-append for cross-module access
6. **Use scoped tokens** — Minimal permissions (GitHub: public_repo only)

---

## Future MCP Tools

- 🟡 Web Search MCP (fetch CVE feeds, security news)
- 🟡 Slack/Discord MCP (send alerts, get feedback)
- 🟡 Arweave MCP (store reports on-chain for permanence)
- 🟡 Contract Verification MCP (check Etherscan verified sources)

---

## Example: Full Workflow

**Scenario:** Hourly threat check via Twitter + GitHub

```python
# In agents/run.py or scheduled workflow:

from skillforge.mcp.integration import mcp_manager, MCPTool
from skillforge.memory.retriever import append_to_memory

def hourly_threat_check():
    """Check Twitter for threats, store in Memory, trigger analysis if needed."""
    
    # 1. Check Twitter for security-related tweets
    print("[workflow] checking Twitter for threats...")
    tweets_result = mcp_manager.call(
        MCPTool.TWITTER,
        "search_tweets",
        {"query": "Base blockchain security OR exploit", "limit": 20}
    )
    
    if not tweets_result:
        print("[workflow] Twitter check failed")
        return
    
    sentiment = tweets_result.get("sentiment")
    tweet_count = len(tweets_result.get("tweets", []))
    
    print(f"[workflow] sentiment={sentiment}, tweets={tweet_count}")
    
    # 2. Store in Memory (auto-done by mcp_manager.call)
    # (already stored due to store_result=True)
    
    # 3. If bearish, check GitHub for related issues
    if sentiment == "bearish":
        print("[workflow] bearish sentiment detected — checking GitHub...")
        
        issues_result = mcp_manager.call(
            MCPTool.GITHUB,
            "search_issues",
            {
                "repo": "jUXTAPOSITION1/V.A.P.E",
                "query": "security threat critical",
                "limit": 5,
            }
        )
        
        if issues_result:
            existing_issues = len(issues_result.get("issues", []))
            print(f"[workflow] found {existing_issues} related issues")
            
            if existing_issues == 0:
                # No existing issue — create one
                print("[workflow] creating crisis issue...")
                mcp_manager.call(
                    MCPTool.GITHUB,
                    "create_issue",
                    {
                        "repo": "jUXTAPOSITION1/V.A.P.E",
                        "title": "🚨 [MCP Alert] Bearish social sentiment detected",
                        "body": f"""MCP Twitter monitoring detected bearish sentiment.

**Summary:** {tweet_count} tweets mentioning Base security issues
**Sentiment:** {sentiment}
**Timestamp:** {datetime.now().isoformat()}

Recommend: Run defensive analysis, monitor for exploits.
""",
                        "labels": ["mcp-alert", "security", "requires-review"],
                    }
                )
    
    print("[workflow] threat check complete")

# Call hourly from GitHub Actions
# (add to .github/workflows/hourly-mcp-check.yml)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `[mcp] no GITHUB_TOKEN found` | Set `GITHUB_TOKEN` env var |
| `rate limit exceeded` | Wait 1 hour or reduce call frequency |
| `403 Forbidden` | Check token scopes (GitHub: need public_repo) |
| `429 Too Many Requests` | Reduce MCP call frequency or upgrade API tier |
