import { Groq } from 'groq-sdk';
import { NetworkNode, Link, ProtocolConfig } from '@/types/network';

// You must set GROQ_API_KEY in your .env.local file
const groq = new Groq({
    apiKey: process.env.GROQ_API_KEY || 'REMOVED_KEY' // Fallback for demo only
});

const SYSTEM_PROMPT = `
You are an Expert Network Design Architect (CCIE Level). Your job is to convert natural language requirements into a detailed, valid JSON network topology.

Output Format: A single JSON object with 'nodes', 'links', and 'protocols'.
- nodes: Array { id, type, name, x, y, interfaces: [{ id, name, ipAddress?, subnetMask? }] }
- links: Array { id, sourceNodeId, targetNodeId }
- protocols: Array { id, type, enabled, settings }

CRITICAL RULES FOR "nodes" ARRAY:
1. **Multiple Interfaces**: If a node connects to 2 other devices, it MUST have 2 separate objects in its \`interfaces\` array.
   - Example Router: \`interfaces: [{name: "GigabitEthernet0/0", ipAddress: "192.168.1.1"}, {name: "GigabitEthernet0/1", ipAddress: "10.0.1.1"}]\`
   - Example Switch: \`interfaces: [{name: "GigabitEthernet1/0/1"}, {name: "GigabitEthernet1/0/2"}, {name: "Vlan1", ipAddress: "192.168.1.2"}]\`

2. **Interface Naming Standards**:
   - Routers: Start with 'GigabitEthernet0/0', increment to '0/1', '0/2'.
   - Switches: Physical ports 'GigabitEthernet1/0/1', '1/0/2'. Management 'Vlan1'.
   - Hosts: 'eth0'.

3. **IP Addressing & Subnet Logic**:
   - **Router-to-Router (WAN)**: MUST use **10.0.x.x/30** (Subnet Mask: 255.255.255.252).
   - **Router-to-Switch (LAN)**: MUST use **192.168.x.1/24** (Subnet Mask: 255.255.255.0).
   - **Switch Management**: Use **192.168.x.y/24** on 'Vlan1' only. Do NOT assign IPs to physical switch ports.
   - **Hosts**: Use **192.168.x.z/24** from the same subnet as their switch/gateway.
   - **Uniqueness**: Every IP must be unique.

4. **Connectivity & Routing**:
   - Routers connect distinct subnets.
   - Any logical connection implies a cable (Link object).

LAYOUT:
- Routers: y=100
- Switches: y=300
- Hosts: y=500
- Distribute x uniformly.

Return ONLY raw JSON. No markdown.
`;

export async function generateTopology(prompt: string) {
    const completion = await groq.chat.completions.create({
        messages: [
            { role: 'system', content: SYSTEM_PROMPT },
            { role: 'user', content: prompt }
        ],
        model: 'llama-3.3-70b-versatile',
        temperature: 0.1,
    });

    const content = completion.choices[0]?.message?.content || '';

    // Attempt to clean JSON if wrapped in markdown
    const jsonStr = content.replace(/```json\n?|```/g, '').trim();

    try {
        return JSON.parse(jsonStr);
    } catch (e) {
        console.error("Failed to parse AI response", content);
        throw new Error("AI generated invalid JSON");
    }
}
