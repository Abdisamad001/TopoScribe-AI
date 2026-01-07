import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

const RouterNode = ({ data }: NodeProps) => {
    return (
        <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-blue-500">
            <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center mb-1 text-2xl">
                    🌐
                </div>
                <div className="text-sm font-bold">{data.label as string}</div>
                <div className="text-xs text-gray-500">{data.ip as string}</div>
            </div>
            <Handle type="target" position={Position.Top} className="w-3 h-3 bg-gray-400" />
            <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-gray-400" />
            <Handle type="target" position={Position.Left} className="w-3 h-3 bg-gray-400" />
            <Handle type="source" position={Position.Right} className="w-3 h-3 bg-gray-400" />
        </div>
    );
};

export default memo(RouterNode);
