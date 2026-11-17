"""Adversarial validation cases for management-IP / subnet overlap (W2). No LLM."""

from __future__ import annotations

import copy
from typing import Any, Dict, Tuple

import pytest

from app.agents.config_agent import config_node
from app.agents.validation_agent import validation_node
from app.generators.topology_layout import _fallback_topology_dict
from app.models.network import Topology


def _dept_plan(n_depts: int) -> dict:
    return {
        "departments": [
            {"name": f"D{i + 1}", "users": 20, "vlan_id": 10 * (i + 1)}
            for i in range(n_depts)
        ]
    }


def _configured(n_depts: int) -> Tuple[Any, Dict[str, Any], dict]:
    plan = _dept_plan(n_depts)
    topo = Topology(**_fallback_topology_dict(plan))
    out = config_node({"topology": topo, "design_plan": plan, "retry_count": 0})
    return out["topology"], out["configurations"], plan


def _configured_flat() -> Tuple[Any, Dict[str, Any], dict]:
    plan = {
        "mode": "flat_inventory",
        "router_count": 1,
        "switch_count": 1,
        "host_count": 2,
        "departments": [],
    }
    topo = Topology(**_fallback_topology_dict(plan))
    out = config_node({"topology": topo, "design_plan": plan, "retry_count": 0})
    return out["topology"], out["configurations"], plan


def _validate(topology, configurations, retry_count: int = 0):
    return validation_node(
        {
            "topology": topology,
            "configurations": configurations,
            "retry_count": retry_count,
        }
    )


def _first_switch_id(configurations: Dict[str, Any]) -> str:
    for nid, cfg in configurations.items():
        if isinstance(cfg, dict) and cfg.get("vlan_plan") is not None:
            return nid
    raise AssertionError("no switch with vlan_plan")


def _first_router_id(configurations: Dict[str, Any]) -> str:
    for nid, cfg in configurations.items():
        if isinstance(cfg, dict) and (
            cfg.get("subinterfaces") or cfg.get("interfaces")
        ):
            return nid
    raise AssertionError("no router config")


def _assert_failed(result, needle: str | None = None):
    assert result["validation_result"]["status"] == "failed"
    assert result["retry_count"] == 1
    errs = result.get("errors") or []
    assert errs
    if needle:
        blob = " | ".join(errs)
        assert needle in blob, blob


# --- Positive controls -------------------------------------------------------


@pytest.mark.parametrize("n", list(range(1, 16)))
def test_positive_control_departmental_1_to_15(n):
    topo, cfgs, _ = _configured(n)
    r = _validate(topo, cfgs)
    assert r["validation_result"]["status"] == "passed", r.get("errors")
    assert r.get("retry_count", 0) == 0


