'use client';

import React, { useCallback } from 'react';
import {
    ReactFlow,
    Background,
    BackgroundVariant,
    Controls,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    Edge,
    Node,
    NodeTypes,
} from '@xyflow/react';

// Import custom nodes
import RouterNode from './nodes/RouterNode';
import SwitchNode from './nodes/SwitchNode';
import HostNode from './nodes/HostNode';
import ConfigPanel from './ConfigPanel';
import ReportModal from './ReportModal';
import AiCopilot from './AiCopilot';
import { clarifyRequirements } from '@/lib/api';
import { NetworkNode, Link, GenerationRuntime, ProtocolConfig, TopologyMetadata } from '@/types/network';

// Register custom node types
const nodeTypes: NodeTypes = {
    router: RouterNode,
    switch: SwitchNode,
    host: HostNode,
};

// Converters
const convertNodes = (netNodes: any[]): Node[] => {
    return netNodes.map((n) => {
        // Handle IP address from backend (ip_address) or frontend (ipAddress)
        let displayIp = '';
        let subnetMask = '';
        const iface = n.interfaces && n.interfaces.length > 0 ? n.interfaces[0] : null;
        if (iface) {
            displayIp = iface.ipAddress || iface.ip_address || iface.ip || '';
            subnetMask = iface.subnetMask || iface.subnet_mask || iface.mask || '';
        }

        return {
            id: n.id,
            type: n.type,
            position: { x: n.x ?? 0, y: n.y ?? 0 },
            data: {
                label: n.name || n.label, // Handle both name and label
                ip: displayIp,
                subnetMask,
                // Preserve backend VLAN mapping for report generation
                config: n.config || {},
            },
        };
    });
};

const convertEdges = (netLinks: any[]): Edge[] => {
    return netLinks.map((l) => ({
        id: l.id,
        // Handle source/target from backend vs sourceNodeId/targetNodeId from frontend
        source: l.sourceNodeId || l.source,
        target: l.targetNodeId || l.target,
        animated: true,
        style: { stroke: '#b1b1b7', strokeWidth: 2 },
    }));
};

