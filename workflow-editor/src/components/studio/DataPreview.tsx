import { useMemo } from 'react';

const format = (value: unknown): string => {
    if (value == null) return '';
    if (typeof value === 'string') return value;
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
};

/**
 * Read-only viewer for a node's captured run data. Objects render one
 * expandable section per top-level key; plain strings render as-is.
 */
export const DataPreview = ({ value, emptyMessage }: { value: unknown; emptyMessage: string }) => {
    const entries = useMemo(() => {
        if (value != null && typeof value === 'object' && !Array.isArray(value)) {
            return Object.entries(value as Record<string, unknown>).filter(([, v]) => v != null && v !== '');
        }
        return null;
    }, [value]);

    if (value == null || (entries !== null && entries.length === 0)) {
        return (
            <div className="rounded-lg border border-dashed border-slate-200 dark:border-slate-800 p-3 text-center text-[11px] font-medium text-slate-400 dark:text-slate-500">
                {emptyMessage}
            </div>
        );
    }

    if (entries === null) {
        return (
            <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/50 p-2.5 font-mono text-[10px] leading-relaxed text-slate-700 dark:text-slate-300 custom-scrollbar">
                {format(value)}
            </pre>
        );
    }

    return (
        <div className="space-y-1">
            {entries.map(([key, entry]) => (
                <details
                    key={key}
                    open={entries.length <= 3}
                    className="group rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/50"
                >
                    <summary className="cursor-pointer select-none px-2.5 py-1.5 text-[10px] font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">
                        {key}
                    </summary>
                    <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words border-t border-slate-200 dark:border-slate-800 p-2.5 font-mono text-[10px] leading-relaxed text-slate-700 dark:text-slate-300 custom-scrollbar">
                        {format(entry)}
                    </pre>
                </details>
            ))}
        </div>
    );
};
