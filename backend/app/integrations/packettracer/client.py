"""Launch MCP worker via uvx (works even if FastAPI runs on older Python)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Set

ROOT = Path(__file__).resolve().parents[3]  # backend/
PROJECTS_DIR = ROOT / "results" / "packettracer_projects"

# In-flight / completed execution ids for duplicate protection (process-local).
_SEEN_EXECUTIONS: Set[str] = set()
_ACTIVE_EXECUTIONS: Set[str] = set()

# Status probes spawn uvx and can take tens of seconds — cache + single-flight
# so polling does not wedge the whole FastAPI worker.
_STATUS_TTL_S = 12.0
_STATUS_LOCK = threading.Lock()
_STATUS_INFLIGHT = threading.Event()
_STATUS_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}


def projects_dir() -> Path:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR


def new_execution_id() -> str:
    return uuid.uuid4().hex


def claim_execution_id(execution_id: str) -> Optional[str]:
    """Return error message if duplicate/in-flight; else claim id."""
    if execution_id in _ACTIVE_EXECUTIONS:
        return f"execution_id {execution_id} is already running"
    if execution_id in _SEEN_EXECUTIONS:
        return f"execution_id {execution_id} was already used (duplicate prevented)"
    _ACTIVE_EXECUTIONS.add(execution_id)
    return None


def release_execution_id(execution_id: str, success: bool) -> None:
    _ACTIVE_EXECUTIONS.discard(execution_id)
    if success:
        _SEEN_EXECUTIONS.add(execution_id)
    else:
        # allow retry with same id after failure
        _SEEN_EXECUTIONS.discard(execution_id)


def mcp_base_url() -> str:
    return (os.getenv("PACKETTRACER_MCP_URL") or "http://127.0.0.1:39400").rstrip("/")


def is_enabled() -> bool:
    return (os.getenv("PACKETTRACER_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def expected_token() -> str:
    return (os.getenv("PACKETTRACER_TOKEN") or "").strip()


def check_token(provided: Optional[str]) -> bool:
    expected = expected_token()
    if not expected:
        # If enabled without token, allow local-only use but discourage it.
        return True
    return (provided or "").strip() == expected


def status_probe() -> Dict[str, Any]:
    """Cached bridge/canvas status. Safe to poll; never blocks other requests for long when cached."""
    if not is_enabled():
        return {
            "ready": False,
            "enabled": False,
            "canvas_empty": False,
            "detail": "PACKETTRACER_ENABLED is false",
        }
    if shutil.which("uvx") is None:
        return {
            "ready": False,
            "enabled": True,
            "canvas_empty": False,
            "detail": "uvx not found on PATH",
        }

    now = time.time()
    with _STATUS_LOCK:
        cached = _STATUS_CACHE.get("data")
        ts = float(_STATUS_CACHE.get("ts") or 0.0)
        if cached is not None and (now - ts) < _STATUS_TTL_S:
            return dict(cached)
        # Another thread already probing — return stale or a fast "checking" payload
        if _STATUS_INFLIGHT.is_set():
            if cached is not None:
                return dict(cached)
            return {
                "ready": False,
                "enabled": True,
                "canvas_empty": False,
                "detail": "Checking Packet Tracer…",
            }
        _STATUS_INFLIGHT.set()

    try:
        data = _status_probe_uncached()
    finally:
        _STATUS_INFLIGHT.clear()

    with _STATUS_LOCK:
        _STATUS_CACHE["ts"] = time.time()
        _STATUS_CACHE["data"] = data
    return dict(data)


def invalidate_status_cache() -> None:
    with _STATUS_LOCK:
        _STATUS_CACHE["ts"] = 0.0
        _STATUS_CACHE["data"] = None


def _status_probe_uncached() -> Dict[str, Any]:
    """Actual MCP HTTP + bridge/canvas check (slow)."""
    try:
        import httpx

        url = mcp_base_url() + "/mcp"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "toposcribe-status", "version": "0.1"},
            },
        }
        with httpx.Client(timeout=3.0) as client:
            r = client.post(url, headers=headers, json=body)
            if r.status_code != 200:
                return {
                    "ready": False,
                    "enabled": True,
                    "mcp_url": mcp_base_url(),
                    "canvas_empty": False,
                    "detail": f"MCP HTTP {r.status_code}",
                }
        return _bridge_status_via_worker()
    except Exception as e:
        return {
            "ready": False,
            "enabled": True,
            "mcp_url": mcp_base_url(),
            "canvas_empty": False,
            "detail": f"MCP unreachable: {e}",
        }


def _bridge_status_via_worker() -> Dict[str, Any]:
    # Bridge + canvas occupancy in one MCP session (for Launch PT button gating).
    code = r"""
