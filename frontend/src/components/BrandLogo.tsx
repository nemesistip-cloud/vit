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
 * VIT Brand Logo Component
 * Implements the "triangular_neural_v" symbolic minimal style.
 * V = Value, I = Intelligence, Trust = T
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  className,
  size = 32,
  withWordmark = false,
  variant = 'primary',
  iconOnly = false
}) => {
  const primaryColor = variant === 'premium' ? '#D4AF37' : '#1E6BFF'; // Neural Blue
  const accentColor = variant === 'premium' ? '#D4AF37' : '#00C896'; // Emerald Green

  const logoIcon = (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="flex-shrink-0 transition-transform duration-300 hover:scale-110"
    >
      {/* Background Glow */}
      <defs>
        <radialGradient id="logoGlow" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
          <stop offset="0%" stopColor={primaryColor} stopOpacity="0.15" />
          <stop offset="100%" stopColor={primaryColor} stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="50" cy="50" r="45" fill="url(#logoGlow)" />

      {/* Triangular Neural V Structure */}
      {/* Unity Triangle (muted) */}
      <path
        d="M50 20L20 75L80 75Z"
        stroke={primaryColor}
        strokeWidth="1"
        strokeOpacity="0.1"
      />

      {/* The Core 'V' (Value & Trust) */}
      <path
        d="M25 30L50 85L75 30"
        stroke={primaryColor}
        strokeWidth="8"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="vit-glow-cyan-s"
      />

      {/* Intelligence Axis (Center Line) */}
      <path
        d="M50 85V40"
        stroke={accentColor}
        strokeWidth="4"
        strokeDasharray="2 4"
        strokeLinecap="round"
      />

      {/* Neural Nodes (Blockchain/AI Connectivity) */}
      {/* Base Node */}
      <circle cx="50" cy="85" r="6" fill={accentColor} className="animate-pulse" />

      {/* Top Nodes */}
      <circle cx="25" cy="30" r="5" fill={primaryColor} />
      <circle cx="75" cy="30" r="5" fill={primaryColor} />

      {/* Intelligence Node */}
      <circle cx="50" cy="40" r="4" fill={accentColor} />

      {/* Blockchain Chain Elements (subtle connections) */}
      <circle cx="37.5" cy="57.5" r="2" fill={primaryColor} fillOpacity="0.4" />
      <circle cx="62.5" cy="57.5" r="2" fill={primaryColor} fillOpacity="0.4" />
    </svg>
  );

  if (iconOnly) return logoIcon;

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {logoIcon}

      {withWordmark && (
        <div className="flex flex-col leading-tight select-none">
          <div className="flex items-baseline">
            <span className="font-bold text-xl tracking-tight font-sans text-foreground">
              VIT
            </span>
            <span className={cn(
              "font-black text-xl tracking-tighter font-sans",
              variant === 'premium' ? "text-[#D4AF37]" : "text-primary"
            )}>
              _OS
            </span>
          </div>
          <span className="text-[8px] uppercase tracking-[0.25em] text-muted-foreground/60 font-mono -mt-0.5 whitespace-nowrap">
            Value Intelligence Trust
          </span>
        </div>
      )}
    </div>
  );
};
