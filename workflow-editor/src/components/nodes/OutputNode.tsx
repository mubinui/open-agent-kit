
import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { Node, NodeProps } from '@xyflow/react';
import { Square } from 'lucide-react';
import type { WorkflowNodeData } from '../../types/workflow';

export const OutputNode = memo(({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
    return (
        <div className="relative flex flex-col items-center justify-center">
            {/* Circular Node */}
            <div
                className={`group flex items-center justify-center w-14 h-14 ag-surface-raised rounded-full border-2 shadow-sm transition-all duration-200
                ${selected
                        ? 'border-red-500 shadow-[0_0_0_4px_rgba(239,68,68,0.2)]'
                        : 'border-red-100 hover:border-red-400 hover:shadow-md' // Changed border-red-200 to 100 to match trigger
                    }`}
            >
                {/* Icon */}
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-red-50 text-red-600 transition-transform group-hover:scale-110">
                    <Square size={20} fill="currentColor" className="ml-0.5" strokeWidth={2.5} />
                </div>

                {/* Input Handle */}
                <Handle
                    type="target"
                    position={Position.Left}
                    className="!w-3 !h-3 !-left-[7px] !bg-[var(--color-surface-raised)] !border-[3px] !border-red-500 group-hover:!bg-red-600 transition-colors z-10"
                />
            </div>

            {/* External Label */}
            <div className="absolute -bottom-6 flex flex-col items-center w-32 pointer-events-none">
                <span className="text-[10px] font-bold uppercase tracking-wide ag-label px-2 py-0.5 rounded-sm">
                    {data.label || 'End'}
                </span>
            </div>
        </div>
    );
});
