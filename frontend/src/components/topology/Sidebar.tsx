import React from 'react';
import { Globe, Share2, Monitor, GripVertical, LucideIcon } from 'lucide-react';

type DeviceCardConfig = {
    type: string;
    title: string;
    subtitle: string;
    Icon: LucideIcon;
    iconWrapClass: string;
    iconClass: string;
    titleHoverClass: string;
};

const DEVICE_CARDS: DeviceCardConfig[] = [
    {
        type: 'router',
        title: 'Router',
        subtitle: 'L3 Networking',
        Icon: Globe,
        iconWrapClass: 'bg-teal-500/10 border-teal-500/20',
        iconClass: 'text-teal-400',
        titleHoverClass: 'group-hover:text-teal-300',
    },
    {
        type: 'switch',
        title: 'Switch',
        subtitle: 'L2 Switching',
        Icon: Share2,
        iconWrapClass: 'bg-blue-500/10 border-blue-500/20',
        iconClass: 'text-blue-400',
        titleHoverClass: 'group-hover:text-blue-300',
    },
    {
        type: 'host',
        title: 'End Device',
        subtitle: 'Workstation / Server',
        Icon: Monitor,
        iconWrapClass: 'bg-purple-500/10 border-purple-500/20',
        iconClass: 'text-purple-400',
        titleHoverClass: 'group-hover:text-purple-300',
    },
];

function DeviceCard({
    card,
    onDragStart,
}: {
    card: DeviceCardConfig;
    onDragStart: (event: React.DragEvent, nodeType: string) => void;
}) {
    const { type, title, subtitle, Icon, iconWrapClass, iconClass, titleHoverClass } = card;
    return (
        <div
            className="group bg-[#212127] hover:bg-[#292931] border border-[#E05216]/10 hover:border-[#E05216]/40 rounded-xl p-3 cursor-grab transition-all duration-300 relative overflow-hidden"
            onDragStart={(event) => onDragStart(event, type)}
            draggable
        >
            <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <GripVertical size={14} className="text-slate-500" />
            </div>
            <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center border group-hover:scale-105 transition-transform ${iconWrapClass}`}>
                    <Icon size={20} className={iconClass} />
                </div>
                <div>
                    <div className={`font-bold text-sm text-gray-100 transition-colors ${titleHoverClass}`}>{title}</div>
                    <div className="text-[10px] text-slate-400 font-mono tracking-tight uppercase">{subtitle}</div>
                </div>
            </div>
        </div>
    );
}

export default function Sidebar() {
    const onDragStart = (event: React.DragEvent, nodeType: string) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <aside className="w-64 h-full bg-[#2C2C34] border-r border-[#E05216]/15 p-4 flex flex-col gap-5 shadow-xl z-30">
            <div className="flex items-center gap-2 pb-4 border-b border-[#E05216]/10">
                <span className="text-[#E05216] font-bold tracking-wider text-xs uppercase">Component Library</span>
            </div>

            <div className="flex flex-col gap-3">
                {DEVICE_CARDS.map((card) => (
                    <DeviceCard key={card.type} card={card} onDragStart={onDragStart} />
                ))}
            </div>

            <div className="mt-auto p-4 rounded-lg bg-[#212127]/50 border border-[#E05216]/10 text-center">
                <p className="text-[10px] text-slate-400 leading-relaxed">
                    Drag components to the canvas to build your topology manually or use AI generation.
                </p>
            </div>
        </aside>
    );
}
