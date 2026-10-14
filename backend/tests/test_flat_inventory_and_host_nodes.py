"""Regression tests for flat_inventory mode and literal host-node counts"""

import pytest

from app.agents.planning_agent import (
    LITERAL_HOST_NODE_THRESHOLD,
    _apply_sme_defaults,
    _extract_device_inventory,
    _is_flat_inventory_request,
    _requested_literal_hosts_each,
    _requested_users_each,
)
from app.agents.topology_agent import (
    DEFAULT_COLUMN_SPACING_PX,
    HOST_CARD_WIDTH_PX,
    _annotate_representative_host_user_counts,
    _build_topology_prompt,
    _count_roles_in_nodes,
    _departmental_column_spacing,
    _fallback_topology_dict,
    _finalize_topology,
    _host_center_gap,
    _sparse_reason,
)


def _role_counts(topo):
    return _count_roles_in_nodes(topo.get("nodes") or [])


# --- Bug A: flat inventory detection & planning


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2 routers connected to a switch with 3 PCs", {"router_count": 2, "switch_count": 1, "host_count": 3}),
        ("a router connected to 2 switches with 5 computers", {"router_count": 1, "switch_count": 2, "host_count": 5}),
        ("three routers, one switch, and four hosts", {"router_count": 3, "switch_count": 1, "host_count": 4}),
        ("1 gateway and 2 switches with 6 laptops", {"router_count": 1, "switch_count": 2, "host_count": 6}),
    ],
)
def test_extract_device_inventory_varied_phrasings(text, expected):
    assert _extract_device_inventory(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "2 routers connected to a switch with 3 PCs",
        "a router connected to 2 switches with 5 computers",
        "build me three switches and eight workstations",
    ],
)
def test_flat_inventory_request_detected(text):
    assert _is_flat_inventory_request(text, []) is True


@pytest.mark.parametrize(
    "text",
    [
        "HR, IT, Finance, 10 users each",
        "departments IT and OP",
        "Design a 4-department SME with 50 users each",
        "Design a campus network, please recommend everything",
        "2 routers for the HR department",
        "just a campus network",
        "2 routers and a switch",  # no hosts → incomplete flat inventory
    ],
)
def test_non_flat_requests_not_detected_as_flat(text):
    assert _is_flat_inventory_request(text, []) is False


def test_flat_plan_skips_departments_and_captures_counts():
    plan = _apply_sme_defaults({}, "2 routers connected to a switch with 3 PCs", [])
    assert plan["mode"] == "flat_inventory"
    assert plan["router_count"] == 2
    assert plan["switch_count"] == 1
    assert plan["host_count"] == 3
    assert plan["departments"] == []
    assert plan["vlans"] == []


def test_flat_plan_alternate_phrasing():
    plan = _apply_sme_defaults(
        {}, "a router connected to 2 switches with 5 computers", []
    )
    assert plan["mode"] == "flat_inventory"
    assert plan["router_count"] == 1
    assert plan["switch_count"] == 2
    assert plan["host_count"] == 5


def test_departmental_users_each_unchanged():
    plan = _apply_sme_defaults({}, "HR, IT, Finance, 10 users each", [])
    assert plan["mode"] == "departmental"
    assert [d["name"] for d in plan["departments"]] == ["HR", "IT", "Finance"]
    assert all(d["users"] == 10 for d in plan["departments"])
    assert all("host_nodes" not in d for d in plan["departments"])
    assert _requested_users_each("HR, IT, Finance, 10 users each") == 10
    assert _requested_literal_hosts_each("HR, IT, Finance, 10 users each") == 0


def test_literal_pcs_each_sets_host_nodes_when_small():
    plan = _apply_sme_defaults({}, "departments HR and IT with 3 PCs each", [])
    assert plan["mode"] == "departmental"
    assert [d["name"] for d in plan["departments"]] == ["HR", "IT"]
    assert all(d.get("host_nodes") == 3 for d in plan["departments"])


