export type DesignSummary = {
    id: string;
    name: string;
    updatedAt: string;
    favourited: boolean;
};

export function getPlaceholderDesigns(): DesignSummary[] {
    // TODO: replace with GET /designs once Supabase is wired
    return [
        { id: '1', name: 'Office Network', updatedAt: '2026-09-16T14:00:00.000Z', favourited: false },
        { id: '2', name: 'IT & OP Departments', updatedAt: '2026-09-15T09:30:00.000Z', favourited: true },
        { id: '3', name: 'Campus Backbone', updatedAt: '2026-09-12T18:45:00.000Z', favourited: false },
        { id: '4', name: 'Lab Topology', updatedAt: '2026-09-10T11:00:00.000Z', favourited: false },
    ];
}
