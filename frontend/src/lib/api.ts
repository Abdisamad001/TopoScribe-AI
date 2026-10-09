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

export type Design = {
    id: string;
    name: string;
    topology: any;
    is_favourite: boolean;
    is_template: boolean;
    created_at: string;
    last_opened_at: string | null;
};

export async function listDesigns(): Promise<Design[]> {
    const response = await fetch(`${API_BASE_URL}/api/designs`);
    if (!response.ok) throw new Error('Failed to load designs');
    return response.json();
}

export async function createDesign(name: string, topology: any): Promise<Design> {
    const response = await fetch(`${API_BASE_URL}/api/designs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, topology })
    });
    if (!response.ok) throw new Error('Failed to save design');
    return response.json();
}

export async function updateDesign(id: string, updates: { name?: string; topology?: any }): Promise<Design> {
    const response = await fetch(`${API_BASE_URL}/api/designs/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    });
    if (!response.ok) throw new Error('Failed to update design');
    return response.json();
}

export async function openDesign(id: string): Promise<Design> {
    const response = await fetch(`${API_BASE_URL}/api/designs/${id}/open`, { method: 'PATCH' });
    if (!response.ok) throw new Error('Failed to open design');
    return response.json();
}

export async function toggleFavourite(id: string): Promise<Design> {
    const response = await fetch(`${API_BASE_URL}/api/designs/${id}/favourite`, { method: 'PATCH' });
    if (!response.ok) throw new Error('Failed to update favourite');
    return response.json();
}

export async function toggleTemplate(id: string): Promise<Design> {
    const response = await fetch(`${API_BASE_URL}/api/designs/${id}/template`, { method: 'PATCH' });
    if (!response.ok) throw new Error('Failed to update template');
    return response.json();
}

export async function deleteDesign(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/designs/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete design');
}
