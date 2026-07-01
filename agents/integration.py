"""
Integration Glue — Wire Memory, Builder, and MCP into Detective Flows

This module coordinates the three new systems:
- Memory: Central brain (findings, lessons, skills, social events)
- Builder: Self-improvement agent (grounded in Memory, auto-appends outputs)
- MCP: External data sources (GitHub, Social, Tool Registry)

All flows query Memory at start, get grounded context, and append new findings at end.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("VAPE.Integration")

# Optional imports (graceful degradation if not available)
try:
    from skillforge.memory.retriever import (
        search_memory, append_to_memory, get_memory_stats
    )
    MEMORY_AVAILABLE = True
except Exception as e:
    logger.warning(f"Memory not available: {e}")
    MEMORY_AVAILABLE = False
    search_memory = None
    append_to_memory = None

try:
    from agents.builder import Builder
    BUILDER_AVAILABLE = True
except Exception as e:
    logger.warning(f"Builder not available: {e}")
    BUILDER_AVAILABLE = False
    Builder = None

try:
    from skillforge.mcp import run_mcp_harvest
    MCP_AVAILABLE = True
except Exception as e:
    logger.warning(f"MCP not available: {e}")
    MCP_AVAILABLE = False
    run_mcp_harvest = None


# ============================================================================
# Flow: Detective Analysis with Memory Grounding
# ============================================================================

def analysis_with_memory_grounding(
    task: str,
    data: Dict[str, Any],
    category: str = "finding"
) -> Dict[str, Any]:
    """
    Run analysis grounded in past findings + auto-append new findings to Memory.
    
    Args:
        task: Analysis task description
        data: Data to analyze (market data, slither results, etc.)
        category: Memory category for append ("finding", "lesson", etc.)
    
    Returns:
        Analysis result dict
    """
    result = {
        "task": task,
        "grounded_in_memory": False,
        "memory_context": [],
        "analysis": None,
        "appended_to_memory": False,
    }
    
    # Step 1: Ground in Memory
    if MEMORY_AVAILABLE and search_memory:
        try:
            context = search_memory(
                query=task,
                max_results=5,
                min_confidence=0.7
            )
            result["memory_context"] = context
            result["grounded_in_memory"] = True
            
            if context:
                logger.info(f"Grounded '{task}' in {len(context)} Memory entries")
            else:
                logger.info(f"No prior Memory entries for '{task}' — starting fresh")
        except Exception as e:
            logger.warning(f"Memory grounding failed: {e}")
    
    # Step 2: Run analysis (caller's responsibility; this just coordinates)
    # The actual analysis happens in agents/run.py, which calls this function
    result["analysis"] = data.get("analysis_result", {})
    
    # Step 3: Append findings to Memory
    if MEMORY_AVAILABLE and append_to_memory and result["analysis"]:
        try:
            entry = append_to_memory(
                category=category,
                title=f"{task} — Finding",
                content=str(result["analysis"])[:2000],
                source="agents/run.py",
                tags=task.split(),
                confidence=data.get("confidence", 0.8),
                metadata={
                    "task": task,
                    "timestamp": data.get("timestamp"),
                }
            )
            result["appended_to_memory"] = True
            logger.info(f"Appended finding to Memory (ID: {entry.get('id')})")
        except Exception as e:
            logger.warning(f"Failed to append to Memory: {e}")
    
    return result


# ============================================================================
# Flow: Builder Code Generation (Self-Improvement)
# ============================================================================

def builder_generate_and_append(
    task: str,
    context_query: Optional[str] = None,
    tier: str = "deep"
) -> Dict[str, Any]:
    """
    Generate code via Builder, grounded in Memory, auto-append to Memory.
    
    Args:
        task: Code generation task
        context_query: Optional Memory search query for grounding
        tier: LLM tier ("fast" or "deep")
    
    Returns:
        Result dict with generated code, metadata, memory append status
    """
    result = {
        "task": task,
        "generated": False,
        "code": "",
        "metadata": {},
        "memory_appended": False,
        "error": None,
    }
    
    if not BUILDER_AVAILABLE or not Builder:
        result["error"] = "Builder not available"
        return result
    
    try:
        builder = Builder()
        
        # Use provided query or default to task
        search_query = context_query or task
        
        # Generate code (Builder internally grounds in Memory)
        code, metadata = builder.generate_code(
            task=task,
            review=True,
            tier=tier
        )
        
        if not code:
            result["error"] = "Code generation failed"
            return result
        
        result["generated"] = True
        result["code"] = code
        result["metadata"] = metadata
        
        # Auto-append to Memory (Builder handles this internally)
        try:
            if builder.auto_append_to_memory(code, metadata):
                result["memory_appended"] = True
        except Exception as e:
            logger.warning(f"Builder Memory append failed: {e}")
        
        logger.info(f"Builder generated code for '{task}'")
    
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Builder generation failed: {e}")
    
    return result


# ============================================================================
# Flow: MCP Data Harvest → Memory Append
# ============================================================================

def mcp_harvest_and_append() -> Dict[str, Any]:
    """
    Run MCP harvest cycle and append results to Memory.
    
    Returns:
        Harvest results (GitHub issues, social sentiment, tool updates)
    """
    result = {
        "harvested": False,
        "appended": False,
        "data": {},
        "error": None,
    }
    
    if not MCP_AVAILABLE or not run_mcp_harvest:
        result["error"] = "MCP not available"
        return result
    
    try:
        # Run MCP harvest
        mcp_data = run_mcp_harvest()
        result["harvested"] = True
        result["data"] = mcp_data
        
        # Append summary to Memory
        if MEMORY_AVAILABLE and append_to_memory:
            try:
                append_to_memory(
                    category="finding",
                    title="MCP Harvest Summary",
                    content=str(mcp_data)[:2000],
                    source="skillforge/mcp.py",
                    tags=["mcp", "harvest", "external-data"],
                    confidence=0.75,
                    metadata=mcp_data
                )
                result["appended"] = True
                logger.info("MCP harvest summary appended to Memory")
            except Exception as e:
                logger.warning(f"Failed to append MCP data to Memory: {e}")
        
        logger.info(f"MCP harvest complete: {mcp_data}")
    
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"MCP harvest failed: {e}")
    
    return result


# ============================================================================
# Flow: Full Cycle (Detective + Builder + MCP + Memory)
# ============================================================================

def run_full_cycle(
    market_data: Dict[str, Any],
    slither_output: str,
    bounties: list
) -> Dict[str, Any]:
    """
    Run the complete V.A.P.E. cycle with all three systems integrated.
    
    Args:
        market_data: Real market/chain data
        slither_output: Static analysis results
        bounties: List of active bounties
    
    Returns:
        Comprehensive result dict
    """
    cycle_result = {
        "timestamp": None,
        "detective_grounded": False,
        "builder_generated": False,
        "mcp_harvested": False,
        "memory_stats": {},
        "findings": [],
        "generated_skills": [],
        "external_data": {},
    }
    
    from datetime import datetime
    cycle_result["timestamp"] = datetime.utcnow().isoformat()
    
    # Step 1: Detective analysis grounded in Memory
    logger.info("Step 1: Running detective analysis grounded in Memory...")
    analysis_result = analysis_with_memory_grounding(
        task="Analyze market anomalies and security threats",
        data={
            "analysis_result": {
                "anomalies_detected": len([b for b in bounties if b.get("priority") == "high"]),
                "threats": "sample_threat_data",
            },
            "confidence": 0.85,
            "timestamp": cycle_result["timestamp"],
        }
    )
    cycle_result["detective_grounded"] = analysis_result["grounded_in_memory"]
    cycle_result["findings"] = analysis_result["memory_context"]
    
    # Step 2: Builder generates improvements grounded in Memory
    logger.info("Step 2: Builder generating code improvements...")
    builder_result = builder_generate_and_append(
        task="Create playbook for analyzing new Solidity smart contracts",
        context_query="static analysis pattern",
        tier="deep"
    )
    cycle_result["builder_generated"] = builder_result["generated"]
    if builder_result["code"]:
        cycle_result["generated_skills"].append({
            "title": builder_result["metadata"].get("title"),
            "code_lines": len(builder_result["code"].split("\n")),
            "memory_appended": builder_result["memory_appended"],
        })
    
    # Step 3: MCP harvest external data
    logger.info("Step 3: Harvesting external data via MCP...")
    mcp_result = mcp_harvest_and_append()
    cycle_result["mcp_harvested"] = mcp_result["harvested"]
    cycle_result["external_data"] = mcp_result["data"]
    
    # Step 4: Memory stats
    if MEMORY_AVAILABLE and get_memory_stats:
        try:
            stats = get_memory_stats()
            cycle_result["memory_stats"] = stats
            logger.info(f"Memory now contains {stats['total_entries']} entries")
        except Exception as e:
            logger.warning(f"Failed to get Memory stats: {e}")
    
    logger.info("Full cycle complete!")
    return cycle_result


# ============================================================================
# Helpers
# ============================================================================

def get_system_status() -> Dict[str, Any]:
    """Get status of all three systems."""
    return {
        "memory_available": MEMORY_AVAILABLE,
        "builder_available": BUILDER_AVAILABLE,
        "mcp_available": MCP_AVAILABLE,
        "memory_stats": get_memory_stats() if MEMORY_AVAILABLE and get_memory_stats else None,
    }


if __name__ == "__main__":
    print("Integration module for Memory, Builder, and MCP")
    print(f"Status: {get_system_status()}")