def test_large_literal_pc_count_does_not_set_host_nodes():
    n = LITERAL_HOST_NODE_THRESHOLD + 1
    plan = _apply_sme_defaults({}, f"departments HR and IT with {n} PCs each", [])
    assert all("host_nodes" not in d for d in plan["departments"])


def test_five_pcs_phrasing_annotates_host_nodes():
    plan = _apply_sme_defaults({}, "finance and JS with five Pcs", [])
    assert [d["name"] for d in plan["departments"]] == ["Finance", "JS"]
    assert all(d.get("host_nodes") == 5 for d in plan["departments"])


# --- Bug B: topology respects mode / host_nodes 


def test_flat_fallback_matches_stated_inventory():
    plan = _apply_sme_defaults({}, "2 routers connected to a switch with 3 PCs", [])
    topo = _fallback_topology_dict(plan)
    assert _role_counts(topo) == (2, 1, 3)
    assert _sparse_reason(topo, plan) is None


def test_flat_sparse_rejects_short_inventory():
    plan = {
        "mode": "flat_inventory",
        "router_count": 2,
        "switch_count": 1,
        "host_count": 3,
        "departments": [],
    }
    short = {
        "nodes": [
            {"id": "R1", "type": "router"},
            {"id": "SW1", "type": "switch"},
            {"id": "H1", "type": "host"},
        ]
    }
    reason = _sparse_reason(short, plan)
    assert reason is not None
    assert "hosts" in reason.lower() or "Flat inventory" in reason


def test_users_each_fallback_still_one_host_per_department():
    plan = _apply_sme_defaults({}, "HR, IT, Finance, 10 users each", [])
    topo = _fallback_topology_dict(plan)
    assert _role_counts(topo) == (1, 4, 3)  # 1 router + 1 core + 3 access + 3 hosts
    assert _sparse_reason(topo, plan) is None


def test_literal_host_nodes_fallback_draws_multiple_hosts():
    plan = _apply_sme_defaults({}, "departments HR and IT with 3 PCs each", [])
    topo = _fallback_topology_dict(plan)
    assert _role_counts(topo) == (1, 3, 6)  # 1R + core + 2 access + 3+3 hosts
    assert _sparse_reason(topo, plan) is None


def test_departmental_sparse_still_uses_sme_formula_for_users_plans():
    plan = {
        "mode": "departmental",
        "departments": [
            {"name": "HR", "users": 10, "vlan_id": 10},
            {"name": "IT", "users": 10, "vlan_id": 20},
            {"name": "Finance", "users": 10, "vlan_id": 30},
        ],
    }
    # Classic under-built campus shape 
    sparse = {
        "nodes": [
            {"id": "R1", "type": "router"},
            {"id": "SW1", "type": "switch", "label": "Core Switch"},
            {"id": "H1", "type": "host", "config": {"vlan_name": "HR"}},
        ]
    }
    assert _sparse_reason(sparse, plan) is not None


def test_flat_prompt_does_not_require_sme_template():
    plan = _apply_sme_defaults({}, "2 routers connected to a switch with 3 PCs", [])
    prompt = _build_topology_prompt(plan, None)
    assert "FLAT INVENTORY" in prompt
    assert "exactly 2 router" in prompt.lower() or "exactly 2 router" in prompt
    assert "2N + 2" not in prompt
    assert "Core Switch" not in prompt or "Do NOT invent" in prompt


def test_departmental_prompt_mentions_host_nodes_when_present():
    plan = _apply_sme_defaults({}, "departments Sales with 2 PCs each", [])
    prompt = _build_topology_prompt(plan, None)
    assert "DEPARTMENTAL" in prompt
    assert "host_nodes" in prompt or "exactly 2 host" in prompt.lower()


# host labels for collapsed "N users" departments


