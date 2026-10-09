'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Download, X, FileText } from 'lucide-react';
import type { NetworkNode, Link, ProtocolConfig, TopologyMetadata, GenerationRuntime } from '@/types/network';
import { generateMarkdownReport } from '@/lib/generator/report';
import { downloadTextFile } from '@/lib/downloadTextFile';
import { copyTextToClipboard, stripMarkdown } from '@/lib/reportUtils';
import CiscoTerminal from './CiscoTerminal';

interface ReportModalProps {
    isOpen: boolean;
    onClose: () => void;
    /** When set, Download also stores the report under Sidebar → Reports. */
    onSaveReport?: (name: string, markdown: string) => void;
    /** Canvas mode: generate markdown from the live topology. */
    topology?: {
        nodes: NetworkNode[];
        links: Link[];
        protocols: ProtocolConfig[];
        name: string;
        id: string;
        version: number;
        lastUpdated: string;
        metadata?: TopologyMetadata;
        runtime?: GenerationRuntime;
    };
    /** Saved-report mode: show this markdown as-is. */
    markdown?: string;
    reportName?: string;
}

export default function ReportModal({
    isOpen,
    onClose,
    topology,
    onSaveReport,
    markdown,
    reportName,
}: ReportModalProps) {
    const [report, setReport] = useState('');
    const displayName = reportName || topology?.name || 'Report';

    React.useEffect(() => {
        if (!isOpen) return;
        if (markdown != null) {
            setReport(markdown);
            return;
        }
        if (topology) {
            setReport(generateMarkdownReport(topology));
        }
    }, [isOpen, topology, markdown]);

    if (!isOpen) return null;

    const handleCopy = async () => {
        const ok = await copyTextToClipboard(stripMarkdown(report));
        if (ok) alert('Clean text copied to clipboard!');
        else alert('Could not copy. Try HTTPS, allow clipboard access, or use Download.');
    };

    const handleDownload = async () => {
        const filename = `${displayName.replace(/\s+/g, '_')}_Report.md`;
        const ok = await downloadTextFile(filename, report);
        if (!ok) {
            alert('Could not download the file. Use Copy Clean Text, then paste into a new file.');
            return;
        }
        if (topology) onSaveReport?.(displayName, report);
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-md">
            <div className="report-modal">
                <div className="report-modal__header">
                    <div className="flex items-center gap-3">
                        <div className="rounded-lg bg-teal-500/10 p-2">
                            <FileText size={20} className="text-teal-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold tracking-wide text-white">Documentation</h2>
                            <p className="text-xs text-slate-400">
                                {topology ? 'Generated Technical Report' : displayName}
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close"
                        className="rounded-full p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="report-modal__body report-md custom-scrollbar">
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                            table: ({ children }) => (
                                <div className="report-md__table-wrap">
                                    <table>{children}</table>
                                </div>
                            ),
                            code: ({ className, children, ...props }) => {
                                if (/language-cisco-cli/.test(className || '')) {
                                    return <CiscoTerminal code={String(children).replace(/\n$/, '')} />;
                                }
                                return (
                                    <code className="report-md__code" {...props}>
                                        {children}
                                    </code>
                                );
                            },
                            pre: ({ children }) => <div className="my-4">{children}</div>,
                        }}
                    >
                        {report}
                    </ReactMarkdown>
                </div>

                <div className="report-modal__footer">
                    <button
                        type="button"
                        onClick={handleCopy}
                        className="flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-white/5 hover:text-white"
                    >
                        <Copy size={16} /> Copy Clean Text
                    </button>
                    <button
                        type="button"
                        onClick={handleDownload}
                        className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-teal-600 to-teal-500 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-teal-900/20 hover:from-teal-500 hover:to-teal-400"
                    >
                        <Download size={16} /> Download Report
                    </button>
                </div>
            </div>
        </div>
    );
}
