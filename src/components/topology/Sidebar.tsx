import React from 'react';
import { Globe, Share2, Monitor, GripVertical } from 'lucide-react';

export default function Sidebar() {
    const onDragStart = (event: React.DragEvent, nodeType: string) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <aside className="w-64 h-full bg-[#1C2F45] border-r border-[#3DD6B5]/15 p-4 flex flex-col gap-5 shadow-xl z-30">
            <div className="flex items-center gap-2 pb-4 border-b border-[#3DD6B5]/10">
                <span className="text-teal-400 font-bold tracking-wider text-xs uppercase">Component Library</span>
            </div>

            <div className="flex flex-col gap-3">
                {/* Router Card */}
                <div
                    className="group bg-[#142338] hover:bg-[#1A2C42] border border-[#3DD6B5]/10 hover:border-[#3DD6B5]/40 rounded-xl p-3 cursor-grab transition-all duration-300 relative overflow-hidden"
                    onDragStart={(event) => onDragStart(event, 'router')}
                    draggable
                >
                    <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <GripVertical size={14} className="text-slate-500" />
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-teal-500/10 flex items-center justify-center border border-teal-500/20 group-hover:scale-105 transition-transform">
                            <Globe size={20} className="text-teal-400" />
                        </div>
                        <div>
                            <div className="font-bold text-sm text-gray-100 group-hover:text-teal-300 transition-colors">Router</div>
                            <div className="text-[10px] text-slate-400 font-mono tracking-tight uppercase">L3 Networking</div>
                        </div>
                    </div>
                </div>

                {/* Switch Card */}
                <div
                    className="group bg-[#142338] hover:bg-[#1A2C42] border border-[#3DD6B5]/10 hover:border-[#3DD6B5]/40 rounded-xl p-3 cursor-grab transition-all duration-300 relative overflow-hidden"
                    onDragStart={(event) => onDragStart(event, 'switch')}
                    draggable
                >
                    <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <GripVertical size={14} className="text-slate-500" />
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center border border-blue-500/20 group-hover:scale-105 transition-transform">
                            <Share2 size={20} className="text-blue-400" />
                        </div>
                        <div>
                            <div className="font-bold text-sm text-gray-100 group-hover:text-blue-300 transition-colors">Switch</div>
                            <div className="text-[10px] text-slate-400 font-mono tracking-tight uppercase">L2 Switching</div>
                        </div>
                    </div>
                </div>

                {/* Host Card */}
                <div
                    className="group bg-[#142338] hover:bg-[#1A2C42] border border-[#3DD6B5]/10 hover:border-[#3DD6B5]/40 rounded-xl p-3 cursor-grab transition-all duration-300 relative overflow-hidden"
                    onDragStart={(event) => onDragStart(event, 'host')}
                    draggable
                >
                    <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <GripVertical size={14} className="text-slate-500" />
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center border border-purple-500/20 group-hover:scale-105 transition-transform">
                            <Monitor size={20} className="text-purple-400" />
                        </div>
                        <div>
                            <div className="font-bold text-sm text-gray-100 group-hover:text-purple-300 transition-colors">End Device</div>
                            <div className="text-[10px] text-slate-400 font-mono tracking-tight uppercase">Workstation / Server</div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="mt-auto p-4 rounded-lg bg-[#142338]/50 border border-[#3DD6B5]/10 text-center">
                <p className="text-[10px] text-slate-400 leading-relaxed">
                    Drag components to the canavas to build your topology manually or use AI generation.
                </p>
            </div>
        </aside>
    );
}