export default function TopologyEditor({
    initialTopology,
    onSave,
}: {
    initialTopology?: any;
    onSave: (topology: any) => Promise<void>;
}) {
    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
    const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>(null);
    const [isReportOpen, setIsReportOpen] = React.useState(false);
    const [topologyMeta, setTopologyMeta] = React.useState<TopologyMetadata | undefined>(undefined);
    const [topologyProtocols, setTopologyProtocols] = React.useState<ProtocolConfig[]>([]);
    const [generationRuntime, setGenerationRuntime] = React.useState<GenerationRuntime | undefined>(undefined);
    const hasTopology = nodes.length > 0;

    // Chat State
    const [isChatOpen, setIsChatOpen] = React.useState(false);
    const [chatMessages, setChatMessages] = React.useState<{ role: 'user' | 'assistant', content: string }[]>([]);
    const [chatLoading, setChatLoading] = React.useState(false);
    const [currentPrompt, setCurrentPrompt] = React.useState('');
    const [saveState, setSaveState] = React.useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

    const onConnect = useCallback(
        (params: Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges],
    );

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

            const position = {
                x: event.clientX - 300,
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

        setEdges((currentEdges) => {
            if (!pathNodeIds || pathNodeIds.length < 2) {
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
                    if (!success && failureNodeId && (v === failureNodeId || u === failureNodeId)) {
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
                        style: { ...e.style, stroke: success ? '#3DD6B5' : '#4A8FFF', strokeWidth: 4, opacity: 1 }
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

        setNodes((currentNodes) => currentNodes.map(n => {
            let status = 'idle';
            if (pathNodeIds.includes(n.id)) {
                if (n.id === failureNodeId) {
                    status = 'error';
                } else {
                    status = 'success';
                }
            }
            return {
                ...n,
                data: { ...n.data, simulationStatus: status }
            };
        }));

    }, [setEdges, setNodes]);

    const onPaneClick = useCallback(() => {
        setSelectedNodeId(null);
        onSimulationPath({ path: [], success: true });
    }, [onSimulationPath]);

    const onTopologyGenerated = useCallback((newTopology: any, runtime?: GenerationRuntime) => {
        if (newTopology.nodes) setNodes(convertNodes(newTopology.nodes));
        if (newTopology.links) setEdges(convertEdges(newTopology.links));
        setTopologyMeta(newTopology.metadata);
        setTopologyProtocols(newTopology.protocols || []);
        setGenerationRuntime(runtime);
        onSimulationPath({ path: [], success: true });
        setSelectedNodeId(null);
        setChatMessages([]);
    }, [setNodes, setEdges, onSimulationPath]);

    // Load a saved design's topology through the same path as AI generation
    React.useEffect(() => {
        if (initialTopology) onTopologyGenerated(initialTopology);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const onSaveClick = async () => {
        setSaveState('saving');
        try {
            await onSave({
                nodes: convertNodesToDomain(nodes),
                links: convertEdgesToDomain(edges),
                protocols: topologyProtocols,
                metadata: topologyMeta,
            });
            setSaveState('saved');
        } catch {
            setSaveState('error');
        }
        setTimeout(() => setSaveState('idle'), 2000);
    };

    const onDeleteNode = useCallback((nodeId: string) => {
        setNodes((nds) => nds.filter((node) => node.id !== nodeId));
        setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
        setSelectedNodeId(null);
        onSimulationPath({ path: [], success: true });
    }, [setNodes, setEdges, onSimulationPath]);

    const handleClarificationRequest = useCallback((prompt: string, questions: string[]) => {
        setCurrentPrompt(prompt);
        setChatMessages([
            { role: 'user', content: prompt },
            { role: 'assistant', content: questions.join('\n\n') }
        ]);
        setIsChatOpen(true);
    }, []);

    const onChatSendMessage = async (message: string) => {
        const newHistory = [...chatMessages, { role: 'user' as const, content: message }];
        setChatMessages(newHistory);
        setChatLoading(true);

        try {
            const data = await clarifyRequirements(currentPrompt, newHistory);

            if (data.status === 'complete' && data.topology) {
                onTopologyGenerated(data.topology, data.runtime);
                setIsChatOpen(false);
            } else if (data.status === 'needs_clarification') {
                const q = data.questions ? data.questions.join('\n\n') : 'Please clarify.';
                setChatMessages(prev => [...prev, { role: 'assistant', content: q }]);
            } else if (data.status === 'generation_failed') {
                const msg =
                    typeof data.message === 'string'
                        ? data.message
                        : 'Topology generation did not complete. Please try again.';
                setChatMessages(prev => [...prev, { role: 'assistant', content: msg }]);
            } else {
                setChatMessages(prev => [...prev, { role: 'assistant', content: "Failed to generate design." }]);
            }
        } catch (error) {
            setChatMessages(prev => [...prev, { role: 'assistant', content: "Error communicating with agent." }]);
        } finally {
            setChatLoading(false);
        }
    };

    const selectedNode = nodes.find(n => n.id === selectedNodeId) || null;

    return (
        <div className="flex h-full w-full relative">
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
                    style={{ background: '#000000' }}
                >
                    <Background
                        variant={BackgroundVariant.Dots}
                        gap={18}
                        size={2}
                        color="rgba(255,255,255,0.12)"
                        bgColor="#000000"
                    />
                    <Controls
                        position="top-right"
                        className="!m-4"
                        style={{
                            '--xy-controls-button-background-color': 'var(--chrome-navy)',
                            '--xy-controls-button-background-color-hover': 'var(--chrome-navy-hover)',
                            '--xy-controls-button-color': '#E5E7EB',
                            '--xy-controls-button-color-hover': '#FFFFFF',
                            '--xy-controls-button-border-color': 'rgba(255,255,255,0.12)',
                        } as React.CSSProperties}
                    />

                    {hasTopology && (
                        <div className="absolute top-4 right-16 z-50 flex gap-2">
                            <button
                                onClick={onSaveClick}
                                disabled={saveState === 'saving'}
                                className="bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-4 py-2 rounded shadow-lg font-bold text-sm hover:scale-105 transition-all flex items-center gap-2 disabled:opacity-60"
                            >
                                💾 {saveState === 'saving' ? 'Saving...' : saveState === 'saved' ? 'Saved' : saveState === 'error' ? 'Save failed' : 'Save'}
                            </button>
                            <button
                                onClick={() => setIsReportOpen(true)}
                                className="bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-4 py-2 rounded shadow-lg font-bold text-sm hover:scale-105 transition-all flex items-center gap-2"
                            >
                                📄 Export Report
                            </button>
                        </div>
                    )}
                </ReactFlow>

                <AiCopilot
                    isOpen={isChatOpen}
                    onOpen={() => setIsChatOpen(true)}
                    onClose={() => setIsChatOpen(false)}
                    messages={chatMessages}
                    onSendMessage={onChatSendMessage}
                    loading={chatLoading}
                    onTopologyGenerated={onTopologyGenerated}
                    onRequestClarification={handleClarificationRequest}
                />
            </div>
            <ConfigPanel
                selectedNode={selectedNode}
                onUpdateNode={onUpdateNode}
                allNodes={nodes}
                allEdges={edges}
                onSimulationPath={onSimulationPath}
                onDeleteNode={onDeleteNode}
                onDeselect={() => setSelectedNodeId(null)}
            />

            {hasTopology && (
                <ReportModal
                    isOpen={isReportOpen}
                    onClose={() => setIsReportOpen(false)}
                    topology={{
                        nodes: convertNodesToDomain(nodes),
                        links: convertEdgesToDomain(edges),
                        protocols: topologyProtocols,
                        metadata: topologyMeta,
                        runtime: generationRuntime,
                        name: "My Generated Network",
                        id: "topo-gen-1",
                        version: 1,
                        lastUpdated: new Date().toISOString()
                    }}
                />
            )}
        </div>
    );
}

// Helper to convert back to domain model
const convertNodesToDomain = (nodes: Node[]): NetworkNode[] => {
    return nodes.map(n => ({
        id: n.id,
        type: n.type as any,
        name: n.data.label as string,
        x: n.position.x,
        y: n.position.y,
        interfaces: [
            {
                id: 'eth0',
                name: 'Ethernet0',
                ipAddress: (n.data.ip as string) || '',
                subnetMask: (n.data as { subnetMask?: string }).subnetMask || undefined,
            },
        ],
        config: (n.data as any).config || {},
    }));
};

const convertEdgesToDomain = (edges: Edge[]): Link[] => {
    return edges.map(e => ({
        id: e.id,
        sourceNodeId: e.source,
        targetNodeId: e.target,
    }));
};
