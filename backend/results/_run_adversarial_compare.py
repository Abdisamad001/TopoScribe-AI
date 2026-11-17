"""Before/after adversarial comparison (no git). Saves results/adversarial_results.csv"""
from __future__ import annotations

import copy
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.config_agent import config_node
from app.agents.validation_agent import validation_node as validation_node_after
from app.generators.cisco import generate_cisco_config
from app.generators.topology_layout import _fallback_topology_dict
from app.models.network import Topology


def validation_node_before(state: Dict[str, Any]) -> Dict[str, Any]:
    """Pre-W2 validator: string IP uniqueness + mgmt exact match only."""
    topology = state.get("topology")
    configurations = state.get("configurations")
    if topology is None or configurations is None:
        missing = []
        if topology is None:
            missing.append("topology")
        if configurations is None:
            missing.append("configurations")
        msg = f"Validation skipped: missing {', '.join(missing)}."
        return {
            "errors": [msg],
            "validation_result": {"status": "failed_fatal", "errors": [msg]},
            "retry_count": int(state.get("retry_count", 0)),
        }

    errors: List[str] = []
    meta = getattr(topology, "metadata", None)
    port_errors = []
    if isinstance(meta, dict):
        port_errors = [str(m) for m in (meta.get("port_errors") or []) if m]
    if port_errors:
        return {
            "errors": port_errors,
            "validation_result": {"status": "failed_fatal", "errors": port_errors},
            "retry_count": int(state.get("retry_count", 0)),
        }

    node_ids = {node.id for node in topology.nodes}
    for link in topology.links:
        if link.source not in node_ids:
            errors.append(f"Link {link.id}: source {link.source} not found")
        if link.target not in node_ids:
            errors.append(f"Link {link.id}: target {link.target} not found")

    used_ips = set()
    for node_id, config in configurations.items():
        for iface in config.get("interfaces", []):
            ip = iface.get("ip")
            if ip:
                if ip in used_ips:
                    errors.append(f"IP conflict: {ip} used multiple times")
                used_ips.add(ip)
        for s in config.get("subinterfaces") or []:
            ip = s.get("ip")
            if ip:
                if ip in used_ips:
                    errors.append(f"IP conflict: {ip} used multiple times (subinterface)")
                used_ips.add(ip)

    for node_id, config in configurations.items():
        mgmt_ip = config.get("management_ip")
        if mgmt_ip:
            if mgmt_ip in used_ips:
                errors.append(
                    f"IP conflict: management IP {mgmt_ip} on {node_id} "
                    f"already used by another interface"
                )
            used_ips.add(mgmt_ip)

    for node_id, config in configurations.items():
        vp = config.get("vlan_plan")
        if not vp:
            continue
        vlans = vp.get("vlans") or []
        vlan_ids = []
        for v in vlans:
            vid = v.get("id")
            if vid is None:
                errors.append(f"VLAN plan {node_id}: missing vlan id in vlans list")
                continue
            if not isinstance(vid, int) or vid < 2 or vid > 4094:
                errors.append(f"VLAN plan {node_id}: invalid vlan id {vid} (must be 2-4094)")
            vlan_ids.append(vid)
        if len(vlan_ids) != len(set(vlan_ids)):
            errors.append(f"VLAN plan {node_id}: duplicate VLAN ids in vlans list")
        defined = set(vlan_ids)
        for p in vp.get("ports") or []:
            mode = p.get("mode")
            if mode == "access":
                av = p.get("vlan_id")
                if av is None:
                    errors.append(f"VLAN plan {node_id}: access port missing vlan_id")
                    continue
                if av not in defined:
                    errors.append(
                        f"VLAN plan {node_id}: access vlan {av} not declared in vlans list"
                    )
            elif mode == "trunk":
                csv = (p.get("allowed_vlans_csv") or "").strip()
                if not csv:
                    errors.append(f"VLAN plan {node_id}: trunk port missing allowed VLANs")
                    continue
                for part in csv.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        tv = int(part)
                    except ValueError:
                        errors.append(
                            f"VLAN plan {node_id}: invalid trunk vlan token {part!r}"
                        )
                        continue
                    if tv != 1 and tv not in defined:
                        errors.append(
                            f"VLAN plan {node_id}: trunk references vlan {tv} not in local VLAN database"
                        )
            else:
                errors.append(f"VLAN plan {node_id}: unknown port mode {mode!r}")

    if errors:
        return {
            "errors": errors,
            "validation_result": {"status": "failed", "errors": errors},
            "retry_count": int(state.get("retry_count", 0)) + 1,
        }
    return {
        "validation_result": {"status": "passed"},
        "retry_count": int(state.get("retry_count", 0)),
        "errors": [],
    }


def _dept_plan(n: int) -> dict:
    return {
        "departments": [
            {"name": f"D{i + 1}", "users": 20, "vlan_id": 10 * (i + 1)}
            for i in range(n)
        ]
    }


