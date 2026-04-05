import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Download, X, FileText, Terminal, Check } from 'lucide-react';
import { NetworkNode, Link, ProtocolConfig, TopologyMetadata } from '@/types/network';
import { generateMarkdownReport } from '@/lib/generator/report';

interface ReportModalProps {
    isOpen: boolean;
    onClose: () => void;
    topology: {
        nodes: NetworkNode[];
        links: Link[];
        protocols: ProtocolConfig[];
        name: string;
        id: string;
        version: number;
        lastUpdated: string;
        metadata?: TopologyMetadata;
    };
}

// ... stripMarkdown ...

// Custom Component for Cisco CLI
const CiscoTerminalWindow = ({ code }: { code: string }) => {
    const [copied, setCopied] = useState(false);

    // Extract device name from first prompt "DeviceName#"
    const deviceNameMatch = code.match(/^(\S+)#/);
    const deviceName = deviceNameMatch ? deviceNameMatch[1] : 'Device';

    // Clean code for copying (remove prompts, etc)
    const getCleanConfig = () => {
        return code
            .split('\n')
            .filter(line => !line.includes('Building configuration...') && !line.includes('[OK]') && !line.includes('show running-config') && !line.includes('write memory'))
            .map(line => line.replace(/^\S+#\s*/, '')) // Remove prompts like "R1#"
            .join('\n')
            .trim();
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(getCleanConfig());
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="my-8 rounded-lg overflow-hidden shadow-[0_10px_30px_rgba(0,0,0,0.5)] border border-[#3DD6B5]/30 ring-1 ring-[#3DD6B5]/10">
            {/* Header */}
            <div className="bg-gradient-to-br from-[#1C2F45] to-[#0F1824] px-5 py-3 flex items-center justify-between border-b-2 border-[#3DD6B5]">
                <div className="flex items-center gap-3">
                    <Terminal size={18} className="text-[#3DD6B5]" />
                    <div className="flex items-baseline gap-2">
                        <span className="text-white font-mono font-bold text-base">{deviceName}</span>
                        <span className="text-[#94A8C0] text-xs font-normal">(CISCO IOS)</span>
                    </div>
                </div>
                <button
                    onClick={handleCopy}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-300 border ${copied
                        ? 'bg-[#3DD6B5]/20 border-[#3DD6B5] text-[#3DD6B5]'
                        : 'bg-[#3DD6B5]/10 border-[#3DD6B5]/30 text-[#3DD6B5] hover:bg-[#3DD6B5]/20 hover:border-[#3DD6B5]'
                        }`}
                >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? 'Copied!' : 'Copy Config'}
                </button>
            </div>

            {/* Terminal Body */}
            <div className="bg-[#0A0F1A] p-6 overflow-x-auto font-mono text-[13px] leading-relaxed relative min-h-[200px]">
                {/* Optional Mac-like dots */}
                {/* <div className="absolute top-4 right-4 flex gap-1.5 opacity-50">
                    <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F56]"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E]"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-[#27C93F]"></div>
                </div> */}

                {code.split('\n').map((line, i) => (
                    <div key={i} className="whitespace-pre-wrap break-words">
                        <SyntaxHighlighter line={line} />
                    </div>
                ))}
            </div>
        </div>
    );
};

// Simple regex-based syntax highlighter for Cisco IOS
const SyntaxHighlighter = ({ line }: { line: string }) => {
    if (!line) return <br />;

    // Comments
    if (line.trim().startsWith('!')) {
        return <span className="text-[#6B7A8F] italic">{line}</span>;
    }

    // Prompts (R1# ...)
    if (/^\S+#/.test(line)) {
        const parts = line.match(/^(\S+#)(.*)/);
        if (parts) {
            return (
                <>
                    <span className="text-[#3DD6B5] font-bold">{parts[1]}</span>
                    <span className="text-slate-300">{parts[2]}</span>
                </>
            );
        }
    }

    // Heuristics for highlighting
    // Keywords
    const keywords = ['version', 'hostname', 'interface', 'no', 'ip', 'address', 'shutdown', 'router', 'network', 'area', 'end', 'write', 'memory', 'building', 'configuration'];
    const parts = line.split(/(\s+)/); // split by whitespace but keep delimiters

    return (
        <span>
            {parts.map((part, index) => {
                if (/^(\d{1,3}\.){3}\d{1,3}$/.test(part) || /^(\d{1,3}\.){3}\d{1,3}\/\d+$/.test(part)) { // IP
                    return <span key={index} className="text-[#FFA94D]">{part}</span>;
                }
                if (/^(Ethernet|FastEthernet|GigabitEthernet|Serial|Vlan)\d+([\/\d]+)?$/i.test(part)) { // Interface
                    return <span key={index} className="text-[#8B5CF6]">{part}</span>;
                }
                if (keywords.includes(part.toLowerCase())) {
                    return <span key={index} className="text-[#4A8FFF]">{part}</span>;
                }
                if (/^\d+(\.\d+)?$/.test(part)) { // Numbers
                    return <span key={index} className="text-[#10B981]">{part}</span>;
                }
                return <span key={index} className="text-[#E2E8F0]">{part}</span>;
            })}
        </span>
    );
};



// Function to strip common markdown syntax for clean copying
const stripMarkdown = (md: string) => {
    if (!md) return '';
    return md
        .replace(/#{1,6}\s?/g, '') // Remove headers
        .replace(/\*\*/g, '')      // Remove bold
        .replace(/\*/g, '')        // Remove italic
        .replace(/`{3}[\s\S]*?`{3}/g, '') // Remove code blocks
        .replace(/`/g, '')         // Remove inline code
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Remove links, keep text
        .replace(/\|/g, ' ')       // Replace table pipes with spaces
        .replace(/-{3,}/g, '')     // Remove horizontal rules
        .trim();
};

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
        const cleanText = stripMarkdown(report);
        navigator.clipboard.writeText(cleanText);
        alert('Clean text copied to clipboard!');
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
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-md p-4 transition-all">
            <div className="bg-[#1C2F45] rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden border border-[#3DD6B5]/20 animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-[#3DD6B5]/10 bg-[#142338]">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-teal-500/10 rounded-lg">
                            <FileText size={20} className="text-teal-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white tracking-wide">Documentation</h2>
                            <p className="text-xs text-slate-400">Generated Technical Report</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white hover:bg-white/10 p-2 rounded-full transition-all"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content Area */}
                <div className="flex-grow p-8 overflow-y-auto bg-[#0F1A2A] text-slate-300 custom-scrollbar">
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                            h1: ({ node, ...props }: any) => <h1 className="text-2xl font-bold text-white mb-6 pb-2 border-b border-[#3DD6B5]/20 flex items-center gap-2" {...props} />,
                            h2: ({ node, ...props }: any) => <h2 className="text-lg font-semibold text-teal-400 mt-8 mb-4 flex items-center gap-2" {...props} />,
                            h3: ({ node, ...props }: any) => <h3 className="text-md font-medium text-slate-200 mt-6 mb-2" {...props} />,
                            p: ({ node, ...props }: any) => <p className="mb-4 text-sm leading-7 text-slate-300" {...props} />,
                            ul: ({ node, ...props }: any) => <ul className="list-disc list-inside mb-4 space-y-2 text-sm text-slate-300 marker:text-teal-500" {...props} />,
                            li: ({ node, ...props }: any) => <li className="pl-1" {...props} />,
                            blockquote: ({ node, ...props }: any) => <blockquote className="border-l-4 border-teal-500/50 pl-4 py-1 my-4 bg-teal-900/10 text-slate-400 italic" {...props} />,
                            table: ({ node, ...props }: any) => <div className="overflow-x-auto my-6 rounded-lg border border-[#3DD6B5]/10"><table className="w-full text-left border-collapse text-sm" {...props} /></div>,
                            thead: ({ node, ...props }: any) => <thead className="bg-[#1C2F45] text-teal-400 font-semibold" {...props} />,
                            th: ({ node, ...props }: any) => <th className="p-4 border-b border-[#3DD6B5]/10" {...props} />,
                            td: ({ node, ...props }: any) => <td className="p-4 border-b border-[#3DD6B5]/5 text-slate-300" {...props} />,
                            // ...
                            code: ({ node, className, children, ...props }: any) => {
                                const match = /language-([\w-]+)/.exec(className || '');
                                const isCisco = match && match[1] === 'cisco-cli';

                                if (isCisco) {
                                    return <CiscoTerminalWindow code={String(children).replace(/\n$/, '')} />;
                                }

                                return <code className="bg-[#1C2F45] px-1.5 py-0.5 rounded text-xs font-mono text-teal-200 border border-teal-500/10 whitespace-pre-wrap break-all" {...props}>{children}</code>;
                            },
                            // ...
                            pre: ({ node, children, ...props }: any) => <div className="my-4">{children}</div>,
                        }}
                    >
                        {report}
                    </ReactMarkdown>
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-[#3DD6B5]/10 bg-[#142338] flex justify-end gap-3">
                    <button
                        onClick={handleCopy}
                        className="px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 border border-white/10 rounded-lg font-medium text-sm flex items-center gap-2 transition-all"
                    >
                        <Copy size={16} /> Copy Clean Text
                    </button>
                    <button
                        onClick={handleDownload}
                        className="px-5 py-2.5 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-500 hover:to-teal-400 text-white rounded-lg font-bold text-sm shadow-lg shadow-teal-900/20 flex items-center gap-2 transition-all hover:-translate-y-0.5 active:translate-y-0"
                    >
                        <Download size={16} /> Download Report
                    </button>
                </div>
            </div>

            <style jsx global>{`
                .custom-scrollbar::-webkit-scrollbar {
                    width: 8px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: #0F1A2A; 
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #1C2F45; 
                    border-radius: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #3DD6B5; 
                }
            `}</style>
        </div>
    );
}
