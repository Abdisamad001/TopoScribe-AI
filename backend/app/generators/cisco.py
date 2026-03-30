from jinja2 import Template

ROUTER_TEMPLATE_CLASSIC = """
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

ROUTER_TEMPLATE_SUBIFS = """
hostname {{ hostname }}
!
{% for t in trunk_interfaces %}
interface {{ t.name }}
 no ip address
 no shutdown
!
{% endfor %}
{% for s in subinterfaces %}
interface {{ s.parent }}.{{ s.vlan_id }}
 encapsulation dot1Q {{ s.vlan_id }}
 ip address {{ s.ip }} {{ s.mask }}
 no shutdown
!
{% endfor %}
!
router ospf 1
{% for s in subinterfaces %}
 network {{ s.network }} {{ s.wildcard }} area 0
{% endfor %}
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
{% for p in vlan_plan.ports %}
interface {{ p["interface"] }}
{% if p["mode"] == "trunk" %}
 switchport mode trunk
 switchport trunk encapsulation dot1q
 switchport trunk allowed vlan {{ p["allowed_vlans_csv"] }}
{% else %}
 switchport mode access
 switchport access vlan {{ p["vlan_id"] }}
{% endif %}
 no shutdown
!
{% endfor %}
end
"""

def _wildcard(mask: str) -> str:
    parts = [int(x) for x in mask.split(".")]
    return ".".join(str(255 - p) for p in parts)

def _network_addr(ip: str, mask: str) -> str:
    ip_parts = [int(x) for x in ip.split(".")]
    m_parts = [int(x) for x in mask.split(".")]
    return ".".join(str(ip_parts[i] & m_parts[i]) for i in range(4))

def generate_cisco_config(node, config: dict) -> str:
    """
    Generates Cisco IOS config from template.
    """
    t = (getattr(node, "type", None) or "").lower()
    if "switch" in t or t == "switch" or "catalyst" in t or "hub" in t:
        vlan_plan = (config or {}).get("vlan_plan")
        if not vlan_plan:
            return ""
        vp = {
            "vlans": list(vlan_plan.get("vlans") or []),
            "ports": list(vlan_plan.get("ports") or []),
        }
        template = Template(SWITCH_TEMPLATE)
        return template.render(hostname=config.get("hostname", node.id), vlan_plan=vp)
    if node.type != "router":
        return ""

    cfg = config or {}
    subs = cfg.get("subinterfaces") or []
    if subs:
        enriched = []
        for s in subs:
            mask = s.get("mask") or "255.255.255.0"
            ip = s.get("ip") or "0.0.0.0"
            enriched.append(
                {
                    "parent": s.get("parent"),
                    "vlan_id": s.get("vlan_id"),
                    "ip": ip,
                    "mask": mask,
                    "network": _network_addr(ip, mask),
                    "wildcard": _wildcard(mask),
                }
            )
        template = Template(ROUTER_TEMPLATE_SUBIFS)
        return template.render(
            hostname=cfg.get("hostname", node.id),
            trunk_interfaces=cfg.get("trunk_interfaces") or [],
            subinterfaces=enriched,
        )
    template = Template(ROUTER_TEMPLATE_CLASSIC)
    return template.render(**cfg)
