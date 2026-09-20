'use client';

import type { DesignSummary } from '@/lib/designs';
import DesignCardGrid from './DesignCardGrid';

export default function FavouritesView({
    designs,
    onOpen,
    onToggleFavourite,
}: {
    designs: DesignSummary[];
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
}) {
    return (
        <div className="h-full overflow-y-auto bg-chrome-surface font-sans">
            <div className="mx-auto max-w-5xl px-6 py-8">
                <DesignCardGrid
                    designs={designs.filter((design) => design.favourited)}
                    emptyMessage="No favourites yet"
                    onOpen={onOpen}
                    onToggleFavourite={onToggleFavourite}
                />
            </div>
        </div>
    );
}
