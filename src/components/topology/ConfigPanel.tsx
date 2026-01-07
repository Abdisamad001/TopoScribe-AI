import React, { useEffect, useState } from 'react';
import { Node, Edge } from '@xyflow/react';
import { NetworkNode, Link } from '@/types/network';

interface ConfigPanelProps {
    selectedNode: Node | null;
    onUpdateNode: (nodeId: string, data: any) => void;
    allNodes: Node[];
    allEdges: Edge[];
    onSimulationPath: (path: string[]) => void;
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
            onSimulationPath([]);
        }
    }, [selectedNode, onSimulationPath]);

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
                interfaces: []
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
                // Pretty print the path
                const pathNames = data.path.map((id: string) => {
                    const n = allNodes.find(an => an.id === id);
                    return n ? n.data.label : id;
                });
                setPingResult(`Success! Path: ${pathNames.join(' → ')}`);
                onSimulationPath(data.path);
            } else {
                setPingResult(`Unreachable: ${data.message || 'Unknown error'}`);
                onSimulationPath([]);
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
            <aside className="w-80 bg-gray-50 dark:bg-zinc-800 border-l border-gray-200 dark:border-zinc-700 p-6 flex flex-col justify-center items-center text-center text-gray-400">
                <p>Select a node to view configuration.</p>
            </aside>
        );
    }

    return (
        <aside className="w-80 bg-white dark:bg-zinc-900 border-l border-gray-200 dark:border-zinc-700 p-4 flex flex-col gap-4 shadow-xl z-20 overflow-y-auto">
            <div className="border-b pb-2 mb-2 border-gray-100 dark:border-zinc-800">
                <h2 className="text-lg font-bold">{selectedNode.data.label as string}</h2>
                <span className="text-xs uppercase px-2 py-1 bg-gray-100 rounded text-gray-600 font-mono">
                    {selectedNode.type}
                </span>
            </div>

            <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">Hostname</label>
                <input
                    className="border p-2 rounded text-sm bg-gray-50 focus:bg-white transition-colors outline-none focus:ring-2 ring-blue-500"
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                />
            </div>

            {selectedNode.type !== 'switch' && (
                <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">Management IP</label>
                    <input
                        className="border p-2 rounded text-sm bg-gray-50 focus:bg-white transition-colors outline-none focus:ring-2 ring-blue-500"
                        value={ip}
                        onChange={(e) => setIp(e.target.value)}
                    />
                </div>
            )}

            <div className="mt-4 pt-4 border-t border-gray-100">
                <button
                    onClick={handleSave}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white p-2 rounded shadow-sm transition-all text-sm font-medium"
                >
                    Apply Changes
                </button>
            </div>

            {/* Simulation Section */}
            <div className="mt-4 pt-4 border-t border-gray-100">
                <h3 className="text-sm font-bold mb-2">Simulation: Ping</h3>

                <div className="flex flex-col gap-2">
                    <label className="text-xs text-gray-500">Target Node</label>
                    <select
                        className="border p-2 rounded text-sm bg-white"
                        value={pingTarget}
                        onChange={(e) => setPingTarget(e.target.value)}
                    >
                        <option value="">Select Target...</option>
                        {allNodes
                            .filter(n => n.id !== selectedNode.id)
                            .map(n => (
                                <option key={n.id} value={n.id}>
                                    {n.data.label as string} ({n.id})
                                </option>
                            ))}
                    </select>

                    <button
                        onClick={handlePing}
                        disabled={!pingTarget || loading}
                        className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white p-2 rounded shadow-sm transition-all text-sm font-medium mt-1"
                    >
                        {loading ? 'Simulating...' : 'Send Packet'}
                    </button>

                    {pingResult && (
                        <div className={`mt-2 p-2 rounded text-xs ${pingResult.startsWith('Success') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {pingResult}
                        </div>
                    )}
                </div>
            </div>

        </aside>
    );
}
