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
                shrink-0 flex flex-col bg-[#111]
                transition-all duration-300 ease-in-out
                ${isOpen
                    ? `
                        border-white/10 gap-5 overflow-y-auto custom-scrollbar
                        max-[1023px]:fixed max-[1023px]:inset-x-0 max-[1023px]:bottom-0 max-[1023px]:h-[min(70vh,32rem)] max-[1023px]:w-full max-[1023px]:z-50 max-[1023px]:rounded-t-2xl max-[1023px]:border-l-0 max-[1023px]:border-t max-[1023px]:p-5
                        min-[1024px]:max-[1439px]:fixed min-[1024px]:max-[1439px]:top-0 min-[1024px]:max-[1439px]:right-0 min-[1024px]:max-[1439px]:h-full min-[1024px]:max-[1439px]:w-80 min-[1024px]:max-[1439px]:z-50 min-[1024px]:max-[1439px]:border-l min-[1024px]:max-[1439px]:p-5
                        min-[1440px]:relative min-[1440px]:w-80 min-[1440px]:h-full min-[1440px]:border-l min-[1440px]:p-5
                    `
                    : 'relative w-0 h-full p-0 border-0 pointer-events-none overflow-hidden'
                }
            `}
        >

            {selectedNode && (
            <>
            <div className="flex justify-end -mt-1 -mr-1">
                <button
                    type="button"
                    aria-label="Collapse panel"
                    onClick={() => setManuallyCollapsed(true)}
                    className="p-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                >
                    <CaretRightIcon size={18} weight="regular" />
                </button>
            </div>

            <div className="border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/5">
                        <NodeTypeIcon />
                    </div>
                    <div>
                        <h2 className="text-sm font-semibold text-white tracking-tight">{selectedNode.data.label as string}</h2>
                        <span className="text-[10px] uppercase tracking-wider font-medium text-zinc-500">
                            {selectedNode.type}
                        </span>
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-4">
                <div>
                    <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                        HOSTNAME
                    </label>
                    <input
                        className="w-full rounded-lg border border-white/10 bg-white/5 p-2.5 text-sm text-white placeholder-zinc-600 transition-colors focus:border-white/20 focus:outline-none"
                        value={label}
                        onChange={(e) => setLabel(e.target.value)}
                        placeholder="Device Name"
                    />
                </div>

                {selectedNode.type !== 'switch' && (
                    <div>
                        <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                            MANAGEMENT IP
                        </label>
                        <input
                            className="w-full rounded-lg border border-white/10 bg-white/5 p-2.5 font-mono text-sm text-white placeholder-zinc-600 transition-colors focus:border-white/20 focus:outline-none"
                            value={ip}
                            onChange={(e) => setIp(e.target.value)}
                            placeholder="0.0.0.0"
                        />
                    </div>
                )}

                <button
                    onClick={handleSave}
                    className="mt-1 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white p-2.5 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200"
                >
                    <FloppyDiskIcon size={16} weight="regular" /> Apply Configuration
                </button>
            </div>

            <div className="h-px w-full bg-white/10"></div>

            <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-zinc-500">
                    <PulseIcon size={14} weight="regular" />
                    <h3 className="text-[10px] font-semibold uppercase tracking-wider">SIMULATION INTERFACE</h3>
                </div>

                <div>
                    <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-zinc-500">TARGET NODE</label>
                    <select
                        className="w-full cursor-pointer appearance-none rounded-lg border border-white/10 bg-white/5 p-2.5 text-sm text-white transition-colors focus:border-white/20 focus:outline-none"
                        value={pingTarget}
                        onChange={(e) => setPingTarget(e.target.value)}
                    >
                        <option value="" className="bg-[#111] text-zinc-500">Select Destination ...</option>
                        {allNodes
                            .filter(n => n.id !== selectedNode.id)
                            .map(n => (
                                <option key={n.id} value={n.id} className="bg-[#111]">
                                    {n.data.label as string} ({n.id})
                                </option>
                            ))}
                    </select>
                </div>

                <button
                    onClick={handlePing}
                    disabled={!pingTarget || loading}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 p-2.5 text-sm font-medium text-zinc-200 transition-colors hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
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
                    <div className={`mt-1 flex items-start gap-2 rounded-lg border p-2.5 text-xs ${pingResult.startsWith('Path')
                        ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
                        : 'border-red-500/20 bg-red-500/10 text-red-300'
                        }`}>
                        {pingResult.startsWith('Path')
                            ? <CheckCircleIcon size={16} weight="regular" className="mt-0.5 flex-shrink-0" />
                            : <ShieldIcon size={16} weight="regular" className="mt-0.5 flex-shrink-0" />
                        }
                        <span className="font-mono leading-relaxed">{pingResult}</span>
                    </div>
                )}
            </div>

            <div className="mt-4">
                <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-2 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/20 hover:text-red-300"
                >
                    <TrashIcon size={14} weight="regular" /> Delete Device
                </button>
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
                    className="mx-4 w-full max-w-sm rounded-xl border border-white/10 bg-[#111] p-6 shadow-2xl"
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
                            className="flex-1 rounded-lg border border-white/10 bg-white/5 p-2.5 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10"
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
