'use client';

import { useEffect, useState } from 'react';
import { ShareNetworkIcon, StarIcon, TrashIcon, CopySimpleIcon } from '@phosphor-icons/react';
import type { Design } from '@/lib/api';
import { formatRelativeTime } from '@/lib/formatDate';

function UpdatedLabel({ iso }: { iso: string }) {
    const [label, setLabel] = useState('');
    useEffect(() => {
        setLabel(formatRelativeTime(iso));
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
            <div className="ui-empty">
                <div className="ui-empty__icon">
                    <Icon size={20} weight="regular" />
                </div>
                <p className="ui-empty__title">{emptyMessage}</p>
                <p className="ui-empty__text">{emptyDescription}</p>
            </div>
        );
    }

    return (
        <>
            <div className="ui-grid">
                {designs.map((design) => (
                    <button
                        key={design.id}
                        type="button"
                        onClick={() => onOpen(design.id)}
                        className="group ui-card ui-card--button design-card"
                    >
                        <div className="design-card__actions">
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
                                className="ui-icon-btn ui-icon-btn--danger ui-icon-btn--fade"
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
                                    className="ui-icon-btn"
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
                                className="ui-icon-btn"
                            >
                                <StarIcon
                                    size={13}
                                    weight={design.is_favourite ? 'fill' : 'regular'}
                                    className={design.is_favourite ? 'text-amber-400' : undefined}
                                />
                            </span>
                        </div>

                        <div className="ui-icon-box">
                            <ShareNetworkIcon size={16} weight="regular" />
                        </div>

                        <div className="design-card__meta">
                            <h3 className="truncate text-sm font-semibold text-white">{design.name}</h3>
                            <p className="mt-1 text-xs text-zinc-500">
                                <UpdatedLabel iso={design.last_opened_at ?? design.created_at} />
                            </p>
                        </div>
                    </button>
                ))}
            </div>

            {pendingDelete && (
                <div className="ui-backdrop" onClick={() => setPendingDelete(null)}>
                    <div className="ui-dialog" onClick={(e) => e.stopPropagation()}>
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
                                className="flex-1 rounded-lg border border-white/10 bg-white/5 p-2.5 text-sm font-medium text-zinc-300 hover:bg-white/10"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    onDelete(pendingDelete.id);
                                    setPendingDelete(null);
                                }}
                                className="flex-1 rounded-lg border border-red-500/20 bg-red-500/10 p-2.5 text-sm font-medium text-red-400 hover:bg-red-500/20 hover:text-red-300"
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
