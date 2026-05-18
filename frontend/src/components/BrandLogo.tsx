import React from 'react';
import { cn } from "@/lib/utils";

interface BrandLogoProps {
  className?: string;
  size?: number | string;
  withWordmark?: boolean;
  variant?: 'primary' | 'light' | 'premium' | 'gold';
  iconOnly?: boolean;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  className,
  size = 32,
  withWordmark = false,
  variant = 'primary',
  iconOnly = false
}) => {
  const isGold = variant === 'premium' || variant === 'gold';
  const gradStart = isGold ? '#FFD700' : '#00F5FF';
  const gradMid   = isGold ? '#D4AF37' : '#1E6BFF';
  const gradEnd   = isGold ? '#B8860B' : '#0033CC';
  const glowColor = isGold ? 'rgba(212,175,55,0.45)' : 'rgba(0,245,255,0.45)';
  const nodeColor = isGold ? '#FFD700' : '#00F5FF';
  const uid = `vit-logo-${variant}`;

  const logoIcon = (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="flex-shrink-0"
    >
      <defs>
        <linearGradient id={`${uid}-grad`} x1="20" y1="16" x2="80" y2="88" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor={gradStart} />
          <stop offset="55%"  stopColor={gradMid}   />
          <stop offset="100%" stopColor={gradEnd}   />
        </linearGradient>
        <radialGradient id={`${uid}-apex-glow`} cx="50%" cy="88%" r="30%">
          <stop offset="0%"   stopColor={nodeColor} stopOpacity="0.6" />
          <stop offset="100%" stopColor={nodeColor} stopOpacity="0"   />
        </radialGradient>
        <radialGradient id={`${uid}-bg-glow`} cx="50%" cy="60%" r="50%">
          <stop offset="0%"   stopColor={glowColor} />
          <stop offset="100%" stopColor="transparent" />
        </radialGradient>
        <filter id={`${uid}-glow`} x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="2" result="b" />
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id={`${uid}-apex`} x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="3.5" result="b" />
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      {/* Background ambient glow */}
      <ellipse cx="50" cy="64" rx="36" ry="26" fill={`url(#${uid}-bg-glow)`} />
      <ellipse cx="50" cy="88" rx="18" ry="10" fill={`url(#${uid}-apex-glow)`} />

      {/* Outer triangle frame */}
      <path d="M50 10 L6 88 L94 88 Z"
        stroke={`url(#${uid}-grad)`} strokeWidth="1.8" strokeOpacity="0.3" fill="none" />

      {/* Second triangle ring */}
      <path d="M50 22 L16 82 L84 82 Z"
        stroke={`url(#${uid}-grad)`} strokeWidth="1.2" strokeOpacity="0.5" fill="none" />

      {/* Horizontal connector between top corners */}
      <line x1="22" y1="26" x2="78" y2="26"
        stroke={nodeColor} strokeWidth="0.8" strokeOpacity="0.3" />

      {/* Left arm of the V */}
      <line x1="22" y1="26" x2="50" y2="86"
        stroke={`url(#${uid}-grad)`} strokeWidth="6"
        strokeLinecap="round" filter={`url(#${uid}-glow)`} />

      {/* Right arm of the V */}
      <line x1="78" y1="26" x2="50" y2="86"
        stroke={`url(#${uid}-grad)`} strokeWidth="6"
        strokeLinecap="round" filter={`url(#${uid}-glow)`} />

      {/* Inner V — left */}
      <line x1="35" y1="34" x2="50" y2="70"
        stroke={nodeColor} strokeWidth="2.5" strokeLinecap="round"
        strokeOpacity="0.85" filter={`url(#${uid}-glow)`} />

      {/* Inner V — right */}
      <line x1="65" y1="34" x2="50" y2="70"
        stroke={nodeColor} strokeWidth="2.5" strokeLinecap="round"
        strokeOpacity="0.85" filter={`url(#${uid}-glow)`} />

      {/* Circuit dots on left arm */}
      <circle cx="31"  cy="44" r="2"   fill={nodeColor} fillOpacity="0.75" />
      <circle cx="37"  cy="56" r="1.5" fill={nodeColor} fillOpacity="0.5"  />
      <circle cx="43.5" cy="68" r="2"  fill={nodeColor} fillOpacity="0.75" />

      {/* Circuit dots on right arm */}
      <circle cx="69"   cy="44" r="2"   fill={nodeColor} fillOpacity="0.75" />
      <circle cx="63"   cy="56" r="1.5" fill={nodeColor} fillOpacity="0.5"  />
      <circle cx="56.5" cy="68" r="2"   fill={nodeColor} fillOpacity="0.75" />

      {/* Horizontal dashed mid-bar */}
      <line x1="28" y1="56" x2="72" y2="56"
        stroke={nodeColor} strokeWidth="0.7" strokeOpacity="0.2"
        strokeDasharray="2.5 4" />

      {/* Top-left node */}
      <circle cx="22" cy="26" r="4" fill="none"
        stroke={nodeColor} strokeWidth="1.6" />
      <circle cx="22" cy="26" r="2" fill={nodeColor} />
      {/* tail left */}
      <line x1="6" y1="26" x2="18" y2="26"
        stroke={nodeColor} strokeWidth="1.1" strokeOpacity="0.45" />
      <circle cx="6" cy="26" r="1.8" fill={nodeColor} fillOpacity="0.5" />

      {/* Top-right node */}
      <circle cx="78" cy="26" r="4" fill="none"
        stroke={nodeColor} strokeWidth="1.6" />
      <circle cx="78" cy="26" r="2" fill={nodeColor} />
      {/* tail right */}
      <line x1="82" y1="26" x2="94" y2="26"
        stroke={nodeColor} strokeWidth="1.1" strokeOpacity="0.45" />
      <circle cx="94" cy="26" r="1.8" fill={nodeColor} fillOpacity="0.5" />

      {/* Apex glow node */}
      <circle cx="50" cy="86" r="6" fill="none"
        stroke={nodeColor} strokeWidth="2" filter={`url(#${uid}-apex)`} />
      <circle cx="50" cy="86" r="3" fill={nodeColor}
        filter={`url(#${uid}-apex)`} />
    </svg>
  );

  if (iconOnly) return logoIcon;

  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      {logoIcon}
      {withWordmark && (
        <div className="flex flex-col leading-tight select-none">
          <div className="flex items-baseline gap-0.5">
            <span className="font-black text-xl tracking-tight text-foreground">VIT</span>
            <span className={cn(
              "font-black text-xl tracking-tighter",
              isGold ? "text-[#D4AF37]" : "text-[#00F5FF]"
            )}>_OS</span>
          </div>
          <span className="text-[8px] uppercase tracking-[0.22em] text-muted-foreground/60 font-mono whitespace-nowrap">
            Value · Intelligence · Trust
          </span>
        </div>
      )}
    </div>
  );
};
