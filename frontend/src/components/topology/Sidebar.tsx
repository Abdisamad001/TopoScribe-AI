'use client';

import React, { useEffect, useState } from 'react';
import { GlobeIcon, ShareNetworkIcon, DesktopIcon, DotsSixVerticalIcon, StackIcon, CursorClickIcon, HouseIcon, StarIcon, BookOpenIcon, SidebarSimpleIcon, type Icon } from '@phosphor-icons/react';

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
        iconWrapClass: 'bg-teal-500/10 border-teal-500/20',
        iconClass: 'text-teal-400',
        titleHoverClass: 'group-hover:text-teal-300',
    },
    {
        type: 'switch',
        title: 'Switch',
        subtitle: 'L2 Switching',
        Icon: ShareNetworkIcon,
        iconWrapClass: 'bg-blue-500/10 border-blue-500/20',
        iconClass: 'text-blue-400',
        titleHoverClass: 'group-hover:text-blue-300',
    },
    {
        type: 'host',
        title: 'End Device',
        subtitle: 'Workstation / Server',
        Icon: DesktopIcon,
        iconWrapClass: 'bg-purple-500/10 border-purple-500/20',
        iconClass: 'text-purple-400',
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
            className={`group bg-[#212127] hover:bg-[#292931] border border-[#14213D]/10 hover:border-[#14213D]/40 rounded-xl cursor-grab transition-all duration-300 relative shadow-md shadow-black/20 ${compact ? 'overflow-visible p-2 flex justify-center' : 'overflow-hidden p-3'}`}
            onDragStart={(event) => onDragStart(event, type)}
            draggable
            title={compact ? title : undefined}
        >
            {!compact && (
                <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <DotsSixVerticalIcon size={14} weight="regular" className="text-slate-500" />
                </div>
            )}
            <div className={`flex items-center ${compact ? 'justify-center' : 'gap-3'}`}>
                <div className={`${compact ? 'w-9 h-9' : 'w-11 h-11'} rounded-lg flex items-center justify-center border group-hover:scale-105 transition-transform ${iconWrapClass}`}>
                    <Icon size={20} weight="regular" className={iconClass} />
                </div>
                {compact && (
                    <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                        {title}
                    </span>
                )}
                {!compact && (
                    <div>
                        <div className={`font-semibold text-sm text-gray-100 transition-colors ${titleHoverClass}`}>{title}</div>
                        <div className="text-xs font-normal text-slate-400">{subtitle}</div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function Sidebar() {
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

            <nav className="flex flex-col gap-1.5">
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-semibold text-white bg-chrome-navy/40 ${expanded ? 'gap-3 px-3 py-2' : 'justify-center px-2 py-2'}`}
                    title="Home"
                >
                    <HouseIcon size={16} weight="regular" className="shrink-0" />
                    {expanded && 'Home'}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Home
                        </span>
                    )}
                </div>
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-semibold text-white hover:bg-white/5 transition-colors cursor-pointer ${expanded ? 'gap-3 px-3 py-2' : 'justify-center px-2 py-2'}`}
                    title="Favourites"
                >
                    <StarIcon size={16} weight="regular" className="shrink-0" />
                    {expanded && 'Favourites'}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Favourites
                        </span>
                    )}
                </div>
                <div
                    className={`relative group flex items-center rounded-lg text-sm font-semibold text-white hover:bg-white/5 transition-colors cursor-pointer ${expanded ? 'gap-3 px-3 py-2' : 'justify-center px-2 py-2'}`}
                    title="Documentation"
                >
                    <BookOpenIcon size={16} weight="regular" className="shrink-0" />
                    {expanded && 'Documentation'}
                    {!expanded && (
                        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-chrome-navy/40 bg-chrome-elevated px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                            Documentation
                        </span>
                    )}
                </div>
            </nav>

            <div className={`flex items-center border-t border-white/10 pt-3 pb-3 ${expanded ? 'gap-2' : 'justify-center'}`}>
                <StackIcon size={14} weight="regular" className="text-white shrink-0" />
                {expanded && (
                    <span className="text-xs font-medium tracking-normal text-slate-400 whitespace-nowrap">Component Library</span>
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
                    <p className="text-[10px] text-slate-400 leading-relaxed">
                        Drag components to the canvas to build your topology manually or use AI generation.
                    </p>
                </div>
            )}
        </aside>
    );
}
