"""
VAPE Builder — Self-Improving Code Generation Agent (Priority 2)

The Builder is V.A.P.E.'s self-improvement engine. It:
1. Grounds all code generation in Central Memory (past lessons, patterns, successful tools)
2. Generates new skills, tools, playbooks, and improvement proposals
3. Auto-appends all outputs back to Memory (creating compounding intelligence)
4. Operates at tier="deep" for complex reasoning tasks
5. Includes comprehensive security validation (no unsafe code, no unrestricted actions)
6. Logs all operations for auditability

Integration points:
- agents/run.py → queries Memory for patterns before calling Builder
- skillforge/synthesize.py → uses Builder to distill harvested CVE/tool data
- agents/self_improve.py → uses Builder to generate improvement PRs
- Future: MCP tools can be wrapped by Builder for safe execution

Usage:
  from agents.builder import Builder
  
  builder = Builder()
  code, metadata = builder.generate_code(
    task="Create a playbook for static analysis on new Solidity repos",
    context_query="static analysis patterns"
  )
  # Builder grounds in Memory, generates, validates, auto-appends to Memory
"""

import json
import sys
from datetime import datetime
from typing import Dict, Any, Tuple, List

# Multi-provider LLM (already proven in agents/llm.py)
try:
    from agents.llm import ask as llm_ask, available as llm_available
except Exception:
    try:
        from llm import ask as llm_ask, available as llm_available
    except Exception:
        llm_ask = None
        llm_available = lambda: []

# Memory system (Priority 1)
try:
    from skillforge.memory.retriever import (
        search_memory,
        append_to_memory,
        get_memory_stats,
    )
except Exception as e:
    print(f"[Builder] Warning: Could not import Memory: {e}")
    search_memory = None
    append_to_memory = None

import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [BUILDER] %(levelname)s: %(message)s"
)
logger = logging.getLogger("VAPE.Builder")


# ============================================================================
# Security Validation
# ============================================================================

# HARD BLOCK: genuinely dangerous constructs. If any appear, the generated
# code is rejected outright (arbitrary code exec, shell exec, unsafe deser).
BLOCK_PATTERNS = [
    "eval(",            # arbitrary code execution
    "exec(",            # arbitrary code execution
    "__import__",       # dynamic import evasion
    "os.system(",       # shell execution
    "os.popen(",        # shell execution
    "subprocess.call(", # shell execution (shell=True risk)
    "subprocess.Popen(",
    "subprocess.run(",
    "pickle.load",      # unsafe deserialization
    "pickle.loads",
    "marshal.load",
    "yaml.load(",       # unsafe unless SafeLoader
    "shell=True",       # command injection surface
]

# SOFT WARN: common, legitimate patterns that merely deserve a reviewer's eye.
# These do NOT block; they are recorded and lower the stored confidence.
WARN_PATTERNS = [
    "open(",            # file I/O — fine, but note write scope
    "requests.",       # network — prefer keyless/rate-limited endpoints
    "urllib.request",   # network
    "import os",        # env/path use — usually benign
    "sys.argv",         # CLI input — ensure validation
    "input(",           # interactive input — ensure validation
]


def validate_security(code: str, task: str) -> Tuple[bool, List[str]]:
    """
    Validate generated code for security issues.

    Two tiers:
      - BLOCK_PATTERNS  -> hard reject (is_safe=False)
      - WARN_PATTERNS   -> advisory only (is_safe stays True, warnings recorded)

    Returns:
        (is_safe, list_of_warnings)  # warnings may be present even when safe
    """
    warnings: List[str] = []
    blocked = False

    for pattern in BLOCK_PATTERNS:
        if pattern in code:
            warnings.append(f"BLOCKED: dangerous construct '{pattern}'")
            blocked = True

    for pattern in WARN_PATTERNS:
        if pattern in code:
            warnings.append(f"review: '{pattern}' present (advisory)")

    # Task-specific: destructive file ops need explicit confirmation gates.
    if ("delete" in task.lower() or "remove" in task.lower()):
        if "os.remove" in code or "shutil.rmtree" in code:
            warnings.append("BLOCKED: destructive fs op without confirmation gate")
            blocked = True

    is_safe = not blocked
    return is_safe, warnings


# ============================================================================
# Prompts & System Instructions
# ============================================================================

