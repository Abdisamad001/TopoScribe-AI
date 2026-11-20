"""Index of saved Packet Tracer runs (no raw filesystem paths exposed)."""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.integrations.packettracer.client import projects_dir

_LOCK = threading.Lock()
INDEX_NAME = "index.json"


def friendly_pkt_name(design_name: Optional[str], execution_id: str = "") -> str:
    """Human download name, e.g. network-design.pkt (unique short suffix if needed)."""
    raw = (design_name or "").strip() or "network-design"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-._")
    slug = re.sub(r"-{2,}", "-", slug)[:60].strip("-._") or "network-design"
    if slug.lower().endswith(".pkt"):
        slug = slug[:-4]
    # Keep downloads unique across runs of the same design
    suffix = ""
    safe = _safe_id(execution_id or "") or ""
    if safe:
        suffix = f"-{safe[:6]}"
    return f"{slug}{suffix}.pkt"


def _index_path() -> Path:
    return projects_dir() / INDEX_NAME


def _load() -> List[Dict[str, Any]]:
    path = _index_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(rows: List[Dict[str, Any]]) -> None:
    path = _index_path()
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _safe_id(execution_id: str) -> Optional[str]:
    safe = "".join(ch for ch in execution_id if ch.isalnum() or ch in ("-", "_"))
    if not safe or safe != execution_id:
        return None
    return safe


def record_run(
    *,
    execution_id: str,
    design_id: Optional[str],
    ok: bool,
    stage: str = "",
    message: str = "",
    filename: Optional[str] = None,
    download_filename: Optional[str] = None,
    design_name: Optional[str] = None,
) -> Dict[str, Any]:
    safe = _safe_id(execution_id)
    if not safe:
        raise ValueError("Invalid execution_id")
    display = download_filename or friendly_pkt_name(design_name, safe)
    row = {
        "execution_id": safe,
        "design_id": design_id,
        "design_name": (design_name or "")[:120] or None,
        "ok": bool(ok),
        "stage": stage or "",
        "message": (message or "")[:500],
        # On-disk name stays execution_id-based; download_filename is user-facing.
        "filename": filename or f"{safe}.pkt",
        "download_filename": display,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _LOCK:
        rows = _load()
        rows = [r for r in rows if r.get("execution_id") != safe]
        rows.insert(0, row)
        _save(rows)
    return row


def attach_design(execution_id: str, design_id: str) -> Optional[Dict[str, Any]]:
    safe = _safe_id(execution_id)
    if not safe or not design_id:
        return None
    with _LOCK:
        rows = _load()
        found = None
        for r in rows:
            if r.get("execution_id") == safe:
                r["design_id"] = design_id
                found = r
                break
        if found is None:
            # Allow attaching a known on-disk project that isn't indexed yet
            base = projects_dir() / safe
            pkt = base / f"{safe}.pkt"
            if not pkt.exists():
                candidates = list(base.glob("*.pkt")) if base.is_dir() else []
                if not candidates:
                    return None
                pkt = candidates[0]
            found = {
                "execution_id": safe,
                "design_id": design_id,
                "ok": True,
                "stage": "done",
                "message": "Attached after design save",
                "filename": pkt.name,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            rows.insert(0, found)
        _save(rows)
        return dict(found)


def list_runs(design_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with _LOCK:
        rows = _load()
    out = []
    for r in rows:
        if design_id is not None and r.get("design_id") != design_id:
            continue
        # Verify pkt still exists under controlled dir
        eid = r.get("execution_id") or ""
        safe = _safe_id(str(eid))
        if not safe:
            continue
        base = projects_dir() / safe
        pkt = base / str(r.get("filename") or f"{safe}.pkt")
        if not pkt.exists():
            candidates = list(base.glob("*.pkt")) if base.is_dir() else []
            if not candidates:
                continue
            pkt = candidates[0]
        display = r.get("download_filename") or friendly_pkt_name(
            r.get("design_name"), safe
        )
        out.append(
            {
                "execution_id": safe,
                "design_id": r.get("design_id"),
                "ok": bool(r.get("ok")),
                "stage": r.get("stage") or "",
                "message": r.get("message") or "",
                "filename": display,
                "created_at": r.get("created_at") or "",
                "has_download": True,
            }
        )
    return out


def download_name_for(execution_id: str) -> str:
    safe = _safe_id(execution_id)
    if not safe:
        return "network-design.pkt"
    with _LOCK:
        for r in _load():
            if r.get("execution_id") == safe:
                return r.get("download_filename") or friendly_pkt_name(
                    r.get("design_name"), safe
                )
    return friendly_pkt_name(None, safe)


def public_result(
    result: Dict[str, Any],
    *,
    design_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Strip absolute filesystem paths from execute results."""
    data = dict(result)
    data.pop("project_file", None)
    eid = data.get("execution_id") or data.get("project_download_id")
    if eid:
        data["project_download_id"] = eid
        data["project_filename"] = friendly_pkt_name(
            design_name or data.get("design_name"), str(eid)
        )
    return data
