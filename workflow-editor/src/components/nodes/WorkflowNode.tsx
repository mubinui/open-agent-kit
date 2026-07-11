
import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { Node, NodeProps } from '@xyflow/react';
import { Workflow } from 'lucide-react';
import type { WorkflowNodeData } from '../../types/workflow';
import { StatusBadge } from '../studio/StatusBadge';
import { getWorkflowSummary } from '../../utils/studioDerivedState';

export const WorkflowNode = memo(({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
    const summary = getWorkflowSummary(data.config);
    return (
        <div className="relative flex flex-col items-center justify-center">
            <div
                className={`group flex min-w-[180px] flex-col gap-2 ag-surface-raised rounded-lg border-2 p-3 shadow-sm transition-all duration-200
                ${selected
                        ? 'border-purple-500 shadow-[0_0_0_4px_rgba(168,85,247,0.2)]'
                        : 'border-purple-100 hover:border-purple-400 hover:shadow-md'
                    }`}
            >
                <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-50 text-purple-600 transition-transform group-hover:scale-110">
                        <Workflow size={19} />
                    </div>
                    <div className="min-w-0">
                        <div className="truncate text-sm font-bold ag-text">{data.label || 'Workflow'}</div>
                        <div className="truncate text-[10px] ag-muted">{summary.entryNode}</div>
                    </div>
                </div>
                <div className="flex flex-wrap gap-1">
                    <StatusBadge tone={summary.health} label={summary.pattern} />
                    <StatusBadge tone="muted" label={`${summary.nodeCount} nodes`} />
                </div>

                {/* Input Handle (Left) */}
                <Handle
                    type="target"
                    position={Position.Left}
                    className="!w-3 !h-3 !-left-[7px] !bg-[var(--color-surface-raised)] !border-[3px] !border-purple-500 group-hover:!bg-purple-500 transition-colors z-10"
                />

                {/* Output Handle (Right) */}
                <Handle
                    type="source"
                    position={Position.Right}
                    className="!w-3 !h-3 !-right-[7px] !bg-[var(--color-surface-raised)] !border-[3px] !border-purple-500 group-hover:!bg-purple-500 transition-colors z-10"
                />
            </div>
        </div>
    );
});