BUILDER_SYSTEM_PROMPT = """You are BUILDER, V.A.P.E.'s autonomous self-improvement engine.

Your role:
1. Ground all code generation in Memory (past lessons, successful patterns, best practices)
2. Generate production-ready Python code for security tools, playbooks, and improvements
3. Ensure all code is safe, auditable, and minimal
4. Follow V.A.P.E.'s architecture: zero external compute costs, use free APIs only, prioritize on-chain data

Constraints:
- NEVER generate unsafe code (no eval/exec, no unrestricted OS access, no shell commands)
- ALWAYS include input validation and error handling
- ALWAYS prefer compute-free solutions (keyless APIs, GitHub Actions)
- ALWAYS document your reasoning and assumptions
- Output ONLY valid Python code; no explanations unless asked

Code style:
- Use type hints
- Add docstrings to all functions
- Use logging for observability
- Prefer stdlib over external deps (minimize dependencies)

If asked to generate a tool/skill/playbook:
1. Search Memory for similar past work and lessons
2. Ground your generation in those findings
3. Include security validation
4. Return code + metadata (for auto-append to Memory)

If unsure, ask clarifying questions. Never hallucinate APIs or endpoints.
"""

BUILDER_USER_TEMPLATE = """Task: {task}

Memory context (past similar work + lessons):
{memory_context}

Current Memory stats:
{memory_stats}

Requirements:
- Generate production-ready code
- Include comprehensive docstrings and type hints
- Use error handling and logging
- Document all assumptions

Output format:
1. Final code (valid Python)
2. Brief reasoning (2-3 sentences)
3. Metadata for Memory append (title, tags, confidence)
"""

# Same constraints as single-file generation, extended to real multi-file
# tools/scripts/small apps — the actual "VAPE can build things" capability
# (agents/build_request.py), not just narrow single-file bug fixes
# (agents/self_improve.py, which still uses generate_code() above).
BUILDER_PROJECT_SYSTEM_PROMPT = """You are BUILDER, V.A.P.E.'s autonomous project-generation
engine — the same self-improvement engine as single-file generation, extended to produce
complete multi-file tools, scripts, or small apps when a task needs more than one file.

VAPE's core specialization areas (stay inside these unless the task explicitly asks for
something else): Base/EVM on-chain investigation and forensics, smart-contract security
(bug bounty hunting, static/dynamic analysis), autonomous agent tooling, and AI-agent
security (prompt injection, red-teaming). This repo's real stack: Python stdlib-first for
agents/, Hono/TypeScript for worker/, vanilla no-bundler JS for docs/assets/ — match the
existing style of whichever area the task targets, don't introduce a new framework/bundler.

Constraints (same as single-file generation):
- NEVER generate unsafe code (no eval/exec, no unrestricted OS access, no shell commands)
- ALWAYS include input validation and error handling
- ALWAYS prefer compute-free/keyless solutions consistent with this repo's ethos
- Never invent APIs, endpoints, or libraries that don't exist
- No disclaimers, no "as an AI" — just the files

Output format — one or more files, each as exactly:
### FILE: relative/path/to/file.ext
```<language>
...full file content...
```

Always include the `### FILE:` header before every code block, even for a single file — the
parser requires it. Use relative paths only (no leading `/`, no `..` segments).
"""


# ============================================================================
# Builder Class
# ============================================================================

