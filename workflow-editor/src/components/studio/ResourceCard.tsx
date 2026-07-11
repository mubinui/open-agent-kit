import type { LucideIcon } from 'lucide-react';
import { ChevronRight, GripVertical } from 'lucide-react';
import type { DragEvent } from 'react';
import type { NodeType } from '../../types/workflow';
import { StatusBadge } from './StatusBadge';

type ResourceTone = 'agent' | 'tool' | 'workflow' | 'trigger' | 'logic' | 'output';

const toneClass: Record<ResourceTone, { icon: string; border: string }> = {
    agent: { icon: 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-100 dark:border-blue-900/50', border: 'hover:border-blue-300 dark:hover:border-blue-700' },
    tool: { icon: 'bg-orange-50 dark:bg-orange-950/40 text-orange-600 dark:text-orange-400 border-orange-100 dark:border-orange-900/50', border: 'hover:border-orange-300 dark:hover:border-orange-700' },
    workflow: { icon: 'bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 border-indigo-100 dark:border-indigo-900/50', border: 'hover:border-indigo-300 dark:hover:border-indigo-700' },
    trigger: { icon: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-100 dark:border-emerald-900/50', border: 'hover:border-emerald-300 dark:hover:border-emerald-700' },
    logic: { icon: 'bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 border-purple-100 dark:border-purple-900/50', border: 'hover:border-purple-300 dark:hover:border-purple-700' },
    output: { icon: 'bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 border-red-100 dark:border-red-900/50', border: 'hover:border-red-300 dark:hover:border-red-700' },
};

export interface ResourceCardBadge {
    label: string;
    tone?: 'ready' | 'warning' | 'error' | 'running' | 'muted';
}

export const ResourceCard = ({
    type,
    label,
    description,
    icon: Icon,
    tone,
    badges = [],
    config,
    collapsed,
    level = 0,
    expandable = false,
    expanded = false,
    onToggle,
    onClick,
    compact = false,
}: {
    type: NodeType;
    label: string;
    description?: string;
    icon: LucideIcon;
    tone: ResourceTone;
    badges?: ResourceCardBadge[];
    config?: Record<string, any>;
    collapsed: boolean;
    level?: number;
    expandable?: boolean;
    expanded?: boolean;
    onToggle?: () => void;
    onClick?: () => void;
    compact?: boolean;
}) => {
    const dragStart = (event: DragEvent) => {
        event.dataTransfer.setData('application/reactflow', type);
        event.dataTransfer.setData('application/reactflow-label', label);
        if (config) event.dataTransfer.setData('application/reactflow-config', JSON.stringify(config));
        event.dataTransfer.effectAllowed = 'move';
    };

    const toneStyles = toneClass[tone];

    if (collapsed) {
        return (
            <button
                draggable
                onDragStart={dragStart}
                onClick={onClick}
                className={`group flex h-10 w-10 items-center justify-center rounded-lg border border-transparent ag-surface hover:shadow-md ${toneStyles.border}`}
                title={label}
            >
                <Icon size={17} />
            </button>
        );
    }

    return (
        <div
            draggable
            onDragStart={dragStart}
            onClick={onClick}
            className={`group relative mb-1 cursor-grab rounded-lg border border-[var(--color-ui-border)] ag-surface-raised ${compact ? 'p-1.5' : 'p-2'} transition-all duration-200 hover:shadow-md ${toneStyles.border}`}
            style={{ marginLeft: `${level * 12}px` }}
            title={description}
        >
            <div className="flex items-center gap-2">
                <button
                    type="button"
                    onClick={(event) => {
                        event.stopPropagation();
                        onToggle?.();
                    }}
                    className={`rounded p-0.5 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-800 ${expandable ? '' : 'invisible'}`}
                    aria-label={expanded ? 'Collapse resource' : 'Expand resource'}
                >
                    <ChevronRight size={12} className={`transition-transform ${expanded ? 'rotate-90' : ''}`} />
                </button>
                <div className={`flex ${compact ? 'h-7 w-7' : 'h-8 w-8'} shrink-0 items-center justify-center rounded-lg border ${toneStyles.icon}`}>
                    <Icon size={compact ? 14 : 16} strokeWidth={2.4} />
                </div>
                <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-semibold ag-text">{label}</span>
                        <GripVertical size={13} className="shrink-0 text-gray-300 dark:text-slate-600 opacity-0 transition-opacity group-hover:opacity-100" />
                    </div>
                    {description && !compact && <div className="mt-0.5 line-clamp-2 text-[10px] leading-4 ag-muted">{description}</div>}
                    {badges.length > 0 && (
                        <div className={`${compact ? 'mt-1' : 'mt-2'} flex flex-wrap gap-1`}>
                            {badges.slice(0, compact ? 2 : 3).map((badge) => (
                                <StatusBadge key={badge.label} tone={badge.tone ?? 'muted'} label={badge.label} compact={compact} />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