def test_positive_control_flat_inventory():
    topo, cfgs, _ = _configured_flat()
    r = _validate(topo, cfgs)
    assert r["validation_result"]["status"] == "passed", r.get("errors")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_positive_legitimate_management_subnet(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    sid = _first_switch_id(cfgs)
    cfgs[sid]["management_ip"] = "192.168.99.10"
    cfgs[sid]["management_mask"] = "255.255.255.0"
    r = _validate(topo, cfgs)
    assert r["validation_result"]["status"] == "passed", r.get("errors")


# --- Fault cases (parametrized on 2, 5, 10) -----------------------------------


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_1_duplicate_interface_ip(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    # Force classic-style interface list collision via two switch management fields
    # Prefer mutating two router subinterface IPs when multiple exist; else inject ifaces.
    rid = _first_router_id(cfgs)
    subs = cfgs[rid].get("subinterfaces") or []
    if len(subs) >= 2:
        subs[1]["ip"] = subs[0]["ip"]
    else:
        sid = _first_switch_id(cfgs)
        ip = (subs[0]["ip"] if subs else "192.168.10.1")
        cfgs[sid]["interfaces"] = [{"name": "Vlan99", "ip": ip, "mask": "255.255.255.0"}]
    r = _validate(topo, cfgs)
    _assert_failed(r, "IP conflict")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_2_interface_equals_subinterface(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    rid = _first_router_id(cfgs)
    subs = cfgs[rid].get("subinterfaces") or []
    assert subs
    cfgs[rid]["interfaces"] = [
        {"name": "GigabitEthernet0/1", "ip": subs[0]["ip"], "mask": subs[0]["mask"]}
    ]
    r = _validate(topo, cfgs)
    _assert_failed(r, str(subs[0]["ip"]))


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_3_mgmt_equals_interface_ip(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    rid = _first_router_id(cfgs)
    sid = _first_switch_id(cfgs)
    ip = cfgs[rid]["subinterfaces"][0]["ip"]
    cfgs[sid]["management_ip"] = ip
    cfgs[sid]["management_mask"] = "255.255.255.0"
    r = _validate(topo, cfgs)
    _assert_failed(r, "management")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_4_two_devices_same_mgmt_ip(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    switches = [
        nid
        for nid, cfg in cfgs.items()
        if isinstance(cfg, dict) and cfg.get("vlan_plan") is not None
    ]
    assert len(switches) >= 2
    for sid in switches[:2]:
        cfgs[sid]["management_ip"] = "192.168.99.10"
        cfgs[sid]["management_mask"] = "255.255.255.0"
    r = _validate(topo, cfgs)
    _assert_failed(r, "192.168.99.10")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_5_mgmt_equals_host_ip(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    hosts = (getattr(topo, "metadata", {}) or {}).get("host_addresses") or []
    assert hosts and hosts[0].get("ip")
    sid = _first_switch_id(cfgs)
    cfgs[sid]["management_ip"] = hosts[0]["ip"]
    cfgs[sid]["management_mask"] = "255.255.255.0"
    r = _validate(topo, cfgs)
    _assert_failed(r, "management")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_6a_mgmt_inside_user_vlan_no_mask(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    gw = (getattr(topo, "metadata", {}) or {}).get("vlan_gateways") or []
    assert gw
    # gateway is .1; pick .5 inside that subnet
    parts = gw[0]["gateway"].split(".")
    parts[-1] = "5"
    sid = _first_switch_id(cfgs)
    cfgs[sid]["management_ip"] = ".".join(parts)
    # no management_mask
    r = _validate(topo, cfgs)
    _assert_failed(r, "falls inside data-plane")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_6b_mgmt_mask_equals_user_vlan_subnet(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    gw = (getattr(topo, "metadata", {}) or {}).get("vlan_gateways") or []
    assert gw
    sid = _first_switch_id(cfgs)
    # Place mgmt host in user subnet with mask matching that VLAN → equal/overlap
    parts = gw[0]["gateway"].split(".")
    parts[-1] = "50"
    cfgs[sid]["management_ip"] = ".".join(parts)
    cfgs[sid]["management_mask"] = gw[0]["mask"]
    r = _validate(topo, cfgs)
    _assert_failed(r, "Subnet overlap")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_6c_mgmt_slash26_inside_user_slash24(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    # Force a /24 data-plane net, then mgmt /26 inside it
    rid = _first_router_id(cfgs)
    cfgs[rid]["subinterfaces"] = [
        {
            "parent": "GigabitEthernet0/0",
            "vlan_id": 10,
            "ip": "192.168.10.1",
            "mask": "255.255.255.0",
        }
    ]
    sid = _first_switch_id(cfgs)
    cfgs[sid]["management_ip"] = "192.168.10.10"
    cfgs[sid]["management_mask"] = "255.255.255.192"  # /26 inside /24
    r = _validate(topo, cfgs)
    errs = " | ".join(r.get("errors") or [])
    assert r["validation_result"]["status"] == "failed"
    assert (
        "falls inside data-plane" in errs
        or "Subnet overlap" in errs
        or "already used" in errs
    )


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_7_mgmt_equals_network_or_broadcast(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    gw = (getattr(topo, "metadata", {}) or {}).get("vlan_gateways") or []
    assert gw
    # network address of that gateway's subnet
    import ipaddress

    net = ipaddress.IPv4Network(f"{gw[0]['gateway']}/{gw[0]['mask']}", strict=False)
    sid = _first_switch_id(cfgs)
    cfgs[sid]["management_ip"] = str(net.network_address)
    cfgs[sid]["management_mask"] = "255.255.255.0"
    r = _validate(topo, cfgs)
    _assert_failed(r, "network/broadcast")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_8_overlapping_vlan_subnets(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    rid = _first_router_id(cfgs)
    subs = cfgs[rid].get("subinterfaces") or []
    assert len(subs) >= 1
    # Make a second subnet that overlaps the first via a wider mask on a neighboring third-octet
    # Simpler: two subifs both claiming 192.168.10.0 with different masks
    cfgs[rid]["subinterfaces"] = [
        {
            "parent": "GigabitEthernet0/0",
            "vlan_id": 10,
            "ip": "192.168.10.1",
            "mask": "255.255.255.0",
        },
        {
            "parent": "GigabitEthernet0/0",
            "vlan_id": 20,
            "ip": "192.168.10.129",
            "mask": "255.255.255.128",
        },
    ]
    r = _validate(topo, cfgs)
    _assert_failed(r, "Subnet overlap")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_9a_access_vlan_not_declared(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    # Prefer an access switch so trunks are not carrying the full catalog CSV.
    access_id = None
    for nid, cfg in cfgs.items():
        if not isinstance(cfg, dict) or not cfg.get("vlan_plan"):
            continue
        if any(p.get("mode") == "access" for p in (cfg["vlan_plan"].get("ports") or [])):
            access_id = nid
            break
    assert access_id
    vp = cfgs[access_id]["vlan_plan"]
    declared = {int(v["id"]) for v in (vp.get("vlans") or []) if v.get("id") is not None}
    bad = max(declared) + 7 if declared else 99
    for p in vp.get("ports") or []:
        if p.get("mode") == "access":
            p["vlan_id"] = bad
            break
        if p.get("mode") == "trunk":
            # keep trunk CSV inside declared set so access error is the signal
            p["allowed_vlans_csv"] = ",".join(str(x) for x in sorted(declared)) or "10"
    r = _validate(topo, cfgs)
    _assert_failed(r, "not declared")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_9b_trunk_undeclared_vlan(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    sid = _first_switch_id(cfgs)
    vp = cfgs[sid]["vlan_plan"]
    for p in vp.get("ports") or []:
        if p.get("mode") == "trunk":
            p["allowed_vlans_csv"] = "10,999"
            break
    r = _validate(topo, cfgs)
    _assert_failed(r, "999")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_9c_duplicate_vlan_ids(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    sid = _first_switch_id(cfgs)
    vp = cfgs[sid]["vlan_plan"]
    # Keep trunk CSV consistent with declared ids to isolate the duplicate-id error.
    vp["vlans"] = [{"id": 10, "name": "A"}, {"id": 10, "name": "B"}]
    for p in vp.get("ports") or []:
        if p.get("mode") == "trunk":
            p["allowed_vlans_csv"] = "10"
        if p.get("mode") == "access":
            p["vlan_id"] = 10
    r = _validate(topo, cfgs)
    _assert_failed(r, "duplicate VLAN")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_9d_vlan_id_out_of_range(n):
    topo, cfgs, _ = _configured(n)
    cfgs = copy.deepcopy(cfgs)
    sid = _first_switch_id(cfgs)
    vp = cfgs[sid]["vlan_plan"]
    vp["vlans"] = [{"id": 5000, "name": "Bad"}]
    for p in vp.get("ports") or []:
        if p.get("mode") == "trunk":
            p["allowed_vlans_csv"] = "5000"
        if p.get("mode") == "access":
            p["vlan_id"] = 5000
    r = _validate(topo, cfgs)
    _assert_failed(r, "5000")


@pytest.mark.parametrize("n", [2, 5, 10])
def test_fault_10_link_missing_node(n):
    topo, cfgs, _ = _configured(n)
    # mutate a link endpoint
    if topo.links:
        topo.links[0].source = "MISSING_NODE"
    r = _validate(topo, cfgs)
    _assert_failed(r, "MISSING_NODE")


def test_invalid_ip_string_reported():
    topo, cfgs, _ = _configured(2)
    cfgs = copy.deepcopy(cfgs)
    rid = _first_router_id(cfgs)
    cfgs[rid]["subinterfaces"][0]["ip"] = "not-an-ip"
    r = _validate(topo, cfgs)
    _assert_failed(r, "invalid IP")
