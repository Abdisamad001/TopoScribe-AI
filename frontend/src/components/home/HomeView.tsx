'use client';

import { PlusIcon } from '@phosphor-icons/react';
import type { DesignSummary } from '@/lib/designs';
import DesignCardGrid from './DesignCardGrid';

export default function HomeView({
    designs,
    onCreate,
    onOpen,
    onToggleFavourite,
}: {
    designs: DesignSummary[];
    onCreate: () => void;
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
}) {
    return (
        <div className="h-full overflow-y-auto bg-chrome-surface font-sans">
            <div className="mx-auto max-w-5xl px-6 py-8">
                <div className="flex flex-col items-center py-16 text-center">
                    <h2 className="text-2xl font-bold text-white">Create a network design</h2>
                    <p className="mt-2 text-sm text-slate-400">
                        Design a topology manually or generate one with AI
                    </p>
                    <button
                        type="button"
                        onClick={onCreate}
                        className="mt-6 inline-flex items-center gap-2 rounded-full bg-chrome-navy px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-chrome-navy-hover"
                    >
                        <PlusIcon size={16} weight="regular" />
                        Create
                    </button>
                </div>
                <DesignCardGrid
                    designs={designs}
                    emptyMessage="No designs yet"
                    onOpen={onOpen}
                    onToggleFavourite={onToggleFavourite}
                />
            </div>
        </div>
    );
}
