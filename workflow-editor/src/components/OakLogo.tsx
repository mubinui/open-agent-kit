interface OakLogoProps {
    className?: string;
}

/**
 * Open Agent Kit mark — an oak tree whose branches end in agent nodes
 * (a tree that is also a workflow graph), on an emerald tile with a soft
 * top-light sheen. Keep in sync with public/oak-logo.svg (the favicon).
 */
export const OakLogo = ({ className = 'w-8 h-8' }: OakLogoProps) => (
    <svg className={className} viewBox="0 0 64 64" role="img" aria-label="Open Agent Kit logo">
        <defs>
            <linearGradient id="oakTile" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#34d399" />
                <stop offset="0.55" stopColor="#059669" />
                <stop offset="1" stopColor="#065f46" />
            </linearGradient>
            <radialGradient id="oakSheen" cx="0.25" cy="0.18" r="0.95">
                <stop offset="0" stopColor="#ffffff" stopOpacity="0.22" />
                <stop offset="0.5" stopColor="#ffffff" stopOpacity="0.05" />
                <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
            </radialGradient>
        </defs>

        {/* Tile */}
        <rect x="3" y="3" width="58" height="58" rx="15" fill="url(#oakTile)" />
        <rect x="3" y="3" width="58" height="58" rx="15" fill="url(#oakSheen)" />
        <rect x="3.5" y="3.5" width="57" height="57" rx="14.5" fill="none" stroke="#ffffff" strokeOpacity="0.14" />

        {/* Oak-as-workflow mark: a tree whose branches end in agent nodes */}
        <g stroke="#ffffff" strokeLinecap="round" fill="none">
            <path strokeWidth="4" d="M32 52 V36" />
            <path strokeWidth="3.4" d="M32 38 C32 31.5 27.5 29.5 22 27.5" />
            <path strokeWidth="3.4" d="M32 38 C32 31.5 36.5 29.5 42 27.5" />
            <path strokeWidth="3.4" d="M32 36 V23" />
            <path strokeWidth="3.4" d="M26.5 54 H37.5" opacity="0.55" />
        </g>
        <g fill="#ffffff">
            <circle cx="32" cy="18.5" r="4.6" />
            <circle cx="20" cy="26" r="4" />
            <circle cx="44" cy="26" r="4" />
        </g>
    </svg>
);
