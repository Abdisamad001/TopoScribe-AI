import { NetworkNode, Link, Topology, TopologyMetadata } from '@/types/network';

/** First usable host in subnet (matches Python IPv4Network[1] / config_agent gateway). */
function firstHostInNetwork(ip: string, mask: string): string {
    const ipParts = ip.split('.').map(Number);
    const maskParts = mask.split('.').map(Number);
    if (ipParts.length < 4 || maskParts.length < 4) return ip;
    const netParts = ipParts.map((p, i) => p & maskParts[i]);
    let n = (netParts[0] << 24) + (netParts[1] << 16) + (netParts[2] << 8) + netParts[3];
    n += 1;
    return `${(n >>> 24) & 255}.${(n >> 16) & 255}.${(n >> 8) & 255}.${n & 255}`;
}

function ifaceIp(iface: NetworkNode['interfaces'][0] | undefined): string | undefined {
    if (!iface) return undefined;
    return iface.ipAddress || (iface as { ip_address?: string }).ip_address || (iface as { ip?: string }).ip;
}

function ifaceMask(iface: NetworkNode['interfaces'][0] | undefined): string | undefined {
    if (!iface) return undefined;
    return iface.subnetMask || (iface as { subnet_mask?: string }).subnet_mask || (iface as { mask?: string }).mask;
}

function gatewayAndMaskForVlan(
    vlanId: number,
    nodes: NetworkNode[],
    metadata?: TopologyMetadata
): { gw: string; mask: string } {
    const rows = metadata?.vlan_gateways;
    if (rows?.length) {
        const row = rows.find((r) => Number(r.vlan_id) === vlanId);
        if (row?.gateway && row?.mask) return { gw: row.gateway, mask: row.mask };
    }
    for (const n of nodes) {
        if (n.type !== 'host') continue;
        const cfg = n.config?.vlan_id;
        if (cfg !== vlanId) continue;
        const ip = ifaceIp(n.interfaces?.[0]);
        const mask = ifaceMask(n.interfaces?.[0]);
        if (ip && mask) return { gw: firstHostInNetwork(ip, mask), mask };
        if (ip) {
            const parts = ip.split('.');
            if (parts.length >= 4) return { gw: `${parts[0]}.${parts[1]}.${parts[2]}.1`, mask: '255.255.255.0' };
        }
    }
    if (vlanId <= 255) return { gw: `192.168.${vlanId}.1`, mask: '255.255.255.0' };
    return { gw: `10.${(vlanId >> 8) & 255}.${vlanId & 255}.1`, mask: '255.255.255.0' };
}

function gatewayForVlan(vlanId: number, nodes: NetworkNode[], metadata?: TopologyMetadata): string {
    return gatewayAndMaskForVlan(vlanId, nodes, metadata).gw;
}

export function isRouterType(t: string): boolean {
    const x = t.toLowerCase();
    return x.includes('router') || x.includes('gateway') || (x.includes('firewall') && !x.includes('switch'));
}

export function isSwitchType(t: string): boolean {
    const x = t.toLowerCase();
    return x === 'switch' || x.includes('switch') || x.includes('catalyst') || x.includes('hub') || x.includes('2960');
}

function getVlanCatalog(topology: Pick<Topology, 'nodes' | 'metadata'>): { id: number; name: string }[] {
    const md = topology.metadata as TopologyMetadata | undefined;
    if (md?.vlans?.length) {
        return md.vlans
            .map((v) => ({
                id: Number(v.id),
                name: String(v.name || `VLAN_${v.id}`),
            }))
            .filter((v) => v.id >= 2 && v.id <= 4094);
    }
    const fromConfig = new Map<number, string>();
    for (const n of topology.nodes) {
        const vid = n.config?.vlan_id;
        if (typeof vid === 'number' && vid >= 2 && vid <= 4094) {
            fromConfig.set(vid, String(n.config?.vlan_name || `VLAN_${vid}`));
        }
    }
    if (fromConfig.size > 0) {
        return [...fromConfig.entries()]
            .sort((a, b) => a[0] - b[0])
            .map(([id, name]) => ({ id, name }));
    }
    const seen = new Map<number, string>();
    for (const n of topology.nodes) {
        if (n.type !== 'host') continue;
        const ip = n.interfaces?.[0]?.ipAddress;
        if (!ip) continue;
        const p = ip.split('.');
        if (p.length < 3) continue;
        const o = parseInt(p[2], 10);
        if (o >= 2 && o <= 4094 && !seen.has(o)) {
            seen.set(o, `VLAN_${o}`);
        }
    }
    return [...seen.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([id, name]) => ({ id, name }));
}