def _host_labels(topo_dict):
    labels = []
    for n in topo_dict.get("nodes") or []:
        t = str(n.get("type") or "").lower()
        if "host" in t or "pc" in t:
            labels.append(n.get("label"))
    return labels


def test_representative_host_gets_user_count_label_when_above_threshold():
    plan = _apply_sme_defaults({}, "HR, IT, Finance, 10 users each", [])
    assert all(d["users"] == 10 for d in plan["departments"])
    assert all(d["users"] > LITERAL_HOST_NODE_THRESHOLD for d in plan["departments"])

    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)
    host_labels = [n.label for n in finalized.nodes if "host" in (n.type or "").lower()]
    assert sorted(host_labels) == [
        "Finance Host (10 PCs)",
        "HR Host (10 PCs)",
        "IT Host (10 PCs)",
    ]


def test_users_at_or_below_threshold_do_not_get_count_label():
 
    plan = {
        "mode": "departmental",
        "departments": [
            {"name": "OP", "users": LITERAL_HOST_NODE_THRESHOLD, "vlan_id": 10},
        ],
    }
    topo = {
        "nodes": [
            {
                "id": "H1",
                "type": "host",
                "label": "OP Host",
                "interfaces": [],
                "config": {"vlan_id": 10, "vlan_name": "OP"},
            }
        ],
        "links": [],
        "protocols": [],
        "metadata": {"vlans": [{"id": 10, "name": "OP"}]},
    }
    _annotate_representative_host_user_counts(topo, plan)
    assert _host_labels(topo) == ["OP Host"]


def test_literal_host_nodes_do_not_get_count_label():
    plan = _apply_sme_defaults({}, "departments HR and IT with 3 PCs each", [])
    assert all(d.get("host_nodes") == 3 for d in plan["departments"])
    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)
    host_labels = [n.label for n in finalized.nodes if "host" in (n.type or "").lower()]
    assert len(host_labels) == 6
    assert all("PCs)" not in lbl for lbl in host_labels)


def test_flat_inventory_hosts_unaffected_by_user_count_labels():
    plan = _apply_sme_defaults({}, "2 routers connected to a switch with 3 PCs", [])
    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)
    after = [n.label for n in finalized.nodes if "host" in (n.type or "").lower()]
    assert len(after) == 3
    assert all("PCs)" not in (lbl or "") for lbl in after)


def test_unmatched_host_label_left_unchanged():
    plan = {
        "mode": "departmental",
        "departments": [{"name": "HR", "users": 50, "vlan_id": 10}],
    }
    topo = {
        "nodes": [
            {
                "id": "H_orphan",
                "type": "host",
                "label": "Mystery Host",
                "interfaces": [],
                "config": {},  # no vlan association
            }
        ],
        "links": [],
        "protocols": [],
        "metadata": {"vlans": []},
    }
    _annotate_representative_host_user_counts(topo, plan)
    assert _host_labels(topo) == ["Mystery Host"]


# --- Four-tier departmental layout vs single-row flat switches 


def _y_by_role_labels(finalized):
    rows = {"router": [], "core": [], "access": [], "host": []}
    for n in finalized.nodes:
        t = (n.type or "").lower()
        lbl = (n.label or "").lower()
        if "router" in t:
            rows["router"].append(n.y)
        elif "host" in t or "pc" in t:
            rows["host"].append(n.y)
        elif "switch" in t:
            if "core" in lbl:
                rows["core"].append(n.y)
            else:
                rows["access"].append(n.y)
    return rows


def test_departmental_layout_is_four_tiers():
    
    plan = _apply_sme_defaults({}, "departments HR and IT, 20 users each", [])
    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)
    rows = _y_by_role_labels(finalized)

    assert len(rows["router"]) == 1
    assert len(rows["core"]) == 1
    assert len(rows["access"]) == 2
    assert len(rows["host"]) == 2

    assert set(rows["router"]) == {0}
    assert set(rows["core"]) == {200}
    assert set(rows["access"]) == {400}
    assert set(rows["host"]) == {500}

    # Access switches sit on the same row 
    assert rows["access"][0] == rows["access"][1]
    assert rows["core"][0] < rows["access"][0] < rows["host"][0]


