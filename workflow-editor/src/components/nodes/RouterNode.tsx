import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { Node, NodeProps } from '@xyflow/react';
import { GitBranch } from 'lucide-react';
import type { WorkflowNodeData } from '../../types/workflow';
import { NODE_TONE } from '../../utils/nodeTheme';

const tone = NODE_TONE.router;

export const RouterNode = memo(({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
    return (
        <div className="group relative flex items-center justify-center w-16 h-16">
            {/* Diamond Shape */}
            <div
                className={`absolute w-12 h-12 ag-surface-raised rotate-45 border-2 shadow-sm transition-all duration-200
                ${selected
                        ? `border-purple-500 dark:border-purple-400 ${tone.ring}`
                        : `${tone.border} ${tone.borderHover} hover:shadow-md`
                    }`}
            >
            </div>

            {/* Icon (Counter-rotated content) */}
            <div className={`relative z-10 flex items-center justify-center ${tone.iconText} pointer-events-none`}>
                <GitBranch size={20} strokeWidth={2.5} />
            </div>

            {/* Handles — LR flow: input on the left, outputs fan out right/top/bottom */}
            <Handle
                type="target"
                position={Position.Left}
                className={`!w-2.5 !h-2.5 !-left-1 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} transition-colors z-20`}
            />

            {/* Outputs */}
            <Handle
                type="source"
                id="right"
                position={Position.Right}
                className={`!w-2.5 !h-2.5 !-right-1 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} transition-colors z-20`}
            />
            <Handle
                type="source"
                id="top"
                position={Position.Top}
                className={`!w-2.5 !h-2.5 !-top-1 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} transition-colors z-20`}
            />
            <Handle
                type="source"
                id="bottom"
                position={Position.Bottom}
                className={`!w-2.5 !h-2.5 !-bottom-1 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} transition-colors z-20`}
            />

            {/* External Label */}
            <div className="absolute -bottom-8 flex flex-col items-center w-32 pointer-events-none">
                <span className="text-[10px] font-bold uppercase tracking-wide ag-label px-2 py-0.5 rounded-sm">
                    {data.label || 'Router'}
                </span>
            </div>
        </div>
    );
});
