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
import { clarifyRequirements, createChat, updateChat, configureTopology, type ChatMessage } from '@/lib/api';
import {
    attachPtProject,
    executePt,
    fetchPtStatus,
    newExecutionId,
    type PtExecuteResult,
    type PtStatus,
} from '@/lib/ptClient';
import { NetworkNode, Link, GenerationRuntime, ProtocolConfig, TopologyMetadata } from '@/types/network';
import PacketTracerPanel from './PacketTracerPanel';
import {
    GlobeIcon,
    ShareNetworkIcon,
    DesktopIcon,
    NoteIcon,
    CaretLeftIcon,
    FloppyDiskIcon,
    FileTextIcon,
    BroadcastIcon,
    StackIcon,
} from '@phosphor-icons/react';

// Component shelf cards
const DEVICE_CARDS = [
    { type: 'router', title: 'Router', subtitle: 'L3 Networking', Icon: GlobeIcon, chipClass: 'bg-teal-500', titleHoverClass: 'group-hover:text-teal-300', disabled: false },
    { type: 'switch', title: 'Switch', subtitle: 'L2 Switching', Icon: ShareNetworkIcon, chipClass: 'bg-blue-500', titleHoverClass: 'group-hover:text-blue-300', disabled: false },
    { type: 'host', title: 'End Device', subtitle: 'Workstation / Server', Icon: DesktopIcon, chipClass: 'bg-purple-500', titleHoverClass: 'group-hover:text-purple-300', disabled: false },
    { type: 'note', title: 'Notes', subtitle: 'Annotation', Icon: NoteIcon, chipClass: 'bg-slate-600', titleHoverClass: '', disabled: true },
];

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
    designId = null,
    designName,
    onRename,
    onBack,
    onSaveReport,
    initialChat = null,
}: {
    initialTopology?: any;
    onSave: (topology: any) => Promise<void>;
    designId?: string | null;
    designName: string;
    onRename: (name: string) => void;
    onBack: () => void;
    onSaveReport?: (name: string, markdown: string) => void;
    initialChat?: { id: string; messages: ChatMessage[] } | null;
}) {
    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
    const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>(null);
    const [isReportOpen, setIsReportOpen] = React.useState(false);
    const [topologyMeta, setTopologyMeta] = React.useState<TopologyMetadata | undefined>(undefined);
    const [topologyProtocols, setTopologyProtocols] = React.useState<ProtocolConfig[]>([]);
    const [generationRuntime, setGenerationRuntime] = React.useState<GenerationRuntime | undefined>(undefined);
    const [shelfOpen, setShelfOpen] = React.useState(false);
    const [editingTitle, setEditingTitle] = React.useState(false);

    // Chat State
    const [isChatOpen, setIsChatOpen] = React.useState(Boolean(initialChat?.messages?.length));
    const [chatMessages, setChatMessages] = React.useState<ChatMessage[]>(initialChat?.messages ?? []);
    const [chatId, setChatId] = React.useState<string | null>(initialChat?.id ?? null);
    const [chatLoading, setChatLoading] = React.useState(false);
    const [currentPrompt, setCurrentPrompt] = React.useState(
        () => initialChat?.messages?.find((m) => m.role === 'user')?.content ?? '',
    );
    const [saveState, setSaveState] = React.useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
    const [exportState, setExportState] = React.useState<'idle' | 'configuring' | 'error'>('idle');
    const [ptStatus, setPtStatus] = React.useState<PtStatus | null>(null);
    const [ptBusy, setPtBusy] = React.useState(false);
    const [ptPreparing, setPtPreparing] = React.useState(false);
    const [ptPanelOpen, setPtPanelOpen] = React.useState(false);
    const [ptElapsed, setPtElapsed] = React.useState(0);
    const [ptResult, setPtResult] = React.useState<PtExecuteResult | null>(null);
    const [ptError, setPtError] = React.useState<string | null>(null);
    const ptRunLock = React.useRef(false);
    const pendingPtAttachments = React.useRef<string[]>([]);
    const designIdRef = React.useRef(designId);
    designIdRef.current = designId;

    React.useEffect(() => {
        let cancelled = false;
        const poll = async () => {
            try {
                const s = await fetchPtStatus();
                if (!cancelled) setPtStatus(s);
            } catch {
                if (!cancelled) {
                    setPtStatus({
                        ready: false,
                        enabled: false,
                        canvas_empty: false,
                        detail: 'Packet Tracer status unavailable',
                    });
                }
            }
        };
        poll();
        const id = window.setInterval(poll, 8000);
        return () => {
            cancelled = true;
            window.clearInterval(id);
        };
    }, []);

    React.useEffect(() => {
        if (!ptBusy) return;
        setPtElapsed(0);
        const id = window.setInterval(() => setPtElapsed((s) => s + 1), 1000);
        return () => window.clearInterval(id);
    }, [ptBusy]);

    React.useEffect(() => {
        if (!designId || pendingPtAttachments.current.length === 0) return;
        const ids = [...pendingPtAttachments.current];
        pendingPtAttachments.current = [];
        ids.forEach((eid) => {
            attachPtProject(eid, designId).catch(() => {});
        });
    }, [designId]);

    // Keep Sidebar → Chats in sync whenever the assistant thread grows.
    React.useEffect(() => {
        if (chatMessages.length === 0) return;
        const title =
            chatMessages.find((m) => m.role === 'user')?.content.trim().slice(0, 80) || 'Chat';
        const timer = window.setTimeout(() => {
            if (chatId) {
                updateChat(chatId, {
                    title,
                    messages: chatMessages,
                    design_id: designId,
                    design_name: designName,
                }).catch(() => {});
            } else {
                createChat({
                    title,
                    messages: chatMessages,
                    design_id: designId,
                    design_name: designName,
                })
                    .then((saved) => setChatId(saved.id))
                    .catch(() => {});
            }
        }, 600);
        return () => window.clearTimeout(timer);
    }, [chatMessages, chatId, designId, designName]);

    const onConnect = useCallback(
        (params: Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges],
    );

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    // Same drag payload the sidebar shelf used; onDrop below is unchanged.
    const onDragStart = (event: React.DragEvent, nodeType: string) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.effectAllowed = 'move';
    };

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

    // clarification history must stay.
    const onTopologyGenerated = useCallback((newTopology: any, runtime?: GenerationRuntime) => {
        if (newTopology.nodes) setNodes(convertNodes(newTopology.nodes));
        if (newTopology.links) setEdges(convertEdges(newTopology.links));
        setTopologyMeta(newTopology.metadata);
        setTopologyProtocols(newTopology.protocols || []);
        setGenerationRuntime(runtime);
        onSimulationPath({ path: [], success: true });
        setSelectedNodeId(null);
    }, [setNodes, setEdges, onSimulationPath]);

    // Load a saved design's 
    React.useEffect(() => {
        if (initialTopology) onTopologyGenerated(initialTopology);
        
    }, []);

    const buildDomainTopology = React.useCallback(
        (meta?: TopologyMetadata) => ({
            nodes: convertNodesToDomain(nodes),
            links: convertEdgesToDomain(edges),
            protocols: topologyProtocols,
            metadata: meta || topologyMeta || {},
        }),
        [nodes, edges, topologyProtocols, topologyMeta],
    );

    const ensureConfigured = React.useCallback(async (): Promise<TopologyMetadata> => {
        const meta = topologyMeta || {};
        const cisco = meta.cisco_configs || {};
        const cabling = meta.cabling || [];
        if (Object.keys(cisco).length > 0 && cabling.length > 0) {
            return meta;
        }
        setPtPreparing(true);
        const data = await configureTopology(buildDomainTopology(meta));
        const enriched = data?.topology?.metadata as TopologyMetadata | undefined;
        if (!enriched) {
            throw new Error('Configure returned no metadata');
        }
        setTopologyMeta(enriched);
        // Keep host IPs / config from configure response on canvas when present
        const enrichedNodes = data?.topology?.nodes;
        if (Array.isArray(enrichedNodes) && enrichedNodes.length > 0) {
            setNodes(convertNodes(enrichedNodes));
        }
        setPtPreparing(false);
        return enriched;
    }, [topologyMeta, buildDomainTopology, setNodes]);

    const ptDisableReason = React.useMemo(() => {
        if (ptBusy) return 'A Packet Tracer run is already in progress';
        if (!ptStatus) return 'Checking Packet Tracer…';
        if (ptStatus.enabled === false) {
            return ptStatus.detail || 'Packet Tracer feature is disabled';
        }
        if (!ptStatus.ready) {
            if (ptStatus.canvas_empty === false) {
                return ptStatus.detail || 'Packet Tracer canvas is not empty — open a blank project';
            }
            return ptStatus.detail || 'Packet Tracer is not ready';
        }
        if (nodes.length === 0) return 'Canvas has no devices';
        return null;
    }, [ptBusy, ptStatus, nodes.length]);

    const onLaunchPtClick = async () => {
        if (ptRunLock.current || ptBusy) return;
        if (ptDisableReason && ptDisableReason !== 'A Packet Tracer run is already in progress') {
            // Still allow click only when reason is null; guard above
        }
        if (ptDisableReason) return;
        ptRunLock.current = true;
        setPtBusy(true);
        setPtPanelOpen(true);
        setPtResult(null);
        setPtError(null);
        setPtPreparing(false);
        const executionId = newExecutionId();
        try {
            const meta = await ensureConfigured();
            const cisco = meta.cisco_configs || {};
            const cabling = meta.cabling || [];
            if (Object.keys(cisco).length === 0 || cabling.length === 0) {
                throw new Error('No CLI configs or cabling available after configure');
            }
            setPtPreparing(false);
            const topology = buildDomainTopology(meta);
            const result = await executePt({
                topology,
                cisco_configs: cisco,
                configurations: (meta.configurations || {}) as Record<string, unknown>,
                execution_id: executionId,
                design_id: designIdRef.current || null,
                design_name: designName || 'network-design',
            });
            setPtResult(result);
            if (!result.ok) {
                setPtError(result.message || 'Packet Tracer deploy failed');
            }
            if (result.ok && result.execution_id && !designIdRef.current) {
                pendingPtAttachments.current.push(result.execution_id);
            }
            // Refresh readiness (canvas will be occupied after success)
            fetchPtStatus().then(setPtStatus).catch(() => {});
        } catch (e) {
            setPtPreparing(false);
            const msg = e instanceof Error ? e.message : 'Packet Tracer deploy failed';
            setPtError(msg);
            setPtResult({
                execution_id: executionId,
                ok: false,
                stage: 'frontend',
                message: msg,
                devices: [],
                links: [],
                cli_lines: [],
                pings: [],
            });
        } finally {
            setPtBusy(false);
            ptRunLock.current = false;
        }
    };

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
            // Attach orphan PT runs once design exists
            const id = designIdRef.current;
            if (id && pendingPtAttachments.current.length > 0) {
                const ids = [...pendingPtAttachments.current];
                pendingPtAttachments.current = [];
                await Promise.all(ids.map((eid) => attachPtProject(eid, id).catch(() => {})));
            }
        } catch {
            setSaveState('error');
        }
        setTimeout(() => setSaveState('idle'), 2000);
    };

    const onExportClick = async () => {
        const configs = (topologyMeta as { configurations?: Record<string, unknown> } | undefined)
            ?.configurations;
        const hasConfigs = Boolean(configs && Object.keys(configs).length > 0);
        if (hasConfigs) {
            setIsReportOpen(true);
            return;
        }
        setExportState('configuring');
        try {
            const data = await configureTopology({
                nodes: convertNodesToDomain(nodes),
                links: convertEdgesToDomain(edges),
                protocols: topologyProtocols,
                metadata: topologyMeta || {},
            });
            const enriched = data?.topology;
            if (!enriched?.metadata) {
                throw new Error('Configure returned no metadata');
            }
            setTopologyMeta(enriched.metadata);
            setExportState('idle');
            setIsReportOpen(true);
        } catch {
            setExportState('error');
            window.setTimeout(() => setExportState('idle'), 2500);
        }
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
                setChatMessages((prev) => [
                    ...prev,
                    {
                        role: 'assistant',
                        content: 'Design generated. Re-open Ask assistant anytime to see this chat again.',
                    },
                ]);
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
        <div className="flex h-full w-full flex-col bg-[#0a0a0a]">
            <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/10 bg-[#0a0a0a] px-3">
                <div className="flex min-w-0 items-center gap-1">
                    <button
                        type="button"
                        onClick={onBack}
                        aria-label="Back to designs"
                        title="Back to designs"
                        className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
                    >
                        <CaretLeftIcon size={18} weight="regular" />
                    </button>
                    <div className="min-w-0">
                        {editingTitle ? (
                            <input
                                autoFocus
                                defaultValue={designName}
                                aria-label="Design name"
                                onBlur={(event) => {
                                    setEditingTitle(false);
                                    onRename(event.target.value);
                                }}
                                onKeyDown={(event) => {
                                    if (event.key === 'Enter') event.currentTarget.blur();
                                }}
                                className="h-7 w-full bg-transparent text-sm font-semibold text-white outline-none"
                            />
                        ) : (
                            <button
                                type="button"
                                onClick={() => setEditingTitle(true)}
                                title="Rename design"
                                className="block truncate text-left text-sm font-semibold text-white hover:text-zinc-200"
                            >
                                {designName}
                            </button>
                        )}
                        <p className="text-[11px] leading-none text-zinc-500">Design workspace</p>
                    </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                    <button
                        type="button"
                        onClick={onSaveClick}
                        disabled={saveState === 'saving'}
                        className="inline-flex items-center gap-1.5 rounded-md border border-white/10 px-2.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-white/5 hover:text-white disabled:opacity-50"
                    >
                        <FloppyDiskIcon size={13} weight="regular" />
                        {saveState === 'saving' ? 'Saving...' : saveState === 'saved' ? 'Saved' : saveState === 'error' ? 'Save failed' : 'Save'}
                    </button>
                    <button
                        type="button"
                        onClick={onExportClick}
                        disabled={exportState === 'configuring'}
                        className="inline-flex items-center gap-1.5 rounded-md border border-white/10 px-2.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-white/5 hover:text-white disabled:opacity-50"
                    >
                        <FileTextIcon size={13} weight="regular" />
                        {exportState === 'configuring'
                            ? 'Preparing…'
                            : exportState === 'error'
                              ? 'Export failed'
                              : 'Export report'}
                    </button>
                    <button
                        type="button"
                        onClick={onLaunchPtClick}
                        disabled={Boolean(ptDisableReason)}
                        title={ptDisableReason || 'Deploy open design into local Packet Tracer'}
                        className="inline-flex items-center gap-1.5 rounded-md bg-white px-2.5 py-1.5 text-xs font-medium text-zinc-900 transition-opacity hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        <BroadcastIcon size={13} weight="regular" />
                        {ptBusy
                            ? ptPreparing
                                ? 'Preparing…'
                                : 'Running…'
                            : 'Launch PT'}
                    </button>
                </div>
            </div>

            <div className="relative flex min-h-0 flex-1">
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
                    style={{ background: '#0a0a0a' }}
                >
                    <Background
                        variant={BackgroundVariant.Dots}
                        gap={20}
                        size={1.4}
                        color="rgba(255,255,255,0.08)"
                        bgColor="#0a0a0a"
                    />
                    <Controls
                        position="bottom-left"
                        showInteractive={false}
                        className="!m-4 !shadow-none !rounded-lg !overflow-hidden !border !border-white/10"
                        style={{
                            '--xy-controls-button-background-color': '#111111',
                            '--xy-controls-button-background-color-hover': '#1a1a1a',
                            '--xy-controls-button-color': '#a1a1aa',
                            '--xy-controls-button-color-hover': '#ffffff',
                            '--xy-controls-button-border-color': 'rgba(255,255,255,0.08)',
                        } as React.CSSProperties}
                    />
                </ReactFlow>

                <div className="absolute top-3 left-3 z-40">
                    {shelfOpen ? (
                        <div className="w-56 rounded-xl border border-white/10 bg-[#111]/95 shadow-xl backdrop-blur-md">
                            <div className="flex items-center justify-between px-3 pt-3 pb-2">
                                <div>
                                    <h3 className="text-sm font-semibold text-white">Components</h3>
                                    <p className="text-[11px] text-zinc-500">Drag to canvas</p>
                                </div>
                                <button
                                    type="button"
                                    aria-label="Collapse component library"
                                    onClick={() => setShelfOpen(false)}
                                    className="p-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                                >
                                    <CaretLeftIcon size={16} weight="regular" />
                                </button>
                            </div>
                            <div className="flex flex-col gap-1.5 p-2">
                                {DEVICE_CARDS.map(({ type, title, subtitle, Icon, chipClass, titleHoverClass, disabled }) => (
                                    <div
                                        key={type}
                                        draggable={!disabled}
                                        onDragStart={disabled ? undefined : (event) => onDragStart(event, type)}
                                        title={disabled ? 'Coming soon' : undefined}
                                        className={`group flex items-center gap-3 rounded-lg border border-white/5 bg-white/[0.03] p-2.5 transition-colors ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-grab hover:bg-white/[0.06]'}`}
                                    >
                                        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${chipClass}`}>
                                            <Icon size={16} weight="regular" className="text-white" />
                                        </div>
                                        <div className="min-w-0">
                                            <div className={`text-sm font-medium text-zinc-100 transition-colors ${titleHoverClass}`}>{title}</div>
                                            <div className="text-[11px] text-zinc-500">{subtitle}</div>
                                        </div>
                                        {disabled && (
                                            <span className="ml-auto rounded-full border border-white/10 px-1.5 py-0.5 text-[10px] text-zinc-500"></span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <button
                            type="button"
                            onClick={() => setShelfOpen(true)}
                            aria-label="Expand component library"
                            className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#111]/95 px-2.5 py-1.5 text-xs font-medium text-zinc-300 shadow-lg backdrop-blur-md transition-colors hover:bg-white/5 hover:text-white"
                        >
                            <StackIcon size={14} weight="regular" />
                            Components
                        </button>
                    )}
                </div>

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

            <ReportModal
                isOpen={isReportOpen}
                onClose={() => setIsReportOpen(false)}
                onSaveReport={onSaveReport}
                topology={{
                    nodes: convertNodesToDomain(nodes),
                    links: convertEdgesToDomain(edges),
                    protocols: topologyProtocols,
                    metadata: topologyMeta,
                    runtime: generationRuntime,
                    name: designName,
                    id: "topo-gen-1",
                    version: 1,
                    lastUpdated: new Date().toISOString()
                }}
            />
            <PacketTracerPanel
                isOpen={ptPanelOpen}
                onClose={() => setPtPanelOpen(false)}
                running={ptBusy && !ptPreparing}
                preparing={ptPreparing}
                elapsedSec={ptElapsed}
                result={ptResult}
                errorMessage={ptError}
            />
            </div>
        </div>
    );
}

// Helper to convert back to domain model
const convertNodesToDomain = (nodes: Node[]): NetworkNode[] => {
    return nodes.map((n) => {
        const ip = (n.data.ip as string) || '';
        const mask = (n.data as { subnetMask?: string }).subnetMask || undefined;
        const ifaceName =
            n.type === 'host' ? 'FastEthernet0' : n.type === 'router' ? 'GigabitEthernet0/0' : 'FastEthernet0/1';
        return {
            id: n.id,
            type: n.type as NetworkNode['type'],
            name: n.data.label as string,
            x: n.position.x,
            y: n.position.y,
            interfaces: [
                {
                    id: 'eth0',
                    name: ifaceName,
                    ipAddress: ip,
                    subnetMask: mask,
                    // Backend / PT mapper also read snake_case
                    ...({ ip_address: ip, subnet_mask: mask } as object),
                },
            ],
            config: (n.data as { config?: Record<string, unknown> }).config || {},
            // Preserve display label for backends that read `label`
            ...({ label: n.data.label as string } as object),
        } as NetworkNode;
    });
};

const convertEdgesToDomain = (edges: Edge[]): Link[] => {
    return edges.map(e => ({
        id: e.id,
        sourceNodeId: e.source,
        targetNodeId: e.target,
    }));
};
