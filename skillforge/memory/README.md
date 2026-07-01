# VAPE Memory System — Central Intelligence Registry

> **Memory is the long-term brain.** Every module (detective, builder, MCP, self-improvement) feeds into and pulls from this append-only registry.

---

## Core Concept

**Memory** is a single, immutable audit trail (`skillforge/memory/memory.jsonl`). Each entry is timestamped, categorized, tagged, and hashed. Queries are fast and relevance-scored. No deletions—only appends (trust through transparency).

**Categories** (not exclusive; use tags for cross-cutting):
- `findings` — Security discoveries, vulnerabilities, exploits
- `skills` — Code tools, techniques, playbooks
- `lessons` — Patterns learned, improvements, best practices
- `social_events` — X/Twitter signals, market sentiment, narratives
- `code_patterns` — Recurring patterns in contracts, proof-of-concepts
- `market_intel` — TVL movements, whale activity, anomalies
- `acp_jobs` — Completed job outcomes, success rates, lessons

---

## API Reference

### `search_memory(query, category=None, limit=10, min_score=0.5)`
Find past findings, lessons, patterns.

**Args:**
- `query` (str): search string (e.g., "reentrancy vulnerability")
- `category` (str, optional): filter by category (e.g., "findings")
- `limit` (int): max results (default 10)
- `min_score` (float): minimum relevance (default 0.5)

**Returns:** List of dicts, sorted by relevance (descending)

**Examples:**
```python
from skillforge.memory.retriever import search_memory

# Detective: find similar past findings
matches = search_memory("reentrancy", category="findings", limit=5)
for match in matches:
    print(f"{match['severity']}: {match['contract']}")

# Builder: look up similar tools before generating
tools = search_memory("contract analysis", category="skills")

# MCP: find recent social signals
signals = search_memory("Base exploit", category="social_events", limit=3)
```

---

### `append_to_memory(category, entry, source="system", tags=None)`
Store a new finding, skill, lesson, etc. Automatically timestamped & hashed.

**Args:**
- `category` (str): one of the categories above
- `entry` (dict): entry data (structure depends on category)
- `source` (str): originating module ("builder", "vape", "hack", "mcp", "self_improve")
- `tags` (list, optional): searchable tags

**Returns:** bool (True if successful)

**Examples:**
```python
from skillforge.memory.retriever import append_to_memory

# Detective: log a critical finding
append_to_memory("findings", {
    "type": "reentrancy",
    "contract": "0xabcd1234",
    "severity": "CRITICAL",
    "chain": "base",
    "poc": "function drain() { receive() { ... } }",
    "timeline": "2026-07-01T15:30:00Z",
}, source="hack", tags=["exploit", "base", "liquidity-pool"])

# Builder: auto-register a generated tool
append_to_memory("skills", {
    "name": "exploit_simulator_v2",
    "desc": "Runs foundry anvil fork simulation of exploit PoC",
    "code": "#!/bin/bash\nforge test --fork-url ...",
    "tier": "fuzzing",
    "confidence": 0.95,
}, source="builder", tags=["forge", "anvil", "simulation"])

# Self-improve: log a lesson
append_to_memory("lessons", {
    "title": "Always search memory before generating new tools",
    "insight": "Found 3 similar tools in memory that could have been reused",
    "impact": "reduce redundancy, improve consistency",
}, source="self_improve", tags=["builder", "efficiency"])

# MCP: feed social signal into memory
append_to_memory("social_events", {
    "platform": "x",
    "timestamp": "2026-07-01T14:20:00Z",
    "content": "New vulnerability in XYZ protocol disclosed",
    "sentiment": "bearish",
    "reach": 50000,
}, source="mcp.twitter", tags=["crisis", "xyzprotocol"])
```

---

### `get_memory_stats()`
Audit trail: total entries, categories breakdown, operations log.

**Returns:** Dict with stats

**Examples:**
```python
from skillforge.memory.retriever import get_memory_stats

stats = get_memory_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"By category: {stats['categories']}")
print(f"Total searches: {stats['total_searches']}")
print(f"Total appends: {stats['total_appends']}")
```

---

## Integration Patterns

