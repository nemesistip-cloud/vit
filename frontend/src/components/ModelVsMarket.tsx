import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, Target, Zap, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface MarketRow {
  market: string;
  side: string;
  modelProb: number | null;
  marketOdds: number | null;
  impliedProb: number | null;
  edge: number | null;
}

interface ModelVsMarketProps {
  homeTeam: string;
  awayTeam: string;
  homeProb: number | null;
  drawProb: number | null;
  awayProb: number | null;
  over25Prob?: number | null;
  under25Prob?: number | null;
  bttsProb?: number | null;
  noBttsProb?: number | null;
  ahLine?: number | null;
  ahHomeProb?: number | null;
  ahAwayProb?: number | null;
  oddsHome?: number | null;
  oddsDraw?: number | null;
  oddsAway?: number | null;
  betSide?: string | null;
}

function vigFreeProbs(h: number, d: number, a: number) {
  const overround = 1 / h + 1 / d + 1 / a;
  return {
    home: 1 / h / overround,
    draw: 1 / d / overround,
    away: 1 / a / overround,
  };
}

function EdgeBadge({ edge }: { edge: number | null }) {
  if (edge == null) return <span className="text-muted-foreground text-[11px] font-mono">—</span>;
  const pct = (edge * 100).toFixed(1);
  if (edge > 0.03)
    return (
      <span className="inline-flex items-center gap-0.5 font-mono text-[11px] font-bold text-emerald-400">
        <TrendingUp className="w-3 h-3" />+{pct}%
      </span>
    );
  if (edge < -0.03)
    return (
      <span className="inline-flex items-center gap-0.5 font-mono text-[11px] font-bold text-red-400">
        <TrendingDown className="w-3 h-3" />{pct}%
      </span>
    );
  return (
    <span className="inline-flex items-center gap-0.5 font-mono text-[11px] text-amber-400">
      <Minus className="w-3 h-3" />{pct}%
    </span>
  );
}

function ProbBar({ prob, color }: { prob: number; color: string }) {
  return (
    <div className="w-full bg-muted/30 rounded-full h-1.5 mt-1">
      <div
        className="h-1.5 rounded-full transition-all"
        style={{ width: `${Math.min(prob * 100, 100)}%`, background: color }}
      />
    </div>
  );
}

