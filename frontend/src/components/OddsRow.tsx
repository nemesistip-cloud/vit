import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface OddsEntry {
  label: string;
  sublabel?: string;
  odds?: number | null;
  prob?: number | null;
  edge?: number | null;
  selected?: boolean;
  onClick?: () => void;
  disabled?: boolean;
}

interface OddsRowProps {
  entries: OddsEntry[];
  className?: string;
  compact?: boolean;
}

function edgeColor(edge: number) {
  if (edge > 0.05) return "text-emerald-400";
  if (edge > 0)    return "text-emerald-400/70";
  if (edge > -0.05) return "text-amber-400";
  return "text-red-400";
}

function EdgeBadge({ edge }: { edge: number }) {
  const color = edgeColor(edge);
  const Icon = edge > 0 ? TrendingUp : edge < 0 ? TrendingDown : Minus;
  return (
    <div className={cn("flex items-center gap-0.5 font-mono text-[9px] font-bold", color)}>
      <Icon className="w-2.5 h-2.5" />
      {edge > 0 ? "+" : ""}{(edge * 100).toFixed(1)}%
    </div>
  );
}

export function OddsRow({ entries, className, compact = false }: OddsRowProps) {
  return (
    <div className={cn("grid gap-2", entries.length === 2 ? "grid-cols-2" : "grid-cols-3", className)}>
      {entries.map((entry, i) => (
        <button
          key={i}
          type="button"
          disabled={entry.disabled ?? !entry.onClick}
          onClick={entry.onClick}
          className={cn(
            "flex flex-col items-center gap-1 rounded-lg border font-mono transition-all",
            compact ? "p-2" : "p-3",
            entry.selected
              ? "border-primary bg-primary/10 shadow-[0_0_14px_rgba(0,245,255,0.12)]"
              : "border-border bg-card/50 hover:border-primary/40 hover:bg-card/80",
            (entry.disabled ?? !entry.onClick) && "cursor-default opacity-80"
          )}
        >
          <span className={cn("font-bold tabular-nums", compact ? "text-sm" : "text-base", entry.selected ? "text-primary" : "text-foreground")}>
            {entry.odds != null ? entry.odds.toFixed(2) : "—"}
          </span>
          <span className={cn("uppercase truncate w-full text-center font-semibold", compact ? "text-[9px]" : "text-[10px]", entry.selected ? "text-primary/80" : "text-muted-foreground")}>
            {entry.label}
          </span>
          {entry.sublabel && (
            <span className="text-[9px] text-muted-foreground/70 truncate w-full text-center">{entry.sublabel}</span>
          )}
          {entry.prob != null && (
            <span className="text-[9px] text-muted-foreground tabular-nums">{(entry.prob * 100).toFixed(0)}% prob</span>
          )}
          {entry.edge != null && <EdgeBadge edge={entry.edge} />}
        </button>
      ))}
    </div>
  );
}

interface OddsCompactTableProps {
  rows: {
    market: string;
    home?: number | null;
    draw?: number | null;
    away?: number | null;
  }[];
  className?: string;
}

export function OddsCompactTable({ rows, className }: OddsCompactTableProps) {
  return (
    <div className={cn("rounded-lg border border-border overflow-hidden", className)}>
      <table className="w-full font-mono text-xs">
        <thead>
          <tr className="border-b border-border/50 bg-muted/10">
            <th className="text-left px-3 py-1.5 text-[10px] uppercase text-muted-foreground">Market</th>
            <th className="text-center px-2 py-1.5 text-[10px] uppercase text-muted-foreground">1</th>
            <th className="text-center px-2 py-1.5 text-[10px] uppercase text-muted-foreground">X</th>
            <th className="text-center px-2 py-1.5 text-[10px] uppercase text-muted-foreground">2</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border/20 hover:bg-muted/10 transition-colors">
              <td className="px-3 py-2 text-muted-foreground uppercase text-[10px]">{row.market}</td>
              <td className="px-2 py-2 text-center font-bold text-primary tabular-nums">{row.home?.toFixed(2) ?? "—"}</td>
              <td className="px-2 py-2 text-center tabular-nums">{row.draw?.toFixed(2) ?? "—"}</td>
              <td className="px-2 py-2 text-center text-orange-400 font-bold tabular-nums">{row.away?.toFixed(2) ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