### Pattern 1: Detective (vape.py / hack.py)
```python
from skillforge.memory.retriever import search_memory, append_to_memory

# At start: ground in past findings
print("[vape] searching memory for similar past findings...")
past_exploits = search_memory("reentrancy Base", category="findings", limit=3)
if past_exploits:
    print(f"  Found {len(past_exploits)} similar past findings — context loaded")

# After analysis: store finding
if vulnerability_found:
    append_to_memory("findings", {
        "type": vulnerability_type,
        "contract": target_contract,
        "severity": severity,
        "poc": poc_code,
        ...
    }, source="hack", tags=[f"severity-{severity.lower()}", "base", ...])
    print("[vape] finding stored in memory for future context")
```

### Pattern 2: Builder (builder.py)
```python
from skillforge.memory.retriever import search_memory, append_to_memory

# Step 1: Search memory for similar tools/patterns
def generate_tool(task_description):
    print(f"[builder] searching memory for similar patterns...")
    similar_skills = search_memory(task_description, category="skills", limit=5)
    
    if similar_skills:
        print(f"  Found {len(similar_skills)} similar tools — grounding context")
        context = "\n".join([s.get("desc", "") for s in similar_skills])
    else:
        context = "[no similar tools found in memory]"
    
    # Step 2: Generate with grounding + context
    system_prompt = f"""You are VAPE Builder. Generate secure code.
    
    Similar past tools for context:
    {context}
    """
    code = ask_llm(system_prompt, task_description, tier="deep")
    
    # Step 3: Auto-append to memory on success
    if code and validate(code):
        append_to_memory("skills", {
            "name": extract_tool_name(code),
            "desc": task_description,
            "code": code,
            "tier": "generated",
        }, source="builder", tags=["auto-generated", "validated"])
        print("[builder] tool stored in memory for reuse")
    
    return code
```

### Pattern 3: MCP Tools
```python
from skillforge.memory.retriever import search_memory, append_to_memory

# Example: X/Twitter MCP feeds social signals
def on_social_event(platform, content, sentiment):
    # Store in memory for future context
    append_to_memory("social_events", {
        "platform": platform,
        "timestamp": datetime.now().isoformat(),
        "content": content,
        "sentiment": sentiment,
    }, source="mcp.twitter", tags=[platform, sentiment])
    
    # Maybe trigger detective if critical
    if sentiment == "crisis":
        print("[mcp] critical social signal — triggering vape analysis...")
```

### Pattern 4: Self-Improvement (self_improve.py)
```python
from skillforge.memory.retriever import search_memory, append_to_memory

# Review past findings to identify patterns
past_findings = search_memory("", category="findings", limit=100)
vulnerability_types = [f["type"] for f in past_findings]

# Learn from successes
successful_tools = search_memory("", category="skills", limit=50)

# Store lesson
append_to_memory("lessons", {
    "title": "Most common vulnerabilities on Base are XYZ",
    "insight": vulnerability_types_summary,
    "action": "Prioritize XYZ detection in future audits",
}, source="self_improve")
```

---

## File Structure

```
skillforge/memory/
├── retriever.py           # Core API
├── memory.jsonl           # Append-only storage (git-tracked)
├── stats.json             # Operation statistics
└── README.md              # This file
```

**memory.jsonl format:**
```json
{"timestamp": "2026-07-01T15:30:00+00:00", "category": "findings", "source": "hack", "tags": ["exploit", "base"], "entry_hash": "a1b2c3d4", "type": "reentrancy", "contract": "0x...", "severity": "CRITICAL", ...}
{"timestamp": "2026-07-01T15:31:00+00:00", "category": "skills", "source": "builder", "tags": [], "entry_hash": "e5f6g7h8", "name": "exploit_sim", "desc": "...", ...}
```

---

## Best Practices

1. **Search before generating** — Builders should always query memory for similar patterns before writing new code.
2. **Tag everything** — Use tags for cross-cutting concerns (severity, chain, protocol, etc.).
3. **Descriptive entries** — Include context, timestamps, links, PoCs in findings.
4. **Source attribution** — Always set `source` to the calling module for traceability.
5. **Regular reviews** — Use `get_memory_stats()` to audit what's been learned.
6. **No sensitive data** — Never store API keys, private keys, or user PII in memory.

---

## Future Enhancements

- 🟡 Semantic embeddings for better relevance (e.g., via Groq)
- 🟡 Category-specific validation schemas
- 🟡 Memory export/sync to external KB
- 🟡 Per-source access logs & audit trail
- 🟡 Automatic deduplication of similar findings
