'use client';

import { useState } from 'react';
import { ShareNetworkIcon, StarIcon, TrashIcon } from '@phosphor-icons/react';
import type { Design } from '@/lib/api';

function formatUpdatedAt(iso: string): string {
    const deltaSec = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
    const abs = Math.abs(deltaSec);
    const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
    if (abs < 60) return rtf.format(Math.round(deltaSec), 'second');
    if (abs < 3600) return rtf.format(Math.round(deltaSec / 60), 'minute');
    if (abs < 86400) return rtf.format(Math.round(deltaSec / 3600), 'hour');
    if (abs < 86400 * 30) return rtf.format(Math.round(deltaSec / 86400), 'day');
    return rtf.format(Math.round(deltaSec / (86400 * 30)), 'month');
}

export default function DesignCardGrid({
    designs,
    emptyMessage,
    onOpen,
    onToggleFavourite,
    onDelete,
}: {
    designs: Design[];
    emptyMessage: string;
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    const [pendingDelete, setPendingDelete] = useState<Design | null>(null);

    if (designs.length === 0) {
        return <p className="text-sm text-slate-400">{emptyMessage}</p>;
    }

    return (
        <>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
            {designs.map((design) => (
                <button
                    key={design.id}
                    type="button"
                    onClick={() => onOpen(design.id)}
                    className="group relative min-h-[160px] rounded-xl border border-white/10 bg-chrome-elevated p-5 text-left transition-colors hover:border-chrome-navy/40 hover:bg-white/[0.03]"
                >
                    <span
                        role="button"
                        tabIndex={0}
                        aria-label="Delete design"
                        onClick={(event) => {
                            event.stopPropagation();
                            setPendingDelete(design);
                        }}
                        onKeyDown={(event) => {
                            if (event.key !== 'Enter' && event.key !== ' ') return;
                            event.preventDefault();
                            event.stopPropagation();
                            setPendingDelete(design);
                        }}
                        className="absolute top-4 right-12 rounded-lg p-1.5 text-slate-400 opacity-0 transition-opacity hover:bg-white/10 hover:text-red-400 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100"
                    >
                        <TrashIcon size={16} weight="regular" />
                    </span>
                    <span
                        role="button"
                        tabIndex={0}
                        aria-label={design.is_favourite ? 'Remove from favourites' : 'Add to favourites'}
                        aria-pressed={design.is_favourite}
                        onClick={(event) => {
                            event.stopPropagation();
                            onToggleFavourite(design.id);
                        }}
                        onKeyDown={(event) => {
                            if (event.key !== 'Enter' && event.key !== ' ') return;
                            event.preventDefault();
                            event.stopPropagation();
                            onToggleFavourite(design.id);
                        }}
                        className="absolute top-4 right-4 rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
                    >
                        <StarIcon
                            size={16}
                            weight={design.is_favourite ? 'fill' : 'regular'}
                            className={design.is_favourite ? 'text-chrome-navy' : undefined}
                        />
                    </span>
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chrome-navy">
                        <ShareNetworkIcon size={20} weight="regular" className="text-white" />
                    </div>
                    <h3 className="mt-4 truncate pr-16 text-base font-semibold text-white">{design.name}</h3>
                    <p className="mt-1 text-xs text-slate-400">{formatUpdatedAt(design.last_opened_at ?? design.created_at)}</p>
                </button>
            ))}
        </div>

        {pendingDelete && (
            <div
                className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
                onClick={() => setPendingDelete(null)}
            >
                <div
                    className="mx-4 w-full max-w-sm rounded-xl border border-red-500/20 bg-[#1C2F45] p-6 shadow-[0_8px_32px_rgba(0,0,0,0.4)] animate-in fade-in slide-in-from-top-2 duration-300"
                    onClick={(e) => e.stopPropagation()}
                >
                    <h3 className="text-lg font-semibold text-white tracking-tight">Delete Design?</h3>
                    <p className="mt-2 text-sm text-slate-400 leading-relaxed">
                        Are you sure you want to delete &quot;{pendingDelete.name}&quot;? This action cannot be undone.
                    </p>
                    <div className="mt-6 flex gap-3">
                        <button
                            type="button"
                            onClick={() => setPendingDelete(null)}
                            className="flex-1 bg-[#142338] hover:bg-slate-700/50 border border-white/10 text-slate-300 p-2.5 rounded-lg transition-all text-sm font-semibold"
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                onDelete(pendingDelete.id);
                                setPendingDelete(null);
                            }}
                            className="flex-1 text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 p-2.5 rounded-lg transition-all text-sm font-semibold"
                        >
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        )}
        </>
    );
}
