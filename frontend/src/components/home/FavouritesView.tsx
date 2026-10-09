'use client';

import type { Design } from '@/lib/api';
import DesignCardGrid from './DesignCardGrid';

export default function FavouritesView({
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
    onToggleTemplate?: (id: string) => void;
    onDelete: (id: string) => void;
    searchQuery?: string;
}) {
    const favourites = designs.filter((design) => design.is_favourite);
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
        ? favourites.filter((design) => design.name.toLowerCase().includes(query))
        : favourites;

    return (
        <div className="app-page">
            <div className="app-page__inner">
                <div className="app-page__header">
                    <h2 className="app-page__title">Favorites</h2>
                </div>
                <DesignCardGrid
                    designs={filtered}
                    emptyMessage={query ? 'No matching favorites' : 'No favourites yet'}
                    emptyDescription={
                        query
                            ? `No favorite designs match “${searchQuery.trim()}”.`
                            : 'Star a design from Home to see it here.'
                    }
                    emptyIcon="star"
                    onOpen={onOpen}
                    onToggleFavourite={onToggleFavourite}
                    onToggleTemplate={onToggleTemplate}
                    onDelete={onDelete}
                />
            </div>
        </div>
    );
}