def _configured(n: int):
    plan = _dept_plan(n)
    topo = Topology(**_fallback_topology_dict(plan))
    out = config_node({"topology": topo, "design_plan": plan, "retry_count": 0})
    return out["topology"], copy.deepcopy(out["configurations"])


def _switch(cfgs):
    for nid, cfg in cfgs.items():
        if isinstance(cfg, dict) and cfg.get("vlan_plan") is not None:
            return nid
    raise RuntimeError("no switch")


def _router(cfgs):
    for nid, cfg in cfgs.items():
        if isinstance(cfg, dict) and (cfg.get("subinterfaces") or cfg.get("interfaces")):
            return nid
    raise RuntimeError("no router")


def _failed(r) -> bool:
    return (r.get("validation_result") or {}).get("status") == "failed"


def _msg(r) -> str:
    errs = r.get("errors") or (r.get("validation_result") or {}).get("errors") or []
    return (errs[0] if errs else "")[:180]


FaultFn = Any


def make_faults(n: int) -> List[Tuple[str, Any, Any]]:
    """Return list of (name, topo, cfgs) already fault-injected."""
    rows = []

    topo, cfgs = _configured(n)
    rid = _router(cfgs)
    subs = cfgs[rid].get("subinterfaces") or []
    if len(subs) >= 2:
        subs[1]["ip"] = subs[0]["ip"]
    else:
        sid = _switch(cfgs)
        cfgs[sid]["interfaces"] = [{"name": "Vlan99", "ip": subs[0]["ip"], "mask": "255.255.255.0"}]
    rows.append(("1_dup_iface_or_subif", topo, cfgs))

    topo, cfgs = _configured(n)
    rid = _router(cfgs)
    subs = cfgs[rid]["subinterfaces"]
    cfgs[rid]["interfaces"] = [
        {"name": "GigabitEthernet0/1", "ip": subs[0]["ip"], "mask": subs[0]["mask"]}
    ]
    rows.append(("2_iface_eq_subif", topo, cfgs))

    topo, cfgs = _configured(n)
    rid, sid = _router(cfgs), _switch(cfgs)
    cfgs[sid]["management_ip"] = cfgs[rid]["subinterfaces"][0]["ip"]
    cfgs[sid]["management_mask"] = "255.255.255.0"
    rows.append(("3_mgmt_eq_iface", topo, cfgs))

    topo, cfgs = _configured(n)
    switches = [nid for nid, c in cfgs.items() if isinstance(c, dict) and c.get("vlan_plan")]
    for sid in switches[:2]:
        cfgs[sid]["management_ip"] = "192.168.99.10"
        cfgs[sid]["management_mask"] = "255.255.255.0"
    rows.append(("4_dup_mgmt", topo, cfgs))

    topo, cfgs = _configured(n)
    host_ip = ((getattr(topo, "metadata", {}) or {}).get("host_addresses") or [{}])[0].get("ip")
    sid = _switch(cfgs)
    cfgs[sid]["management_ip"] = host_ip
    cfgs[sid]["management_mask"] = "255.255.255.0"
    rows.append(("5_mgmt_eq_host", topo, cfgs))

    topo, cfgs = _configured(n)
    gw = ((getattr(topo, "metadata", {}) or {}).get("vlan_gateways") or [])[0]
    parts = gw["gateway"].split(".")
    parts[-1] = "5"
    sid = _switch(cfgs)
    cfgs[sid]["management_ip"] = ".".join(parts)
    rows.append(("6a_mgmt_in_user_no_mask", topo, cfgs))

    topo, cfgs = _configured(n)
    gw = ((getattr(topo, "metadata", {}) or {}).get("vlan_gateways") or [])[0]
    parts = gw["gateway"].split(".")
    parts[-1] = "50"
    sid = _switch(cfgs)
    cfgs[sid]["management_ip"] = ".".join(parts)
    cfgs[sid]["management_mask"] = gw["mask"]
    rows.append(("6b_mgmt_mask_eq_user", topo, cfgs))

    topo, cfgs = _configured(n)
    rid, sid = _router(cfgs), _switch(cfgs)
    cfgs[rid]["subinterfaces"] = [
        {"parent": "GigabitEthernet0/0", "vlan_id": 10, "ip": "192.168.10.1", "mask": "255.255.255.0"}
    ]
    cfgs[sid]["management_ip"] = "192.168.10.10"
    cfgs[sid]["management_mask"] = "255.255.255.192"
    rows.append(("6c_mgmt_26_in_24", topo, cfgs))

    import ipaddress
    topo, cfgs = _configured(n)
    gw = ((getattr(topo, "metadata", {}) or {}).get("vlan_gateways") or [])[0]
    net = ipaddress.IPv4Network(f"{gw['gateway']}/{gw['mask']}", strict=False)
    sid = _switch(cfgs)
    cfgs[sid]["management_ip"] = str(net.network_address)
    cfgs[sid]["management_mask"] = "255.255.255.0"
    rows.append(("7_mgmt_network_addr", topo, cfgs))

    topo, cfgs = _configured(n)
    rid = _router(cfgs)
    cfgs[rid]["subinterfaces"] = [
        {"parent": "GigabitEthernet0/0", "vlan_id": 10, "ip": "192.168.10.1", "mask": "255.255.255.0"},
        {"parent": "GigabitEthernet0/0", "vlan_id": 20, "ip": "192.168.10.129", "mask": "255.255.255.128"},
    ]
    rows.append(("8_overlap_subnets", topo, cfgs))

    topo, cfgs = _configured(n)
    access_id = None
    for nid, cfg in cfgs.items():
        if isinstance(cfg, dict) and cfg.get("vlan_plan"):
            if any(p.get("mode") == "access" for p in (cfg["vlan_plan"].get("ports") or [])):
                access_id = nid
                break
    vp = cfgs[access_id]["vlan_plan"]
    declared = {int(v["id"]) for v in (vp.get("vlans") or []) if v.get("id") is not None}
    bad = max(declared) + 7 if declared else 99
    for p in vp.get("ports") or []:
        if p.get("mode") == "access":
            p["vlan_id"] = bad
        if p.get("mode") == "trunk":
            p["allowed_vlans_csv"] = ",".join(str(x) for x in sorted(declared)) or "10"
    rows.append(("9a_access_undeclared", topo, cfgs))

    topo, cfgs = _configured(n)
    sid = _switch(cfgs)
    for p in cfgs[sid]["vlan_plan"].get("ports") or []:
        if p.get("mode") == "trunk":
            p["allowed_vlans_csv"] = "10,999"
            break
    rows.append(("9b_trunk_undeclared", topo, cfgs))

    topo, cfgs = _configured(n)
    sid = _switch(cfgs)
    vp = cfgs[sid]["vlan_plan"]
    vp["vlans"] = [{"id": 10, "name": "A"}, {"id": 10, "name": "B"}]
    for p in vp.get("ports") or []:
        if p.get("mode") == "trunk":
            p["allowed_vlans_csv"] = "10"
        if p.get("mode") == "access":
            p["vlan_id"] = 10
    rows.append(("9c_dup_vlan_id", topo, cfgs))

    topo, cfgs = _configured(n)
    sid = _switch(cfgs)
    vp = cfgs[sid]["vlan_plan"]
    vp["vlans"] = [{"id": 5000, "name": "Bad"}]
    for p in vp.get("ports") or []:
        if p.get("mode") == "trunk":
            p["allowed_vlans_csv"] = "5000"
        if p.get("mode") == "access":
            p["vlan_id"] = 5000
    rows.append(("9d_vlan_oor", topo, cfgs))

    topo, cfgs = _configured(n)
    if topo.links:
        topo.links[0].source = "MISSING_NODE"
    rows.append(("10_missing_link_node", topo, cfgs))

    topo, cfgs = _configured(n)
    rows.append(("positive_clean", topo, cfgs))

    topo, cfgs = _configured(n)
    sid = _switch(cfgs)
    cfgs[sid]["management_ip"] = "192.168.99.10"
    cfgs[sid]["management_mask"] = "255.255.255.0"
    rows.append(("positive_mgmt_99", topo, cfgs))

    return rows


