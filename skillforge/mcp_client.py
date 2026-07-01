#!/usr/bin/env python3
"""
V.A.P.E. MCP Client — makes VAPE a standard MCP *host*.

Pure stdlib. Spawns any MCP server over stdio, performs the JSON-RPC 2.0
handshake (protocol 2024-11-05), and lists / calls its tools. This is what lets
VAPE consume the whole MCP ecosystem — official reference servers (filesystem,
git, sqlite, fetch) and community search/scrape servers (Brave, Tavily,
Firecrawl, Apify, Bright Data) — without a bespoke integration for each.

Design (matches VAPE's model):
  - ZERO new dependencies. subprocess + json only.
  - Lazy: a server is only spawned when actually called, then torn down.
  - Safe: env is allow-listed per server (only declared keys pass through).
  - Keyless-first: servers needing a missing key report `available=False`
    instead of crashing, so callers can fall back.

Server definitions live in `mcp_servers/registry.json`. Use this module directly:

  python -m skillforge.mcp_client list                 # registry + availability
  python -m skillforge.mcp_client tools <server>       # discover a server's tools
  python -m skillforge.mcp_client call <server> <tool> '<json-args>'
"""
import os
import sys
import json
import shutil
import subprocess
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "mcp_servers", "registry.json")
PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "vape-host", "version": "1.0.0"}


def load_registry() -> Dict[str, Any]:
    try:
        with open(REGISTRY) as f:
            return json.load(f)
    except Exception:
        return {"servers": {}}


# Common install locations for uvx/npx so servers resolve even when the parent
# process PATH is minimal (e.g. cron/CI). Appended, never overriding real PATH.
_EXTRA_PATH = [
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.cargo/bin"),
    "/usr/local/bin",
]


def _augmented_path():
    parts = os.environ.get("PATH", "").split(os.pathsep)
    for p in _EXTRA_PATH:
        if p and p not in parts and os.path.isdir(p):
            parts.append(p)
    return os.pathsep.join(parts)


def _which(cmd):
    return shutil.which(cmd, path=_augmented_path()) if cmd else None


def _resolve_env(spec: Dict[str, Any]):
    """Return (env_dict, missing_keys). Only declared env vars pass through."""
    env = {"PATH": _augmented_path(), "HOME": os.environ.get("HOME", "")}
    missing = []
    for var in spec.get("env", []):
        val = os.environ.get(var)
        if val:
            env[var] = val
        else:
            missing.append(var)
    return env, missing


def server_status(name: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    cmd = spec.get("command")
    _, missing = _resolve_env(spec)
    have_cmd = bool(_which(cmd))
    keyless = spec.get("keyless", False)
    available = have_cmd and (keyless or not missing)
    return {
        "name": name,
        "purpose": spec.get("purpose", ""),
        "command": cmd,
        "keyless": keyless,
        "runtime_present": have_cmd,
        "missing_env": missing,
        "available": available,
    }


class MCPServer:
    """A single MCP server subprocess speaking JSON-RPC 2.0 over stdio."""

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.proc: Optional[subprocess.Popen] = None
        self._id = 0

    def __enter__(self):
        env, _ = _resolve_env(self.spec)
        args = [self.spec["command"], *self.spec.get("args", [])]
        # expand ${ROOT} and env placeholders in args
        args = [a.replace("${ROOT}", ROOT) for a in args]
        self.proc = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=env, text=True, bufsize=1)
        self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        })
        self._notify("notifications/initialized")
        return self

    def __exit__(self, *exc):
        try:
            if self.proc:
                self.proc.terminate()
                self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass

    def _send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _rpc(self, method, params=None, timeout=60):
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method,
                    "params": params or {}})
        # read until we get the matching id (skip notifications/logs)
        import select
        while True:
            if self.proc.poll() is not None:
                raise RuntimeError("server exited")
            r, _, _ = select.select([self.proc.stdout], [], [], timeout)
            if not r:
                raise TimeoutError(f"{method} timed out")
            line = self.proc.stdout.readline()
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == rid:
                if "error" in msg:
                    raise RuntimeError(msg["error"].get("message", "rpc error"))
                return msg.get("result", {})

    def list_tools(self) -> List[Dict[str, Any]]:
        return self._rpc("tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        res = self._rpc("tools/call", {"name": name, "arguments": arguments})
        # normalize MCP content array to text/json
        out = []
        for c in res.get("content", []):
            if c.get("type") == "text":
                out.append(c.get("text", ""))
        text = "\n".join(out)
        try:
            return {"isError": res.get("isError", False), "data": json.loads(text)}
        except Exception:
            return {"isError": res.get("isError", False), "data": text}


def call(server_name: str, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Spawn a server, call one tool, tear down. Returns {ok,data|error}."""
    reg = load_registry()
    spec = reg.get("servers", {}).get(server_name)
    if not spec:
        return {"ok": False, "error": f"unknown server: {server_name}"}
    st = server_status(server_name, spec)
    if not st["available"]:
        return {"ok": False, "error": "server unavailable",
                "status": st}
    try:
        with MCPServer(spec) as s:
            res = s.call_tool(tool, arguments)
            return {"ok": not res.get("isError"), "data": res.get("data")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tools(server_name: str) -> Dict[str, Any]:
    reg = load_registry()
    spec = reg.get("servers", {}).get(server_name)
    if not spec:
        return {"ok": False, "error": f"unknown server: {server_name}"}
    st = server_status(server_name, spec)
    if not st["available"]:
        return {"ok": False, "error": "server unavailable", "status": st}
    try:
        with MCPServer(spec) as s:
            return {"ok": True, "tools": [t["name"] for t in s.list_tools()]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def status_all() -> List[Dict[str, Any]]:
    reg = load_registry()
    return [server_status(n, s) for n, s in reg.get("servers", {}).items()]


def main():
    if len(sys.argv) < 2:
        print("usage: mcp_client [list | tools <server> | call <server> <tool> <json>]")
        return
    cmd = sys.argv[1]
    if cmd == "list":
        print(json.dumps(status_all(), indent=2))
    elif cmd == "tools" and len(sys.argv) >= 3:
        print(json.dumps(tools(sys.argv[2]), indent=2))
    elif cmd == "call" and len(sys.argv) >= 4:
        args = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        print(json.dumps(call(sys.argv[2], sys.argv[3], args), indent=2))
    else:
        print("bad args")


if __name__ == "__main__":
    main()
