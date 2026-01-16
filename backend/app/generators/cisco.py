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

def generate_cisco_config(node, config: dict) -> str:
    """
    Generates Cisco IOS config from template.
    """
    if node.type != "router":
        return ""
    template = Template(ROUTER_TEMPLATE)
    return template.render(**config)
