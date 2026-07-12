// Shared color tokens for canvas nodes (mirrors the pattern already used correctly by
// `components/studio/ResourceCard.tsx` and `components/studio/StatusBadge.tsx`).
//
// Every tone below pairs a light-mode chip color with an explicit `dark:` variant.
// Node components previously hardcoded only the light-mode classes (e.g. `bg-blue-50
// text-blue-600`) with no `dark:` counterpart, which is why node accents stayed
// bright/washed-out after switching to dark theme — this is the single source of truth
// so that bug can't reappear per-node.
//
// Tailwind's scanner only picks up class names that appear as complete literal strings,
// so every value here is written out in full rather than built with template interpolation.
export type NodeTone =
    | 'agent'
    | 'tool'
    | 'router'
    | 'workflow'
    | 'output'
    | 'trigger-manual'
    | 'trigger-chat'
    | 'trigger-webhook';

export interface NodeToneTokens {
    /** Icon chip background */
    iconBg: string;
    /** Icon glyph color */
    iconText: string;
    /** Icon chip border */
    iconBorder: string;
    /** Idle card/shape border */
    border: string;
    /** Hover border */
    borderHover: string;
    /** Selected-state focus ring (box-shadow) */
    ring: string;
    /** Connection handle hover color */
    handleHover: string;
    /** Solid handle border color (small circular nodes) */
    handleBorder: string;
    /** Solid action-button background (e.g. trigger run button) */
    actionBg: string;
}

