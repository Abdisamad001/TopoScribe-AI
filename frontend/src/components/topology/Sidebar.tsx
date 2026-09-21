'use client';

import React, { useEffect, useState } from 'react';
import { GlobeIcon, ShareNetworkIcon, DesktopIcon, CursorClickIcon, HouseIcon, StarIcon, BookOpenIcon, SidebarSimpleIcon, type Icon } from '@phosphor-icons/react';

type DeviceCardConfig = {
    type: string;
    title: string;
    subtitle: string;
    Icon: Icon;
    iconWrapClass: string;
    iconClass: string;
    titleHoverClass: string;
};

const DEVICE_CARDS: DeviceCardConfig[] = [
    {
        type: 'router',
        title: 'Router',
        subtitle: 'L3 Networking',
        Icon: GlobeIcon,
        iconWrapClass: 'bg-teal-500',
        iconClass: 'text-white',
        titleHoverClass: 'group-hover:text-teal-300',
    },
    {
        type: 'switch',
        title: 'Switch',
        subtitle: 'L2 Switching',
        Icon: ShareNetworkIcon,
        iconWrapClass: 'bg-blue-500',
        iconClass: 'text-white',
        titleHoverClass: 'group-hover:text-blue-300',
    },
    {
        type: 'host',
        title: 'End Device',
        subtitle: 'Workstation / Server',
        Icon: DesktopIcon,
        iconWrapClass: 'bg-purple-500',
        iconClass: 'text-white',
        titleHoverClass: 'group-hover:text-purple-300',
    },
];

function DeviceCard({
    card,
    onDragStart,
    compact,
}: {
    card: DeviceCardConfig;
    onDragStart: (event: React.DragEvent, nodeType: string) => void;
    compact: boolean;
}) {
    const { type, title, subtitle, Icon, iconWrapClass, iconClass, titleHoverClass } = card;
    return (
        <div
            className={`group bg-[#212127] hover:bg-[#292931] rounded-xl cursor-grab transition-all duration-300 relative ${compact ? 'overflow-visible px-2 py-3 flex justify-center' : 'overflow-hidden px-3 py-3'}`}
            onDragStart={(event) => onDragStart(event, type)}
            draggable
            title={compact ? title : undefined}
        >
            <div className={`flex items-center ${compact ? 'justify-center' : 'gap-3.5'}`}>
                <div className={`${compact ? 'w-9 h-9' : 'w-11 h-11'} rounded-lg flex items-center justify-center ${iconWrapClass}`}>
                    <Icon size={20} weight="regular" className={iconClass} />
                </div>
                {compact && (
                    <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                        {title}
                    </span>
                )}
                {!compact && (
                    <div>
                        <div className={`font-semibold text-sm text-gray-100 transition-colors ${titleHoverClass}`}>{title}</div>
                        <div className="text-xs font-normal text-slate-300">{subtitle}</div>
                    </div>
                )}
            </div>
        </div>
    );
}

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

    const onDragStart = (event: React.DragEvent, nodeType: string) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.effectAllowed = 'move';
    };

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

            {activeView === 'canvas' && (
                <>
                    <div className={`flex items-center pt-3 pb-3 ${expanded ? 'gap-2' : 'justify-center'}`}>
                        {expanded && (
                            <span className="text-xs font-bold tracking-wide text-slate-300 whitespace-nowrap">COMPONENTS</span>
                        )}
                    </div>

                    <div className="flex flex-col gap-3">
                        {DEVICE_CARDS.map((card) => (
                            <DeviceCard key={card.type} card={card} onDragStart={onDragStart} compact={!expanded} />
                        ))}
                    </div>

                    {expanded && (
                        <div className="mt-auto p-3 rounded-lg bg-[#212127]/50 border border-[#14213D]/10 flex items-start gap-2.5">
                            <CursorClickIcon size={14} weight="regular" className="text-slate-500 mt-0.5 shrink-0" />
                            <p className="text-xs text-slate-300 leading-relaxed">
                                Drag components to the canvas to build your topology manually or use AI generation.
                            </p>
                        </div>
                    )}
                </>
            )}
        </aside>
    );
}
