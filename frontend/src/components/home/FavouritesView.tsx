'use client';

import type { Design } from '@/lib/api';
import DesignCardGrid from './DesignCardGrid';

export default function FavouritesView({
    designs,
    onOpen,
    onToggleFavourite,
    onDelete,
    searchQuery = '',
}: {
    designs: Design[];
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
    onDelete: (id: string) => void;
    searchQuery?: string;
}) {
    const favourites = designs.filter((design) => design.is_favourite);
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
        ? favourites.filter((design) => design.name.toLowerCase().includes(query))
        : favourites;

    return (
        <div className="h-full overflow-y-auto bg-[#0a0a0a] font-sans">
            <div className="mx-auto flex min-h-full max-w-5xl flex-col px-6 py-8">
                <h2 className="mb-4 border-b border-white/10 pb-3 text-base font-semibold text-white">Favorites</h2>
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
                    onDelete={onDelete}
                />
            </div>
        </div>
    );
}
