'use client';

import React, { useCallback } from 'react';
import {
    ReactFlow,
    MiniMap,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    Edge,
    Node,
    NodeTypes,
    BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Import custom nodes
import RouterNode from './nodes/RouterNode';
import SwitchNode from './nodes/SwitchNode';
import HostNode from './nodes/HostNode';
import Sidebar from './Sidebar';
import ConfigPanel from './ConfigPanel';
import ChatInterface from './ChatInterface';
import ReportModal from './ReportModal';
import MetricsDashboard from './MetricsDashboard';
import { initialTopology } from '@/data/initialTopology';
import { NetworkNode, Link } from '@/types/network';

// Register custom node types
const nodeTypes: NodeTypes = {
    router: RouterNode,
    switch: SwitchNode,
    host: HostNode,
};

// Converters
const convertNodes = (netNodes: NetworkNode[]): Node[] => {
    return netNodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: { x: n.x, y: n.y },
        data: {
            label: n.name,
            ip: n.interfaces.find(i => i.ipAddress)?.ipAddress // Grab first IP for display
        },
    }));
};

const convertEdges = (netLinks: Link[]): Edge[] => {
    return netLinks.map((l) => ({
        id: l.id,
        source: l.sourceNodeId,
        target: l.targetNodeId,
        animated: true,
        style: { stroke: '#b1b1b7', strokeWidth: 2 },
    }));
};

