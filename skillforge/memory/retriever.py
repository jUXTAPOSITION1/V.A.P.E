"""
VAPE Memory Retriever — General-Purpose Long-Term Brain

Central nervous system for the entire V.A.P.E. autonomous system.
Any module (detective flows, builder, MCP tools, self-improvement) can:
  - search_memory(query, category) → find past findings, lessons, patterns
  - append_to_memory(category, entry_dict) → store new findings automatically
  - get_memory_stats() → audit trail + retrieval stats

Storage: Append-only JSON lines (memory.jsonl) — git-tracked, immutable, auditable.
Search: Simple relevance scoring (keyword match + position boost).
Security: Input sanitization, no sensitive data, full logging.

Usage:
  from skillforge.memory.retriever import search_memory, append_to_memory
  
  # Detective finds something
  matches = search_memory("reentrancy vulnerability", category="findings")
  
  # Builder generates a tool, auto-learns it
  append_to_memory("skills", {
    "name": "exploit_simulator",
    "desc": "Run PoC on Anvil fork",
    "code": "...",
    "source": "builder",
  })
"""

import json
import os
from datetime import datetime, timezone
import logging
from pathlib import Path
import hashlib
import re
from typing import List, Dict, Optional, Tuple, Any

# Setup logging
logger = logging.getLogger("vape.memory")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(handler)

# Memory file location
MEMORY_DIR = Path(__file__).parent
MEMORY_FILE = MEMORY_DIR / "memory.jsonl"
STATS_FILE = MEMORY_DIR / "stats.json"


def _sanitize_input(s: str, max_len: int = 5000) -> str:
    """Sanitize user input: strip, limit length, remove control chars."""
    if not isinstance(s, str):
        return ""
    s = s.strip()[:max_len]
    s = re.sub(r'[\x00-\x1f\x7f]', ' ', s)  # remove control chars
    return s


def _relevance_score(query: str, text: str) -> float:
    """
    Simple relevance scoring:
      - keyword match: +1 per match
      - early position boost: +0.5 if match in first 20% of text
    """
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Split query into keywords
    keywords = [kw for kw in query_lower.split() if len(kw) > 2]
    if not keywords:
        return 0.0
    
    score = 0.0
    text_len = len(text_lower)
    early_cutoff = max(100, text_len // 5)
    
    for kw in keywords:
        # Count occurrences
        count = text_lower.count(kw)
        score += count
        
        # Boost if early
        if text_lower[:early_cutoff].find(kw) >= 0:
            score += 0.5
    
    return score


def append_to_memory(
    category: str,
    entry: Dict[str, Any],
    source: str = "system",
    tags: Optional[List[str]] = None
) -> bool:
    """
    Append a timestamped entry to memory.
    
    Args:
      category: "findings", "skills", "lessons", "social_events", "code_patterns", etc.
      entry: dict with entry data (name, desc, etc.)
      source: originating module ("builder", "vape", "hack", "mcp", "self_improve")
      tags: optional list of search tags
    
    Returns:
      bool: True if appended successfully
    
    Example:
      append_to_memory("findings", {
        "type": "reentrancy",
        "contract": "0x...",
        "severity": "CRITICAL",
        "poc": "...",
      }, source="hack", tags=["exploit", "base-chain"])
    """
    try:
        # Validate inputs
        category = _sanitize_input(category, 100)
        source = _sanitize_input(source, 50)
        if not category:
            logger.error("append_to_memory: category is empty after sanitization")
            return False
        
        if not isinstance(entry, dict):
            logger.error(f"append_to_memory: entry must be dict, got {type(entry)}")
            return False
        
        # Sanitize entry values (only strings)
        sanitized_entry = {}
        for k, v in entry.items():
            if isinstance(v, str):
                sanitized_entry[k] = _sanitize_input(v, 5000)
            elif isinstance(v, (int, float, bool)):
                sanitized_entry[k] = v
            elif isinstance(v, list):
                sanitized_entry[k] = [
                    _sanitize_input(item, 500) if isinstance(item, str) else item
                    for item in v
                ]
            else:
                # Skip non-serializable types
                pass
        
        # Build memory record
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "source": source,
            "tags": tags or [],
            "entry_hash": hashlib.md5(json.dumps(sanitized_entry, sort_keys=True).encode()).hexdigest()[:8],
            **sanitized_entry,
        }
        
        # Append to file (create if missing)
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
        
        logger.info(f"appended to memory: {category} / {source} / hash:{record['entry_hash']}")
        
        # Update stats
        _update_stats("append", category)
        return True
    
    except Exception as e:
        logger.error(f"append_to_memory failed: {e}", exc_info=True)
        return False


