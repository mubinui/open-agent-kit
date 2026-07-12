interface OakLogoProps {
    className?: string;
}

/** Open Agent Kit mark — a branching oak tree in the OAK emerald gradient. */
export const OakLogo = ({ className = 'w-8 h-8' }: OakLogoProps) => (
    <svg className={className} viewBox="0 0 64 64" role="img" aria-label="Open Agent Kit logo">
        <defs>
            <linearGradient id="oakGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#10b981" />
                <stop offset="1" stopColor="#047857" />
            </linearGradient>
        </defs>
        <rect x="4" y="4" width="56" height="56" rx="16" fill="url(#oakGrad)" />
        <path
            fill="none"
            stroke="white"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2.4"
            transform="translate(15,14) scale(1.45)"
            d="m12 13l-2-2m2 1l2-2m-2 11V8m-2.176 8a3 3 0 0 1-2.743-3.69a3 3 0 0 1 .304-4.833A3 3 0 0 1 12 3.77a3 3 0 0 1 4.614 3.707a3 3 0 0 1 .305 4.833A3 3 0 0 1 14 16.005h-4z"
        />
    </svg>
);
