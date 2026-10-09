'use client';

import { useState } from 'react';
import { FileTextIcon, TrashIcon } from '@phosphor-icons/react';
import type { SavedReport } from '@/lib/api';
import ReportModal from '@/components/topology/ReportModal';
import { formatDateTime } from '@/lib/formatDate';

export default function ReportsView({
    reports,
    onDelete,
    searchQuery = '',
}: {
    reports: SavedReport[];
    onDelete: (id: string) => void;
    searchQuery?: string;
}) {
    const [open, setOpen] = useState<SavedReport | null>(null);
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
        ? reports.filter((report) => report.name.toLowerCase().includes(query))
        : reports;

    return (
        <div className="app-page">
            <div className="app-page__inner">
                <div className="app-page__header">
                    <h2 className="app-page__title">Reports</h2>
                    <p className="app-page__subtitle">
                        Reports saved when you download from Export report on the canvas.
                    </p>
                </div>

                {filtered.length === 0 ? (
                    <div className="ui-empty">
                        <FileTextIcon size={20} weight="regular" className="text-zinc-400" />
                        <p className="ui-empty__title">
                            {query ? 'No matching reports' : 'No reports yet'}
                        </p>
                        <p className="ui-empty__text">
                            Open a design, click Export report, then Download — it is saved here automatically.
                        </p>
                    </div>
                ) : (
                    <div className="ui-grid ui-grid--3">
                        {filtered.map((report) => (
                            <button
                                key={report.id}
                                type="button"
                                onClick={() => setOpen(report)}
                                className="group ui-card ui-card--button"
                            >
                                <span
                                    role="button"
                                    tabIndex={0}
                                    aria-label="Delete report"
                                    title="Delete report (design stays)"
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        onDelete(report.id);
                                    }}
                                    onKeyDown={(event) => {
                                        if (event.key !== 'Enter' && event.key !== ' ') return;
                                        event.preventDefault();
                                        event.stopPropagation();
                                        onDelete(report.id);
                                    }}
                                    className="absolute top-2.5 right-2.5 ui-icon-btn ui-icon-btn--danger ui-icon-btn--fade"
                                >
                                    <TrashIcon size={13} weight="regular" />
                                </span>
                                <div className="ui-icon-box">
                                    <FileTextIcon size={16} weight="regular" />
                                </div>
                                <div className="mt-6 min-w-0 pr-6">
                                    <h3 className="truncate text-sm font-semibold text-white">{report.name}</h3>
                                    <p className="mt-1 text-xs text-zinc-500">{formatDateTime(report.created_at)}</p>
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <ReportModal
                isOpen={Boolean(open)}
                onClose={() => setOpen(null)}
                reportName={open?.name}
                markdown={open?.markdown}
            />
        </div>
    );
}
