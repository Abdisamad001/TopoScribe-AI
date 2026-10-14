const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

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

/** Run canvas topology through metadata. */
export async function configureTopology(topology: any, designPlan: Record<string, unknown> = {}) {
    const response = await fetch(`${API_BASE_URL}/api/topology/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topology, design_plan: designPlan }),
    });
    if (!response.ok) throw new Error('Topology configure failed');
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

// --- Projects (folder of design ids) ---

export type Project = {
    id: string;
    name: string;
    design_ids: string[];
    created_at: string;
};

export async function listProjects(): Promise<Project[]> {
    const response = await fetch(`${API_BASE_URL}/api/projects`);
    if (!response.ok) throw new Error('Failed to load projects');
    return response.json();
}

export async function createProject(name: string): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
    });
    if (!response.ok) throw new Error('Failed to create project');
    return response.json();
}

export async function updateProject(
    id: string,
    updates: { name?: string; design_ids?: string[] },
): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/api/projects/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update project');
    return response.json();
}

export async function deleteProject(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/projects/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete project');
}

// --- Reports (saved export markdown) ---

export type SavedReport = {
    id: string;
    name: string;
    markdown: string;
    design_id: string | null;
    created_at: string;
};

export async function listReports(): Promise<SavedReport[]> {
    const response = await fetch(`${API_BASE_URL}/api/reports`);
    if (!response.ok) throw new Error('Failed to load reports');
    return response.json();
}

export async function createReport(
    name: string,
    markdown: string,
    designId?: string | null,
): Promise<SavedReport> {
    const response = await fetch(`${API_BASE_URL}/api/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, markdown, design_id: designId ?? null }),
    });
    if (!response.ok) throw new Error('Failed to save report');
    return response.json();
}

export async function deleteReport(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/reports/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete report');
}

// --- Chats (saved assistant threads) ---

export type ChatMessage = { role: 'user' | 'assistant'; content: string };

export type SavedChat = {
    id: string;
    title: string;
    messages: ChatMessage[];
    design_id: string | null;
    design_name: string | null;
    created_at: string;
    updated_at: string;
};

export async function listChats(): Promise<SavedChat[]> {
    const response = await fetch(`${API_BASE_URL}/api/chats`);
    if (!response.ok) throw new Error('Failed to load chats');
    return response.json();
}

export async function createChat(input: {
    title: string;
    messages: ChatMessage[];
    design_id?: string | null;
    design_name?: string | null;
}): Promise<SavedChat> {
    const response = await fetch(`${API_BASE_URL}/api/chats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
    });
    if (!response.ok) throw new Error('Failed to save chat');
    return response.json();
}

export async function updateChat(
    id: string,
    updates: {
        title?: string;
        messages?: ChatMessage[];
        design_id?: string | null;
        design_name?: string | null;
    },
): Promise<SavedChat> {
    const response = await fetch(`${API_BASE_URL}/api/chats/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update chat');
    return response.json();
}

export async function deleteChat(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/chats/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete chat');
}
