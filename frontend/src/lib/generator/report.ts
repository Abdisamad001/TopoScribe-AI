import { Topology } from '@/types/network';
import { generateCiscoConfig, isRouterType, isSwitchType } from './cisco';

type MetaWithCli = {
    cisco_configs?: Record<string, string>;
    configurations?: Record<string, unknown>;
};

export function generateMarkdownReport(topology: Topology): string {
    const date = new Date().toLocaleDateString();
    const runtime = topology.runtime;

    let md = `# Network Design Report\n`;
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

    md += `## 3. IP Addressing Schema\n`;
    md += `| Device | Interface | IP Address | Subnet Mask |\n`;
    md += `| :--- | :--- | :--- | :--- |\n`;

    topology.nodes.forEach(node => {
        node.interfaces.forEach(iface => {
            const ip = iface.ipAddress || (iface as { ip_address?: string }).ip_address;
            if (ip && ip !== 'no ip address') {
                let mask =
                    iface.subnetMask ||
                    (iface as { subnet_mask?: string }).subnet_mask ||
                    (iface as { mask?: string }).mask;
                if (!mask) {
                    // Auto-detect mask based on IP class/usage if missing
                    if (ip.startsWith('10.')) {
                        mask = '255.255.255.252'; // Assume /30 for 10.x block (WAN)
                    } else {
                        mask = '255.255.255.0';   // Assume /24 for others
                    }
                }
                md += `| ${node.name} | ${iface.name} | ${ip} | ${mask} |\n`;
            }
        });
    });
    md += `\n`;

    md += `## 4. Device Configurations\n`;
    md += `The following configurations are generated for Cisco IOS devices.\n\n`;

    const cliMap = (topology.metadata as MetaWithCli | undefined)?.cisco_configs;

    topology.nodes.forEach(node => {
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
            md += `### ${node.name} (HOST)\n`;
            md += `\`\`\`text\n`;
            md += generateCiscoConfig(node, topology);
            md += `\`\`\`\n\n`;
        }
    });

    return md;
}
