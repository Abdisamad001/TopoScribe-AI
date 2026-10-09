'use client';

import { useEffect, useState } from 'react';
import { ShareNetworkIcon, StarIcon, TrashIcon, CopySimpleIcon } from '@phosphor-icons/react';
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

function UpdatedLabel({ iso }: { iso: string }) {
    const [label, setLabel] = useState('');
    useEffect(() => {
        setLabel(formatUpdatedAt(iso));
    }, [iso]);
    if (!label) return <span className="invisible">Updated</span>;
    return <>Updated {label}</>;
}

export default function DesignCardGrid({
    designs,
    emptyMessage,
    emptyDescription,
    emptyIcon = 'network',
    removeAs = 'design',
    onOpen,
    onToggleFavourite,
    onToggleTemplate,
    onDelete,
}: {
    designs: Design[];
    emptyMessage: string;
    emptyDescription: string;
    emptyIcon?: 'network' | 'star';
    removeAs?: 'design' | 'template';
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
    onToggleTemplate?: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    const [pendingDelete, setPendingDelete] = useState<Design | null>(null);
    const removingTemplate = removeAs === 'template';

    if (designs.length === 0) {
        const Icon = emptyIcon === 'star' ? StarIcon : ShareNetworkIcon;
        return (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 px-6 py-12 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-[#141414]">
                    <Icon size={20} weight="regular" className="text-zinc-400" />
                </div>
                <div className="mt-3 space-y-1">
                    <p className="text-sm font-semibold text-white">{emptyMessage}</p>
                    <p className="max-w-[260px] text-xs text-zinc-500">{emptyDescription}</p>
                </div>
            </div>
        );
    }

    return (
        <>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {designs.map((design) => (
                <button
                    key={design.id}
                    type="button"
                    onClick={() => onOpen(design.id)}
                    className="group relative flex min-h-[148px] flex-col justify-between rounded-xl border border-white/10 bg-[#141414] p-4 text-left transition-colors hover:border-white/20 hover:bg-[#1a1a1a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20"
                >
                    <div className="absolute top-2.5 right-2.5 z-10 flex items-center">
                        <span
                            role="button"
                            tabIndex={0}
                            aria-label={removingTemplate ? 'Remove from templates' : 'Delete design'}
                            title={removingTemplate ? 'Remove from templates' : 'Delete design'}
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
                            className="inline-flex min-h-7 min-w-7 items-center justify-center rounded-md p-1 text-zinc-500 opacity-0 transition-opacity hover:bg-white/10 hover:text-red-400 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100"
                        >
                            <TrashIcon size={13} weight="regular" />
                        </span>
                        {onToggleTemplate && (
                            <span
                                role="button"
                                tabIndex={0}
                                aria-label={design.is_template ? 'Remove template' : 'Save as template'}
                                aria-pressed={design.is_template}
                                title={design.is_template ? 'Remove template' : 'Save as template'}
                                onClick={(event) => {
                                    event.stopPropagation();
                                    onToggleTemplate(design.id);
                                }}
                                onKeyDown={(event) => {
                                    if (event.key !== 'Enter' && event.key !== ' ') return;
                                    event.preventDefault();
                                    event.stopPropagation();
                                    onToggleTemplate(design.id);
                                }}
                                className="inline-flex min-h-7 min-w-7 items-center justify-center rounded-md p-1 text-zinc-500 hover:bg-white/10 hover:text-white"
                            >
                                <CopySimpleIcon
                                    size={13}
                                    weight={design.is_template ? 'fill' : 'regular'}
                                    className={design.is_template ? 'text-teal-400' : undefined}
                                />
                            </span>
                        )}
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
                            className="inline-flex min-h-7 min-w-7 items-center justify-center rounded-md p-1 text-zinc-500 hover:bg-white/10 hover:text-white"
                        >
                            <StarIcon
                                size={13}
                                weight={design.is_favourite ? 'fill' : 'regular'}
                                className={design.is_favourite ? 'text-amber-400' : undefined}
                            />
                        </span>
                    </div>

                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#0a0a0a] ring-1 ring-white/10">
                        <ShareNetworkIcon size={16} weight="regular" className="text-zinc-200" />
                    </div>

                    <div className="mt-8 min-w-0 pr-6">
                        <div className="flex items-center gap-1.5">
                            <h3 className="truncate text-sm font-semibold text-white">{design.name}</h3>
                            {design.is_template && (
                                <span className="shrink-0 rounded border border-teal-500/30 px-1.5 py-0.5 text-[10px] text-teal-400">
                                    Template
                                </span>
                            )}
                        </div>
                        <p className="mt-1 text-xs text-zinc-500">
                            <UpdatedLabel iso={design.last_opened_at ?? design.created_at} />
                        </p>
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
                    className="mx-4 w-full max-w-sm rounded-xl border border-white/10 bg-[#111] p-6 shadow-2xl"
                    onClick={(e) => e.stopPropagation()}
                >
                    <h3 className="text-lg font-semibold tracking-tight text-white">
                        {removingTemplate ? 'Remove from Templates?' : 'Delete Design?'}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-zinc-400">
                        {removingTemplate
                            ? <>Remove &quot;{pendingDelete.name}&quot; from templates? Your saved design on Home stays.</>
                            : <>Are you sure you want to delete &quot;{pendingDelete.name}&quot;? This action cannot be undone.</>}
                    </p>
                    <div className="mt-6 flex gap-3">
                        <button
                            type="button"
                            onClick={() => setPendingDelete(null)}
                            className="flex-1 rounded-lg border border-white/10 bg-white/5 p-2.5 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10"
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                onDelete(pendingDelete.id);
                                setPendingDelete(null);
                            }}
                            className="flex-1 rounded-lg border border-red-500/20 bg-red-500/10 p-2.5 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/20 hover:text-red-300"
                        >
                            {removingTemplate ? 'Remove' : 'Delete'}
                        </button>
                    </div>
                </div>
            </div>
        )}
        </>
    );
}
