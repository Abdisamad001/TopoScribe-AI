import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

const HostNode = ({ data, selected }: NodeProps) => {
    return (
        <div
            className={`
                px-4 py-3 rounded-xl border transition-all w-48
                bg-[#101B2C]/95 backdrop-blur-sm shadow-[0_8px_24px_rgba(0,0,0,0.45)]
                ${selected ? 'border-cyan-400 shadow-[0_0_0_2px_rgba(34,211,238,0.35),0_10px_28px_rgba(0,0,0,0.5)]' : 'border-slate-400/70'}
            `}
        >
            <div className="flex flex-col items-center">
                <div className="w-9 h-9 rounded-md bg-slate-300/15 border border-slate-300/30 flex items-center justify-center mb-2 text-xl">
                    💻
                </div>
                <div className="text-sm font-semibold text-slate-100 text-center leading-tight">
                    {data.label as string}
                </div>
                <div className="text-xs text-slate-300 mt-1 font-mono">
                    {data.ip as string || 'No IP'}
                </div>
            </div>
            <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-slate-300" />
        </div>
    );
};

export default memo(HostNode);
