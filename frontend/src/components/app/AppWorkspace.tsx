'use client';

import { useEffect, useState } from 'react';
import Sidebar, { type AppView } from '@/components/topology/Sidebar';
import TopologyEditor from '@/components/topology/TopologyEditor';
import HomeView from '@/components/home/HomeView';
import FavouritesView from '@/components/home/FavouritesView';
import DocumentationView from '@/components/home/DocumentationView';
import {
    createDesign,
    deleteDesign,
    listDesigns,
    openDesign,
    toggleFavourite,
    updateDesign,
    type Design,
} from '@/lib/api';

export default function AppWorkspace({
    view,
    onViewChange,
    activeDesign,
    onActiveDesignChange,
}: {
    view: AppView;
    onViewChange: (view: AppView) => void;
    activeDesign: { id: string | null; name: string };
    onActiveDesignChange: (design: { id: string | null; name: string }) => void;
}) {
    const [canvasKey, setCanvasKey] = useState(0);
    const [designs, setDesigns] = useState<Design[]>([]);
    const [pendingTopology, setPendingTopology] = useState<any>(null);
    const [deleteError, setDeleteError] = useState<string | null>(null);

    useEffect(() => {
        if (view !== 'home' && view !== 'favourites') return;
        listDesigns().then(setDesigns).catch(() => {});
    }, [view]);

    const openBlankCanvas = () => {
        setPendingTopology(null);
        onActiveDesignChange({ id: null, name: 'Untitled Design' });
        setCanvasKey((key) => key + 1);
        onViewChange('canvas');
    };

    const openExistingDesign = async (id: string) => {
        try {
            const design = await openDesign(id);
            setPendingTopology(design.topology);
            onActiveDesignChange({ id: design.id, name: design.name });
            setCanvasKey((key) => key + 1);
            onViewChange('canvas');
        } catch {
            // stay on the current view if the design cannot be opened
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

    return (
        <div className="flex h-full w-full">
            <Sidebar activeView={view} onNavigate={onViewChange} />
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
                        onDelete={onDeleteDesign}
                    />
                )}
                {view === 'canvas' && (
                    <TopologyEditor
                        key={canvasKey}
                        initialTopology={pendingTopology}
                        onSave={handleSave}
                    />
                )}
                {view === 'favourites' && (
                    <FavouritesView
                        designs={designs}
                        onOpen={openExistingDesign}
                        onToggleFavourite={onToggleFavourite}
                        onDelete={onDeleteDesign}
                    />
                )}
                {view === 'documentation' && <DocumentationView />}
            </div>
        </div>
    );
}
