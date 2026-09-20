'use client';

import { useState } from 'react';
import Sidebar, { type AppView } from '@/components/topology/Sidebar';
import TopologyEditor from '@/components/topology/TopologyEditor';
import HomeView from '@/components/home/HomeView';
import FavouritesView from '@/components/home/FavouritesView';
import DocumentationView from '@/components/home/DocumentationView';
import { getPlaceholderDesigns } from '@/lib/designs';

export default function AppWorkspace() {
    const [view, setView] = useState<AppView>('home');
    const [canvasKey, setCanvasKey] = useState(0);
    const [designs, setDesigns] = useState(getPlaceholderDesigns);

    const openCanvas = () => {
        setCanvasKey((key) => key + 1);
        setView('canvas');
    };

    const toggleFavourite = (id: string) => {
        setDesigns((current) =>
            current.map((design) =>
                design.id === id ? { ...design, favourited: !design.favourited } : design
            )
        );
    };

    return (
        <div className="flex h-full w-full">
            <Sidebar activeView={view} onNavigate={setView} />
            <div className="h-full min-w-0 flex-1">
                {view === 'home' && (
                    <HomeView
                        designs={designs}
                        onCreate={openCanvas}
                        onOpen={() => openCanvas()}
                        onToggleFavourite={toggleFavourite}
                    />
                )}
                {view === 'canvas' && <TopologyEditor key={canvasKey} />}
                {view === 'favourites' && (
                    <FavouritesView
                        designs={designs}
                        onOpen={() => openCanvas()}
                        onToggleFavourite={toggleFavourite}
                    />
                )}
                {view === 'documentation' && <DocumentationView />}
            </div>
        </div>
    );
}
