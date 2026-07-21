# VIT Network — Reusable Component Library

**Version:** 6.0.0
**Domain:** /docs/components/
**Status:** Component Blueprint Approved

---

## 1. Overview & Reusability Philosophy

All components in the VIT Network frontend are built as **highly modular, reusable primitives** utilizing React, TypeScript, Tailwind CSS, and shadcn/ui. Components accept strict TypeScript properties, manage their own loading/error sub-states, and are completely decoupled from workspace-specific logic.

---

## 2. Core Card Primitives

### 2.1 GlassCard Component
- **Aesthetic:** Translucent dark backdrop with subtle border borders, mimicking physical glass overlays.
- **Props interface:**
  ```typescript
  interface GlassCardProps {
    title?: string;
    hoverGlow?: boolean;
    padding?: "none" | "sm" | "md" | "lg";
    onClick?: () => void;
  }
  ```
- **Styles:** `bg-surface-800/60 border border-surface-700/80 backdrop-blur-md rounded-xl shadow-lg shadow-black/20`.

### 2.2 StatCard Component
- **Aesthetic:** Primary high-density metric card displaying a single, focused system value.
- **Visual Structure:**
  ```
  ┌──────────────────────────────────────────────┐
  │  Metric Label                     [Icon]     │
  │  Large Numerical Value                       │
  │  Percentage Change (or subtext)              │
  └──────────────────────────────────────────────┘
  ```
- **Props interface:**
  ```typescript
  interface StatCardProps {
    label: string;
    value: string | number;
    icon?: React.ReactNode;
    trend?: { value: number; isPositive: boolean };
    loading?: boolean;
  }
  ```

---

## 3. Data Tables & High-Density Lists

### 3.1 DataGrid Component
- **Aesthetic:** Excel-dense table with sorting, paging, and responsive cell formatting. Uses *JetBrains Mono* for numeric content.
- **Key Capabilities:**
  - Column sorting via click headers.
  - Client-side or server-side pagination with limit/offset.
  - Row click navigation.
- **Implementation Style:**
  ```typescript
  export const DataGrid = <T,>({ columns, data, loading }: DataGridProps<T>) => {
    // ...
  };
  ```

---

## 4. Analytical Visualization Cards

### 4.1 CalibrationChart Component
- **Aesthetic:** Multi-line or area chart comparing model probabilities against actual event outcomes.
- **Technology:** Driven by **Recharts** with responsive resizing.
- **Props interface:**
  ```typescript
  interface CalibrationData {
    modelName: string;
    dataPoints: { x: number; y: number }[];
  }
  ```

---

## 5. Feeds, Timelines, & Insight Panels

### 5.1 AIInsightPanel Component
- **Aesthetic:** Highlighted side drawer or collapsible card displaying natural-language reasoning produced by agents.
- **Features:** Shows confidence score, active model weights breakdown, and an action button to "Execute Recommended Strategy".

### 5.2 ActivityFeed Component
- **Aesthetic:** Vertical, stacked timeline with live-scrolling items linked directly to an active websocket connection.
- **Items:** Includes dynamic type icons (gas flame, wallet currency, node checkmark) and relative time durations (e.g. "2 min ago").

---

## 6. Feedback & Overlay Components

### 6.1 Modal & Dialog Primitive
- **Aesthetic:** Fixed centered backdrop overlay with entrance fade-in (`animate-fade-in`) animations. Includes automatic backdrop click dismissal.

### 6.2 BottomDrawer Component
- **Aesthetic:** Mobile-friendly overlay sheet that slides up from the screen bottom (`animate-slide-up`). Replaces the centered modal layout on mobile screen sizes.

---

## 7. Actionable Implementation Guidance

Developers can implement the standard `StatCard` using the following shadcn/ui pattern:

```typescript
import React from "react";
import { Skeleton } from "@/components/ui/skeleton";

export const StatCard: React.FC<StatCardProps> = ({ label, value, icon, trend, loading }) => {
  if (loading) return <Skeleton className="h-32 w-full rounded-xl bg-surface-800" />;

  return (
    <div className="bg-surface-800/60 border border-surface-700/80 backdrop-blur-md rounded-xl p-6 relative overflow-hidden transition-all duration-200 hover:border-blue-500/50">
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs uppercase tracking-wider font-medium text-slate-400">{label}</span>
        {icon && <div className="text-blue-400">{icon}</div>}
      </div>
      <div className="text-3xl font-bold tracking-tight text-white font-mono">{value}</div>
      {trend && (
        <span className={`text-xs font-semibold ${trend.isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
          {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
        </span>
      )}
    </div>
  );
};
```

This reusable component library guarantees UI modularity across every workspace in the VIT Network.
