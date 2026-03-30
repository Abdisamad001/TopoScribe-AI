import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Globe, CheckCircle, AlertTriangle } from 'lucide-react';

const RouterNode = ({ data, selected }: NodeProps) => {
    const status = data.simulationStatus as string;

    return (
        <div className={`
            px-4 py-3 rounded-xl border transition-all w-52
            bg-[#0F1A2B]/95 backdrop-blur-sm shadow-[0_8px_24px_rgba(0,0,0,0.45)]
            ${selected ? 'border-cyan-400 shadow-[0_0_0_2px_rgba(34,211,238,0.35),0_10px_28px_rgba(0,0,0,0.5)]' : 'border-slate-500/60'}
            ${status === 'error' ? '!border-rose-400 bg-rose-950/40' : ''}
            ${status === 'success' ? '!border-emerald-400 bg-emerald-950/30' : ''}
        `}>
            <div className="flex flex-col items-center">
                <div className={`p-2 rounded-full mb-2 relative ${status === 'error' ? 'bg-rose-300/20' : 'bg-cyan-300/20'}`}>
                    <Globe size={21} className={status === 'error' ? 'text-rose-300' : 'text-cyan-300'} />

                    {/* Status Icons Overlay */}
                    {status === 'success' && (
                        <div className="absolute -top-1 -right-1 bg-slate-900 rounded-full p-0.5 shadow">
                            <CheckCircle size={14} className="text-emerald-400 fill-emerald-900/60" />
                        </div>
                    )}
                    {status === 'error' && (
                        <div className="absolute -top-1 -right-1 bg-slate-900 rounded-full p-0.5 shadow">
                            <AlertTriangle size={14} className="text-rose-400 fill-rose-900/60" />
                        </div>
                    )}
                </div>

                <div className="text-sm font-semibold text-slate-100 text-center leading-tight">{data.label as string}</div>
                <div className="text-xs text-slate-300 font-mono mt-1">
                    {data.ip as string || 'No IP'}
                </div>
            </div>

            <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-slate-300" />
            <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-slate-300" />
            <Handle type="target" position={Position.Left} className="w-3 h-3 !bg-slate-300" />
            <Handle type="source" position={Position.Right} className="w-3 h-3 !bg-slate-300" />
        </div>
    );
};

export default memo(RouterNode);
