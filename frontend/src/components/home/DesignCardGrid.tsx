'use client';

import { ShareNetworkIcon, StarIcon } from '@phosphor-icons/react';
import type { DesignSummary } from '@/lib/designs';

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
}: {
    designs: DesignSummary[];
    emptyMessage: string;
    onOpen: (id: string) => void;
    onToggleFavourite: (id: string) => void;
}) {
    if (designs.length === 0) {
        return <p className="text-sm text-slate-400">{emptyMessage}</p>;
    }

    return (
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
                        aria-label={design.favourited ? 'Remove from favourites' : 'Add to favourites'}
                        aria-pressed={design.favourited}
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
                            weight={design.favourited ? 'fill' : 'regular'}
                            className={design.favourited ? 'text-chrome-navy' : undefined}
                        />
                    </span>
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chrome-navy">
                        <ShareNetworkIcon size={20} weight="regular" className="text-white" />
                    </div>
                    <h3 className="mt-4 truncate pr-8 text-base font-semibold text-white">{design.name}</h3>
                    <p className="mt-1 text-xs text-slate-400">{formatUpdatedAt(design.updatedAt)}</p>
                </button>
            ))}
        </div>
    );
}
