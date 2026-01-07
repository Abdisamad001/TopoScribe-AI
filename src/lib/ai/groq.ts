import { Groq } from 'groq-sdk';
import { NetworkNode, Link, ProtocolConfig } from '@/types/network';

// You must set GROQ_API_KEY in your .env.local file
const groq = new Groq({
    apiKey: process.env.GROQ_API_KEY || 'REMOVED_KEY' // Fallback for demo only
});

const SYSTEM_PROMPT = `
You are a Network Design Architect. Your job is to convert natural language requirements into a structured JSON network topology.

Output Format: A single JSON object with 'nodes', 'links', and 'protocols'.
- nodes: Array of objects { id, type, name, x, y, interfaces: [{ id, name, ipAddress?, subnetMask? }] }
- links: Array of objects { id, sourceNodeId, targetNodeId }
- protocols: Array of objects { id, type, enabled, settings }

Node Types: 'router', 'switch', 'host'
Protocol Types: 'ospf', 'static', 'vlan'

Rules:
- Assign reasonable IP addresses (e.g., 192.168.x.x, 10.x.x.x).
- CRITICAL: Ensure EVERY node has a UNIQUE IP address. Never assign the same IP to two devices.
- Ensure valid subnet masks.
- Layout nodes (x, y) logically:
  - Routers at top (y: 100)
  - Switches in middle (y: 300)
  - Hosts at bottom (y: 500)
  - Spread x values to avoid overlap.
- Connect devices logically (Host -> Switch -> Router).
- Start node IDs with 'node-', link IDs with 'link-'.
- Return ONLY the JSON. No markdown backticks, no explanation.
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
