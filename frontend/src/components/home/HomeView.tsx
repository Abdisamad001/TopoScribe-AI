'use client';

import { useMemo, useState } from 'react';
import { PlusIcon, ShareNetworkIcon, GlobeIcon, DesktopIcon, NoteIcon, StarIcon, CaretDownIcon } from '@phosphor-icons/react';
import type { Design } from '@/lib/api';
import DesignCardGrid from './DesignCardGrid';

const LIBRARY_CARDS = [
    { title: 'Router', subtitle: 'L3 Networking', Icon: GlobeIcon, chipClass: 'bg-teal-500/20 text-teal-300' },
    { title: 'Switch', subtitle: 'L2 Switching', Icon: ShareNetworkIcon, chipClass: 'bg-blue-500/20 text-blue-300' },
    { title: 'Notes', subtitle: 'Annotation', Icon: NoteIcon, chipClass: 'bg-violet-500/20 text-violet-300' },
    { title: 'End Device', subtitle: 'Workstation / Server', Icon: DesktopIcon, chipClass: 'bg-amber-500/20 text-amber-300' },
];

type SortMode = 'az' | 'za';

export default function HomeView({
    designs,
    onCreate,
    onOpen,
    onToggleFavourite,
    onToggleTemplate,
    onDelete,
    onOpenFavourites,
    searchQuery = '',
}: {
    designs: Design[];
    onCreate: () => void;
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
    onToggleTemplate: (id: string) => void;
    onDelete: (id: string) => void;
    onOpenFavourites: () => void;
    searchQuery?: string;
}) {
    const [sortMode, setSortMode] = useState<SortMode>('az');

    const query = searchQuery.trim().toLowerCase();
    const filtered = useMemo(() => {
        const list = query
            ? designs.filter((design) => design.name.toLowerCase().includes(query))
            : [...designs];

        list.sort((a, b) => {
            const cmp = a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
            return sortMode === 'az' ? cmp : -cmp;
        });
        return list;
    }, [designs, query, sortMode]);

    return (
        <div className="app-page">
            <div className="app-page__inner app-page__inner--home">
                <section className="home-hero">
                    <div className="home-hero__icon">
                        <ShareNetworkIcon size={18} weight="regular" />
                    </div>
                    <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">Create a network design</h2>
                    <p className="mt-1.5 max-w-md text-sm text-zinc-500">
                        Design a topology manually or generate one with AI.
                    </p>
                    <button type="button" onClick={onCreate} className="ui-btn-primary mt-4 px-4">
                        <PlusIcon size={16} weight="regular" />
                        Create design
                    </button>
                </section>

                <section>
                    <div className="home-section-bar">
                        <div className="flex items-center gap-1">
                            <h3 className="app-page__title">Your designs</h3>
                            <button
                                type="button"
                                onClick={onOpenFavourites}
                                className="ml-2 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
                            >
                                <StarIcon size={13} weight="regular" />
                                Favorites
                            </button>
                        </div>
                        <button
                            type="button"
                            onClick={() => setSortMode((mode) => (mode === 'az' ? 'za' : 'az'))}
                            title="Toggle A–Z / Z–A"
                            className="inline-flex items-center gap-1 rounded-md border border-white/10 px-2.5 py-1 text-xs text-zinc-300 hover:bg-white/5 hover:text-white"
                        >
                            Sort {sortMode === 'az' ? 'A–Z' : 'Z–A'}
                            <CaretDownIcon size={12} weight="regular" />
                        </button>
                    </div>
                    <DesignCardGrid
                        designs={filtered}
                        emptyMessage={query ? 'No matching designs' : 'No designs yet'}
                        emptyDescription={
                            query
                                ? `No saved designs match “${searchQuery.trim()}”.`
                                : 'Create your first network design to get started.'
                        }
                        emptyIcon="network"
                        onOpen={onOpen}
                        onToggleFavourite={onToggleFavourite}
                        onToggleTemplate={onToggleTemplate}
                        onDelete={onDelete}
                    />
                </section>

                <section>
                    <div className="mb-4">
                        <h3 className="app-page__title">Component library</h3>
                        <p className="app-page__subtitle">
                            Open a design and drag components onto the canvas.
                        </p>
                    </div>
                    <div className="ui-grid">
                        {LIBRARY_CARDS.map(({ title, subtitle, Icon, chipClass }) => (
                            <div key={title} className="library-card">
                                <div className={`library-card__chip ${chipClass}`}>
                                    <Icon size={16} weight="regular" />
                                </div>
                                <div className="min-w-0">
                                    <p className="truncate text-sm font-medium text-zinc-100">{title}</p>
                                    <p className="truncate text-[11px] text-zinc-500">{subtitle}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            </div>
        </div>
    );
}
