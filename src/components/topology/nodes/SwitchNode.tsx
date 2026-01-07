import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

const SwitchNode = ({ data }: NodeProps) => {
    return (
        <div className="px-4 py-2 shadow-md rounded-sm bg-white border-2 border-green-500 min-w-[100px]">
            <div className="flex flex-col items-center">
                <div className="w-12 h-6 rounded-sm bg-green-100 flex items-center justify-center mb-1 border border-green-300">
                    <span className="text-xs">⇿</span>
                </div>
                <div className="text-sm font-bold">{data.label as string}</div>
            </div>
            <Handle type="target" position={Position.Top} className="w-3 h-3 bg-gray-400" />
            <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-gray-400" />
        </div>
    );
};

export default memo(SwitchNode);
