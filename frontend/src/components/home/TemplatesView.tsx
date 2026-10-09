'use client';

import type { Design } from '@/lib/api';
import DesignCardGrid from './DesignCardGrid';

export default function TemplatesView({
    designs,
    onOpen,
    onToggleFavourite,
    onToggleTemplate,
    onDelete,
    searchQuery = '',
}: {
    designs: Design[];
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
    onToggleTemplate: (id: string) => void;
    onDelete: (id: string) => void;
    searchQuery?: string;
}) {
    const templates = designs.filter((design) => design.is_template);
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
        ? templates.filter((design) => design.name.toLowerCase().includes(query))
        : templates;

    return (
        <div className="h-full overflow-y-auto bg-[#0a0a0a] font-sans">
            <div className="mx-auto flex min-h-full max-w-5xl flex-col px-6 py-8">
                <div className="mb-4 border-b border-white/10 pb-3">
                    <h2 className="text-base font-semibold text-white">Templates</h2>
                    <p className="mt-1 text-xs text-zinc-500">
                        Saved designs marked as templates. Open one to start a new design from that layout.
                    </p>
                </div>
                <DesignCardGrid
                    designs={filtered}
                    emptyMessage={query ? 'No matching templates' : 'No templates yet'}
                    emptyDescription={
                        query
                            ? `No templates match “${searchQuery.trim()}”.`
                            : 'On Home, click the copy icon on a design card to save it as a template.'
                    }
                    emptyIcon="network"
                    removeAs="template"
                    onOpen={onOpen}
                    onToggleFavourite={onToggleFavourite}
                    onToggleTemplate={onToggleTemplate}
                    onDelete={onDelete}
                />
            </div>
        </div>
    );
}
