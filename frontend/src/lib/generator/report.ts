import { Topology } from '@/types/network';
import { isRouterType, isSwitchType } from './cisco';

type DeviceConfig = {
    hostname?: string;
    interfaces?: Array<{ name?: string; ip?: string; mask?: string }>;
    trunk_interfaces?: Array<{ name?: string }>;
    subinterfaces?: Array<{ parent?: string; vlan_id?: number; ip?: string; mask?: string }>;
    vlan_plan?: {
        ports?: Array<{ interface?: string; mode?: string; vlan_id?: number }>;
    };
};

type MetaReport = {
    cisco_configs?: Record<string, string>;
    configurations?: Record<string, DeviceConfig>;
    cabling?: Array<{
        a_id: string;
        a_port: string;
        b_id: string;
        b_port: string;
        cable: string;
    }>;
    vlans?: Array<{ id: number; name: string }>;
    vlan_gateways?: Array<{
        vlan_id: number;
        gateway: string;
        mask: string;
        network?: string;
        prefix_len?: number;
        users?: number;
    }>;
    host_addresses?: Array<{
        id: string;
        label: string;
        interface: string;
        ip?: string | null;
        mask?: string | null;
        gateway?: string | null;
        vlan_id?: number | null;
    }>;
};

/** Matches backend LITERAL_HOST_NODE_THRESHOLD */
const REPRESENTATIVE_USERS_THRESHOLD = 8;

const REGENERATE_NOTE =
    'No validated design data for this section. Generate or regenerate the design with the AI assistant, then export again.';

function hostnameFor(
    configs: Record<string, DeviceConfig>,
    nodeId: string,
    fallback: string
): string {
    return configs[nodeId]?.hostname || fallback;
}

