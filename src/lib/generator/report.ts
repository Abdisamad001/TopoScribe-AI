import { Topology } from '@/types/network';
import { generateCiscoConfig } from './cisco';

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
            if (iface.ipAddress) {
                md += `| ${node.name} | ${iface.name} | ${iface.ipAddress} | ${iface.subnetMask || '-'} |\n`;
            }
        });
    });
    md += `\n`;

    md += `## 3. Device Configurations\n`;
    md += `The following configurations are generated for Cisco IOS devices.\n\n`;

    topology.nodes.forEach(node => {
        if (node.type === 'router' || node.type === 'switch') {
            md += `### ${node.name} (${node.type.toUpperCase()})\n`;
            md += `\`\`\`text\n`;
            md += generateCiscoConfig(node, topology.nodes, topology.links, topology.protocols);
            md += `\`\`\`\n\n`;
        }
    });

    return md;
}
