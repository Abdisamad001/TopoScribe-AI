"""
Standalone MCP deploy worker (run via uvx Python >=3.10).

Usage:
  uvx --from "mcp[cli]" --with mcp python -m app.integrations.packettracer.mcp_worker \\
      request.json result.json
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.integrations.packettracer.mapper import (
    build_name_map,
    classify_rejection,
    count_user_devices,
    get_cabling_rows,
    host_ip_gateway,
    layout_positions,
    map_cable_type,
    pt_model_for_node,
    pt_name_for_node,
    split_cli_commands,
)
from app.integrations.packettracer.pings import derive_ping_pairs


DEFAULT_URL = "http://127.0.0.1:39400/mcp"

ALLOWLIST = frozenset(
    {
        "pt_bridge_status",
        "pt_canvas_info",
        "pt_query_topology",
        "pt_list_devices",
        "pt_get_device_details",
        "pt_add_device",
        "pt_add_link",
        "pt_cli",
        "pt_host_ip_config",
        "pt_verify_connectivity",
        "pt_fast_forward",
        "pt_save_project",
    }
)


def _texts(result) -> List[str]:
    out = []
    for c in result.content or []:
        t = getattr(c, "text", None)
        out.append(t if t is not None else str(c))
    return out


async def _call(session: ClientSession, name: str, arguments: Dict[str, Any] | None = None):
    if name not in ALLOWLIST:
        raise RuntimeError(f"MCP tool not allowlisted: {name}")
    result = await session.call_tool(name, arguments or {})
    return result, _texts(result)


def _parse_cli_line_statuses(cli_report: str, commands: List[str], device_id: str, device_type: str):
    """Best-effort parse of pt_cli transcript into per-line results."""
    lines_out = []
    # Pattern examples: "Router#configure terminal    [ok]" or "> enable    [ok]"
    tagged = re.findall(
        r"^[^\n]*?#?\s*(.+?)\s{2,}\[(ok|ERROR|unknown command|timeout|waiting for an answer)\]",
        cli_report,
        flags=re.I | re.M,
    )
    status_by_cmd: Dict[str, str] = {}
    for cmd, st in tagged:
        status_by_cmd[cmd.strip()] = st.lower()

    for cmd in commands:
        st = status_by_cmd.get(cmd)
        if st is None:
            # fuzzy: endswith match
            for k, v in status_by_cmd.items():
                if k.endswith(cmd) or cmd.endswith(k):
                    st = v
                    break
        if st is None:
            if "ok" in cli_report.lower() and "error" not in cli_report.lower():
                st = "ok"
            else:
                st = "unknown"
        if st == "ok":
            lines_out.append(
                {
                    "device_id": device_id,
                    "line": cmd,
                    "status": "ok",
                    "impact": "",
                    "detail": "",
                }
            )
        else:
            impact = classify_rejection(cmd, device_type)
            lines_out.append(
                {
                    "device_id": device_id,
                    "line": cmd,
                    "status": "rejected" if st != "ok" else "ok",
                    "impact": impact if st != "ok" else "",
                    "detail": st or "",
                }
            )
    return lines_out


async def run_execute(req: Dict[str, Any]) -> Dict[str, Any]:
    url = (req.get("mcp_url") or DEFAULT_URL).rstrip("/")
    if not url.endswith("/mcp"):
        url = url + "/mcp"

    execution_id = req["execution_id"]
    topology = req["topology"]
    cisco_configs = req.get("cisco_configs") or {}
    nodes = [n for n in (topology.get("nodes") or []) if isinstance(n, dict) and n.get("id")]
    name_map = build_name_map(nodes)
    positions = layout_positions(nodes)
    project_dir = req["project_dir"]
    Path(project_dir).mkdir(parents=True, exist_ok=True)
    pkt_name = f"{execution_id}.pkt"

    result: Dict[str, Any] = {
        "execution_id": execution_id,
        "ok": False,
        "stage": "init",
        "message": "",
        "devices": [],
        "links": [],
        "cli_lines": [],
        "pings": [],
        "project_file": None,
        "project_download_id": execution_id,
        "name_map": name_map,
        "raw_notes": [],
    }

    async with streamable_http_client(url) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()

            result["stage"] = "bridge"
            _, status_texts = await _call(session, "pt_bridge_status")
            status_blob = "\n".join(status_texts)
            result["raw_notes"].append(status_blob)
            if "NOT connected" in status_blob or "not connected" in status_blob.lower():
                result["message"] = "Packet Tracer bridge not connected"
                return result

            result["stage"] = "canvas_check"
            _, topo_texts = await _call(session, "pt_query_topology")
            topo_blob = "\n".join(topo_texts)
            user_count = count_user_devices(topo_blob)
            result["raw_notes"].append(f"pre_topology={topo_blob!r} user_devices={user_count}")
            if user_count > 0:
                result["message"] = (
                    f"Canvas not empty ({user_count} user device(s)). "
                    "Open a blank Packet Tracer project and retry."
                )
                return result

            # --- devices ---
            result["stage"] = "add_devices"
            for n in nodes:
                nid = str(n["id"])
                pt_name = name_map[nid]
                model = pt_model_for_node(n)
                x, y = positions[nid]
                try:
                    _, texts = await _call(
                        session,
                        "pt_add_device",
                        {"name": pt_name, "model": model, "x": x, "y": y},
                    )
                    detail = "\n".join(texts)
                    ok = "created" in detail.lower() or "ok" in detail.lower()
                    result["devices"].append(
                        {
                            "node_id": nid,
                            "label": str(n.get("label") or ""),
                            "pt_name": pt_name,
                            "pt_model": model,
                            "ok": ok,
                            "detail": detail,
                        }
                    )
                    if not ok:
                        result["message"] = f"Failed to create device {pt_name}: {detail}"
                        return result
                except Exception as e:
                    result["devices"].append(
                        {
                            "node_id": nid,
                            "label": str(n.get("label") or ""),
                            "pt_name": pt_name,
                            "pt_model": model,
                            "ok": False,
                            "detail": str(e),
                        }
                    )
                    result["message"] = f"Failed to create device {pt_name}: {e}"
                    return result

            # --- links from cabling ---
            result["stage"] = "add_links"
            cabling = get_cabling_rows(topology)
            if not cabling:
                result["message"] = "topology.metadata.cabling is missing; configure topology first"
                return result
            for row in cabling:
                a_id = str(row.get("a_id") or "")
                b_id = str(row.get("b_id") or "")
                a_port = str(row.get("a_port") or "")
                b_port = str(row.get("b_port") or "")
                cable = map_cable_type(row.get("cable"))
                try:
                    _, texts = await _call(
                        session,
                        "pt_add_link",
                        {
                            "device1": name_map.get(a_id, a_id),
                            "port1": a_port,
                            "device2": name_map.get(b_id, b_id),
                            "port2": b_port,
                            "cable_type": cable,
                        },
                    )
                    detail = "\n".join(texts)
                    ok = "link created" in detail.lower()
                    result["links"].append(
                        {
                            "link_id": str(row.get("link_id") or ""),
                            "a_id": a_id,
                            "a_port": a_port,
                            "b_id": b_id,
                            "b_port": b_port,
                            "cable_type": cable,
                            "ok": ok,
                            "detail": detail,
                        }
                    )
                    if not ok:
                        result["message"] = f"Failed link {a_id}-{b_id}: {detail}"
                        return result
                except Exception as e:
                    result["links"].append(
                        {
                            "link_id": str(row.get("link_id") or ""),
                            "a_id": a_id,
                            "a_port": a_port,
                            "b_id": b_id,
                            "b_port": b_port,
                            "cable_type": cable,
                            "ok": False,
                            "detail": str(e),
                        }
                    )
                    result["message"] = f"Failed link {a_id}-{b_id}: {e}"
                    return result

            # --- CLI (routers/switches) preserve order; key by node.id ---
            result["stage"] = "apply_cli"
            node_type = {str(n["id"]): (n.get("type") or "") for n in nodes}
            for nid, cli in cisco_configs.items():
                pt_name = name_map.get(nid, nid)
                commands = split_cli_commands(cli)
                if not commands:
                    continue
                _, texts = await _call(
                    session, "pt_cli", {"device": pt_name, "commands": commands, "timeout": 120}
                )
                report = "\n".join(texts)
                result["raw_notes"].append(f"cli:{pt_name}:{report[:2000]}")
                result["cli_lines"].extend(
                    _parse_cli_line_statuses(report, commands, nid, node_type.get(nid, ""))
                )

            # --- host IPs ---
            result["stage"] = "host_ip"
            for n in nodes:
                t = (n.get("type") or "").lower()
                if not (t == "host" or "host" in t or t == "pc"):
                    continue
                info = host_ip_gateway(n, topology)
                if not info:
                    result["raw_notes"].append(f"host {n.get('id')}: no IP found")
                    continue
                pt_name = name_map[str(n["id"])]
                _, texts = await _call(
                    session,
                    "pt_host_ip_config",
                    {
                        "device": pt_name,
                        "mode": "static",
                        "ip": info["ip"],
                        "mask": info["mask"],
                        "gateway": info.get("gateway") or "",
                    },
                )
                result["raw_notes"].append(f"host_ip:{pt_name}:{texts}")

            # --- convergence ---
            result["stage"] = "convergence"
            _, ff_texts = await _call(session, "pt_fast_forward")
            result["raw_notes"].append("fast_forward=" + "\n".join(ff_texts))
            await asyncio.sleep(2)

            # --- pings ---
            result["stage"] = "pings"
            for src, dst_ip in derive_ping_pairs(topology):
                pt_src = name_map.get(src, src)
                messages = []
                final = "fail"
                attempts = 0
                for attempt in (1, 2):
                    attempts = attempt
                    _, texts = await _call(
                        session,
                        "pt_verify_connectivity",
                        {"from_device": pt_src, "to_ip": dst_ip, "count": 4, "timeout_s": 60},
                    )
                    msg = "\n".join(texts)
                    messages.append(msg)
                    if "CONNECTIVITY OK" in msg or "ok" in msg.lower() and "lost = 0" in msg.lower():
                        final = "pass"
                        break
                    # ARP / first-ping retry
                    await asyncio.sleep(1)
                result["pings"].append(
                    {
                        "source": src,
                        "destination": dst_ip,
                        "attempts": attempts,
                        "final_status": final,
                        "messages": messages,
                    }
                )

            # --- save ---
            result["stage"] = "save"
            _, save_texts = await _call(
                session,
                "pt_save_project",
                {
                    "filename": pkt_name,
                    "directory": str(project_dir),
                    "overwrite": True,
                },
            )
            save_msg = "\n".join(save_texts)
            result["raw_notes"].append(save_msg)
            pkt_path = str(Path(project_dir) / pkt_name)
            if Path(pkt_path).exists() or "saved" in save_msg.lower():
                result["project_file"] = pkt_path.replace("\\", "/")
            else:
                result["message"] = f"Save may have failed: {save_msg}"
                return result

            result["ok"] = True
            result["stage"] = "done"
            result["message"] = "Packet Tracer deploy completed"
            return result


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print("Usage: mcp_worker.py request.json result.json", file=sys.stderr)
        return 2
    req_path = Path(argv[1])
    out_path = Path(argv[2])
    req = json.loads(req_path.read_text(encoding="utf-8"))
    # Ensure backend imports resolve when launched via uvx
    started = time.time()
    try:
        result = asyncio.run(run_execute(req))
    except Exception as e:
        result = {
            "execution_id": req.get("execution_id", ""),
            "ok": False,
            "stage": "exception",
            "message": str(e),
            "devices": [],
            "links": [],
            "cli_lines": [],
            "pings": [],
            "project_file": None,
            "project_download_id": req.get("execution_id"),
            "name_map": {},
            "raw_notes": [f"exception:{e}"],
        }
    result["elapsed_s"] = round(time.time() - started, 3)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
