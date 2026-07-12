import { ArrowDownToDot, ArrowUpFromDot } from 'lucide-react';
import type { WorkflowNodeData } from '../../types/workflow';

/**
 * Tiny in/out chips shown on a node once live-run data has been captured.
 * Full payloads live in the Properties panel's Data tab.
 */
export function IoBadges({ data }: { data: WorkflowNodeData }) {
    if (!data.lastInput && !data.lastOutput) return null;
    return (
        <div className="flex shrink-0 items-center gap-1">
            {data.lastInput && (
                <span
                    className="inline-flex items-center gap-0.5 rounded px-1 py-px text-[8px] font-bold uppercase tracking-wide bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
                    title="Input captured — open the Data tab to inspect"
                >
                    <ArrowDownToDot size={8} /> in
                </span>
            )}
            {data.lastOutput && (
                <span
                    className="inline-flex items-center gap-0.5 rounded px-1 py-px text-[8px] font-bold uppercase tracking-wide bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300"
                    title="Output captured — open the Data tab to inspect"
                >
                    <ArrowUpFromDot size={8} /> out
                </span>
            )}
        </div>
    );
}
