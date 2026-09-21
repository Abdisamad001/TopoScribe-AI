'use client';

import { PlusIcon, ShareNetworkIcon } from '@phosphor-icons/react';
import type { Design } from '@/lib/api';
import DesignCardGrid from './DesignCardGrid';

function CreateButton({ onCreate }: { onCreate: () => void }) {
    return (
        <button
            type="button"
            onClick={onCreate}
            className="inline-flex items-center gap-2 rounded-full bg-chrome-navy px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-chrome-navy-hover"
        >
            <PlusIcon size={16} weight="regular" />
            Create
        </button>
    );
}

export default function HomeView({
    designs,
    onCreate,
    onOpen,
    onToggleFavourite,
    onDelete,
}: {
    designs: Design[];
    onCreate: () => void;
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    const isEmpty = designs.length === 0;

    return (
        <div className="h-full overflow-y-auto bg-chrome-surface font-sans">
            <div className="mx-auto flex min-h-full max-w-5xl flex-col px-6 py-8">
                {isEmpty ? (
                    <div className="flex flex-1 flex-col items-center justify-center text-center">
                        <div className="rounded-lg bg-chrome-navy/30 p-2.5">
                            <ShareNetworkIcon size={48} weight="regular" className="text-chrome-navy" />
                        </div>
                        <div className="mt-4 space-y-1">
                            <h2 className="text-lg font-semibold text-white">No designs yet</h2>
                            <p className="max-w-[280px] text-sm text-slate-400">
                                Create your first network design to get started.
                            </p>
                        </div>
                        <div className="mt-6">
                            <CreateButton onCreate={onCreate} />
                        </div>
                    </div>
                ) : (
                    <>
                        <div className="mb-6 flex items-center justify-between">
                            <h2 className="text-xl font-semibold text-white">Your designs</h2>
                            <CreateButton onCreate={onCreate} />
                        </div>
                        <DesignCardGrid
                            designs={designs}
                            emptyMessage="No designs yet"
                            emptyDescription="Create your first network design to get started."
                            emptyIcon="network"
                            onOpen={onOpen}
                            onToggleFavourite={onToggleFavourite}
                            onDelete={onDelete}
                        />
                    </>
                )}
            </div>
        </div>
    );
}
