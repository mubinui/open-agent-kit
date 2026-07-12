import type { LucideIcon } from 'lucide-react';

export interface InspectorTab {
    id: string;
    label: string;
    icon: LucideIcon;
    disabled?: boolean;
}

// Tailwind can't build class names dynamically — map the tab count to a literal.
const GRID_COLS: Record<number, string> = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6',
};

export const InspectorTabs = ({
    tabs,
    activeTab,
    onChange,
}: {
    tabs: InspectorTab[];
    activeTab: string;
    onChange: (tab: string) => void;
}) => (
    <div className={`grid ${GRID_COLS[tabs.length] ?? 'grid-cols-5'} gap-1 rounded-lg border border-[var(--color-ui-border)] bg-slate-50/80 dark:bg-slate-900/60 p-1`}>
        {tabs.map(({ id, label, icon: Icon, disabled }) => (
            <button
                key={id}
                type="button"
                disabled={disabled}
                onClick={() => onChange(id)}
                className={`flex h-12 min-w-0 flex-col items-center justify-center gap-1 rounded-md text-[10px] font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-40 ${
                    activeTab === id
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
            >
                <Icon size={14} />
                <span className="truncate">{label}</span>
            </button>
        ))}
    </div>
);
