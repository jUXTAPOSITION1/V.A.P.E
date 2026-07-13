"""
Integration status — reports whether Memory, Builder, and MCP are wired up.

Earlier versions of this module also contained analysis_with_memory_grounding(),
builder_generate_and_append(), mcp_harvest_and_append(), and run_full_cycle() —
all gated behind a VAPE_FULL_CYCLE env var that was never set in any workflow
(confirmed via repo-wide grep), so they never ran in production, and all built
on fabricated placeholder data (a literal "sample_threat_data" string, a
`bounties=[]  # Would fetch real bounties` stub) rather than real evidence.
Removed rather than left as dead capability-shaped code that isn't real —
each of the three systems below is already wired into the actual pipelines
that use it directly (agents/run.py, agents/builder.py, skillforge/mcp.py),
so nothing here was a genuine gap.
"""

import importlib
import logging

logger = logging.getLogger("VAPE.Integration")

# Availability checks only — each system is used directly by its own real
# caller (agents/run.py, agents/builder.py, skillforge/mcp.py), not through
# this module, so nothing here needs to bind an unused name.
try:
    from skillforge.memory.retriever import get_memory_stats
    MEMORY_AVAILABLE = True
except Exception as e:
    logger.warning(f"Memory not available: {e}")
    MEMORY_AVAILABLE = False
    get_memory_stats = None

try:
    importlib.import_module("agents.builder")
    BUILDER_AVAILABLE = True
except Exception as e:
    logger.warning(f"Builder not available: {e}")
    BUILDER_AVAILABLE = False

try:
    importlib.import_module("skillforge.mcp")
    MCP_AVAILABLE = True
except Exception as e:
    logger.warning(f"MCP not available: {e}")
    MCP_AVAILABLE = False


def get_system_status():
    """Real availability check for the three optional subsystems — printed
    at the start of every agents/run.py cycle."""
    return {
        "memory_available": MEMORY_AVAILABLE,
        "builder_available": BUILDER_AVAILABLE,
        "mcp_available": MCP_AVAILABLE,
        "memory_stats": get_memory_stats() if MEMORY_AVAILABLE and get_memory_stats else None,
    }


if __name__ == "__main__":
    print("Integration status for Memory, Builder, and MCP")
    print(f"Status: {get_system_status()}")