function ipv4ToInt(ip: string): number | null {
    const parts = ip.split('.').map(Number);
    if (parts.length !== 4 || parts.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return null;
    return ((parts[0] << 24) >>> 0) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
}

function intToIpv4(n: number): string {
    return `${(n >>> 24) & 255}.${(n >>> 16) & 255}.${(n >>> 8) & 255}.${n & 255}`;
}

function maskToPrefix(mask: string): number | null {
    const n = ipv4ToInt(mask);
    if (n == null) return null;
    let bits = 0;
    let v = n;
    for (let i = 0; i < 32; i++) {
        if (v & 0x80000000) bits++;
        else break;
        v = (v << 1) >>> 0;
    }
    const expected = bits === 0 ? 0 : (~0 << (32 - bits)) >>> 0;
    if (n !== expected) return null;
    return bits;
}

/**
 * Representative range: first = gateway+1, end = gateway+users, clamped to the
 * last usable address in the subnet (broadcast-1). If users would pass the
 * subnet, end stops at last usable (range is not invented past the mask).
 */
function hostAddressRange(gateway: string, mask: string, users: number): string {
    const gw = ipv4ToInt(gateway);
    const prefix = maskToPrefix(mask);
    if (gw == null || prefix == null || users <= 0) return '';
    const hostBits = 32 - prefix;
    if (hostBits <= 1) return '';
    const size = 2 ** hostBits;
    const net = gw - (gw % size);
    const lastUsable = net + size - 2;
    const first = gw + 1;
    if (first > lastUsable) return '';
    let end = gw + users;
    if (end > lastUsable) end = lastUsable;
    return `${intToIpv4(first)}-${intToIpv4(end)}`;
}

function hasValidatedDesignMeta(meta: MetaReport): boolean {
    const cfg = meta.configurations && Object.keys(meta.configurations).length > 0;
    const cab = (meta.cabling || []).length > 0;
    const vg = (meta.vlan_gateways || []).length > 0;
    return Boolean(cfg || cab || vg);
}

export function generateMarkdownReport(topology: Topology): string {
    const date = new Date().toLocaleDateString();
    const runtime = topology.runtime;
    const meta = (topology.metadata || {}) as MetaReport;
    const configs = meta.configurations || {};
    const cliMap = meta.cisco_configs;
    const cabling = meta.cabling || [];
    const vlanGateways = meta.vlan_gateways || [];
    const hostAddresses = meta.host_addresses || [];
    const vlanNames = new Map(
        (meta.vlans || []).map((v) => [Number(v.id), String(v.name || `VLAN_${v.id}`)])
    );
    const nodeById = new Map(topology.nodes.map((n) => [n.id, n]));
    const validated = hasValidatedDesignMeta(meta);

    let md = `Generated from the last validated design; regenerate after edits.\n\n`;
    md += `# Network Design Report\n`;
    md += `**Project:** ${topology.name}\n`;
    md += `**Date:** ${date}\n\n`;

    md += `## 1. Executive Summary\n`;
    md += `This document details the logical network design for ${topology.name}. The network consists of ${topology.nodes.length} devices and ${topology.links.length} connections.\n\n`;

    md += `## 2. Topology Generation Runtime\n`;
    if (runtime?.elapsed_ms !== undefined || runtime?.elapsed_seconds !== undefined || runtime?.started_at_utc) {
        if (runtime?.started_at_utc) md += `- Start Time (UTC): ${runtime.started_at_utc}\n`;
        if (runtime?.elapsed_ms !== undefined) md += `- Runtime (ms): ${runtime.elapsed_ms}\n`;
        if (runtime?.elapsed_seconds !== undefined) md += `- Runtime (seconds): ${runtime.elapsed_seconds}\n`;
    } else {
        md += `- Runtime not available for this generation.\n`;
    }
    md += `\n`;

    if (!validated) {
        md += `## 3. IP Addressing Schema\n${REGENERATE_NOTE}\n\n`;
        md += `## 4. Cabling\n${REGENERATE_NOTE}\n\n`;
        md += `## 5. VLANs\n${REGENERATE_NOTE}\n\n`;
        md += `## 6. Hosts\n${REGENERATE_NOTE}\n\n`;
        md += `## 7. Canvas label -> Hostname\n${REGENERATE_NOTE}\n\n`;
    } else {
        const ipLines: string[] = [];
        for (const node of topology.nodes) {
            const cfg = configs[node.id];
            if (!cfg) continue;
            const label = node.name;
            const hostname = cfg.hostname || label;

            if (isRouterType(node.type)) {
                for (const s of cfg.subinterfaces || []) {
                    if (!s.parent || s.vlan_id == null) continue;
                    ipLines.push(
                        `| ${label} | ${hostname} | ${s.parent}.${s.vlan_id} | subinterface | ${s.ip || ''} | ${s.mask || ''} |  |\n`
                    );
                }
                for (const t of cfg.trunk_interfaces || []) {
                    if (!t.name) continue;
                    ipLines.push(`| ${label} | ${hostname} | ${t.name} | trunk parent |  |  |  |\n`);
                }
                for (const iface of cfg.interfaces || []) {
                    if (!iface.name) continue;
                    ipLines.push(
                        `| ${label} | ${hostname} | ${iface.name} | routed | ${iface.ip || ''} | ${iface.mask || ''} |  |\n`
                    );
                }
            } else if (isSwitchType(node.type)) {
                for (const p of cfg.vlan_plan?.ports || []) {
                    if (!p.interface) continue;
                    let role = p.mode || '';
                    if (role === 'access' && p.vlan_id != null) role = `access VLAN ${p.vlan_id}`;
                    ipLines.push(`| ${label} | ${hostname} | ${p.interface} | ${role} |  |  |  |\n`);
                }
            }
        }
        for (const h of hostAddresses) {
            const lab = h.label || h.id;
            ipLines.push(
                `| ${lab} | ${lab} | ${h.interface || 'FastEthernet0'} | host | ${h.ip || ''} | ${h.mask || ''} | ${h.gateway || ''} |\n`
            );
        }

        md += `## 3. IP Addressing Schema\n`;
        if (ipLines.length === 0) {
            md += `${REGENERATE_NOTE}\n\n`;
        } else {
            md += `| Device (canvas) | Hostname | Interface | Role | IP Address | Subnet Mask | Gateway |\n`;
            md += `| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n`;
            md += ipLines.join('');
            md += `\n`;
            md += `_Wire one physical PC per host row in Packet Tracer. A canvas label like "(20 PCs)" means that row is representative of N department users._\n`;
            if (hostAddresses.length === 0) {
                md += `\n_Host IP rows missing (design saved before Step C). ${REGENERATE_NOTE}_\n`;
            }
            md += `\n`;
        }

        md += `## 4. Cabling\n`;
        if (cabling.length === 0) {
            md += `${REGENERATE_NOTE}\n\n`;
        } else {
            md += `| Device A | Port A | Device B | Port B | Cable |\n`;
            md += `| :--- | :--- | :--- | :--- | :--- |\n`;
            for (const row of cabling) {
                const aLabel = nodeById.get(row.a_id)?.name || row.a_id;
                const bLabel = nodeById.get(row.b_id)?.name || row.b_id;
                const aName = hostnameFor(configs, row.a_id, aLabel);
                const bName = hostnameFor(configs, row.b_id, bLabel);
                md += `| ${aName} | ${row.a_port} | ${bName} | ${row.b_port} | ${row.cable} |\n`;
            }
            md += `\n`;
            md += `_Host ends labeled "(N PCs)" are representative: cable one PC on that access port in Packet Tracer._\n\n`;
        }

        md += `## 5. VLANs\n`;
        if (vlanGateways.length === 0) {
            md += `${REGENERATE_NOTE}\n\n`;
        } else {
            md += `| VLAN ID | Name | Subnet | Gateway | Users | Host address range |\n`;
            md += `| :--- | :--- | :--- | :--- | :--- | :--- |\n`;
            for (const g of vlanGateways) {
                const vid = Number(g.vlan_id);
                const name = vlanNames.get(vid) || '';
                const subnet =
                    g.network != null && g.prefix_len != null ? `${g.network}/${g.prefix_len}` : '';
                const users = g.users;
                let range = '';
                if (
                    users != null &&
                    users > REPRESENTATIVE_USERS_THRESHOLD &&
                    g.gateway &&
                    g.mask
                ) {
                    range = hostAddressRange(g.gateway, g.mask, users);
                }
                md += `| ${vid} | ${name} | ${subnet} | ${g.gateway || ''} | ${users ?? ''} | ${range} |\n`;
            }
            md += `\n`;
            if (vlanGateways.every((g) => g.users == null)) {
                md += `_Department user counts missing (design saved before Step C). ${REGENERATE_NOTE}_\n\n`;
            }
        }

        md += `## 6. Hosts\n`;
        if (hostAddresses.length === 0) {
            md += `${REGENERATE_NOTE}\n\n`;
        } else {
            md += `| Canvas label | Interface | IP Address | Subnet Mask | Gateway |\n`;
            md += `| :--- | :--- | :--- | :--- | :--- |\n`;
            for (const h of hostAddresses) {
                md += `| ${h.label || h.id} | ${h.interface || 'FastEthernet0'} | ${h.ip || ''} | ${h.mask || ''} | ${h.gateway || ''} |\n`;
            }
            md += `\n`;
            md += `_Each row is one Packet Tracer host on FastEthernet0. "(N PCs)" on the canvas label means this IP represents N users; configure one PC._\n\n`;
        }

        md += `## 7. Canvas label -> Hostname\n`;
        const hostnameRows: string[] = [];
        for (const node of topology.nodes) {
            const hn = configs[node.id]?.hostname;
            if (!hn) continue;
            hostnameRows.push(`| ${node.name} | ${hn} |\n`);
        }
        if (hostnameRows.length === 0) {
            md += `${REGENERATE_NOTE}\n\n`;
        } else {
            md += `| Canvas label | Hostname |\n`;
            md += `| :--- | :--- |\n`;
            md += hostnameRows.join('');
            md += `\n`;
        }
    }

    md += `## 8. Device Configurations\n`;
    md += `The following configurations are generated for Cisco IOS devices.\n\n`;

    topology.nodes.forEach((node) => {
        if (isRouterType(node.type) || isSwitchType(node.type)) {
            md += `### ${node.name} (${node.type.toUpperCase()})\n`;
            md += `\`\`\`cisco-cli\n`;
            const cli = cliMap?.[node.id];
            if (cli) {
                md += cli.endsWith('\n') ? cli : `${cli}\n`;
            } else {
                md += `! No validated CLI for ${node.name}. Regenerate the design.\n`;
            }
            md += `\`\`\`\n\n`;
        } else if (node.type === 'host') {
            const h = hostAddresses.find((x) => x.id === node.id);
            md += `### ${node.name} (HOST)\n`;
            md += `\`\`\`text\n`;
            if (h && h.ip) {
                md += `Host Configuration for ${node.name}:\n`;
                md += `----------------------------------------\n`;
                md += `IP Address      : ${h.ip}\n`;
                md += `Subnet Mask     : ${h.mask || ''}\n`;
                md += `Default Gateway : ${h.gateway || ''}\n`;
                md += `----------------------------------------\n`;
                md += `Note: Wire one PC in Packet Tracer with these settings.\n`;
            } else {
                md += `! No validated host address for ${node.name}. Regenerate the design.\n`;
            }
            md += `\`\`\`\n\n`;
        }
    });

    return md;
}
