import type { LucideIcon } from 'lucide-react';
import { AlertTriangle, CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';

type StatusTone = 'ready' | 'warning' | 'error' | 'running' | 'muted';

const toneClass: Record<StatusTone, string> = {
    ready: 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400',
    warning: 'border-amber-200 dark:border-amber-900/60 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-400',
    error: 'border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400',
    running: 'border-blue-200 dark:border-blue-900/60 bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400',
    muted: 'border-gray-200 dark:border-slate-800 bg-gray-50 dark:bg-slate-900/50 text-gray-600 dark:text-gray-400',
};

const toneIcon: Record<StatusTone, LucideIcon> = {
    ready: CheckCircle2,
    warning: AlertTriangle,
    error: XCircle,
    running: Loader2,
    muted: Circle,
};

export const StatusBadge = ({
    tone,
    label,
    icon,
    className = '',
    compact = false,
}: {
    tone: StatusTone;
    label: string;
    icon?: LucideIcon;
    className?: string;
    compact?: boolean;
}) => {
    const Icon = icon ?? toneIcon[tone];
    return (
        <span className={`inline-flex max-w-full items-center gap-1 rounded-md border ${compact ? 'px-1.5 py-px text-[9px]' : 'px-1.5 py-0.5 text-[10px]'} font-semibold ${toneClass[tone]} ${className}`}>
            <Icon size={compact ? 9 : 11} className={tone === 'running' ? 'animate-spin' : ''} />
            <span className="truncate">{label}</span>
        </span>
    );
};
