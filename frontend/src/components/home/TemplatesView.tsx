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
        <div className="app-page">
            <div className="app-page__inner">
                <div className="app-page__header">
                    <h2 className="app-page__title">Templates</h2>
                    <p className="app-page__subtitle">
                        Saved designs marked as templates. Open one to start a new design from that layout.
                    </p>
                </div>

                {filtered.length === 0 ? (
                    <div className="ui-empty">
                        <img src="/no-template-yet.svg" alt="" className="ui-empty__art" />
                        <p className="ui-empty__title">
                            {query ? 'No matching templates' : 'No templates yet'}
                        </p>
                        <p className="ui-empty__text">
                            On Home, use the copy icon on a design to save it as a template.
                        </p>
                    </div>
                ) : (
                    <DesignCardGrid
                        designs={filtered}
                        emptyMessage="No templates yet"
                        emptyDescription=""
                        removeAs="template"
                        onOpen={onOpen}
                        onToggleFavourite={onToggleFavourite}
                        onToggleTemplate={onToggleTemplate}
                        onDelete={onDelete}
                    />
                )}
            </div>
        </div>
    );
}
