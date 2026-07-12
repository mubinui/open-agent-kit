
import { memo } from 'react';
import { Handle, Position, useConnection } from '@xyflow/react';
import type { Node, NodeProps } from '@xyflow/react';
import { Bot, CheckCircle2, GitBranch, Hand, Play, Wrench } from 'lucide-react';
import type { WorkflowNodeData } from '../../types/workflow';
import { StatusBadge } from '../studio/StatusBadge';
import { IoBadges } from '../studio/IoBadges';
import { getAgentSummary } from '../../utils/studioDerivedState';
import { NODE_TONE } from '../../utils/nodeTheme';
import { auxKindForToolType } from '../../utils/connectionRules';

// Auxiliary attachment handles along the bottom edge: tool/memory/knowledge
// nodes plug in here instead of joining the main left→right flow.
const AUX_HANDLE_STYLE: Array<{ id: 'tools' | 'memory' | 'knowledge'; left: string; label: string; className: string; glow: string }> = [
    {
        id: 'tools',
        left: '25%',
        label: 'Tools',
        className: '!bg-orange-400 dark:!bg-orange-500 hover:!bg-orange-500 dark:hover:!bg-orange-400',
        glow: '!shadow-[0_0_0_4px_rgba(249,115,22,0.35)]',
    },
    {
        id: 'memory',
        left: '50%',
        label: 'Memory',
        className: '!bg-violet-400 dark:!bg-violet-500 hover:!bg-violet-500 dark:hover:!bg-violet-400',
        glow: '!shadow-[0_0_0_4px_rgba(168,85,247,0.35)]',
    },
    {
        id: 'knowledge',
        left: '75%',
        label: 'Knowledge',
        className: '!bg-teal-400 dark:!bg-teal-500 hover:!bg-teal-500 dark:hover:!bg-teal-400',
        glow: '!shadow-[0_0_0_4px_rgba(20,184,166,0.35)]',
    },
];

const tone = NODE_TONE.agent;

export const AgentNode = memo(({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
    const summary = getAgentSummary(data.config);

    // While a connection is being dragged from a tool's attach handle, light up
    // the one aux handle that will accept it and show the handle labels.
    // Selector form: without it every node re-renders on every pointer move
    // of an in-progress connection, which makes dragging feel choppy.
    const pendingAuxKind = useConnection((conn) =>
        conn.inProgress && conn.fromHandle?.id === 'attach' && conn.fromNode?.type === 'tool'
            ? auxKindForToolType((conn.fromNode?.data as WorkflowNodeData | undefined)?.config?.type)
            : null,
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
            className={`group relative min-w-[210px] max-w-[250px] ag-surface-raised rounded-xl border transition-all duration-200 shadow-sm
            ${liveClass || (selected
                    ? `border-blue-500 dark:border-sky-400 ${tone.ring}`
                    : `${tone.border} ${tone.borderHover} hover:shadow-md`
                )}`}
        >
            {/* Input Handle (Left) - like n8n */}
            <Handle
                type="target"
                position={Position.Left}
                className={`!w-3 !h-3 !-left-1.5 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} transition-colors`}
            />

            <div className="flex flex-col gap-2 p-2.5">
                {/* Header: Icon + Type */}
                <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-start gap-2">
                        <div className={`p-1.5 rounded-md border ${tone.iconBg} ${tone.iconText} ${tone.iconBorder} transition-colors`}>
                            <Bot size={14} strokeWidth={2.5} />
                        </div>
                        <div className="min-w-0 flex-1">
                            <span className="block text-[10px] font-bold ag-faint uppercase tracking-wider">{summary.strategy}</span>
                            <div className="font-semibold ag-text text-sm leading-tight text-left line-clamp-2" title={data.label}>
                                {data.label || 'Untitled Agent'}
                            </div>
                        </div>
                    </div>
                    <StatusBadge tone={summary.health} label={summary.health === 'ready' ? 'Ready' : 'Setup'} compact />
                </div>

                <div className="flex items-center justify-between gap-2 rounded-md ag-surface-subtle border border-[var(--color-ui-border)] px-2 py-1.5">
                    <div className="min-w-0">
                        <div className="truncate text-[10px] font-semibold ag-text">{summary.model}</div>
                        <div className="truncate text-[9px] ag-muted">{summary.provider}</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                        <StatusBadge tone={summary.toolCount > 0 ? 'ready' : 'muted'} label={`${summary.toolCount}`} icon={Wrench} compact />
                        {summary.isSelector && <StatusBadge tone="running" label="" icon={GitBranch} compact />}
                        {summary.humanInput !== 'NEVER' && <StatusBadge tone="warning" label="" icon={Hand} compact />}
                    </div>
                </div>

                {/* Footer: Config/Status (Minimal) */}
                {(data.status || summary.issues.length > 0 || data.lastInput || data.lastOutput) && (
                    <div className="flex items-center gap-1.5 border-t border-[var(--color-ui-border)] pt-2">
                        {data.status === 'running' && <Play size={8} className="text-yellow-500 fill-yellow-500 animate-pulse" />}
                        {data.status === 'configured' && <CheckCircle2 size={8} className="text-green-500" />}
                        {data.status === 'error' && <span className="w-2 h-2 rounded-full bg-red-500" />}
                        <span className="min-w-0 flex-1 truncate text-[9px] ag-muted">
                            {summary.issues[0] ?? (data.status ? String(data.status) : 'Configured')}
                        </span>
                        <IoBadges data={data} />
                    </div>
                )}
            </div>

            {/* Output Handle (Right) - like n8n */}
            <Handle
                type="source"
                position={Position.Right}
                className={`!w-3 !h-3 !-right-1.5 !bg-gray-400 dark:!bg-slate-600 !border-2 !border-[var(--color-surface-raised)] ${tone.handleHover} transition-colors`}
            />

            {/* Auxiliary attachment handles (Bottom): Tools / Memory / Knowledge */}
            {AUX_HANDLE_STYLE.map((aux) => {
                const isPendingTarget = pendingAuxKind === aux.id;
                const isDimmed = pendingAuxKind !== null && !isPendingTarget;
                return (
                    <Handle
                        key={aux.id}
                        id={aux.id}
                        type="target"
                        position={Position.Bottom}
                        style={{ left: aux.left }}
                        className={`!w-3.5 !h-3.5 !-bottom-2 !border-2 !border-[var(--color-surface-raised)] ${aux.className} ${
                            isPendingTarget ? `${aux.glow} animate-pulse` : ''
                        } ${isDimmed ? '!opacity-30' : ''} transition-all`}
                    />
                );
            })}
            <div
                className={`pointer-events-none absolute -bottom-6 left-0 flex w-full select-none transition-opacity duration-150 ${
                    pendingAuxKind !== null ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                }`}
            >
                {AUX_HANDLE_STYLE.map((aux) => (
                    <span
                        key={aux.id}
                        className={`absolute -translate-x-1/2 text-[8px] font-bold uppercase tracking-wider ${
                            pendingAuxKind === aux.id ? 'ag-text' : 'ag-faint'
                        } ${pendingAuxKind !== null && pendingAuxKind !== aux.id ? 'opacity-30' : ''}`}
                        style={{ left: aux.left }}
                    >
                        {aux.label}
                    </span>
                ))}
            </div>
        </div>
    );
});
