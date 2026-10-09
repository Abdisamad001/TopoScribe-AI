'use client';

import { useEffect, useState } from 'react';
import Sidebar, { type AppView } from '@/components/topology/Sidebar';
import TopologyEditor from '@/components/topology/TopologyEditor';
import HomeView from '@/components/home/HomeView';
import FavouritesView from '@/components/home/FavouritesView';
import TemplatesView from '@/components/home/TemplatesView';
import ProjectsView from '@/components/home/ProjectsView';
import ReportsView from '@/components/home/ReportsView';
import ChatsView from '@/components/home/ChatsView';
import DocumentationView from '@/components/home/DocumentationView';
import {
    createDesign,
    createProject,
    createReport,
    deleteChat,
    deleteDesign,
    deleteProject,
    deleteReport,
    listChats,
    listDesigns,
    listProjects,
    listReports,
    openDesign,
    toggleFavourite,
    toggleTemplate,
    updateDesign,
    updateProject,
    type Design,
    type Project,
    type SavedChat,
    type SavedReport,
} from '@/lib/api';

export default function AppWorkspace({
    view,
    onViewChange,
    activeDesign,
    onActiveDesignChange,
    onRenameDesign,
    searchQuery = '',
}: {
    view: AppView;
    onViewChange: (view: AppView) => void;
    activeDesign: { id: string | null; name: string };
    onActiveDesignChange: (design: { id: string | null; name: string }) => void;
    onRenameDesign: (name: string) => void;
    searchQuery?: string;
}) {
    const [canvasKey, setCanvasKey] = useState(0);
    const [designs, setDesigns] = useState<Design[]>([]);
    const [projects, setProjects] = useState<Project[]>([]);
    const [reports, setReports] = useState<SavedReport[]>([]);
    const [chats, setChats] = useState<SavedChat[]>([]);
    const [pendingTopology, setPendingTopology] = useState<any>(null);
    const [pendingChat, setPendingChat] = useState<{ id: string; messages: SavedChat['messages'] } | null>(null);
    const [deleteError, setDeleteError] = useState<string | null>(null);

    useEffect(() => {
        if (view === 'canvas' || view === 'documentation') return;
        listDesigns().then(setDesigns).catch(() => {});
        if (view === 'projects') listProjects().then(setProjects).catch(() => {});
        if (view === 'reports') listReports().then(setReports).catch(() => {});
        if (view === 'chats') listChats().then(setChats).catch(() => {});
    }, [view]);

    useEffect(() => {
        if (!searchQuery.trim()) return;
        const searchable: AppView[] = [
            'home',
            'favourites',
            'templates',
            'projects',
            'reports',
            'chats',
        ];
        if (searchable.includes(view)) return;
        onViewChange('home');
    }, [searchQuery, view, onViewChange]);

    const openBlankCanvas = () => {
        setPendingTopology(null);
        setPendingChat(null);
        onActiveDesignChange({ id: null, name: 'Untitled Design' });
        setCanvasKey((key) => key + 1);
        onViewChange('canvas');
    };

    const openExistingDesign = async (id: string) => {
        try {
            const design = await openDesign(id);
            setPendingTopology(design.topology);
            // Restore the latest Ask-assistant thread linked to this design, if any.
            try {
                const allChats = await listChats();
                const linked = allChats.find((chat) => chat.design_id === id);
                setPendingChat(linked ? { id: linked.id, messages: linked.messages } : null);
            } catch {
                setPendingChat(null);
            }
            onActiveDesignChange({ id: design.id, name: design.name });
            setCanvasKey((key) => key + 1);
            onViewChange('canvas');
        } catch {
            // stay on the current view if the design cannot be opened
        }
    };

    // Opening a template starts a new unsaved design so the shared template stays unchanged.
    const openTemplateAsNew = async (id: string) => {
        try {
            const design = await openDesign(id);
            setPendingTopology(design.topology);
            setPendingChat(null);
            onActiveDesignChange({ id: null, name: `${design.name} copy` });
            setCanvasKey((key) => key + 1);
            onViewChange('canvas');
        } catch {
            // stay on templates if open fails
        }
    };

    const openSavedChat = async (chat: SavedChat) => {
        try {
            if (chat.design_id) {
                const design = await openDesign(chat.design_id);
                setPendingTopology(design.topology);
                onActiveDesignChange({ id: design.id, name: design.name });
            } else {
                setPendingTopology(null);
                onActiveDesignChange({
                    id: null,
                    name: chat.design_name || 'Untitled Design',
                });
            }
            setPendingChat({ id: chat.id, messages: chat.messages });
            setCanvasKey((key) => key + 1);
            onViewChange('canvas');
        } catch {
            // stay on chats if open fails
        }
    };

    const onToggleFavourite = async (id: string) => {
        try {
            const updated = await toggleFavourite(id);
            setDesigns((current) => current.map((d) => (d.id === updated.id ? updated : d)));
        } catch {
            // keep the current flag if the toggle fails
        }
    };

    const onToggleTemplate = async (id: string) => {
        try {
            const updated = await toggleTemplate(id);
            setDesigns((current) => current.map((d) => (d.id === updated.id ? updated : d)));
        } catch {
            // keep the current flag if the toggle fails
        }
    };

    // Templates trash: drop the template mark only. The design itself stays on Home.
    const onRemoveFromTemplates = async (id: string) => {
        const design = designs.find((d) => d.id === id);
        if (!design?.is_template) return;
        await onToggleTemplate(id);
    };

    const onDeleteDesign = (id: string) => {
        const index = designs.findIndex((d) => d.id === id);
        const removed = index >= 0 ? designs[index] : undefined;
        setDesigns((current) => current.filter((d) => d.id !== id));
        setDeleteError(null);
        deleteDesign(id).catch(() => {
            if (removed) {
                setDesigns((current) => {
                    const next = [...current];
                    next.splice(Math.min(index, next.length), 0, removed);
                    return next;
                });
            }
            setDeleteError('Failed to delete design');
            window.setTimeout(() => setDeleteError(null), 3000);
        });
    };

    const handleSave = async (topology: any) => {
        if (activeDesign.id) {
            await updateDesign(activeDesign.id, { name: activeDesign.name, topology });
        } else {
            const created = await createDesign(activeDesign.name, topology);
            onActiveDesignChange({ id: created.id, name: created.name });
        }
    };

    const handleSaveReport = (name: string, markdown: string) => {
        createReport(name, markdown, activeDesign.id)
            .then((saved) => setReports((current) => [saved, ...current]))
            .catch(() => {});
    };

    return (
        <div className="flex h-full w-full">
            {view !== 'canvas' && (
                <Sidebar
                    activeView={view}
                    onNavigate={onViewChange}
                    onCreate={openBlankCanvas}
                />
            )}
            <div className="relative h-full min-w-0 flex-1">
                {deleteError && (
                    <div className="pointer-events-none absolute top-4 left-1/2 z-50 -translate-x-1/2">
                        <span className="rounded-full border border-red-500/20 bg-red-500/10 px-4 py-2 text-xs text-red-300 shadow-lg backdrop-blur-sm">
                            {deleteError}
                        </span>
                    </div>
                )}
                {view === 'home' && (
                    <HomeView
                        designs={designs}
                        onCreate={openBlankCanvas}
                        onOpen={openExistingDesign}
                        onToggleFavourite={onToggleFavourite}
                        onToggleTemplate={onToggleTemplate}
                        onDelete={onDeleteDesign}
                        onOpenFavourites={() => onViewChange('favourites')}
                        searchQuery={searchQuery}
                    />
                )}
                {view === 'canvas' && (
                    <TopologyEditor
                        key={canvasKey}
                        initialTopology={pendingTopology}
                        onSave={handleSave}
                        designId={activeDesign.id}
                        designName={activeDesign.name}
                        onRename={onRenameDesign}
                        onBack={() => onViewChange('home')}
                        onSaveReport={handleSaveReport}
                        initialChat={pendingChat}
                    />
                )}
                {view === 'favourites' && (
                    <FavouritesView
                        designs={designs}
                        onOpen={openExistingDesign}
                        onToggleFavourite={onToggleFavourite}
                        onToggleTemplate={onToggleTemplate}
                        onDelete={onDeleteDesign}
                        searchQuery={searchQuery}
                    />
                )}
                {view === 'templates' && (
                    <TemplatesView
                        designs={designs}
                        onOpen={openTemplateAsNew}
                        onToggleFavourite={onToggleFavourite}
                        onToggleTemplate={onToggleTemplate}
                        onDelete={onRemoveFromTemplates}
                        searchQuery={searchQuery}
                    />
                )}
                {view === 'projects' && (
                    <ProjectsView
                        projects={projects}
                        designs={designs}
                        searchQuery={searchQuery}
                        onCreate={(name) => {
                            createProject(name)
                                .then((created) => setProjects((current) => [created, ...current]))
                                .catch(() => {});
                        }}
                        onDelete={(id) => {
                            setProjects((current) => current.filter((p) => p.id !== id));
                            deleteProject(id).catch(() => {
                                listProjects().then(setProjects).catch(() => {});
                            });
                        }}
                        onAddDesign={(projectId, designId) => {
                            const project = projects.find((p) => p.id === projectId);
                            if (!project || project.design_ids.includes(designId)) return;
                            const design_ids = [...project.design_ids, designId];
                            updateProject(projectId, { design_ids })
                                .then((updated) =>
                                    setProjects((current) =>
                                        current.map((p) => (p.id === updated.id ? updated : p)),
                                    ),
                                )
                                .catch(() => {});
                        }}
                        onRemoveDesign={(projectId, designId) => {
                            const project = projects.find((p) => p.id === projectId);
                            if (!project) return;
                            const design_ids = project.design_ids.filter((id) => id !== designId);
                            updateProject(projectId, { design_ids })
                                .then((updated) =>
                                    setProjects((current) =>
                                        current.map((p) => (p.id === updated.id ? updated : p)),
                                    ),
                                )
                                .catch(() => {});
                        }}
                        onOpenDesign={openExistingDesign}
                    />
                )}
                {view === 'reports' && (
                    <ReportsView
                        reports={reports}
                        searchQuery={searchQuery}
                        onDelete={(id) => {
                            setReports((current) => current.filter((r) => r.id !== id));
                            deleteReport(id).catch(() => {
                                listReports().then(setReports).catch(() => {});
                            });
                        }}
                    />
                )}
                {view === 'chats' && (
                    <ChatsView
                        chats={chats}
                        searchQuery={searchQuery}
                        onOpen={openSavedChat}
                        onDelete={(id) => {
                            setChats((current) => current.filter((c) => c.id !== id));
                            deleteChat(id).catch(() => {
                                listChats().then(setChats).catch(() => {});
                            });
                        }}
                    />
                )}
                {view === 'documentation' && <DocumentationView />}
            </div>
        </div>
    );
}
