const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function generateDesign(description: string, history: any[] = []) {
    const response = await fetch(`${API_BASE_URL}/api/design/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, conversation_history: history })
    });
    if (!response.ok) throw new Error('Design generation failed');
    return response.json();
}

export async function clarifyRequirements(description: string, history: any[]) {
    const response = await fetch(`${API_BASE_URL}/api/design/clarify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, conversation_history: history })
    });
    if (!response.ok) throw new Error('Clarification failed');
    return response.json();
}

export async function simulateNetwork(topology: any, source: string, target: string) {
    const response = await fetch(`${API_BASE_URL}/api/simulate/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topology, source, target })
    });
    if (!response.ok) throw new Error('Simulation failed');
    return response.json();
}
