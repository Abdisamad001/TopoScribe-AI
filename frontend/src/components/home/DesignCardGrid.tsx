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
    emptyDescription,
    emptyIcon = 'network',
    onOpen,
    onToggleFavourite,
    onDelete,
}: {
    designs: Design[];
    emptyMessage: string;
    emptyDescription: string;
    emptyIcon?: 'network' | 'star';
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    const [pendingDelete, setPendingDelete] = useState<Design | null>(null);

    if (designs.length === 0) {
        const Icon = emptyIcon === 'star' ? StarIcon : ShareNetworkIcon;
        return (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
                <div className="rounded-lg bg-chrome-navy/30 p-2.5">
                    <Icon size={48} weight="regular" className="text-chrome-navy" />
                </div>
                <div className="mt-4 space-y-1">
                    <p className="text-lg font-semibold text-white">{emptyMessage}</p>
                    <p className="max-w-[280px] text-sm text-slate-400">{emptyDescription}</p>
                </div>
            </div>
        );
    }

    return (
        <>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-6">
            {designs.map((design) => (
                <button
                    key={design.id}
                    type="button"
                    onClick={() => onOpen(design.id)}
                    className="group relative flex min-h-[200px] flex-col overflow-hidden rounded-2xl border border-white/10 bg-chrome-elevated text-left transition-all hover:-translate-y-1 hover:border-white/25 hover:bg-[#292931] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-chrome-navy/40"
                >
                    <div className="absolute top-3 right-3 z-10 flex items-center">
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
                            className="inline-flex min-h-9 min-w-9 items-center justify-center rounded-lg p-2.5 text-slate-400 opacity-0 transition-opacity hover:bg-white/10 hover:text-red-400 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100"
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
                            className="inline-flex min-h-9 min-w-9 items-center justify-center rounded-lg p-2.5 text-slate-400 hover:bg-white/10 hover:text-white"
                        >
                            <StarIcon
                                size={16}
                                weight={design.is_favourite ? 'fill' : 'regular'}
                                className={design.is_favourite ? 'text-chrome-navy' : undefined}
                            />
                        </span>
                    </div>
                    <div className="relative min-h-[120px] flex-1 overflow-hidden bg-[#10131c]">
                        <img
                            src="/cards-thumbnail.svg"
                            alt=""
                            aria-hidden="true"
                            className="pointer-events-none absolute inset-3 h-[calc(100%-1.5rem)] w-[calc(100%-1.5rem)] object-contain object-center"
                        />
                    </div>
                    <div className="px-5 py-4">
                        <h3 className="truncate text-base font-semibold text-white">{design.name}</h3>
                        <p className="mt-1 text-sm text-slate-300">{formatUpdatedAt(design.last_opened_at ?? design.created_at)}</p>
                    </div>
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
