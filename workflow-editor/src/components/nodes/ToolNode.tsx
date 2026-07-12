import { memo } from 'react';
import { Handle, Position, useConnection } from '@xyflow/react';
import type { Node, NodeProps } from '@xyflow/react';
import type { LucideIcon } from 'lucide-react';
import { Brain, Database, FileSearch, KeyRound, Link2, Mail, Server, Wrench } from 'lucide-react';
import type { WorkflowNodeData } from '../../types/workflow';
import { StatusBadge } from '../studio/StatusBadge';
import { IoBadges } from '../studio/IoBadges';
import { getToolSummary } from '../../utils/studioDerivedState';
import { NODE_TONE } from '../../utils/nodeTheme';
import { auxKindForToolType, isAuxHandle } from '../../utils/connectionRules';

const tone = NODE_TONE.tool;

const TOOL_TYPE_ICON: Record<string, LucideIcon> = {
    mcp: Server,
    database: Database,
    gmail: Mail,
    memory: Brain,
    knowledge: FileSearch,
};

const TOOL_TYPE_CAPTION: Record<string, string> = {
    mcp: 'MCP server',
    database: 'NL2SQL database',
    gmail: 'Gmail account',
    memory: 'Memory store',
    knowledge: 'Knowledge source',
    function: 'Function',
};

export const ToolNode = memo(({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
    const summary = getToolSummary(data.config);

    // Highlight this tool's attach handle when an agent aux handle of the
    // matching kind is being dragged toward it. Selector form avoids
    // re-rendering on every pointer move of an in-progress connection.
    const attachWanted = useConnection(
        (conn) =>
            conn.inProgress &&
            conn.fromNode?.type === 'agent' &&
            isAuxHandle(conn.fromHandle?.id) &&
            conn.fromHandle?.id === auxKindForToolType(summary.type),
    );
    const liveClass =
        data.status === 'running'
            ? 'border-blue-500 dark:border-sky-400 shadow-[0_0_0_4px_rgba(37,99,235,0.18)] dark:shadow-[0_0_0_4px_rgba(56,189,248,0.28)] animate-pulse'
            : data.status === 'configured'
                ? 'border-green-400 dark:border-emerald-500 shadow-[0_0_0_3px_rgba(34,197,94,0.15)] dark:shadow-[0_0_0_3px_rgba(52,211,153,0.25)]'
                : data.status === 'error'
                    ? 'border-red-500 dark:border-red-400 shadow-[0_0_0_3px_rgba(239,68,68,0.18)] dark:shadow-[0_0_0_3px_rgba(248,113,113,0.28)]'
                    : '';
    return (
        <div
            className={`group relative flex min-w-[150px] max-w-[210px] items-center gap-2 rounded-xl border px-2.5 py-2 ag-surface-raised shadow-sm transition-all duration-200
            ${liveClass || (selected
                    ? `border-orange-500 dark:border-orange-400 ${tone.ring}`
                    : `${tone.border} ${tone.borderHover} hover:shadow-md`
                )}`}
        >
            {/* Input Handle (Left) */}
            <Handle
                type="target"
                position={Position.Left}
                className={`!w-2.5 !h-2.5 !-left-1.5 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} transition-colors`}
            />

            {/* Attach Handle (Top) — connects this tool to an agent's Tools/Memory/Knowledge handle */}
            <Handle
                id="attach"
                type="source"
                position={Position.Top}
                className={`!w-3 !h-3 !-top-2 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} ${
                    attachWanted ? '!bg-orange-400 dark:!bg-orange-500 !shadow-[0_0_0_4px_rgba(249,115,22,0.35)] animate-pulse' : ''
                } transition-all`}
            />

            {/* Icon — reflects the tool's integration type */}
            {(() => {
                const Icon = TOOL_TYPE_ICON[summary.type] ?? Wrench;
                return (
                    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${tone.iconBorder} ${tone.iconBg} ${tone.iconText}`}>
                        <Icon size={15} strokeWidth={2.5} />
                    </div>
                );
            })()}

            {/* Label */}
            <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                <div className="min-w-0">
                    <span className="block truncate text-sm font-bold ag-text">{data.label}</span>
                    <span className="block truncate text-[10px] ag-muted">
                        {summary.type === 'api' ? `${summary.method} action` : (TOOL_TYPE_CAPTION[summary.type] ?? 'Function action')}
                    </span>
                </div>
                <div className="flex flex-wrap gap-1">
                    <StatusBadge tone={summary.health} label={summary.health === 'ready' ? summary.type : 'Setup'} compact />
                    {summary.type === 'api' && <StatusBadge tone="muted" label={summary.method} icon={Link2} compact />}
                    {summary.type === 'mcp' && summary.transport && <StatusBadge tone="muted" label={summary.transport} icon={Server} compact />}
                    {summary.type === 'gmail' && summary.accountEmail && <StatusBadge tone="muted" label={summary.accountEmail} icon={Mail} compact />}
                    {(summary.type === 'api' || summary.type === 'function') && (
                        <StatusBadge tone={summary.auth === 'none' ? 'muted' : 'warning'} label={summary.auth === 'none' ? 'No auth' : summary.auth} icon={KeyRound} compact />
                    )}
                    <IoBadges data={data} />
                </div>
            </div>

            {/* Output Handle (Right) */}
            <Handle
                type="source"
                position={Position.Right}
                className={`!w-2.5 !h-2.5 !-right-1.5 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} transition-colors`}
            />
        </div>
    );
});