function allowedVlansCsv(catalog: { id: number; name: string }[]): string {
    return catalog.map((v) => v.id).join(',');
}

function matchVlanFromCatalog(text: string, catalog: { id: number; name: string }[]): number | null {
    const t = text.toLowerCase();
    if (!t) return null;
    let best: { score: number; id: number } | null = null;
    for (const v of catalog) {
        const name = v.name.toLowerCase();
        if (!name) continue;
        if (t.includes(name) || t.includes(name.replace(/\s+/g, '_'))) {
            const score = name.length;
            if (!best || score > best.score) best = { score, id: v.id };
        }
        for (const tok of name.split(/[\s_/\-]+/)) {
            if (tok.length >= 2 && t.includes(tok)) {
                const score = tok.length;
                if (!best || score > best.score) best = { score, id: v.id };
            }
        }
    }
    return best ? best.id : null;
}

function vlanFromHostIp(ip: string | undefined): number | null {
    if (!ip || ip === 'no ip address' || ip === '0.0.0.0') return null;
    const parts = ip.split('.');
    if (parts.length < 3) return null;
    const o = parseInt(parts[2], 10);
    if (o >= 2 && o <= 4094) return o;
    return null;
}

function resolveAccessVlan(
    host: NetworkNode,
    switchNode: NetworkNode | undefined,
    catalog: { id: number; name: string }[],
    rr: { n: number }
): number {
    const ids = new Set(catalog.map((c) => c.id));
    if (ids.size === 0) {
        const fromIp = vlanFromHostIp(host.interfaces?.[0]?.ipAddress);
        return fromIp ?? 1;
    }
    const cfgVid = host.config?.vlan_id;
    if (typeof cfgVid === 'number' && ids.has(cfgVid)) return cfgVid;

    const m =
        matchVlanFromCatalog(`${host.name} ${host.id}`, catalog) ??
        (switchNode ? matchVlanFromCatalog(`${switchNode.name} ${switchNode.id}`, catalog) : null);
    if (m !== null && ids.has(m)) return m;

    const fromIp = vlanFromHostIp(host.interfaces?.[0]?.ipAddress);
    if (fromIp !== null && ids.has(fromIp)) return fromIp;

    const order = [...ids].sort((a, b) => a - b);
    const v = order[rr.n % order.length];
    rr.n += 1;
    return v;
}

export function generateCiscoConfig(node: NetworkNode, topology: Topology): string {
    if (node.type === 'router' || isRouterType(node.type)) {
        return generateRouterConfig(node, topology);
    } else if (node.type === 'switch' || isSwitchType(node.type)) {
        return generateSwitchConfig(node, topology);
    } else if (node.type === 'host') {
        return generateHostConfig(node, topology.nodes);
    }
    return '! Unknown device type\n';
}

