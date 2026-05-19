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
 * VIT Brand Logo — Neural Delta Mark
 * Delta triangle = Value, Intelligence, Trust convergence point.
 * Three neural nodes (V·I·T) connected by a circuit lattice.
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  className,
  size = 32,
  withWordmark = false,
  variant = 'primary',
  iconOnly = false
}) => {
  const primary = variant === 'premium' ? '#D4AF37' : '#00C8FF';
  const accent  = variant === 'premium' ? '#F0D060' : '#00F5C8';
  const id      = `vit-grad-${variant}`;

  const logoIcon = (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="flex-shrink-0 transition-transform duration-300 hover:scale-110"
    >
      <defs>
        <radialGradient id={id} cx="50%" cy="60%" r="55%">
          <stop offset="0%"   stopColor={primary} stopOpacity="0.18" />
          <stop offset="100%" stopColor={primary} stopOpacity="0"    />
        </radialGradient>
        <filter id="glow-node">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* Ambient glow */}
      <circle cx="50" cy="54" r="44" fill={`url(#${id})`} />

      {/* ── Outer Delta (upward-pointing triangle) ── */}
      <polygon
        points="50,12 16,72 84,72"
        stroke={primary}
        strokeWidth="2.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        fill="none"
        opacity="0.85"
      />

      {/* ── Inner circuit crossbar ── */}
      <line x1="33" y1="42" x2="67" y2="42"
        stroke={accent} strokeWidth="1.5" strokeLinecap="round" opacity="0.55" />

      {/* ── Dashed neural axes from center ── */}
      <line x1="50" y1="50" x2="50" y2="14"
        stroke={primary} strokeWidth="1" strokeDasharray="2 4" strokeLinecap="round" opacity="0.35" />
      <line x1="50" y1="50" x2="18" y2="70"
        stroke={primary} strokeWidth="1" strokeDasharray="2 4" strokeLinecap="round" opacity="0.35" />
      <line x1="50" y1="50" x2="82" y2="70"
        stroke={primary} strokeWidth="1" strokeDasharray="2 4" strokeLinecap="round" opacity="0.35" />

      {/* ── V·I·T vertex nodes ── */}
      {/* Top — V */}
      <circle cx="50" cy="12" r="5.5" fill={primary} filter="url(#glow-node)" />
      {/* Bottom-left — I */}
      <circle cx="16" cy="72" r="4.5" fill={primary} opacity="0.9" />
      {/* Bottom-right — T */}
      <circle cx="84" cy="72" r="4.5" fill={primary} opacity="0.9" />

      {/* ── Mid-arm relay nodes ── */}
      <circle cx="33" cy="42" r="3" fill={accent} opacity="0.85" />
      <circle cx="67" cy="42" r="3" fill={accent} opacity="0.85" />

      {/* ── Central AI core (pulsing) ── */}
      <circle cx="50" cy="50" r="5.5" fill={accent} filter="url(#glow-node)" className="animate-pulse" />
      <circle cx="50" cy="50" r="2.5" fill="#fff" opacity="0.7" />
    </svg>
  );

  if (iconOnly) return logoIcon;

  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      {logoIcon}
      {withWordmark && (
        <div className="flex flex-col leading-tight select-none">
          <div className="flex items-baseline">
            <span className="font-bold text-xl tracking-tight font-sans text-foreground">VIT</span>
            <span className={cn(
              "font-black text-xl tracking-tighter font-sans",
              variant === 'premium' ? "text-[#D4AF37]" : "text-primary"
            )}>_OS</span>
          </div>
          <span className="text-[8px] uppercase tracking-[0.25em] text-muted-foreground/60 font-mono -mt-0.5 whitespace-nowrap">
            Value · Intelligence · Trust
          </span>
        </div>
      )}
    </div>
  );
};
