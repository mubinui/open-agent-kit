interface OakLogoProps {
    className?: string;
}

/** Open Agent Kit mark — an acorn-inspired node graph in the OAK emerald. */
export const OakLogo = ({ className = 'w-8 h-8' }: OakLogoProps) => (
    <svg className={className} viewBox="0 0 64 64" role="img" aria-label="Open Agent Kit logo">
        <rect x="6" y="6" width="52" height="52" rx="14" fill="#059669" />
        <circle cx="32" cy="21" r="7" fill="white" />
        <circle cx="20" cy="43" r="5.5" fill="white" />
        <circle cx="44" cy="43" r="5.5" fill="white" />
        <path
            d="M32 28V34M32 34L22 40M32 34L42 40"
            stroke="white"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
        />
    </svg>
);
