import React, { useEffect, useState } from 'react';
import { Node, Edge } from '@xyflow/react';
import { NetworkNode, Link } from '@/types/network';
import { Share2, CheckCircle, Activity, Save, Monitor, Shield, Globe } from 'lucide-react';

interface ConfigPanelProps {
    selectedNode: Node | null;
    onUpdateNode: (nodeId: string, data: any) => void;
    allNodes: Node[];
    allEdges: Edge[];
    onSimulationPath: (result: { path: string[], success: boolean, failureNodeId?: string }) => void;
}

export default function ConfigPanel({ selectedNode, onUpdateNode, allNodes, allEdges, onSimulationPath }: ConfigPanelProps) {
    const [label, setLabel] = useState('');
    const [ip, setIp] = useState('');
    const [pingTarget, setPingTarget] = useState('');
    const [pingResult, setPingResult] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (selectedNode) {
            setLabel((selectedNode.data.label as string) || '');
            setIp((selectedNode.data.ip as string) || '');
            setPingResult(null);
            setPingTarget('');
        }
    }, [selectedNode?.id]);

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

    if (!selectedNode) {
        return (
            <aside className="w-80 h-full backdrop-blur-md border-l border-teal-500/15 p-6 flex flex-col justify-center items-center text-center text-gray-400 z-20"
                style={{ backgroundColor: '#1C2F45', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)' }}>
                <Activity size={48} className="text-teal-500/30 mb-4 animate-pulse" />
                <p className="font-semibold text-slate-400">Select a device to configure</p>
                <div className="mt-2 text-xs text-slate-600">Click any node on the canvas</div>
            </aside>
        );
    }

    const NodeTypeIcon = () => {
        switch (selectedNode.type) {
            case 'router': return <Globe size={18} className="text-teal-400" />;
            case 'switch': return <Share2 size={18} className="text-blue-400" />;
            case 'host': return <Monitor size={18} className="text-purple-400" />;
            default: return <Shield size={18} className="text-gray-400" />;
        }
    };

    return (
        <aside className="w-80 h-full backdrop-blur-md border-l border-teal-500/15 p-6 flex flex-col gap-6 shadow-2xl z-20 overflow-y-auto transition-all duration-300"
            style={{ backgroundColor: '#1C2F45', boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.2)' }}>

            <div className="border-b border-teal-500/20 pb-4">
                <div className="flex items-center gap-3 mb-1">
                    <div className="p-2 rounded-lg bg-slate-800/50 border border-white/10 shadow-inner">
                        <NodeTypeIcon />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-white tracking-tight">{selectedNode.data.label as string}</h2>
                        <span className="text-[10px] uppercase tracking-wider font-bold text-teal-400/80 bg-teal-900/20 px-2 py-0.5 rounded-full border border-teal-500/20">
                            {selectedNode.type}
                        </span>
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-5">
                <div className="group">
                    <label className="text-[10px] uppercase font-bold text-slate-400 mb-2 block tracking-wider group-hover:text-teal-400/70 transition-colors">
                        Hostname
                    </label>
                    <input
                        className="w-full bg-[#142338] border border-teal-500/20 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-teal-400 focus:ring-1 focus:ring-teal-400/20 transition-all duration-300 hover:border-teal-400/40 placeholder-slate-600"
                        value={label}
                        onChange={(e) => setLabel(e.target.value)}
                        placeholder="Device Name"
                    />
                </div>

                {selectedNode.type !== 'switch' && (
                    <div className="group">
                        <label className="text-[10px] uppercase font-bold text-slate-400 mb-2 block tracking-wider group-hover:text-teal-400/70 transition-colors">
                            Management IP
                        </label>
                        <input
                            className="w-full bg-[#142338] border border-teal-500/20 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-teal-400 focus:ring-1 focus:ring-teal-400/20 transition-all duration-300 hover:border-teal-400/40 placeholder-slate-600 font-mono"
                            value={ip}
                            onChange={(e) => setIp(e.target.value)}
                            placeholder="0.0.0.0"
                        />
                    </div>
                )}

                <button
                    onClick={handleSave}
                    className="w-full mt-2 bg-gradient-to-br from-teal-500 to-teal-700 hover:from-teal-400 hover:to-teal-600 text-white p-3 rounded-lg shadow-lg shadow-teal-900/20 transition-all duration-300 transform hover:-translate-y-0.5 active:scale-95 flex items-center justify-center gap-2 font-semibold text-sm"
                >
                    <Save size={16} /> Apply Configuration
                </button>
            </div>

            {/* Logical Divider */}
            <div className="h-px w-full bg-gradient-to-r from-transparent via-teal-500/20 to-transparent my-2"></div>

            {/* Simulation Section */}
            <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2 text-slate-400">
                    <Activity size={14} className="text-teal-400" />
                    <h3 className="text-[10px] uppercase font-bold tracking-wider">Simulation Interface</h3>
                </div>

                <div className="flex flex-col gap-3">
                    <div className="group">
                        <label className="text-[10px] uppercase font-bold text-slate-500 mb-2 block tracking-wider group-hover:text-blue-400/70 transition-colors">Target Node</label>
                        <select
                            className="w-full bg-[#142338] border border-teal-500/20 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400/20 transition-all duration-300 cursor-pointer hover:border-blue-400/40 appearance-none"
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
                        className="w-full bg-[#142338] hover:bg-teal-500/10 border border-teal-500/30 text-teal-400 p-3 rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-semibold text-sm hover:border-teal-400 active:bg-teal-500/20"
                    >
                        {loading ? (
                            <span className="flex items-center gap-2">
                                <Activity className="animate-spin" size={16} /> Transmitting...
                            </span>
                        ) : (
                            <span className="flex items-center gap-2">
                                <Share2 size={16} /> Send Packet
                            </span>
                        )}
                    </button>

                    {pingResult && (
                        <div className={`mt-2 p-3 rounded-lg border text-xs flex items-start gap-2 animate-in fade-in slide-in-from-top-2 duration-300 ${pingResult.startsWith('Path')
                            ? 'bg-teal-500/10 border-teal-500/30 text-teal-300 shadow-[0_0_15px_rgba(45,212,191,0.1)]'
                            : 'bg-red-500/10 border-red-500/30 text-red-300'
                            }`}>
                            {pingResult.startsWith('Path')
                                ? <CheckCircle size={16} className="mt-0.5 flex-shrink-0" />
                                : <Shield size={16} className="mt-0.5 flex-shrink-0" />
                            }
                            <span className="leading-relaxed font-mono">{pingResult}</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="mt-auto pt-6 text-[10px] text-slate-600 text-center border-t border-teal-500/5">
                System Status: <span className="text-teal-500 font-bold">ONLINE</span>
            </div>
        </aside>
    );
}