export default function TopologyEditor() {
    const [nodes, setNodes, onNodesChange] = useNodesState(convertNodes(initialTopology.nodes));
    const [edges, setEdges, onEdgesChange] = useEdgesState(convertEdges(initialTopology.links));
    const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>(null);
    const [isReportOpen, setIsReportOpen] = React.useState(false);
    const [isMetricsOpen, setIsMetricsOpen] = React.useState(false);

    const onConnect = useCallback(
        (params: Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges],
    );

    // ... (keep existing DnD handlers)


    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();

            const type = event.dataTransfer.getData('application/reactflow');
            if (typeof type === 'undefined' || !type) {
                return;
            }

            // Check if the drop target is valid (in this case, just the react flow wrapper)
            // We can improve this coordinate calculation later
            const position = {
                x: event.clientX - 300, // Approximate offset for sidebar
                y: event.clientY - 100
            };

            const newNode: Node = {
                id: `node-${nodes.length + 1}`,
                type,
                position,
                data: { label: `${type.charAt(0).toUpperCase() + type.slice(1)} ${nodes.length + 1}`, ip: '' },
            };

            setNodes((nds) => nds.concat(newNode));
        },
        [nodes, setNodes],
    );

    const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
        setSelectedNodeId(node.id);
    }, []);

    const onUpdateNode = useCallback((nodeId: string, newData: any) => {
        setNodes((nds) => nds.map((node) => {
            if (node.id === nodeId) {
                return { ...node, data: newData };
            }
            return node;
        }));
    }, [setNodes]);

    const onSimulationPath = useCallback((result: { path: string[], success: boolean, failureNodeId?: string }) => {
        const { path, success, failureNodeId } = result;
        const pathNodeIds = path || [];

        // 1. Update Edges
        setEdges((currentEdges) => {
            if (!pathNodeIds || pathNodeIds.length < 2) {
                // Reset to default
                return currentEdges.map(e => ({
                    ...e,
                    animated: false,
                    style: { ...e.style, stroke: '#b1b1b7', strokeWidth: 2, opacity: 1 }
                }));
            }

            const involvedEdges = new Set<string>();
            const failureEdges = new Set<string>();

            for (let i = 0; i < pathNodeIds.length - 1; i++) {
                const u = pathNodeIds[i];
                const v = pathNodeIds[i + 1];
                const edge = currentEdges.find(e =>
                    (e.source === u && e.target === v) ||
                    (e.source === v && e.target === u)
                );

                if (edge) {
                    involvedEdges.add(edge.id);
                    // If this segment leads to the failure node, mark it
                    if (!success && failureNodeId && (v === failureNodeId || u === failureNodeId)) {
                        // Note: graph path is ordered, so v is the next step. If v is failure node, this edge failed.
                        if (v === failureNodeId) {
                            failureEdges.add(edge.id);
                        }
                    }
                }
            }

            return currentEdges.map(e => {
                if (failureEdges.has(e.id)) {
                    return {
                        ...e,
                        animated: true,
                        style: { ...e.style, stroke: '#FF6B6B', strokeWidth: 4, opacity: 1 }
                    };
                } else if (involvedEdges.has(e.id)) {
                    return {
                        ...e,
                        animated: true,
                        style: { ...e.style, stroke: success ? '#3DD6B5' : '#4A8FFF', strokeWidth: 4, opacity: 1 } // Green if success, Blue if processing/partial
                    };
                } else {
                    return {
                        ...e,
                        animated: false,
                        style: { ...e.style, stroke: '#b1b1b7', strokeWidth: 2, opacity: 0.3 }
                    };
                }
            });
        });

        // 2. Update Nodes (to show status icons)
        setNodes((currentNodes) => currentNodes.map(n => {
            let status = 'idle';
            if (pathNodeIds.includes(n.id)) {
                if (n.id === failureNodeId) {
                    status = 'error';
                } else {
                    status = success ? 'success' : 'processing'; // or just 'success' for passed nodes in a failed path? 
                    // User said: "All subsequent nodes... remain grayed out". 
                    // Nodes in partial path should probably look roughly successful or 'visited'.
                    // Let's use 'success' for visited nodes even in failed path, except the fail one.
                    status = 'success';
                }
            }
            return {
                ...n,
                data: { ...n.data, simulationStatus: status }
            };
        }));

    }, [setEdges, setNodes]);

    // Reset simulation when clicking pane
    const onPaneClick = useCallback(() => {
        setSelectedNodeId(null);
        onSimulationPath({ path: [], success: true }); // Clear simulation
    }, [onSimulationPath]);

    const onTopologyGenerated = useCallback((newTopology: any) => {
        if (newTopology.nodes) setNodes(convertNodes(newTopology.nodes));
        if (newTopology.links) setEdges(convertEdges(newTopology.links));
        onSimulationPath({ path: [], success: true });
        setSelectedNodeId(null);
    }, [setNodes, setEdges, onSimulationPath]);

    const onDeleteNode = useCallback((nodeId: string) => {
        setNodes((nds) => nds.filter((node) => node.id !== nodeId));
        setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
        setSelectedNodeId(null);
        onSimulationPath({ path: [], success: true });
    }, [setNodes, setEdges, onSimulationPath]);

    const selectedNode = nodes.find(n => n.id === selectedNodeId) || null;

    return (
        <div className="flex h-full w-full relative">
            <Sidebar />
            <div className="flex-grow h-full relative" onDrop={onDrop} onDragOver={onDragOver}>
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onNodeClick={onNodeClick}
                    onPaneClick={onPaneClick}
                    nodeTypes={nodeTypes}
                    fitView
                >
                    <Controls />
                    <MiniMap />
                    <Background variant={BackgroundVariant.Dots} gap={12} size={1} />

                    <div className="absolute top-4 right-4 z-50 flex gap-2">
                        <button
                            onClick={() => setIsMetricsOpen(!isMetricsOpen)}
                            className={`px-4 py-2 rounded shadow-lg font-bold text-sm hover:scale-105 transition-all flex items-center gap-2 ${isMetricsOpen ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 dark:bg-zinc-800 dark:text-gray-200'}`}
                        >
                            📊 Metrics
                        </button>
                        <button
                            onClick={() => setIsReportOpen(true)}
                            className="bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-4 py-2 rounded shadow-lg font-bold text-sm hover:scale-105 transition-all flex items-center gap-2"
                        >
                            📄 Export Report
                        </button>
                    </div>
                </ReactFlow>
                <ChatInterface onTopologyGenerated={onTopologyGenerated} />
            </div>
            <ConfigPanel
                selectedNode={selectedNode}
                onUpdateNode={onUpdateNode}
                allNodes={nodes}
                allEdges={edges}
                onSimulationPath={onSimulationPath}
                onDeleteNode={onDeleteNode}
            />

            <ReportModal
                isOpen={isReportOpen}
                onClose={() => setIsReportOpen(false)}
                topology={{
                    nodes: convertNodesToDomain(nodes),
                    links: convertEdgesToDomain(edges),
                    protocols: initialTopology.protocols,
                    name: "My Generated Network",
                    id: "topo-gen-1",
                    version: 1,
                    lastUpdated: new Date().toISOString()
                }}
            />

            {isMetricsOpen && <MetricsDashboard />}
        </div>
    );
}

// Helper to convert back to domain model (duplicate logic from ConfigPanel - should be refactored)
const convertNodesToDomain = (nodes: Node[]): NetworkNode[] => {
    return nodes.map(n => ({
        id: n.id,
        type: n.type as any,
        name: n.data.label as string,
        x: n.position.x,
        y: n.position.y,
        interfaces: [{ id: 'eth0', name: 'Ethernet0', ipAddress: n.data.ip as string }] // Simplified
    }));
};

const convertEdgesToDomain = (edges: Edge[]): Link[] => {
    return edges.map(e => ({
        id: e.id,
        sourceNodeId: e.source,
        targetNodeId: e.target,
    }));
};
