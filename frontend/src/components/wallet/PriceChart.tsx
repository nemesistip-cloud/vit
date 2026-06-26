import React, { useMemo } from "react";

interface PriceChartProps {
  data: number[];
  height?: number;
  color?: string;
  showLabels?: boolean;
}

export function PriceChart({ data, height = 64, color = "#00E676", showLabels = false }: PriceChartProps) {
  const points = useMemo(() => {
    if (!data || data.length < 2) return null;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const w = 100;
    const h = height;
    const pad = 4;
    const pts = data.map((v, i) => {
      const x = (i / (data.length - 1)) * (w - pad * 2) + pad;
      const y = h - pad - ((v - min) / range) * (h - pad * 2);
      return `${x},${y}`;
    });
    return pts.join(" ");
  }, [data, height]);

  if (!points) {
    return (
      <div
        style={{ height }}
        className="w-full rounded flex items-center justify-center"
      >
        <span className="text-xs text-white/20 font-['Outfit']">No data</span>
      </div>
    );
  }

  const isPositive = data[data.length - 1] >= data[0];
  const lineColor = color || (isPositive ? "#00E676" : "#f87171");

  return (
    <div className="w-full relative" style={{ height }}>
      <svg
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        className="w-full h-full"
      >
        <defs>
          <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={lineColor} stopOpacity="0.15" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polyline
          points={`${points} 100,${height} 0,${height}`}
          fill="url(#chartGrad)"
          stroke="none"
        />
        <polyline
          points={points}
          fill="none"
          stroke={lineColor}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      {showLabels && data.length >= 2 && (
        <div className="absolute inset-x-0 bottom-0 flex justify-between px-1">
          <span className="text-[9px] font-['JetBrains_Mono'] text-white/20">
            ${Math.min(...data).toFixed(4)}
          </span>
          <span className="text-[9px] font-['JetBrains_Mono'] text-white/20">
            ${Math.max(...data).toFixed(4)}
          </span>
        </div>
      )}
    </div>
  );
}