def main():
    out_path = ROOT / "results" / "adversarial_results.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dept_size",
        "fault_case",
        "detected_before",
        "detected_after",
        "error_message_after",
    ]
    rows_out = []
    md_lines = [
        "| Dept | Fault case | Detected before | Detected after | Error message (after) |",
        "| ---: | --- | --- | --- | --- |",
    ]
    totals = {}
    for n in (2, 5, 10):
        totals[n] = {"before": 0, "after": 0, "cases": 0}
        for name, topo, cfgs in make_faults(n):
            state = {"topology": topo, "configurations": cfgs, "retry_count": 0}
            b = validation_node_before(state)
            a = validation_node_after(state)
            expect_fail = not name.startswith("positive_")
            db = _failed(b)
            da = _failed(a)
            # For positives, "detected" means incorrectly failed; report as detected=False when passed
            if expect_fail:
                totals[n]["cases"] += 1
                if db:
                    totals[n]["before"] += 1
                if da:
                    totals[n]["after"] += 1
            rows_out.append(
                {
                    "dept_size": n,
                    "fault_case": name,
                    "detected_before": db if expect_fail else (not (b.get("validation_result") or {}).get("status") == "passed"),
                    "detected_after": da if expect_fail else (not (a.get("validation_result") or {}).get("status") == "passed"),
                    "error_message_after": _msg(a) if expect_fail else (
                        "PASS" if (a.get("validation_result") or {}).get("status") == "passed" else _msg(a)
                    ),
                }
            )
            r = rows_out[-1]
            md_lines.append(
                f"| {n} | {name} | {r['detected_before']} | {r['detected_after']} | {r['error_message_after'].replace('|', '/')} |"
            )

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    print("\n".join(md_lines))
    print()
    for n in (2, 5, 10):
        t = totals[n]
        print(
            f"TOTALS dept={n}: faults={t['cases']} "
            f"detected_before={t['before']} detected_after={t['after']}"
        )
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
