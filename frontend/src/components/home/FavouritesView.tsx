'use client';

import type { Design } from '@/lib/api';
import DesignCardGrid from './DesignCardGrid';

export default function FavouritesView({
    designs,
    onOpen,
    onToggleFavourite,
    onDelete,
}: {
    designs: Design[];
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    return (
        <div className="h-full overflow-y-auto bg-chrome-surface font-sans">
            <div className="mx-auto max-w-5xl px-6 py-8">
                <DesignCardGrid
                    designs={designs.filter((design) => design.is_favourite)}
                    emptyMessage="No favourites yet"
                    onOpen={onOpen}
                    onToggleFavourite={onToggleFavourite}
                    onDelete={onDelete}
                />
            </div>
        </div>
    );
}
