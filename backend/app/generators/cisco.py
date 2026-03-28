from jinja2 import Template

ROUTER_TEMPLATE = """
hostname {{ hostname }}
!
{% for interface in interfaces %}
interface {{ interface.name }}
 ip address {{ interface.ip }} {{ interface.mask }}
 no shutdown
!
{% endfor %}
!
router ospf 1
 network 0.0.0.0 255.255.255.255 area 0
!
end
"""

SWITCH_TEMPLATE = """
hostname {{ hostname }}
!
{% for v in vlan_plan.vlans %}
vlan {{ v["id"] }}
 name {{ v["name"] }}
!
{% endfor %}
{% for a in vlan_plan.access_assignments %}
interface FastEthernet0/{{ loop.index }}
 switchport mode access
 switchport access vlan {{ a["vlan_id"] }}
!
{% endfor %}
end
"""

def generate_cisco_config(node, config: dict) -> str:
    """
    Generates Cisco IOS config from template.
    """
    t = (getattr(node, "type", None) or "").lower()
    if "switch" in t or t == "switch" or "catalyst" in t or "hub" in t:
        vlan_plan = (config or {}).get("vlan_plan")
        if not vlan_plan:
            return ""
        # Ensure template always receives vlan DB + assignments (dicts, not missing keys)
        vp = {
            "vlans": list(vlan_plan.get("vlans") or []),
            "access_assignments": list(vlan_plan.get("access_assignments") or []),
        }
        template = Template(SWITCH_TEMPLATE)
        return template.render(hostname=config.get("hostname", node.id), vlan_plan=vp)
    if node.type != "router":
        return ""
    template = Template(ROUTER_TEMPLATE)
    return template.render(**config)
