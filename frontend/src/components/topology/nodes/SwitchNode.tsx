import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

const SwitchNode = ({ data, selected }: NodeProps) => {
    return (
        <div
            className={`
                px-4 py-3 rounded-xl border transition-all min-w-[180px]
                bg-[#13233A]/95 backdrop-blur-sm shadow-[0_8px_24px_rgba(0,0,0,0.45)]
                ${selected ? 'border-cyan-400 shadow-[0_0_0_2px_rgba(34,211,238,0.35),0_10px_28px_rgba(0,0,0,0.5)]' : 'border-emerald-400/70'}
            `}
        >
            <div className="flex flex-col items-center">
                <div className="w-12 h-7 rounded-md bg-emerald-300/20 flex items-center justify-center mb-2 border border-emerald-300/40">
                    <span className="text-sm text-emerald-200">⇿</span>
                </div>
                <div className="text-sm font-semibold text-slate-100 text-center leading-tight">
                    {data.label as string}
                </div>
            </div>
            <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-slate-300" />
            <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-slate-300" />
            <Handle type="target" position={Position.Left} className="w-3 h-3 !bg-slate-300" />
            <Handle type="source" position={Position.Right} className="w-3 h-3 !bg-slate-300" />
        </div>
    );
};

export default memo(SwitchNode);
