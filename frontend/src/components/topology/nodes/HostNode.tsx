import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

const HostNode = ({ data }: NodeProps) => {
    return (
        <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-gray-500">
            <div className="flex flex-col items-center">
                <div className="w-8 h-8 rounded-md bg-gray-100 flex items-center justify-center mb-1 text-xl">
                    💻
                </div>
                <div className="text-sm font-bold">{data.label as string}</div>
                <div className="text-xs text-gray-400">{data.ip as string}</div>
            </div>
            <Handle type="target" position={Position.Top} className="w-3 h-3 bg-gray-400" />
        </div>
    );
};

export default memo(HostNode);
