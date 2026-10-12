from app.graph.state import NetworkDesignState
from app.generators.config_builder import (
    vlan_catalog_from_state,
    _allocate_vlan_networks,
    _assign_host_ips_from_networks,
    _assign_host_vlan_membership,
    _assign_design_ports,
    _build_router_configuration,
    _build_switch_configuration,
    _collect_host_nodes,
    _is_switch,
    _sync_topology_vlan_catalog,
    _users_by_vlan_from_plan,
    _vlan_maps_from_catalog,
    _write_host_addresses_metadata,
    _write_vlan_gateways_metadata,
)
from typing import Dict, Any


def config_node(state: NetworkDesignState) -> Dict[str, Any]:
    topology = state.get("topology")
    if topology is None:
        return {
            "errors": ["Configuration skipped: topology is missing from state."],
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "Configuration skipped because topology generation did not produce a topology.",
                }
            ],
        }

    design_plan = state.get("design_plan") or {}

    catalog = vlan_catalog_from_state(topology, design_plan if isinstance(design_plan, dict) else {})

    # Ensure frontend has the VLAN catalog (names/ids) even if topology_agent omitted metadata merge.
    _sync_topology_vlan_catalog(topology, catalog)

    # Assign each host to a VLAN id and a valid subnet sized from design_plan users per department.
    vlan_name_by_id, vlan_ids_in_order = _vlan_maps_from_catalog(catalog)

    plan_dict = design_plan if isinstance(design_plan, dict) else {}
    users_by_vlan = _users_by_vlan_from_plan(plan_dict)
    vlan_networks = _allocate_vlan_networks(vlan_ids_in_order, users_by_vlan)
    _write_vlan_gateways_metadata(topology, vlan_ids_in_order, vlan_networks, users_by_vlan)

    # Hosts that don't match anything will be assigned in deterministic RR order.
    rr = [0]
    host_nodes = _collect_host_nodes(topology)
    hosts_by_vlan = _assign_host_vlan_membership(
        topology, host_nodes, catalog or [], vlan_name_by_id, rr
    )
    _assign_host_ips_from_networks(hosts_by_vlan, vlan_ids_in_order, vlan_networks)
    _assign_design_ports(topology)
    _write_host_addresses_metadata(topology)

    configurations: Dict[str, Any] = {}
    subnet_base = "192.168"
    subnet_counter = 1
    used_hostnames: set = set()

    for node in topology.nodes:
        if node.type == "router":
            configurations[node.id], subnet_counter = _build_router_configuration(
                node,
                catalog,
                vlan_ids_in_order,
                vlan_networks,
                subnet_base,
                subnet_counter,
                used_hostnames,
                topology,
            )

    for node in topology.nodes:
        if not _is_switch(node.type or ""):
            continue
        configurations[node.id] = _build_switch_configuration(
            topology, node, catalog, used_hostnames
        )

    return {
        "configurations": configurations,
        "topology": topology,
        "conversation_history": [{"role": "assistant", "content": "Configuration complete."}],
    }