export const NODE_TONE: Record<NodeTone, NodeToneTokens> = {
    agent: {
        iconBg: 'bg-blue-50 dark:bg-blue-950/40',
        iconText: 'text-blue-600 dark:text-blue-400',
        iconBorder: 'border-blue-100 dark:border-blue-900/50',
        border: 'border-slate-200 dark:border-slate-800',
        borderHover: 'hover:border-blue-300 dark:hover:border-blue-700',
        ring: 'shadow-[0_0_0_2px_rgba(59,130,246,0.3)] dark:shadow-[0_0_0_2px_rgba(56,189,248,0.35)]',
        handleHover: 'group-hover:!bg-blue-500 dark:group-hover:!bg-sky-400',
        handleBorder: 'border-blue-500 dark:border-sky-400',
        actionBg: 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400',
    },
    tool: {
        iconBg: 'bg-orange-50 dark:bg-orange-950/40',
        iconText: 'text-orange-600 dark:text-orange-400',
        iconBorder: 'border-orange-100 dark:border-orange-900/50',
        border: 'border-slate-200 dark:border-slate-800',
        borderHover: 'hover:border-orange-300 dark:hover:border-orange-700',
        ring: 'shadow-[0_0_0_2px_rgba(249,115,22,0.3)] dark:shadow-[0_0_0_2px_rgba(251,146,60,0.35)]',
        handleHover: 'group-hover:!bg-orange-500 dark:group-hover:!bg-orange-400',
        handleBorder: 'border-orange-500 dark:border-orange-400',
        actionBg: 'bg-orange-600 hover:bg-orange-700 dark:bg-orange-500 dark:hover:bg-orange-400',
    },
    router: {
        iconBg: 'bg-purple-50 dark:bg-purple-950/40',
        iconText: 'text-purple-600 dark:text-purple-400',
        iconBorder: 'border-purple-200 dark:border-purple-900/50',
        border: 'border-purple-200 dark:border-purple-900/50',
        borderHover: 'hover:border-purple-400 dark:hover:border-purple-600',
        ring: 'shadow-[0_0_0_4px_rgba(168,85,247,0.2)] dark:shadow-[0_0_0_4px_rgba(192,132,252,0.3)]',
        handleHover: 'group-hover:!bg-purple-500 dark:group-hover:!bg-purple-400',
        handleBorder: 'border-purple-500 dark:border-purple-400',
        actionBg: 'bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-400',
    },
    workflow: {
        iconBg: 'bg-purple-50 dark:bg-purple-950/40',
        iconText: 'text-purple-600 dark:text-purple-400',
        iconBorder: 'border-purple-100 dark:border-purple-900/50',
        border: 'border-purple-100 dark:border-purple-900/50',
        borderHover: 'hover:border-purple-400 dark:hover:border-purple-600',
        ring: 'shadow-[0_0_0_4px_rgba(168,85,247,0.2)] dark:shadow-[0_0_0_4px_rgba(192,132,252,0.3)]',
        handleHover: 'group-hover:!bg-purple-500 dark:group-hover:!bg-purple-400',
        handleBorder: 'border-purple-500 dark:border-purple-400',
        actionBg: 'bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-400',
    },
    output: {
        iconBg: 'bg-red-50 dark:bg-red-950/40',
        iconText: 'text-red-600 dark:text-red-400',
        iconBorder: 'border-red-100 dark:border-red-900/50',
        border: 'border-red-100 dark:border-red-900/50',
        borderHover: 'hover:border-red-400 dark:hover:border-red-600',
        ring: 'shadow-[0_0_0_4px_rgba(239,68,68,0.2)] dark:shadow-[0_0_0_4px_rgba(248,113,113,0.3)]',
        handleHover: 'group-hover:!bg-red-600 dark:group-hover:!bg-red-400',
        handleBorder: 'border-red-500 dark:border-red-400',
        actionBg: 'bg-red-600 hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-400',
    },
    'trigger-manual': {
        iconBg: 'bg-emerald-50 dark:bg-emerald-950/40',
        iconText: 'text-emerald-600 dark:text-emerald-400',
        iconBorder: 'border-emerald-100 dark:border-emerald-900/50',
        border: 'border-emerald-100 dark:border-emerald-900/50',
        borderHover: 'hover:border-emerald-400 dark:hover:border-emerald-600',
        ring: 'shadow-[0_0_0_4px_rgba(16,185,129,0.2)] dark:shadow-[0_0_0_4px_rgba(52,211,153,0.3)]',
        handleHover: 'group-hover:!bg-emerald-500 dark:group-hover:!bg-emerald-400',
        handleBorder: 'border-emerald-500 dark:border-emerald-400',
        actionBg: 'bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-400',
    },
    'trigger-chat': {
        iconBg: 'bg-blue-50 dark:bg-blue-950/40',
        iconText: 'text-blue-600 dark:text-blue-400',
        iconBorder: 'border-blue-100 dark:border-blue-900/50',
        border: 'border-blue-100 dark:border-blue-900/50',
        borderHover: 'hover:border-blue-400 dark:hover:border-blue-600',
        ring: 'shadow-[0_0_0_4px_rgba(37,99,235,0.2)] dark:shadow-[0_0_0_4px_rgba(56,189,248,0.3)]',
        handleHover: 'group-hover:!bg-blue-500 dark:group-hover:!bg-sky-400',
        handleBorder: 'border-blue-500 dark:border-sky-400',
        actionBg: 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400',
    },
    'trigger-webhook': {
        iconBg: 'bg-pink-50 dark:bg-pink-950/40',
        iconText: 'text-pink-600 dark:text-pink-400',
        iconBorder: 'border-pink-100 dark:border-pink-900/50',
        border: 'border-pink-100 dark:border-pink-900/50',
        borderHover: 'hover:border-pink-400 dark:hover:border-pink-600',
        ring: 'shadow-[0_0_0_4px_rgba(219,39,119,0.2)] dark:shadow-[0_0_0_4px_rgba(244,114,182,0.3)]',
        handleHover: 'group-hover:!bg-pink-500 dark:group-hover:!bg-pink-400',
        handleBorder: 'border-pink-500 dark:border-pink-400',
        actionBg: 'bg-pink-600 hover:bg-pink-700 dark:bg-pink-500 dark:hover:bg-pink-400',
    },
};

export const triggerToneForType = (type?: string): NodeTone => {
    if (type === 'chat') return 'trigger-chat';
    if (type === 'webhook') return 'trigger-webhook';
    return 'trigger-manual';
};