import asyncio, json, sys, re
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
url = sys.argv[1].rstrip('/') + '/mcp'
POWER = re.compile(r'power\s*distribution', re.I)

def count_user(text: str) -> int:
    text = text or ''
    m = re.search(r'DEVICES\s*:\s*(\d+)', text, re.I)
    if m and 'Power Distribution' not in text and '\n  ' not in text:
        return int(m.group(1))
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if not s or s.upper().startswith('DEVICES') or s.upper().startswith('LINKS'):
            continue
        if POWER.search(s):
            continue
        if re.match(r'^[A-Za-z0-9_.-]+\s+\[', s) or ('[' in s and re.match(r'^[A-Za-z0-9_.-]+\s+', s)):
            n += 1
    if n:
        return n
    if m:
        power = len(re.findall(r'Power Distribution Device', text, re.I))
        return max(0, int(m.group(1)) - power)
    return 0

async def main():
    async with streamable_http_client(url) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            br = await session.call_tool('pt_bridge_status', {})
            bridge_texts = [getattr(c,'text',str(c)) for c in (br.content or [])]
            tr = await session.call_tool('pt_query_topology', {})
            topo_texts = [getattr(c,'text',str(c)) for c in (tr.content or [])]
            topo = '\n'.join(topo_texts)
            print(json.dumps({
                'bridge_texts': bridge_texts,
                'topology': topo,
                'user_devices': count_user(topo),
            }))
asyncio.run(main())
"""
    try:
        proc = subprocess.run(
            [
                "uvx",
                "--from",
                "mcp[cli]",
                "--with",
                "mcp",
                "python",
                "-c",
                code,
                mcp_base_url(),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if proc.returncode != 0:
            return {
                "ready": False,
                "enabled": True,
                "mcp_url": mcp_base_url(),
                "canvas_empty": False,
                "detail": (proc.stderr or proc.stdout or "bridge status failed")[:500],
            }
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        text = "\n".join(payload.get("bridge_texts") or [])
        ready = "CONNECTED" in text and "NOT connected" not in text
        user_devices = int(payload.get("user_devices") or 0)
        canvas_empty = user_devices == 0
        detail = "ok"
        if not ready:
            detail = "Packet Tracer not connected (open Extensions > MCP BUILDER)"
        elif not canvas_empty:
            detail = f"Canvas not empty ({user_devices} device(s)). Open a blank Packet Tracer project."
        return {
            "ready": ready and canvas_empty,
            "enabled": True,
            "mcp_url": mcp_base_url(),
            "pt_bridge": text,
            "canvas_empty": canvas_empty,
            "user_devices": user_devices,
            "detail": detail,
        }
    except Exception as e:
        return {
            "ready": False,
            "enabled": True,
            "mcp_url": mcp_base_url(),
            "canvas_empty": False,
            "detail": str(e),
        }


def run_worker(request: Dict[str, Any], timeout_s: int = 900) -> Dict[str, Any]:
    """Execute full deploy worker; returns result dict."""
    projects_dir().mkdir(parents=True, exist_ok=True)
    exec_dir = projects_dir() / request["execution_id"]
    exec_dir.mkdir(parents=True, exist_ok=True)
    req_path = exec_dir / "request.json"
    res_path = exec_dir / "result.json"
    request = dict(request)
    request["project_dir"] = str(exec_dir)
    request["mcp_url"] = mcp_base_url()
    req_path.write_text(json.dumps(request), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.run(
        [
            "uvx",
            "--from",
            "mcp[cli]",
            "--with",
            "mcp",
            "python",
            "-m",
            "app.integrations.packettracer.mcp_worker",
            str(req_path),
            str(res_path),
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if not res_path.exists():
        return {
            "execution_id": request.get("execution_id"),
            "ok": False,
            "stage": "worker",
            "message": f"worker failed: rc={proc.returncode} stderr={proc.stderr[:1000]}",
            "devices": [],
            "links": [],
            "cli_lines": [],
            "pings": [],
            "raw_notes": [proc.stdout[-2000:], proc.stderr[-2000:]],
        }
    data = json.loads(res_path.read_text(encoding="utf-8"))
    if proc.returncode != 0 and data.get("ok"):
        # prefer file content
        pass
    if proc.stderr:
        data.setdefault("raw_notes", []).append(f"worker_stderr:{proc.stderr[-1500:]}")
    return data
