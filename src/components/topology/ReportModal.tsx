import React, { useState } from 'react';
import { NetworkNode, Link, ProtocolConfig, Topology } from '@/types/network'; // Assuming these exist
import { generateMarkdownReport } from '@/lib/generator/report'; // We'll assume you import the function

interface ReportModalProps {
    isOpen: boolean;
    onClose: () => void;
    topology: {
        nodes: NetworkNode[];
        links: Link[];
        protocols: ProtocolConfig[];
        name: string;
        id: string; // Add other necessary props for Topology
        version: number;
        lastUpdated: string;
    };
}

export default function ReportModal({ isOpen, onClose, topology }: ReportModalProps) {
    const [report, setReport] = useState('');

    React.useEffect(() => {
        if (isOpen) {
            const md = generateMarkdownReport(topology);
            setReport(md);
        }
    }, [isOpen, topology]);

    if (!isOpen) return null;

    const handleCopy = () => {
        navigator.clipboard.writeText(report);
        alert('Report copied to clipboard!');
    };

    const handleDownload = () => {
        const blob = new Blob([report], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${topology.name.replace(/\s+/g, '_')}_Report.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-zinc-900 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden border border-gray-200 dark:border-zinc-700">
                <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-zinc-800">
                    <h2 className="text-xl font-bold">Project Documentation</h2>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-full">
                        ✕
                    </button>
                </div>

                <div className="flex-grow p-6 overflow-y-auto bg-gray-50 dark:bg-zinc-950 font-mono text-sm">
                    <pre className="whitespace-pre-wrap">{report}</pre>
                </div>

                <div className="p-4 border-t border-gray-100 dark:border-zinc-800 flex justify-end gap-2 bg-white dark:bg-zinc-900">
                    <button
                        onClick={handleCopy}
                        className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded font-medium"
                    >
                        Copy Text
                    </button>
                    <button
                        onClick={handleDownload}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium shadow-sm"
                    >
                        Download Markdown
                    </button>
                </div>
            </div>
        </div>
    );
}
