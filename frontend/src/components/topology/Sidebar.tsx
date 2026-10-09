'use client';

import { useEffect, useState } from 'react';
import { HouseIcon, StarIcon, BookOpenIcon, SidebarSimpleIcon, FolderIcon, FileTextIcon, ChatCircleIcon, CheckCircleIcon } from '@phosphor-icons/react';

export type AppView = 'home' | 'canvas' | 'favourites' | 'documentation';

export default function Sidebar({
    activeView,
    onNavigate,
}: {
    activeView: AppView;
    onNavigate: (view: 'home' | 'favourites' | 'documentation') => void;
}) {
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        const mediaQuery = window.matchMedia('(max-width: 1023px)');
        const collapseIfNeeded = () => {
            if (mediaQuery.matches) setExpanded(false);
        };
        collapseIfNeeded();
        mediaQuery.addEventListener('change', collapseIfNeeded);
        return () => mediaQuery.removeEventListener('change', collapseIfNeeded);
    }, []);

    return (
        <aside
            className={`h-full bg-chrome-surface border-r border-[#14213D]/15 flex flex-col gap-4 shadow-xl z-30 shrink-0 font-sans transition-[width] duration-300 ease-in-out ${expanded ? 'w-64 overflow-hidden p-4' : 'w-[72px] overflow-visible p-2'}`}
        >
            <div className={`flex items-center ${expanded ? 'justify-end' : 'justify-center'}`}>
                <button
                    type="button"
                    aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
                    aria-expanded={expanded}
                    onClick={() => setExpanded((open) => !open)}
                    className="p-2 rounded-lg text-white hover:bg-white/10 transition-colors"
                >
                    <SidebarSimpleIcon size={20} weight="regular" mirrored={expanded} />
                </button>
            </div>

            <div className={`flex items-center pt-3 pb-3 ${expanded ? 'gap-2' : 'justify-center'}`}>
                {expanded && (
                    <span className="text-xs font-bold tracking-wide text-slate-300 whitespace-nowrap">EXPLORE</span>
                )}
            </div>

            <nav className="flex flex-col gap-1.5">
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-medium cursor-pointer ${activeView === 'home' ? 'text-white bg-white/8' : 'text-slate-300 hover:bg-white/5 hover:text-white'} ${expanded ? 'gap-3.5 px-3 py-3' : 'justify-center px-2 py-3'}`}
                    title="Home"
                    onClick={() => onNavigate('home')}
                >
                    <HouseIcon size={20} weight="regular" className="shrink-0" />
                    {expanded && 'Home'}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Home
                        </span>
                    )}
                </div>
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-medium cursor-pointer transition-colors ${activeView === 'favourites' ? 'text-white bg-white/8' : 'text-slate-300 hover:bg-white/5 hover:text-white'} ${expanded ? 'gap-3.5 px-3 py-3' : 'justify-center px-2 py-3'}`}
                    title="Favourites"
                    onClick={() => onNavigate('favourites')}
                >
                    <StarIcon size={20} weight="regular" className="shrink-0" />
                    {expanded && 'Favourites'}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Favourites
                        </span>
                    )}
                </div>
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-medium cursor-not-allowed text-slate-500 ${expanded ? 'gap-3.5 px-3 py-3' : 'justify-center px-2 py-3'}`}
                    title="Coming soon"
                >
                    <FolderIcon size={20} weight="regular" className="shrink-0" />
                    {expanded && 'Projects'}
                    {expanded && (
                        <span className="ml-auto rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">Soon</span>
                    )}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Projects (coming soon)
                        </span>
                    )}
                </div>
            </nav>

            <div className={`flex items-center pt-3 pb-3 ${expanded ? 'gap-2' : 'justify-center'}`}>
                {expanded && (
                    <span className="text-xs font-bold tracking-wide text-slate-300 whitespace-nowrap">WORKSPACE</span>
                )}
            </div>

            <nav className="flex flex-col gap-1.5">
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-medium cursor-not-allowed text-slate-500 ${expanded ? 'gap-3.5 px-3 py-3' : 'justify-center px-2 py-3'}`}
                    title="Coming soon"
                >
                    <FileTextIcon size={20} weight="regular" className="shrink-0" />
                    {expanded && 'Reports'}
                    {expanded && (
                        <span className="ml-auto rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">Soon</span>
                    )}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Reports (coming soon)
                        </span>
                    )}
                </div>
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-medium cursor-not-allowed text-slate-500 ${expanded ? 'gap-3.5 px-3 py-3' : 'justify-center px-2 py-3'}`}
                    title="Coming soon"
                >
                    <ChatCircleIcon size={20} weight="regular" className="shrink-0" />
                    {expanded && 'Chats'}
                    {expanded && (
                        <span className="ml-auto rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">Soon</span>
                    )}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Chats (coming soon)
                        </span>
                    )}
                </div>
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-medium cursor-not-allowed text-slate-500 ${expanded ? 'gap-3.5 px-3 py-3' : 'justify-center px-2 py-3'}`}
                    title="Coming soon"
                >
                    <CheckCircleIcon size={20} weight="regular" className="shrink-0" />
                    {expanded && 'Validation'}
                    {expanded && (
                        <span className="ml-auto rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">Soon</span>
                    )}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Validation (coming soon)
                        </span>
                    )}
                </div>
            </nav>

            <div className={`flex items-center pt-3 pb-3 ${expanded ? 'gap-2' : 'justify-center'}`}>
                {expanded && (
                    <span className="text-xs font-bold tracking-wide text-slate-300 whitespace-nowrap">SUPPORT</span>
                )}
            </div>

            <nav className="flex flex-col gap-1.5">
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-medium cursor-pointer transition-colors ${activeView === 'documentation' ? 'text-white bg-white/8' : 'text-slate-300 hover:bg-white/5 hover:text-white'} ${expanded ? 'gap-3.5 px-3 py-3' : 'justify-center px-2 py-3'}`}
                    title="Documentation"
                    onClick={() => onNavigate('documentation')}
                >
                    <BookOpenIcon size={20} weight="regular" className="shrink-0" />
                    {expanded && 'Documentation'}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Documentation
                        </span>
                    )}
                </div>
            </nav>

        </aside>
    );
}
