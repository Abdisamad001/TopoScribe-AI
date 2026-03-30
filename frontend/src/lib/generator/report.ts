import { Topology } from '@/types/network';
import { generateCiscoConfig, isRouterType, isSwitchType } from './cisco';

export function generateMarkdownReport(topology: Topology): string {
    const date = new Date().toLocaleDateString();

    let md = `# Network Design Report\n`;
    md += `**Project:** ${topology.name}\n`;
    md += `**Date:** ${date}\n\n`;

    md += `## 1. Executive Summary\n`;
    md += `This document details the logical network design for ${topology.name}. The network consists of ${topology.nodes.length} devices and ${topology.links.length} connections.\n\n`;

    md += `## 2. IP Addressing Schema\n`;
    md += `| Device | Interface | IP Address | Subnet Mask |\n`;
    md += `| :--- | :--- | :--- | :--- |\n`;

    topology.nodes.forEach(node => {
        node.interfaces.forEach(iface => {
            if (iface.ipAddress && iface.ipAddress !== 'no ip address') {
                let mask = iface.subnetMask;
                if (!mask) {
                    // Auto-detect mask based on IP class/usage if missing
                    if (iface.ipAddress.startsWith('10.')) {
                        mask = '255.255.255.252'; // Assume /30 for 10.x block (WAN)
                    } else {
                        mask = '255.255.255.0';   // Assume /24 for others
                    }
                }
                md += `| ${node.name} | ${iface.name} | ${iface.ipAddress} | ${mask} |\n`;
            }
        });
    });
    md += `\n`;

    md += `## 3. Device Configurations\n`;
    md += `The following configurations are generated for Cisco IOS devices.\n\n`;

    topology.nodes.forEach(node => {
        if (isRouterType(node.type) || isSwitchType(node.type)) {
            md += `### ${node.name} (${node.type.toUpperCase()})\n`;
            md += `\`\`\`cisco-cli\n`;
            md += generateCiscoConfig(node, topology);
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