function generateRouterConfig(node: NetworkNode, topology: Topology): string {
    const { nodes, links, protocols, metadata } = topology;
    const catalog = getVlanCatalog(topology);
    const prompt = `${node.name}#`;
    let config = `${prompt} show running-config\n`;
    config += `Building configuration...\n\n`;
    config += `Current configuration : 2048 bytes\n`;
    config += `!\n! Cisco IOS Configuration for ${node.name}\n! Generated by TopoScribe AI\n!\n`;

    config += `version 15.1\n`;
    config += `service timestamps debug datetime msec\n`;
    config += `service timestamps log datetime msec\n`;
    config += `service password-encryption\n!\n`;
    config += `hostname ${node.name}\n!\n`;
    config += `boot-start-marker\nboot-end-marker\n!\n`;
    config += `enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0\n!\n`;
    config += `no ip domain lookup\nip domain name toposcribe.local\n!\n`;

    if (catalog.length > 0) {
        const parent = node.interfaces[0]?.name || 'GigabitEthernet0/0';
        config += `interface ${parent}\n`;
        config += ` description Trunk to switching infrastructure\n`;
        config += ` no ip address\n`;
        config += ` no shutdown\n`;
        config += ` duplex auto\n speed auto\n`;
        config += `!\n`;

        for (const v of catalog) {
            const { gw, mask } = gatewayAndMaskForVlan(v.id, nodes, metadata);
            config += `interface ${parent}.${v.id}\n`;
            config += ` encapsulation dot1Q ${v.id}\n`;
            config += ` ip address ${gw} ${mask}\n`;
            config += ` no shutdown\n`;
            config += `!\n`;
        }

        const ospf = protocols.find((p) => p.type === 'ospf');
        if (ospf || true) {
            config += `router ospf 1\n`;
            config += ` router-id ${findRouterIdFromCatalog(catalog, nodes, metadata)}\n`;
            for (const v of catalog) {
                const { gw, mask } = gatewayAndMaskForVlan(v.id, nodes, metadata);
                const wildcard = calculateWildcard(mask);
                const network = getNetworkAddress(gw, mask);
                config += ` network ${network} ${wildcard} area 0\n`;
            }
            config += `!\n`;
        }
    } else {
        node.interfaces.forEach((iface) => {
            config += `interface ${iface.name}\n`;

            const link = links.find(
                (l) =>
                    (l.sourceNodeId === node.id && (l.sourceInterfaceId === iface.id || !l.sourceInterfaceId)) ||
                    (l.targetNodeId === node.id && (l.targetInterfaceId === iface.id || !l.targetInterfaceId))
            );

            if (link) {
                const peerId = link.sourceNodeId === node.id ? link.targetNodeId : link.sourceNodeId;
                const peer = nodes.find((n) => n.id === peerId);
                if (peer) config += ` description Link to ${peer.name}\n`;
            }

            if (iface.ipAddress && iface.ipAddress !== 'no ip address') {
                const mask = iface.subnetMask || '255.255.255.0';
                config += ` ip address ${iface.ipAddress} ${mask}\n`;
            } else {
                config += ` no ip address\n`;
            }

            config += ` no shutdown\n`;
            if (node.type === 'router' && (!iface.ipAddress || iface.ipAddress === '0.0.0.0')) {
                config += ` duplex auto\n speed auto\n`;
            }
            config += `!\n`;
        });

        const ospf = protocols.find((p) => p.type === 'ospf');
        if (ospf || true) {
            config += `router ospf 1\n`;
            config += ` router-id ${findRouterId(node)}\n`;
            node.interfaces.forEach((iface) => {
                if (iface.ipAddress && iface.ipAddress !== '0.0.0.0') {
                    const mask = iface.subnetMask || '255.255.255.0';
                    const wildcard = calculateWildcard(mask);
                    const network = getNetworkAddress(iface.ipAddress, mask);
                    config += ` network ${network} ${wildcard} area 0\n`;
                }
            });
            config += `!\n`;
        }
    }

    config += `line con 0\n password 7 0822455D0A16\n login\n logging synchronous\n!\n`;
    config += `line vty 0 4\n password 7 0822455D0A16\n login\n transport input ssh\n!\n`;

    config += `end\n\n`;
    config += `${prompt} write memory\n`;
    config += `Building configuration...\n[OK]\n`;

    return config;
}

type SwitchPortJob = { ifaceName: string; peer: NetworkNode | undefined };

function buildSwitchPortJobs(node: NetworkNode, links: Link[], allNodes: NetworkNode[]): SwitchPortJob[] {
    // For report generation we must create one access port per connected host.
    // The canvas may only store a single interface on each switch, so we ignore node.interfaces
    // and instead derive ports from topology links.
    const jobs: SwitchPortJob[] = [];
    const connectedLinks = links
        .filter((l) => l.sourceNodeId === node.id || l.targetNodeId === node.id)
        .sort((a, b) => a.id.localeCompare(b.id));

    connectedLinks.forEach((link, idx) => {
        const peerId = link.sourceNodeId === node.id ? link.targetNodeId : link.sourceNodeId;
        const peer = allNodes.find((n) => n.id === peerId);
        jobs.push({ ifaceName: `FastEthernet0/${idx + 1}`, peer });
    });

    return jobs;
}