def search_memory(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
    min_score: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Search memory by query and optional category filter.
    
    Args:
      query: search string (e.g., "reentrancy vulnerability")
      category: filter by category (e.g., "findings", "skills")
      limit: max results to return
      min_score: minimum relevance score (0-100+)
    
    Returns:
      List of matching entries, sorted by relevance (descending)
    
    Example:
      matches = search_memory("reentrancy", category="findings", limit=5)
      for match in matches:
        print(f"{match['severity']}: {match['contract']}")
    """
    try:
        query = _sanitize_input(query, 500)
        if not query:
            logger.warning("search_memory: query is empty after sanitization")
            return []
        
        if category:
            category = _sanitize_input(category, 100)
        
        results = []
        
        # Check if memory file exists
        if not MEMORY_FILE.exists():
            logger.info("search_memory: memory file does not exist yet")
            return []
        
        # Read & score each entry
        try:
            with open(MEMORY_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    # Filter by category if specified
                    if category and record.get("category") != category:
                        continue
                    
                    # Calculate relevance
                    # Search across entry_data (all fields except metadata)
                    text_to_search = " ".join([
                        str(v) for k, v in record.items()
                        if k not in ["timestamp", "category", "source", "tags", "entry_hash"]
                        and isinstance(v, (str, int, float, bool))
                    ])
                    
                    score = _relevance_score(query, text_to_search)
                    
                    if score >= min_score:
                        results.append({
                            "score": score,
                            "data": record,
                        })
        except IOError as e:
            logger.error(f"search_memory: failed to read memory file: {e}")
            return []
        
        # Sort by score (descending) and return top N
        results.sort(key=lambda x: x["score"], reverse=True)
        top_results = [r["data"] for r in results[:limit]]
        
        logger.info(f"search_memory: query='{query}' category={category} found={len(top_results)}/{len(results)}")
        _update_stats("search", category or "all")
        
        return top_results
    
    except Exception as e:
        logger.error(f"search_memory failed: {e}", exc_info=True)
        return []


def get_memory_stats() -> Dict[str, Any]:
    """
    Retrieve memory statistics: total entries, categories, operations.
    
    Returns:
      Dict with stats like {"total_entries": 42, "categories": {...}, "operations": {...}}
    """
    try:
        stats = {
            "total_entries": 0,
            "categories": {},
            "total_searches": 0,
            "total_appends": 0,
            "last_updated": None,
        }
        
        if not MEMORY_FILE.exists():
            return stats
        
        try:
            with open(MEMORY_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        stats["total_entries"] += 1
                        cat = record.get("category", "unknown")
                        stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
                        stats["last_updated"] = record.get("timestamp")
                    except json.JSONDecodeError:
                        continue
        except IOError as e:
            logger.warning(f"get_memory_stats: failed to read: {e}")
        
        # Load operation stats if exists
        if STATS_FILE.exists():
            try:
                with open(STATS_FILE, "r") as f:
                    op_stats = json.load(f)
                    stats["total_searches"] = op_stats.get("searches", 0)
                    stats["total_appends"] = op_stats.get("appends", 0)
            except Exception as e:
                logger.warning(f"get_memory_stats: failed to read op stats: {e}")
        
        return stats
    
    except Exception as e:
        logger.error(f"get_memory_stats failed: {e}", exc_info=True)
        return {}


def _update_stats(operation: str, category: str) -> None:
    """Update operation statistics (internal)."""
    try:
        stats = {}
        if STATS_FILE.exists():
            try:
                with open(STATS_FILE, "r") as f:
                    stats = json.load(f)
            except:
                pass
        
        if operation == "append":
            stats["appends"] = stats.get("appends", 0) + 1
            stats["last_append_category"] = category
        elif operation == "search":
            stats["searches"] = stats.get("searches", 0) + 1
            stats["last_search_category"] = category
        
        stats["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        logger.debug(f"_update_stats failed (non-critical): {e}")


def clear_memory() -> bool:
    """Clear all memory (DESTRUCTIVE — use with caution)."""
    try:
        if MEMORY_FILE.exists():
            MEMORY_FILE.unlink()
        if STATS_FILE.exists():
            STATS_FILE.unlink()
        logger.warning("memory cleared")
        return True
    except Exception as e:
        logger.error(f"clear_memory failed: {e}")
        return False


if __name__ == "__main__":
    # Simple test
    print("=== Memory Retriever Test ===\n")
    
    # Test append
    print("1. Testing append_to_memory...")
    append_to_memory("findings", {
        "type": "test_finding",
        "severity": "HIGH",
        "description": "This is a test finding for memory system validation",
    }, source="test", tags=["test", "validation"])
    
    append_to_memory("skills", {
        "name": "test_skill",
        "description": "A test skill to verify memory storage",
        "tier": "static",
    }, source="test")
    
    # Test search
    print("\n2. Testing search_memory...")
    results = search_memory("test finding")
    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  - {r['category']}: {r.get('name', r.get('type', 'N/A'))}")
    
    # Test stats
    print("\n3. Testing get_memory_stats...")
    stats = get_memory_stats()
    print(f"Total entries: {stats['total_entries']}")
    print(f"Categories: {stats['categories']}")
    print(f"Total searches: {stats['total_searches']}")
    print(f"Total appends: {stats['total_appends']}")
    
    print("\n✅ Memory retriever functional!\n")