class Builder:
    """Self-improving code generation agent grounded in Memory."""
    
    def __init__(self):
        self.name = "BUILDER"
        self.created_at = datetime.utcnow().isoformat()
        self.outputs = []  # Track all outputs (for audit trail)
        
        if not llm_available():
            logger.warning("No LLM provider available. Builder will not function.")
            self.llm_ready = False
        else:
            self.llm_ready = True
            logger.info(f"Builder initialized with LLM providers: {llm_available()}")
    
    def _ground_in_memory(self, task: str) -> str:
        """Search Memory for relevant context to ground task."""
        if not search_memory:
            return "Memory not available."
        
        # Broad search for patterns + lessons relevant to task
        results = search_memory(
            query=task,
            category=None,  # Search all categories
            max_results=5,
            min_confidence=0.7
        )
        
        if not results:
            return "No prior Memory entries found. Starting fresh."
        
        context = "Recent Memory findings:\n"
        for r in results:
            context += f"\n- [{r['category'].upper()}] {r['title']}\n"
            context += f"  Source: {r['source']} | Confidence: {r['confidence']}\n"
            context += f"  Content: {r['content'][:200]}...\n"
        
        return context
    
    def _build_prompt(self, task: str) -> str:
        """Build the full prompt with Memory grounding."""
        memory_context = self._ground_in_memory(task)
        
        try:
            stats = get_memory_stats()
            stats_str = f"Entries: {stats['total_entries']} | Categories: {stats['by_category']}"
        except Exception:
            stats_str = "Stats unavailable"
        
        prompt = BUILDER_USER_TEMPLATE.format(
            task=task,
            memory_context=memory_context,
            memory_stats=stats_str
        )
        
        return prompt
    
    def generate_code(
        self,
        task: str,
        review: bool = True,
        tier: str = "deep"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate production code for a task, grounded in Memory.
        
        Args:
            task: Task description (e.g., "Create a playbook for static analysis")
            review: Whether to validate code before returning
            tier: LLM tier ("fast" or "deep" for reasoning)
        
        Returns:
            (code, metadata) where metadata has title, tags, confidence for Memory append
        """
        if not self.llm_ready:
            logger.error("LLM not ready. Cannot generate code.")
            return "", {}
        
        logger.info(f"Builder generating code for task: {task[:80]}...")
        
        # Build prompt with Memory grounding
        prompt = self._build_prompt(task)
        
        # Call LLM
        try:
            response, provider = llm_ask(
                system=BUILDER_SYSTEM_PROMPT,
                user=prompt,
                tier=tier,
                max_tokens=3000,
                temperature=0.7
            )
            logger.info(f"LLM generation complete (provider: {provider})")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return "", {}
        
        # Extract code from response (assume it's marked with ```python ... ```)
        code = self._extract_code_block(response)
        
        if not code:
            logger.error("No code block found in LLM response")
            return "", {}
        
        # Security review
        if review:
            is_safe, warnings = validate_security(code, task)
            if warnings:
                logger.warning("Security review notes:\n" + "\n".join(warnings))
            if not is_safe:
                logger.error("Code contains BLOCKED constructs. Rejecting generation.")
                return "", {}
            # Advisory (non-blocking) warnings are recorded in metadata below.
        
        # Generate metadata for Memory append
        metadata = self._extract_metadata(task, response, is_safe if review else True)
        
        # Store in audit trail
        self.outputs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "task": task,
            "code_len": len(code),
            "provider": provider,
            "metadata": metadata,
            "safe": is_safe if review else True
        })
        
        logger.info(f"Code generation successful ({len(code)} chars)")
        return code, metadata
    
    def generate_project(
        self,
        task: str,
        review: bool = True,
        tier: str = "deep"
    ) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """
        Generate a real multi-file tool/script/small app for a task, grounded
        in Memory — the extension that makes "VAPE can build things" concrete
        rather than limited to generate_code()'s single-file scope.

        Args:
            task: Task description, e.g. a real GitHub issue's title + body
            review: Whether to validate all generated files before returning
            tier: LLM tier ("fast" or "deep" for reasoning)

        Returns:
            (files, metadata) where files is {relative_path: content}. Empty
            dict on any failure — callers should treat that as "nothing to
            do this cycle," never fabricate files to fill the gap.
        """
        if not self.llm_ready:
            logger.error("LLM not ready. Cannot generate project.")
            return {}, {}

        logger.info(f"Builder generating project for task: {task[:80]}...")
        prompt = self._build_prompt(task)

        try:
            response, provider = llm_ask(
                system=BUILDER_PROJECT_SYSTEM_PROMPT,
                user=prompt,
                tier=tier,
                max_tokens=4000,
                temperature=0.7
            )
            logger.info(f"LLM generation complete (provider: {provider})")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {}, {}

        files = self._extract_files(response)
        if not files:
            logger.error("No FILE blocks found in LLM response")
            return {}, {}

        if review:
            combined = "\n\n".join(files.values())
            is_safe, warnings = validate_security(combined, task)
            if warnings:
                logger.warning("Security review notes:\n" + "\n".join(warnings))
            if not is_safe:
                logger.error("Project contains BLOCKED constructs. Rejecting generation.")
                return {}, {}

        metadata = self._extract_metadata(task, response, True)
        metadata["files"] = list(files.keys())

        self.outputs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "task": task,
            "files": list(files.keys()),
            "provider": provider,
            "metadata": metadata,
            "safe": True,
        })

        logger.info(f"Project generation successful ({len(files)} files)")
        return files, metadata

    def propose_improvement(
        self,
        module: str,
        issue: str,
        tier: str = "deep"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Propose an improvement to an existing module.
        
        Args:
            module: Which module to improve (e.g., "agents/run.py")
            issue: What to improve (e.g., "Add Memory querying to find past patterns")
        
        Returns:
            (code_diff_or_patch, metadata)
        """
        task = f"Improve {module}: {issue}"
        logger.info(f"Builder proposing improvement: {task[:80]}...")

        # This would typically read the existing file, ground in Memory, then propose changes
        # For now, delegate to generate_code with improvement framing
        code, metadata = self.generate_code(
            task=task,
            review=True,
            tier=tier
        )
        
        return code, metadata
    
    def auto_append_to_memory(self, code: str, metadata: Dict[str, Any]) -> bool:
        """Auto-append generated code/skill to Memory."""
        if not append_to_memory:
            logger.warning("Memory not available. Cannot auto-append.")
            return False
        
        try:
            result = append_to_memory(
                category="skill",
                title=metadata.get("title", "Generated Skill"),
                content=code,
                source="agents/builder.py",
                tags=metadata.get("tags", ["builder", "generated"]),
                confidence=metadata.get("confidence", 0.8),
                metadata={
                    "task_summary": metadata.get("task_summary", ""),
                    "code_lines": len(code.split("\n")),
                    "generated_at": datetime.utcnow().isoformat(),
                }
            )
            logger.info(f"Auto-appended to Memory: {result.get('id', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to auto-append to Memory: {e}")
            return False
    
    # ========================================================================
    # Utilities
    # ========================================================================
    
    @staticmethod
    def _extract_code_block(response: str) -> str:
        """Extract Python code from markdown code block."""
        import re
        # Look for ```python ... ``` or ``` ... ```
        match = re.search(r'```(?:python)?\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback: if response looks like code, return it
        if "def " in response or "class " in response or "import " in response:
            return response.strip()
        
        return ""
    
    @staticmethod
    def _extract_files(response: str) -> Dict[str, str]:
        """Parse '### FILE: path\\n```lang\\ncontent\\n```' blocks into
        {path: content}. Rejects path traversal / absolute paths (this
        parses LLM output that may be influenced by untrusted input, e.g. a
        GitHub issue body in agents/build_request.py) and caps file count
        and size so a runaway generation can't produce an enormous diff."""
        import re
        MAX_FILES = 20
        MAX_FILE_BYTES = 50_000
        files: Dict[str, str] = {}
        pattern = re.compile(r'###\s*FILE:\s*(\S+)\s*\n```[a-zA-Z0-9_+-]*\n(.*?)\n```', re.DOTALL)
        for match in pattern.finditer(response):
            if len(files) >= MAX_FILES:
                logger.warning(f"generate_project: hit MAX_FILES={MAX_FILES}, dropping the rest")
                break
            path = match.group(1).strip()
            if path.startswith("/") or path.startswith("~") or ".." in path.split("/"):
                logger.warning(f"generate_project: rejected unsafe path '{path}'")
                continue
            content = match.group(2)
            if len(content.encode("utf-8", errors="ignore")) > MAX_FILE_BYTES:
                logger.warning(f"generate_project: truncating oversized file '{path}'")
                content = content[:MAX_FILE_BYTES]
            files[path] = content
        return files

    @staticmethod
    def _extract_metadata(task: str, response: str, is_safe: bool) -> Dict[str, Any]:
        """Extract metadata from task + response."""
        # Simple extraction: first line of response as title
        first_line = response.split("\n")[0][:100]
        
        # Infer tags from task
        tags = ["builder", "generated"]
        if "playbook" in task.lower():
            tags.append("playbook")
        if "static" in task.lower():
            tags.append("static-analysis")
        if "recon" in task.lower():
            tags.append("recon")
        if "fuzzing" in task.lower():
            tags.append("fuzzing")
        
        return {
            "title": f"Generated: {first_line}",
            "task_summary": task[:200],
            "tags": tags,
            "confidence": 0.85 if is_safe else 0.6,  # Lower confidence if unsafe patterns
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Return audit trail of all code generation tasks."""
        return self.outputs
    
    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "created_at": self.created_at,
            "total_tasks": len(self.outputs),
            "safe_tasks": sum(1 for o in self.outputs if o.get("safe", False)),
            "total_code_chars": sum(o.get("code_len", 0) for o in self.outputs),
        }


# ============================================================================
# CLI Usage
# ============================================================================

def main():
    """CLI entry point for Builder."""
    import argparse
    
    parser = argparse.ArgumentParser(description="V.A.P.E. Builder - Self-Improvement Agent")
    parser.add_argument("task", nargs="?", help="Task to generate code for")
    parser.add_argument("--improve", help="Module to improve (propose improvement)")
    parser.add_argument("--no-review", action="store_true", help="Skip security review")
    parser.add_argument("--tier", default="deep", choices=["fast", "deep"], help="LLM tier")
    parser.add_argument("--stats", action="store_true", help="Show Builder statistics")
    
    args = parser.parse_args()
    
    builder = Builder()
    
    if args.stats:
        stats = builder.get_stats()
        print(json.dumps(stats, indent=2))
        return
    
    if not args.task and not args.improve:
        parser.print_help()
        return
    
    if args.improve:
        # Propose improvement
        module, issue = args.improve.split(":", 1) if ":" in args.improve else (args.improve, "general improvement")
        code, metadata = builder.propose_improvement(module, issue, tier=args.tier)
    else:
        # Generate code
        code, metadata = builder.generate_code(
            task=args.task,
            review=not args.no_review,
            tier=args.tier
        )
    
    if code:
        print("\n" + "=" * 80)
        print("GENERATED CODE")
        print("=" * 80)
        print(code)
        print("\n" + "=" * 80)
        print("METADATA")
        print("=" * 80)
        print(json.dumps(metadata, indent=2))
        
        # Auto-append to Memory
        if builder.auto_append_to_memory(code, metadata):
            print("\n✅ Auto-appended to Memory")
    else:
        print("❌ Code generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