export function ModelVsMarket({
  homeTeam,
  awayTeam,
  homeProb,
  drawProb,
  awayProb,
  over25Prob,
  under25Prob,
  bttsProb,
  noBttsProb,
  ahLine,
  ahHomeProb,
  ahAwayProb,
  oddsHome,
  oddsDraw,
  oddsAway,
  betSide,
}: ModelVsMarketProps) {
  const hasOdds = oddsHome != null && oddsDraw != null && oddsAway != null;
  const implied = hasOdds ? vigFreeProbs(oddsHome!, oddsDraw!, oddsAway!) : null;

  const rows: MarketRow[] = [];

  if (homeProb != null)
    rows.push({
      market: "1X2",
      side: `${homeTeam} (Home)`,
      modelProb: homeProb,
      marketOdds: oddsHome ?? null,
      impliedProb: implied?.home ?? null,
      edge: implied ? homeProb - implied.home : null,
    });
  if (drawProb != null)
    rows.push({
      market: "1X2",
      side: "Draw",
      modelProb: drawProb,
      marketOdds: oddsDraw ?? null,
      impliedProb: implied?.draw ?? null,
      edge: implied ? drawProb - implied.draw : null,
    });
  if (awayProb != null)
    rows.push({
      market: "1X2",
      side: `${awayTeam} (Away)`,
      modelProb: awayProb,
      marketOdds: oddsAway ?? null,
      impliedProb: implied?.away ?? null,
      edge: implied ? awayProb - implied.away : null,
    });
  if (over25Prob != null)
    rows.push({ market: "Goals", side: "Over 2.5", modelProb: over25Prob, marketOdds: null, impliedProb: null, edge: null });
  if (under25Prob != null)
    rows.push({ market: "Goals", side: "Under 2.5", modelProb: under25Prob, marketOdds: null, impliedProb: null, edge: null });
  if (bttsProb != null)
    rows.push({ market: "BTTS", side: "Yes", modelProb: bttsProb, marketOdds: null, impliedProb: null, edge: null });
  if (noBttsProb != null)
    rows.push({ market: "BTTS", side: "No", modelProb: noBttsProb, marketOdds: null, impliedProb: null, edge: null });
  if (ahLine != null && ahHomeProb != null)
    rows.push({
      market: "AH",
      side: `${homeTeam} ${ahLine > 0 ? `+${ahLine}` : ahLine}`,
      modelProb: ahHomeProb,
      marketOdds: null,
      impliedProb: null,
      edge: null,
    });
  if (ahLine != null && ahAwayProb != null)
    rows.push({
      market: "AH",
      side: `${awayTeam} ${ahLine > 0 ? `-${ahLine}` : `+${Math.abs(ahLine)}`}`,
      modelProb: ahAwayProb,
      marketOdds: null,
      impliedProb: null,
      edge: null,
    });

  const bestValueRow = rows
    .filter((r) => r.edge != null && r.edge > 0)
    .sort((a, b) => (b.edge ?? 0) - (a.edge ?? 0))[0];

  const marketColors: Record<string, string> = {
    "1X2":   "hsl(var(--primary))",
    "Goals": "hsl(173 80% 50%)",
    "BTTS":  "hsl(262 83% 58%)",
    "AH":    "hsl(38 92% 50%)",
  };

  const groups = ["1X2", "Goals", "BTTS", "AH"] as const;

  return (
    <div className="rounded-xl border border-border bg-card/50 backdrop-blur overflow-hidden">
      <div className="px-4 py-3 border-b border-border/50 flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-primary" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-primary">
            Model vs Market
          </span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {bestValueRow ? (
            <Badge
              variant="outline"
              className="font-mono text-[10px] bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
            >
              <CheckCircle2 className="w-2.5 h-2.5 mr-1" />
              Best value: {bestValueRow.side} (+{((bestValueRow.edge ?? 0) * 100).toFixed(1)}%)
            </Badge>
          ) : null}
          {!hasOdds && (
            <Badge variant="outline" className="font-mono text-[10px] text-muted-foreground/60">
              <AlertTriangle className="w-2.5 h-2.5 mr-1" />
              No market odds stored
            </Badge>
          )}
          {betSide && (
            <Badge
              variant="outline"
              className="font-mono text-[10px] bg-primary/10 border-primary/30 text-primary"
            >
              <Zap className="w-2.5 h-2.5 mr-1" />
              Model pick: {betSide.replace("_", " ").toUpperCase()}
            </Badge>
          )}
        </div>
      </div>

      <div className="divide-y divide-border/30">
        {groups.map((group) => {
          const groupRows = rows.filter((r) => r.market === group);
          if (!groupRows.length) return null;
          const color = marketColors[group];
          return (
            <div key={group} className="px-4 py-3">
              <div
                className="font-mono text-[9px] uppercase tracking-widest mb-2"
                style={{ color }}
              >
                {group === "1X2" ? "Match Result (1X2)" : group === "AH" ? `Asian Handicap (Line: ${ahLine ?? "—"})` : group}
              </div>
              <div className="space-y-2">
                {groupRows.map((row, i) => {
                  const isBest = bestValueRow === row;
                  return (
                    <div
                      key={i}
                      className={cn(
                        "grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                        isBest
                          ? "bg-emerald-500/8 border border-emerald-500/20"
                          : "bg-background/40 border border-border/30"
                      )}
                    >
                      <div className="min-w-0">
                        <div className="font-medium text-[12px] truncate">{row.side}</div>
                        {row.modelProb != null && (
                          <ProbBar prob={row.modelProb} color={color} />
                        )}
                      </div>

                      <div className="text-center">
                        <div className="text-[9px] font-mono text-muted-foreground uppercase mb-0.5">Model</div>
                        <div
                          className="font-mono text-[13px] font-bold"
                          style={{ color }}
                        >
                          {row.modelProb != null ? `${(row.modelProb * 100).toFixed(1)}%` : "—"}
                        </div>
                      </div>

                      <div className="text-center">
                        <div className="text-[9px] font-mono text-muted-foreground uppercase mb-0.5">Odds</div>
                        <div className="font-mono text-[13px] font-semibold text-foreground">
                          {row.marketOdds != null ? row.marketOdds.toFixed(2) : "—"}
                        </div>
                        {row.impliedProb != null && (
                          <div className="font-mono text-[9px] text-muted-foreground">
                            {(row.impliedProb * 100).toFixed(1)}% implied
                          </div>
                        )}
                      </div>

                      <div className="text-center min-w-[52px]">
                        <div className="text-[9px] font-mono text-muted-foreground uppercase mb-0.5">Edge</div>
                        <EdgeBadge edge={row.edge} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {!hasOdds && (
        <div className="px-4 py-3 border-t border-border/30 bg-muted/10">
          <p className="font-mono text-[10px] text-muted-foreground/60 text-center">
            Add opening/closing odds via Admin → Match Upload to unlock full edge analysis
          </p>
        </div>
      )}
    </div>
  );
}
