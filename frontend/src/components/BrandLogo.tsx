import React from 'react';
import { cn } from "@/lib/utils";

interface BrandLogoProps {
  className?: string;
  size?: number | string;
  withWordmark?: boolean;
  variant?: 'primary' | 'light' | 'premium';
  iconOnly?: boolean;
}

/**
 * VIT Brand Logo — Hexagonal AI Core Mark v2
 * Hex frame = institutional precision. Inner delta = direction + edge.
 * Six circuit nodes = the 6-layer model stack.
 * Central pulse = live AI inference engine.
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  className,
  size = 32,
  withWordmark = false,
  variant = 'primary',
  iconOnly = false
}) => {
  const cyan    = variant === 'premium' ? '#D4AF37' : '#00C8FF';
  const teal    = variant === 'premium' ? '#F0D060' : '#00F5C8';
  const purple  = variant === 'premium' ? '#C8A030' : '#7C3AED';
  const id      = `vit-${variant}`;
  const glowId  = `vit-glow-${variant}`;
  const hexId   = `vit-hex-${variant}`;

  const logoIcon = (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="flex-shrink-0"
      aria-label="VIT Sports Intelligence Logo"
    >
      <defs>
        {/* Core radial gradient */}
        <radialGradient id={id} cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor={cyan}   stopOpacity="0.25" />
          <stop offset="60%"  stopColor={teal}   stopOpacity="0.08" />
          <stop offset="100%" stopColor={purple} stopOpacity="0"    />
        </radialGradient>

        {/* Hex face fill */}
        <linearGradient id={hexId} x1="20" y1="10" x2="80" y2="90" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor={cyan}   stopOpacity="0.14" />
          <stop offset="100%" stopColor={purple} stopOpacity="0.08" />
        </linearGradient>


        <clipPath id={`${id}-clip`}>
          <polygon points="50,6 88,28 88,72 50,94 12,72 12,28" />
        </clipPath>
      </defs>

      {/* ── Ambient field ── */}
      <circle cx="50" cy="50" r="46" fill={`url(#${id})`} />

      {/* ── Hex outer ring (faint) ── */}
      <polygon
        points="50,5 89,27.5 89,72.5 50,95 11,72.5 11,27.5"
        stroke={cyan}
        strokeWidth="1"
        fill="none"
        opacity="0.18"
      />

      {/* ── Hex face ── */}
      <polygon
        points="50,12 83,31 83,69 50,88 17,69 17,31"
        stroke={cyan}
        strokeWidth="1.5"
        fill={`url(#${hexId})`}
        opacity="0.9"
        strokeLinejoin="round"
      />

      {/* ── Six circuit nodes at hex vertices ── */}
      {[
        { cx: 50, cy: 12 },
        { cx: 83, cy: 31 },
        { cx: 83, cy: 69 },
        { cx: 50, cy: 88 },
        { cx: 17, cy: 69 },
        { cx: 17, cy: 31 },
      ].map(({ cx, cy }, i) => (
        <g key={i}>
          <circle cx={cx} cy={cy} r="3.8" fill={i === 0 ? teal : cyan} opacity={i === 0 ? 1 : 0.7} />
          <circle cx={cx} cy={cy} r="1.8" fill="#fff" opacity={i === 0 ? 0.9 : 0.5} />
        </g>
      ))}

      {/* ── Inner delta triangle (Value · Intelligence · Trust) ── */}
      <polygon
        points="50,24 68,56 32,56"
        stroke={teal}
        strokeWidth="2"
        strokeLinejoin="round"
        fill="none"
        opacity="0.85"
      />

      {/* ── Delta interior fill gradient ── */}
      <polygon
        points="50,24 68,56 32,56"
        fill={teal}
        opacity="0.07"
      />

      {/* ── V·I·T vertex indicators on delta ── */}
      <circle cx="50" cy="24" r="3.2" fill={teal} opacity="0.9" />
      <circle cx="68" cy="56" r="2.8" fill={cyan} opacity="0.85" />
      <circle cx="32" cy="56" r="2.8" fill={cyan} opacity="0.85" />

      {/* ── Circuit crossbar across delta mid ── */}
      <line x1="35" y1="41" x2="65" y2="41"
        stroke={cyan} strokeWidth="1" strokeDasharray="2.5 3" strokeLinecap="round" opacity="0.4" />

      {/* ── Radial spokes from centre to hex midpoints (faint data lines) ── */}
      {[
        [50, 50, 50, 12], [50, 50, 83, 31], [50, 50, 83, 69],
        [50, 50, 50, 88], [50, 50, 17, 69], [50, 50, 17, 31],
      ].map(([x1, y1, x2, y2], i) => (
        <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={i % 2 === 0 ? cyan : purple}
          strokeWidth="0.7" strokeDasharray="1.5 5"
          strokeLinecap="round" opacity="0.22" />
      ))}

      {/* ── Central AI core ── */}
      <circle cx="50" cy="50" r="7.5"
        fill={teal} opacity="0.15"
        className="animate-pulse"
      />
      <circle cx="50" cy="50" r="5"
        fill={teal} opacity="0.9"
      />
      <circle cx="50" cy="50" r="2.5"
        fill="#fff" opacity="0.85"
      />
    </svg>
  );

  if (iconOnly) return logoIcon;

  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      {logoIcon}
      {withWordmark && (
        <div className="flex flex-col leading-tight select-none">
          <div className="flex items-baseline gap-0.5">
            <span className="font-black text-lg tracking-tight font-mono text-foreground">VIT</span>
            <span className={cn(
              "font-black text-lg tracking-tighter font-mono",
              variant === 'premium' ? "text-[#D4AF37]" : "text-primary"
            )}>_OS</span>
          </div>
          <span className="text-[7.5px] uppercase tracking-[0.22em] text-muted-foreground/55 font-mono -mt-0.5 whitespace-nowrap">
            Intelligence · Edge · Trust
          </span>
        </div>
      )}
    </div>
  );
};
