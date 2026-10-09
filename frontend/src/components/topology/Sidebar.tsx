'use client';

import { useEffect, useState, type ReactNode } from 'react';
import {
    SidebarSimpleIcon,
    FolderIcon,
    FileTextIcon,
    PlusIcon,
    CopySimpleIcon,
    BookOpenIcon,
} from '@phosphor-icons/react';
import { LayoutGrid, Bot, Zap, ChevronDown } from 'lucide-react';

export type AppView =
    | 'home'
    | 'canvas'
    | 'favourites'
    | 'templates'
    | 'projects'
    | 'reports'
    | 'chats'
    | 'documentation';

function NavTooltip({ label }: { label: string }) {
    return (
        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-white/10 bg-[#111] px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
            {label}
        </span>
    );
}

export default function Sidebar({
    activeView,
    onNavigate,
    onCreate,
}: {
    activeView: AppView;
    onNavigate: (view: AppView) => void;
    onCreate: () => void;
}) {
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        const mediaQuery = window.matchMedia('(max-width: 1023px)');
        const sync = () => setExpanded(!mediaQuery.matches);
        sync();
        mediaQuery.addEventListener('change', sync);
        return () => mediaQuery.removeEventListener('change', sync);
    }, []);

    const navItem = (
        opts: {
            label: string;
            active?: boolean;
            disabled?: boolean;
            onClick?: () => void;
            icon: ReactNode;
        },
    ) => (
        <div
            className={`relative group flex items-center rounded-lg text-sm font-medium transition-colors ${
                opts.disabled
                    ? 'cursor-not-allowed text-zinc-500'
                    : opts.active
                        ? 'cursor-pointer bg-white/8 text-white'
                        : 'cursor-pointer text-zinc-300 hover:bg-white/5 hover:text-white'
            } ${expanded ? 'gap-3 px-3 py-2.5' : 'justify-center px-2 py-2.5'}`}
            title={opts.disabled ? 'Coming soon' : opts.label}
            onClick={opts.disabled ? undefined : opts.onClick}
        >
            {opts.icon}
            {expanded && <span className="truncate">{opts.label}</span>}
            {!expanded && <NavTooltip label={opts.disabled ? `${opts.label} (coming soon)` : opts.label} />}
        </div>
    );

    return (
        <aside
            className={`z-30 flex h-full shrink-0 flex-col border-r border-white/10 bg-[#0a0a0a] font-sans transition-[width] duration-300 ease-in-out ${expanded ? 'w-64 overflow-y-auto overflow-x-hidden p-3 custom-scrollbar' : 'w-[72px] overflow-visible p-2'}`}
        >
            <div className={`mb-3 flex ${expanded ? 'flex-col gap-2' : 'flex-col items-center gap-2'}`}>
                <div className={`flex items-center ${expanded ? 'justify-end' : 'justify-center'}`}>
                    <button
                        type="button"
                        aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
                        aria-expanded={expanded}
                        onClick={() => setExpanded((open) => !open)}
                        className="rounded-lg p-2 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
                    >
                        <SidebarSimpleIcon size={18} weight="regular" mirrored={expanded} />
                    </button>
                </div>
                {expanded ? (
                    <button
                        type="button"
                        onClick={onCreate}
                        className="inline-flex w-full items-center justify-between gap-2 rounded-lg bg-zinc-200 px-3 py-2.5 text-xs font-medium text-zinc-900 transition-colors hover:bg-white"
                    >
                        <span className="inline-flex min-w-0 items-center gap-1.5 whitespace-nowrap">
                            <PlusIcon size={14} weight="regular" className="shrink-0" />
                            New network design
                        </span>
                        <ChevronDown size={14} className="shrink-0 text-zinc-600" />
                    </button>
                ) : (
                    <button
                        type="button"
                        onClick={onCreate}
                        aria-label="New network design"
                        title="New network design"
                        className="flex items-center justify-center rounded-lg bg-zinc-200 p-2.5 text-zinc-900 transition-colors hover:bg-white"
                    >
                        <PlusIcon size={16} weight="regular" />
                    </button>
                )}
            </div>

            <nav className="flex flex-col gap-0.5">
                {navItem({
                    label: 'Home',
                    active: activeView === 'home',
                    onClick: () => onNavigate('home'),
                    icon: <LayoutGrid size={18} className="shrink-0" />,
                })}
                {navItem({
                    label: 'Projects',
                    active: activeView === 'projects',
                    onClick: () => onNavigate('projects'),
                    icon: <FolderIcon size={18} weight="regular" className="shrink-0" />,
                })}
                {navItem({
                    label: 'Templates',
                    active: activeView === 'templates',
                    onClick: () => onNavigate('templates'),
                    icon: <CopySimpleIcon size={18} weight="regular" className="shrink-0" />,
                })}
            </nav>

            <div className={`mt-4 mb-2 ${expanded ? 'px-1' : 'flex justify-center'}`}>
                {expanded ? (
                    <div className="border-t border-white/10 px-2 pt-3">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Workspace</span>
                    </div>
                ) : (
                    <div className="h-px w-6 bg-white/10" />
                )}
            </div>

            <nav className="flex flex-col gap-0.5">
                {navItem({
                    label: 'Reports',
                    active: activeView === 'reports',
                    onClick: () => onNavigate('reports'),
                    icon: <FileTextIcon size={18} weight="regular" className="shrink-0" />,
                })}
                {navItem({
                    label: 'Chats',
                    active: activeView === 'chats',
                    onClick: () => onNavigate('chats'),
                    icon: <Bot size={18} className="shrink-0" />,
                })}
                {navItem({
                    label: 'Validation',
                    disabled: true,
                    icon: <Zap size={18} className="shrink-0" />,
                })}
            </nav>

            <div className={`mt-4 mb-2 ${expanded ? 'px-1' : 'flex justify-center'}`}>
                {expanded ? (
                    <div className="border-t border-white/10 px-2 pt-3">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Support</span>
                    </div>
                ) : (
                    <div className="h-px w-6 bg-white/10" />
                )}
            </div>

            <nav className="flex flex-col gap-0.5">
                {navItem({
                    label: 'Documentation',
                    active: activeView === 'documentation',
                    onClick: () => onNavigate('documentation'),
                    icon: <BookOpenIcon size={18} weight="regular" className="shrink-0" />,
                })}
            </nav>
        </aside>
    );
}