def test_flat_inventory_keeps_all_switches_on_one_row():
    plan = _apply_sme_defaults({}, "a router connected to 2 switches with 5 computers", [])
    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)
    switch_ys = [n.y for n in finalized.nodes if "switch" in (n.type or "").lower()]
    host_ys = [n.y for n in finalized.nodes if "host" in (n.type or "").lower()]
    router_ys = [n.y for n in finalized.nodes if "router" in (n.type or "").lower()]

    assert set(router_ys) == {0}
    assert set(switch_ys) == {200}
    assert len(switch_ys) == 2
    assert set(host_ys) == {500}


def test_departmental_hosts_cluster_under_their_access_switch():
    plan = _apply_sme_defaults({}, "departments HR and IT with 3 PCs each", [])
    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)

    access = [
        n for n in finalized.nodes
        if "switch" in (n.type or "").lower() and "core" not in (n.label or "").lower()
    ]
    hosts = [n for n in finalized.nodes if "host" in (n.type or "").lower()]
    assert len(access) == 2
    assert len(hosts) == 6

    by_id = {n.id: n for n in finalized.nodes}
    for host in hosts:
        parent = None
        for link in finalized.links:
            if link.source == host.id and link.target in {s.id for s in access}:
                parent = by_id[link.target]
                break
            if link.target == host.id and link.source in {s.id for s in access}:
                parent = by_id[link.source]
                break
        assert parent is not None
        assert host.y == 500
        assert abs(host.x - parent.x) <= _host_center_gap()


def test_flat_inventory_hosts_stay_on_one_spread_row():
    plan = _apply_sme_defaults({}, "2 routers connected to a switch with 3 PCs", [])
    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)
    host_xs = sorted(n.x for n in finalized.nodes if "host" in (n.type or "").lower())
    # Three hosts on one row, spaced by the global 300px row layout — not clustered.
    assert len(host_xs) == 3
    assert host_xs[1] - host_xs[0] == 300
    assert host_xs[2] - host_xs[1] == 300


def _hosts_by_parent(finalized):
    access_ids = {
        n.id
        for n in finalized.nodes
        if "switch" in (n.type or "").lower() and "core" not in (n.label or "").lower()
    }
    grouped = {sid: [] for sid in access_ids}
    for host in finalized.nodes:
        if "host" not in (host.type or "").lower():
            continue
        for link in finalized.links:
            if link.source == host.id and link.target in access_ids:
                grouped[link.target].append(host)
                break
            if link.target == host.id and link.source in access_ids:
                grouped[link.source].append(host)
                break
    return grouped


def _assert_no_card_overlap(nodes, card_width=HOST_CARD_WIDTH_PX):
    xs = sorted(n.x for n in nodes)
    for a, b in zip(xs, xs[1:]):
        assert b - a >= card_width, f"cards overlap: {a} then {b} (need gap >= {card_width})"


def test_five_hosts_each_do_not_overlap_within_or_across_departments():
    plan = _apply_sme_defaults({}, "departments HR and IT with 5 PCs each", [])
    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)
    grouped = _hosts_by_parent(finalized)
    assert [len(v) for v in grouped.values()] == [5, 5]
    for cluster in grouped.values():
        _assert_no_card_overlap(cluster)
        xs = sorted(n.x for n in cluster)
        assert xs[1] - xs[0] == _host_center_gap()
    all_hosts = [n for n in finalized.nodes if "host" in (n.type or "").lower()]
    _assert_no_card_overlap(all_hosts)