function generateSwitchConfig(node: NetworkNode, topology: Topology): string {
    const { nodes, links } = topology;
    const catalog = getVlanCatalog(topology);
    const prompt = `${node.name}#`;
    let config = `${prompt} show running-config\n`;
    config += `Building configuration...\n\n`;
    config += `Current configuration : 1536 bytes\n`;
    config += `!\n! Cisco IOS Configuration for ${node.name}\n! Generated by TopoScribe AI\n!\n`;

    config += `version 15.1\n`;
    config += `service timestamps debug datetime msec\n`;
    config += `service timestamps log datetime msec\n!\n`;
    config += `hostname ${node.name}\n!\n`;
    config += `boot-start-marker\nboot-end-marker\n!\n`;
    config += `enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0\n!\n`;

    const vlanUnion = new Map<number, string>();
    for (const v of catalog) {
        vlanUnion.set(v.id, v.name);
    }

    const portJobs = buildSwitchPortJobs(node, links, nodes);
    const rr = { n: 0 };
    const accessVlans: number[] = [];

    for (const job of portJobs) {
        config += `interface ${job.ifaceName}\n`;
        const peer = job.peer;
        if (peer) {
            config += ` description Link to ${peer.name}\n`;
        }

        if (peer && (isRouterType(peer.type) || isSwitchType(peer.type))) {
            const csv = catalog.length > 0 ? allowedVlansCsv(catalog) : '1';
            for (const v of catalog) {
                vlanUnion.set(v.id, v.name);
            }
            config += ` switchport mode trunk\n`;
            config += ` switchport trunk encapsulation dot1q\n`;
            config += ` switchport trunk allowed vlan ${csv}\n`;
        } else if (peer) {
            const vid = resolveAccessVlan(peer, node, catalog, rr);
            accessVlans.push(vid);
            if (!vlanUnion.has(vid)) {
                vlanUnion.set(vid, `VLAN_${vid}`);
            }
            config += ` switchport mode access\n`;
            config += ` switchport access vlan ${vid}\n`;
        } else {
            config += ` switchport mode access\n`;
            config += ` switchport access vlan 1\n`;
        }
        config += ` no shutdown\n`;
        config += `!\n`;
    }

    for (const vid of accessVlans) {
        vlanUnion.set(vid, vlanUnion.get(vid) || `VLAN_${vid}`);
    }

    const vlanBlock = [...vlanUnion.entries()]
        .filter(([id]) => id >= 2 && id <= 4094)
        .sort((a, b) => a[0] - b[0]);

    let vlanSection = '';
    for (const [id, name] of vlanBlock) {
        vlanSection += `vlan ${id}\n`;
        vlanSection += ` name ${name}\n`;
        vlanSection += `!\n`;
    }
    config = config.replace(
        /(boot-end-marker\n!\n)/,
        `$1${vlanSection}`
    );

    let vlanIface = node.interfaces.find((i) => i.name.toLowerCase().startsWith('vlan'));
    if (!vlanIface) {
        vlanIface = node.interfaces.find(
            (i) => i.ipAddress && i.ipAddress !== 'no ip address' && i.ipAddress !== '0.0.0.0'
        );
    }

    if (vlanIface && vlanIface.ipAddress && vlanIface.ipAddress !== 'no ip address') {
        config += `interface Vlan1\n`;
        config += ` description Management Interface\n`;
        config += ` ip address ${vlanIface.ipAddress} ${vlanIface.subnetMask || '255.255.255.0'}\n`;
        config += ` no shutdown\n`;
        config += `!\n`;
    }

    if (vlanIface && vlanIface.ipAddress) {
        const parts = vlanIface.ipAddress.split('.');
        parts[3] = '1';
        config += `ip default-gateway ${parts.join('.')}\n!\n`;
    }

    config += `line con 0\n password cisco\n login\n!\n`;
    config += `line vty 0 4\n password cisco\n login\n!\n`;

    config += `end\n\n`;
    config += `${prompt} write memory\n`;
    config += `Building configuration...\n[OK]\n`;

    return config;
}

function generateHostConfig(node: NetworkNode, _allNodes: NetworkNode[]): string {
    const iface = node.interfaces[0];
    const ip = ifaceIp(iface) || 'DHCP';
    const mask = ifaceMask(iface) || '255.255.255.0';

    let gateway = 'Unknown';
    if (ip !== 'DHCP' && ip) {
        gateway = firstHostInNetwork(ip, mask);
    }

    return `Host Configuration for ${node.name}:
----------------------------------------
IP Address      : ${ip}
Subnet Mask     : ${mask}
Default Gateway : ${gateway}
DNS Server      : 8.8.8.8
----------------------------------------
`;
}

function findRouterId(node: NetworkNode): string {
    const validIface = node.interfaces.find((i) => i.ipAddress && i.ipAddress !== '0.0.0.0');
    return validIface ? validIface.ipAddress! : '1.1.1.1';
}

function findRouterIdFromCatalog(
    catalog: { id: number; name: string }[],
    nodes: NetworkNode[],
    metadata?: TopologyMetadata
): string {
    if (catalog.length > 0) {
        return gatewayForVlan(catalog[0].id, nodes, metadata);
    }
    return '1.1.1.1';
}

function calculateWildcard(mask: string): string {
    const parts = mask.split('.').map(Number);
    const wildcardParts = parts.map((p) => 255 - p);
    return wildcardParts.join('.');
}

function getNetworkAddress(ip: string, mask: string): string {
    const ipParts = ip.split('.').map(Number);
    const maskParts = mask.split('.').map(Number);
    const netParts = ipParts.map((p, i) => p & maskParts[i]);
    return netParts.join('.');
}
