import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Globe, CheckCircle, AlertTriangle } from 'lucide-react';

const RouterNode = ({ data, selected }: NodeProps) => {
    const status = data.simulationStatus as string;

    return (
        <div className={`
            px-4 py-2 shadow-md rounded-md bg-white border-2 transition-all w-40
            ${selected ? 'border-blue-500 shadow-lg' : 'border-gray-200'}
            ${status === 'error' ? 'border-red-500 bg-red-50' : ''}
            ${status === 'success' ? 'border-teal-500' : ''}
        `}>
            <div className="flex flex-col items-center">
                <div className={`p-2 rounded-full mb-1 relative ${status === 'error' ? 'bg-red-100' : 'bg-blue-100'}`}>
                    <Globe size={20} className={status === 'error' ? 'text-red-500' : 'text-blue-500'} />

                    {/* Status Icons Overlay */}
                    {status === 'success' && (
                        <div className="absolute -top-1 -right-1 bg-white rounded-full p-0.5 shadow">
                            <CheckCircle size={14} className="text-teal-500 fill-teal-100" />
                        </div>
                    )}
                    {status === 'error' && (
                        <div className="absolute -top-1 -right-1 bg-white rounded-full p-0.5 shadow">
                            <AlertTriangle size={14} className="text-red-500 fill-red-100" />
                        </div>
                    )}
                </div>

                <div className="text-xs font-bold text-gray-700">{data.label as string}</div>
                <div className="text-[10px] text-gray-500 font-mono mt-1">
                    {data.ip as string || 'No IP'}
                </div>
            </div>

            <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-gray-400" />
            <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-gray-400" />
            <Handle type="target" position={Position.Left} className="w-3 h-3 !bg-gray-400" />
            <Handle type="source" position={Position.Right} className="w-3 h-3 !bg-gray-400" />
        </div>
    );
};

export default memo(RouterNode);