def test_eight_host_threshold_clusters_do_not_overlap():
    n = LITERAL_HOST_NODE_THRESHOLD
    plan = _apply_sme_defaults({}, f"departments HR and IT with {n} PCs each", [])
    topo = _fallback_topology_dict(plan)
    finalized = _finalize_topology(topo, plan)
    grouped = _hosts_by_parent(finalized)
    assert sorted(len(v) for v in grouped.values()) == [n, n]
    for cluster in grouped.values():
        _assert_no_card_overlap(cluster)
    all_hosts = [n for n in finalized.nodes if "host" in (n.type or "").lower()]
    _assert_no_card_overlap(all_hosts)
    access = [
        s for s in finalized.nodes
        if "switch" in (s.type or "").lower() and "core" not in (s.label or "").lower()
    ]
    access_xs = sorted(s.x for s in access)
    assert access_xs[1] - access_xs[0] == _departmental_column_spacing(n)
    assert access_xs[1] - access_xs[0] > DEFAULT_COLUMN_SPACING_PX


def _dept_plan_one_host():
    return {
        "mode": "departmental",
        "departments": [{"name": "HR", "users": 20, "vlan_id": 10}],
    }


def _dept_topo_with_host_link(source: str, target: str) -> dict:
    return {
        "nodes": [
            {"id": "R1", "type": "router", "label": "Router", "interfaces": [], "config": {}},
            {"id": "SW_CORE", "type": "switch", "label": "Core Switch", "interfaces": [], "config": {}},
            {
                "id": "SW_HR",
                "type": "switch",
                "label": "Access HR",
                "interfaces": [],
                "config": {"vlan_id": 10, "vlan_name": "HR"},
            },
            {
                "id": "H1",
                "type": "host",
                "label": "HR Host",
                "interfaces": [],
                "config": {"vlan_id": 10, "vlan_name": "HR"},
            },
        ],
        "links": [
            {"id": "link-r-core", "source": "R1", "target": "SW_CORE", "bandwidth": 1000},
            {"id": "link-core-acc", "source": "SW_CORE", "target": "SW_HR", "bandwidth": 1000},
            {"id": "link-host", "source": source, "target": target, "bandwidth": 1000},
        ],
        "protocols": [],
        "metadata": {"vlans": [{"id": 10, "name": "HR"}]},
    }


def test_finalize_swaps_reversed_host_to_switch_link():
    topo = _dept_topo_with_host_link("H1", "SW_HR")
    finalized = _finalize_topology(topo, _dept_plan_one_host())
    host_link = next(l for l in finalized.links if l.id == "link-host")
    assert host_link.source == "SW_HR"
    assert host_link.target == "H1"


def test_finalize_leaves_correct_switch_to_host_link_unchanged():
    topo = _dept_topo_with_host_link("SW_HR", "H1")
    finalized = _finalize_topology(topo, _dept_plan_one_host())
    host_link = next(l for l in finalized.links if l.id == "link-host")
    assert host_link.source == "SW_HR"
    assert host_link.target == "H1"
    core = next(l for l in finalized.links if l.id == "link-r-core")
    assert core.source == "R1" and core.target == "SW_CORE"


def test_finalize_swaps_reversed_host_to_router_link():
    """Flat inventory may link a host directly to a router when there is no switch."""
    topo = {
        "nodes": [
            {"id": "R1", "type": "router", "label": "Router", "interfaces": [], "config": {}},
            {"id": "H1", "type": "host", "label": "Host", "interfaces": [], "config": {}},
        ],
        "links": [
            {"id": "link-rh", "source": "H1", "target": "R1", "bandwidth": 1000},
        ],
        "protocols": [],
        "metadata": {"vlans": []},
    }
    plan = {"mode": "flat_inventory", "router_count": 1, "switch_count": 0, "host_count": 1}
    finalized = _finalize_topology(topo, plan)
    link = finalized.links[0]
    assert link.source == "R1"
    assert link.target == "H1"
