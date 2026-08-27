import React, { useEffect, useState } from 'react';
import { Node, Edge } from '@xyflow/react';
import { NetworkNode, Link } from '@/types/network';
import { ShareNetworkIcon, CheckCircleIcon, PulseIcon, FloppyDiskIcon, DesktopIcon, ShieldIcon, GlobeIcon, TrashIcon, CaretRightIcon } from '@phosphor-icons/react';

interface ConfigPanelProps {
    selectedNode: Node | null;
    onUpdateNode: (nodeId: string, data: any) => void;
    allNodes: Node[];
    allEdges: Edge[];
    onSimulationPath: (result: { path: string[], success: boolean, failureNodeId?: string }) => void;
    onDeleteNode: (nodeId: string) => void;
    onDeselect: () => void;
}

export default function ConfigPanel({ selectedNode, onUpdateNode, allNodes, allEdges, onSimulationPath, onDeleteNode, onDeselect }: ConfigPanelProps) {
    const [label, setLabel] = useState('');
    const [ip, setIp] = useState('');
    const [pingTarget, setPingTarget] = useState('');
    const [pingResult, setPingResult] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [manuallyCollapsed, setManuallyCollapsed] = useState(false);

    const isOpen = !!selectedNode && !manuallyCollapsed;

    useEffect(() => {
        setManuallyCollapsed(false);
        if (selectedNode) {
            setLabel((selectedNode.data.label as string) || '');
            setIp((selectedNode.data.ip as string) || '');
            setPingResult(null);
            setPingTarget('');
        }
    }, [selectedNode?.id]);

    useEffect(() => {
        if (!selectedNode) return;
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') onDeselect();
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [selectedNode, onDeselect]);

    const handleSave = () => {
        if (selectedNode) {
            onUpdateNode(selectedNode.id, {
                ...selectedNode.data,
                label,
                ip
            });
        }
    };

    const handlePing = async () => {
        if (!selectedNode || !pingTarget) return;

        setLoading(true);
        setPingResult(null);

        try {
            // Convert React Flow nodes/edges back to our domain model
            const simNodes: NetworkNode[] = allNodes.map(n => ({
                id: n.id,
                type: n.type as any,
                name: n.data.label as string,
                x: n.position.x,
                y: n.position.y,
                interfaces: [{
                    id: 'eth0',
                    name: 'Ethernet0',
                    ipAddress: n.data.ip as string
                }]
            }));

            const simLinks: Link[] = allEdges.map(e => ({
                id: e.id,
                sourceNodeId: e.source,
                targetNodeId: e.target,
            }));

            const res = await fetch('/api/simulate/ping', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nodes: simNodes,
                    links: simLinks,
                    sourceId: selectedNode.id,
                    targetId: pingTarget
                })
            });

            const data = await res.json();

            if (data.success) {
                // Success case
                const pathNames = data.path.map((id: string) => {
                    const n = allNodes.find(an => an.id === id);
                    return n ? n.data.label : id;
                });
                setPingResult(`Path: ${pathNames.join(' → ')}`);
                onSimulationPath({ path: data.path, success: true });
            } else {
                // Failure case: The API now returns 'path' (partial path), 'failureNodeId', and 'failureReason'
                const partialPath = data.path || [];
                const failReason = data.failureReason || data.message || 'Unknown error';

                setPingResult(failReason);
                onSimulationPath({
                    path: partialPath,
                    success: false,
                    failureNodeId: data.failureNodeId
                });
            }

        } catch (e) {
            setPingResult('Error executing ping request.');
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const NodeTypeIcon = () => {
        switch (selectedNode?.type) {
            case 'router': return <GlobeIcon size={18} weight="regular" className="text-teal-400" />;
            case 'switch': return <ShareNetworkIcon size={18} weight="regular" className="text-blue-400" />;
            case 'host': return <DesktopIcon size={18} weight="regular" className="text-purple-400" />;
            default: return <ShieldIcon size={18} weight="regular" className="text-gray-400" />;
        }
    };

    return (
        <>
        {isOpen && (
            <div
                className="fixed inset-0 z-40 bg-black/50 min-[1440px]:hidden"
                onClick={onDeselect}
            />
        )}
        <aside
            aria-hidden={!isOpen}
            className={`
                shrink-0 backdrop-blur-md flex flex-col
                transition-all duration-300 ease-in-out
                ${isOpen
                    ? `
                        border-[#14213D]/15 gap-6 overflow-y-auto
                        max-[1023px]:fixed max-[1023px]:inset-x-0 max-[1023px]:bottom-0 max-[1023px]:h-[min(70vh,32rem)] max-[1023px]:w-full max-[1023px]:z-50 max-[1023px]:rounded-t-2xl max-[1023px]:border-l-0 max-[1023px]:border-t max-[1023px]:p-6
                        min-[1024px]:max-[1439px]:fixed min-[1024px]:max-[1439px]:top-0 min-[1024px]:max-[1439px]:right-0 min-[1024px]:max-[1439px]:h-full min-[1024px]:max-[1439px]:w-80 min-[1024px]:max-[1439px]:z-50 min-[1024px]:max-[1439px]:border-l min-[1024px]:max-[1439px]:p-6
                        min-[1440px]:relative min-[1440px]:w-80 min-[1440px]:h-full min-[1440px]:border-l min-[1440px]:p-6
                    `
                    : 'relative w-0 h-full p-0 border-0 pointer-events-none overflow-hidden'
                }
            `}
            style={{ backgroundColor: '#1C2F45', boxShadow: isOpen ? '-8px 0 32px rgba(0, 0, 0, 0.2)' : 'none' }}
        >

            {selectedNode && (
            <>
            <div className="flex justify-end -mt-1 -mr-1">
                <button
                    type="button"
                    aria-label="Collapse panel"
                    onClick={() => setManuallyCollapsed(true)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                >
                    <CaretRightIcon size={18} weight="regular" />
                </button>
            </div>

            <div className="border-b border-[#14213D]/20 pb-4">
                <div className="flex items-center gap-3 mb-1">
                    <div className="p-2 rounded-lg bg-slate-800/50 border border-white/10 shadow-inner">
                        <NodeTypeIcon />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-white tracking-tight">{selectedNode.data.label as string}</h2>
                        <span className="text-[10px] uppercase tracking-wider font-bold text-white/80 bg-[#14213D]/20 px-2 py-0.5 rounded-full border border-[#14213D]/20">
                            {selectedNode.type}
                        </span>
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-5">
                <div className="group">
                    <label className="text-[10px] uppercase font-bold text-slate-400 mb-2 block tracking-wider group-hover:text-white/70 transition-colors">
                        Hostname
                    </label>
                    <input
                        className="w-full bg-[#142338] border border-[#14213D]/20 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-[#14213D] focus:ring-1 focus:ring-[#14213D]/20 transition-all duration-300 hover:border-[#14213D]/40 placeholder-slate-600"
                        value={label}
                        onChange={(e) => setLabel(e.target.value)}
                        placeholder="Device Name"
                    />
                </div>

                {selectedNode.type !== 'switch' && (
                    <div className="group">
                        <label className="text-[10px] uppercase font-bold text-slate-400 mb-2 block tracking-wider group-hover:text-white/70 transition-colors">
                            Management IP
                        </label>
                        <input
                            className="w-full bg-[#142338] border border-[#14213D]/20 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-[#14213D] focus:ring-1 focus:ring-[#14213D]/20 transition-all duration-300 hover:border-[#14213D]/40 placeholder-slate-600 font-mono"
                            value={ip}
                            onChange={(e) => setIp(e.target.value)}
                            placeholder="0.0.0.0"
                        />
                    </div>
                )}

                <button
                    onClick={handleSave}
                    className="w-full mt-2 bg-gradient-to-br from-[#14213D] to-[#14213D] hover:from-[#14213D] hover:to-[#14213D] text-white p-3 rounded-lg shadow-lg shadow-[#14213D]/20 transition-all duration-300 transform hover:-translate-y-0.5 active:scale-95 flex items-center justify-center gap-2 font-semibold text-sm"
                >
                    <FloppyDiskIcon size={16} weight="regular" /> Apply Configuration
                </button>
            </div>

            {/* Logical Divider */}
            <div className="h-px w-full bg-gradient-to-r from-transparent via-[#14213D]/20 to-transparent my-2"></div>

            {/* Simulation Section */}
            <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2 text-slate-400">
                    <PulseIcon size={14} weight="regular" className="text-white" />
                    <h3 className="text-[10px] uppercase font-bold tracking-wider">Simulation Interface</h3>
                </div>

                <div className="flex flex-col gap-3">
                    <div className="group">
                        <label className="text-[10px] uppercase font-bold text-slate-500 mb-2 block tracking-wider group-hover:text-blue-400/70 transition-colors">Target Node</label>
                        <select
                            className="w-full bg-[#142338] border border-[#14213D]/20 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400/20 transition-all duration-300 cursor-pointer hover:border-blue-400/40 appearance-none"
                            value={pingTarget}
                            onChange={(e) => setPingTarget(e.target.value)}
                        >
                            <option value="" className="text-slate-500">Select Destination...</option>
                            {allNodes
                                .filter(n => n.id !== selectedNode.id)
                                .map(n => (
                                    <option key={n.id} value={n.id} className="bg-[#1C2F45]">
                                        {n.data.label as string} ({n.id})
                                    </option>
                                ))}
                        </select>
                    </div>

                    <button
                        onClick={handlePing}
                        disabled={!pingTarget || loading}
                        className="w-full bg-[#142338] hover:bg-[#14213D]/10 border border-[#14213D]/30 text-white p-3 rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-semibold text-sm hover:border-[#14213D] active:bg-[#14213D]/20"
                    >
                        {loading ? (
                            <span className="flex items-center gap-2">
                                <PulseIcon weight="regular" className="animate-spin" size={16} /> Transmitting...
                            </span>
                        ) : (
                            <span className="flex items-center gap-2">
                                <ShareNetworkIcon size={16} weight="regular" /> Send Packet
                            </span>
                        )}
                    </button>

                    {pingResult && (
                        <div className={`mt-2 p-3 rounded-lg border text-xs flex items-start gap-2 animate-in fade-in slide-in-from-top-2 duration-300 ${pingResult.startsWith('Path')
                            ? 'bg-[#14213D]/10 border-[#14213D]/30 text-teal-300 shadow-[0_0_15px_rgba(20,33,61,0.1)]'
                            : 'bg-red-500/10 border-red-500/30 text-red-300'
                            }`}>
                            {pingResult.startsWith('Path')
                                ? <CheckCircleIcon size={16} weight="regular" className="mt-0.5 flex-shrink-0" />
                                : <ShieldIcon size={16} weight="regular" className="mt-0.5 flex-shrink-0" />
                            }
                            <span className="leading-relaxed font-mono">{pingResult}</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="mt-8 px-1">
                <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="w-full flex items-center justify-center gap-2 text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 p-2 rounded-lg transition-all text-xs font-semibold"
                >
                    <TrashIcon size={14} weight="regular" /> Delete Device
                </button>
            </div>

            <div className="mt-auto pt-6 text-[10px] text-slate-600 text-center border-t border-[#14213D]/5">
                System Status: <span className="text-white font-bold">ONLINE</span>
            </div>
            </>
            )}
        </aside>

        {selectedNode && showDeleteConfirm && (
            <div
                className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
                onClick={() => setShowDeleteConfirm(false)}
            >
                <div
                    className="mx-4 w-full max-w-sm rounded-xl border border-red-500/20 bg-[#1C2F45] p-6 shadow-[0_8px_32px_rgba(0,0,0,0.4)] animate-in fade-in slide-in-from-top-2 duration-300"
                    onClick={(e) => e.stopPropagation()}
                >
                    <h3 className="text-lg font-semibold text-white tracking-tight">Delete Device?</h3>
                    <p className="mt-2 text-sm text-slate-400 leading-relaxed">
                        Are you sure you want to delete &quot;{selectedNode.data.label as string}&quot;? This action cannot be undone.
                    </p>
                    <div className="mt-6 flex gap-3">
                        <button
                            type="button"
                            onClick={() => setShowDeleteConfirm(false)}
                            className="flex-1 bg-[#142338] hover:bg-slate-700/50 border border-white/10 text-slate-300 p-2.5 rounded-lg transition-all text-sm font-semibold"
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                onDeleteNode(selectedNode.id);
                                setShowDeleteConfirm(false);
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
