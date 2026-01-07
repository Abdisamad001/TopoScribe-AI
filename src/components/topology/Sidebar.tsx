import React from 'react';

export default function Sidebar() {
    const onDragStart = (event: React.DragEvent, nodeType: string) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <aside className="w-64 bg-white dark:bg-zinc-900 border-r border-gray-200 dark:border-zinc-700 p-4 flex flex-col gap-4">
            <h2 className="text-sm font-bold uppercase text-gray-500 dark:text-gray-400">Library</h2>

            <div
                className="p-3 bg-blue-50 border border-blue-200 rounded cursor-grab shadow-sm hover:shadow-md transition-all flex items-center gap-2"
                onDragStart={(event) => onDragStart(event, 'router')}
                draggable
            >
                <div className="w-8 h-8 flex items-center justify-center bg-blue-100 rounded-full text-lg">🌐</div>
                <div>
                    <div className="font-semibold text-sm">Router</div>
                    <div className="text-xs text-gray-500">L3 Device</div>
                </div>
            </div>

            <div
                className="p-3 bg-green-50 border border-green-200 rounded cursor-grab shadow-sm hover:shadow-md transition-all flex items-center gap-2"
                onDragStart={(event) => onDragStart(event, 'switch')}
                draggable
            >
                <div className="w-8 h-8 flex items-center justify-center bg-green-100 rounded-sm text-lg border border-green-300">⇿</div>
                <div>
                    <div className="font-semibold text-sm">Switch</div>
                    <div className="text-xs text-gray-500">L2 Device</div>
                </div>
            </div>

            <div
                className="p-3 bg-gray-50 border border-gray-200 rounded cursor-grab shadow-sm hover:shadow-md transition-all flex items-center gap-2"
                onDragStart={(event) => onDragStart(event, 'host')}
                draggable
            >
                <div className="w-8 h-8 flex items-center justify-center bg-gray-100 rounded-md text-lg">💻</div>
                <div>
                    <div className="font-semibold text-sm">Host</div>
                    <div className="text-xs text-gray-500">End Device</div>
                </div>
            </div>

            <div className="mt-auto text-xs text-gray-400">
                Drag items to the canvas to add them.
            </div>
        </aside>
    );
}
