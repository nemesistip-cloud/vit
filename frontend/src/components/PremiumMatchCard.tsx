import { useState, useEffect } from "react";
import { Link } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { format, formatDistanceToNow, isPast, differenceInMinutes, differenceInSeconds } from "date-fns";
import {
  Activity, BrainCircuit, TrendingUp, Zap, Brain, ChevronDown, ChevronUp,
  Clock, Star, Target, ShieldCheck, BarChart2, Radio
} from "lucide-react";
import type { Match } from "@/api-client/schemas";
import { PredictionFlow } from "@/components/PredictionFlow";

// ── Source label badge ────────────────────────────────────────────────

const SOURCE_META: Record<string, { label: string; cls: string; title: string }> = {
  user_csv:       { label: "CSV",    cls: "border-purple-500/40 text-purple-400",   title: "Imported via CSV upload" },
  manual_upload:  { label: "Manual", cls: "border-yellow-500/40 text-yellow-400",   title: "Added manually by admin" },
  footballdata:   { label: "API",    cls: "border-primary/40 text-primary",          title: "Synced from Football-Data API" },
  api_football:   { label: "API",    cls: "border-primary/40 text-primary",          title: "Synced from API-Football" },
  odds_api:       { label: "API",    cls: "border-cyan-500/40 text-cyan-400",        title: "Synced from Odds API" },
  sportmonks:     { label: "API",    cls: "border-primary/40 text-primary",          title: "Synced from Sportmonks API" },
  sportsdb:       { label: "Live",   cls: "border-green-500/40 text-green-400",      title: "Synced from TheSportsDB" },
  seed:           { label: "Seed",   cls: "border-muted/40 text-muted-foreground",   title: "Seeded fixture" },
  synthetic:      { label: "Synth",  cls: "border-orange-500/40 text-orange-400",   title: "Synthetically generated fixture" },
  unknown:        { label: "?",      cls: "border-muted/30 text-muted-foreground/50", title: "Unknown source" },
};

function SourceBadge({ source }: { source?: string }) {
  if (!source || source === "unknown") return null;
  const meta = SOURCE_META[source] ?? SOURCE_META.unknown;
  return (
    <span
      className={`inline-flex items-center border rounded px-1 py-0 text-[9px] font-mono leading-[14px] ${meta.cls}`}
      title={meta.title}
    >
      {meta.label}
    </span>
  );
}

// ── Match quality grade ───────────────────────────────────────────────

function getQualityGrade(confidence: number, modelConsensus?: any) {
  // When model_consensus is absent (predictions not yet run through the full
  // ensemble) default agreement to 50 — a neutral baseline — so that grade is
  // driven primarily by confidence rather than always bottoming out at D.
  const agrPct = modelConsensus?.agreement_pct ?? 50;
  const score = confidence * 0.6 + (agrPct / 100) * 0.4;
  // Thresholds are calibrated for football predictions where confidence
  // typically ranges 0.45–0.75 and agreement 50–80 %.
  if (score >= 0.70) return { grade: "A", color: "text-green-400", bg: "bg-green-400/10 border-green-400/30", label: "High Quality" };
  if (score >= 0.58) return { grade: "B", color: "text-primary", bg: "bg-primary/10 border-primary/30", label: "Good Quality" };
  if (score >= 0.48) return { grade: "C", color: "text-yellow-400", bg: "bg-yellow-400/10 border-yellow-400/30", label: "Fair Quality" };
  return { grade: "D", color: "text-orange-400", bg: "bg-orange-400/10 border-orange-400/30", label: "Low Quality" };
}

// ── Countdown timer ───────────────────────────────────────────────────

function CountdownTimer({ kickoff }: { kickoff: string }) {
  const [remaining, setRemaining] = useState("");

  useEffect(() => {
    const update = () => {
      const ko = new Date(kickoff);
      const now = new Date();
      const diffSecs = differenceInSeconds(ko, now);
      if (diffSecs <= 0) {
        setRemaining("");
        return;
      }
      const h = Math.floor(diffSecs / 3600);
      const m = Math.floor((diffSecs % 3600) / 60);
      const s = diffSecs % 60;
      if (h > 0) setRemaining(`${h}h ${m}m`);
      else if (m > 0) setRemaining(`${m}m ${s}s`);
      else setRemaining(`${s}s`);
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [kickoff]);

  if (!remaining) return null;
  return (
    <span className="flex items-center gap-1 text-yellow-400 font-mono text-[10px] font-bold">
      <Clock className="w-3 h-3" />
      {remaining}
    </span>
  );
}

// ── Live match minute estimator ───────────────────────────────────────

function LiveMinute({ kickoff }: { kickoff: string }) {
  const [minute, setMinute] = useState(0);

  useEffect(() => {
    const update = () => {
      const ko = new Date(kickoff);
      const mins = differenceInMinutes(new Date(), ko);
      setMinute(Math.min(Math.max(mins, 1), 90));
    };
    update();
    const id = setInterval(update, 60_000);
    return () => clearInterval(id);
  }, [kickoff]);

  return (
    <span className="flex items-center gap-1 text-green-400 font-mono text-xs font-bold animate-pulse">
      <Radio className="w-3 h-3" />
      {minute}&apos;
    </span>
  );
}

// ── Probability bar ───────────────────────────────────────────────────

function ProbBar({ label, prob, color = "bg-primary", teamName }: {
  label: string; prob: number; color?: string; teamName?: string;
}) {
  return (
    <div className="flex flex-col gap-1 text-center px-2 py-2.5">
      <div className="text-[9px] font-mono text-muted-foreground uppercase tracking-wide">{label}</div>
      <div className="text-xl font-bold font-mono text-primary leading-none">{(prob * 100).toFixed(0)}%</div>
      {teamName && <div className="text-[9px] font-mono text-muted-foreground/70 truncate">{teamName}</div>}
      <div className="h-0.5 w-full bg-muted/30 rounded-full mt-1 overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700`}
          style={{ width: `${Math.max(4, prob * 100)}%` }}
        />
      </div>
    </div>
  );
}

// ── Confidence meter ──────────────────────────────────────────────────

function ConfidenceMeter({ confidence, risk }: { confidence: number; risk: number }) {
  const riskLevel = risk > 0.7 ? "HIGH" : risk > 0.4 ? "MED" : "LOW";
  const riskColor = riskLevel === "HIGH" ? "text-destructive" : riskLevel === "MED" ? "text-yellow-400" : "text-primary";
  const riskBg   = riskLevel === "HIGH" ? "bg-destructive" : riskLevel === "MED" ? "bg-yellow-400" : "bg-primary";

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="text-muted-foreground w-20 uppercase">Confidence</span>
        <div className="flex-1 h-1.5 bg-muted/40 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary to-cyan-400 rounded-full transition-all duration-700"
            style={{ width: `${Math.max(0, Math.min(100, confidence * 100))}%` }}
          />
        </div>
        <span className="text-primary font-bold w-8 text-right">{(confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="text-muted-foreground w-20 uppercase">Risk</span>
        <div className="flex-1 flex gap-0.5">
          {[0.2, 0.4, 0.6, 0.8, 1.0].map((t, i) => (
            <div key={i} className={`flex-1 h-1.5 rounded-sm transition-all ${risk >= t ? riskBg : "bg-muted/30"}`} />
          ))}
        </div>
        <span className={`font-bold w-8 text-right ${riskColor}`}>{riskLevel}</span>
      </div>
    </div>
  );
}

// ── AI Insight Panel ─────────────────────────────────────────────────

function AIInsightPanel({ match }: { match: any }) {
  const confidence = match.confidence ?? match.avg_1x2_confidence ?? 0.65;
  const edge = match.edge;
  const betSide = match.bet_side;
  const overProb = match.over_25_prob;
  const bttsProb = match.btts_prob;
  const stake = match.recommended_stake;

  const insights: { label: string; value: string; accent?: string }[] = [];

  if (betSide) {
    const sideLabel = betSide === "home" ? match.home_team : betSide === "away" ? match.away_team : "Draw";
    insights.push({ label: "ML Signal", value: `Back ${sideLabel}`, accent: "text-primary" });
  }

  if (edge != null) {
    const edgeStr = `${(edge * 100).toFixed(2)}% edge`;
    insights.push({ label: "Value Edge", value: edgeStr, accent: edge > 0.03 ? "text-green-400" : edge > 0 ? "text-yellow-400" : "text-destructive" });
  }

  if (confidence > 0) {
    const tier = confidence >= 0.75 ? "HIGH" : confidence >= 0.65 ? "MED" : "LOW";
    insights.push({ label: "Confidence", value: `${(confidence * 100).toFixed(0)}% (${tier})`, accent: confidence >= 0.75 ? "text-green-400" : confidence >= 0.65 ? "text-yellow-400" : "text-orange-400" });
  }

  if (overProb != null) {
    const overSide = overProb > 0.5 ? `Over 2.5 (${(overProb * 100).toFixed(0)}%)` : `Under 2.5 (${((1 - overProb) * 100).toFixed(0)}%)`;
    insights.push({ label: "Goals Mkt", value: overSide });
  }

  if (bttsProb != null) {
    insights.push({ label: "BTTS", value: bttsProb > 0.5 ? `YES (${(bttsProb * 100).toFixed(0)}%)` : `NO (${((1 - bttsProb) * 100).toFixed(0)}%)` });
  }

  if (stake != null) {
    insights.push({ label: "Kelly %", value: `${(stake * 100).toFixed(1)}%` });
  }

  const consensus = match.model_consensus as
    | { agreed_side?: string; agreement_pct?: number; voted_models?: number;
        total_models?: number; side_distribution?: Record<string, number>;
        top_pick_avg_prob?: number; matches_final_pick?: boolean } | undefined;

  const alternatives = (match.alternative_bets ?? []) as Array<{
    market: string; side: string; edge: number; odds: number;
    model_prob: number; kelly_stake: number;
  }>;

  const sideLabelFor = (s?: string) => {
    if (!s) return "—";
    if (s === "home") return match.home_team ?? "Home";
    if (s === "away") return match.away_team ?? "Away";
    if (s === "draw") return "Draw";
    return s.replace(/_/g, " ").toUpperCase();
  };

  if (insights.length === 0 && !consensus && alternatives.length === 0) {
    return (
      <p className="text-xs font-mono text-muted-foreground text-center py-1">
        Run the ML ensemble for insights
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {insights.length > 0 && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
          {insights.map((ins) => (
            <div key={ins.label} className="flex items-center gap-1.5 text-xs font-mono">
              <span className="text-muted-foreground shrink-0 w-[72px]">{ins.label}</span>
              <span className={`font-medium ${ins.accent ?? "text-foreground"}`}>{ins.value}</span>
            </div>
          ))}
        </div>
      )}

      {consensus && consensus.voted_models ? (
        <div className="border-t border-border/30 pt-2 space-y-1.5">
          <div className="flex items-center justify-between text-[10px] font-mono uppercase text-muted-foreground">
            <span>Model Consensus</span>
            <span className={consensus.matches_final_pick ? "text-primary" : "text-yellow-400"}>
              {consensus.matches_final_pick ? "aligned" : "split"}
            </span>
          </div>
          <div className="text-xs font-mono">
            <span className="font-bold text-primary">
              {consensus.side_distribution?.[consensus.agreed_side ?? ""] ?? 0}/{consensus.voted_models}
            </span>{" "}
            models picked{" "}
            <span className="font-bold text-foreground">{sideLabelFor(consensus.agreed_side)}</span>
            {consensus.top_pick_avg_prob != null && (
              <> at avg <span className="text-foreground">{(consensus.top_pick_avg_prob * 100).toFixed(0)}%</span></>
            )}
          </div>
          <div className="flex h-1.5 rounded overflow-hidden bg-muted/40">
            {(["home", "draw", "away"] as const).map((s) => {
              const n = consensus.side_distribution?.[s] ?? 0;
              const pct = consensus.voted_models ? (n / consensus.voted_models) * 100 : 0;
              const color = s === "home" ? "bg-primary" : s === "draw" ? "bg-yellow-400" : "bg-orange-500";
              return pct > 0 ? <div key={s} className={color} style={{ width: `${pct}%` }} title={`${s}: ${n}`} /> : null;
            })}
          </div>
          <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
            <span>Home {consensus.side_distribution?.home ?? 0}</span>
            <span>Draw {consensus.side_distribution?.draw ?? 0}</span>
            <span>Away {consensus.side_distribution?.away ?? 0}</span>
            <span>{consensus.voted_models}/{consensus.total_models}</span>
          </div>
        </div>
      ) : null}

      {alternatives.length > 0 && (
        <div className="border-t border-border/30 pt-2 space-y-1">
          <div className="text-[10px] font-mono uppercase text-muted-foreground">
            Alternative Bets
          </div>
          {alternatives.slice(0, 3).map((a, i) => (
            <div
              key={`${a.market}-${a.side}-${i}`}
              className="flex items-center justify-between text-xs font-mono"
            >
              <span className="truncate flex-1 text-foreground">
                <span className="text-muted-foreground">{a.market.replace(/_/g, " ")}</span>{" · "}
                {sideLabelFor(a.side)}
              </span>
              <span className="text-muted-foreground mx-2">@ {a.odds.toFixed(2)}</span>
              <span className={`font-bold w-14 text-right ${a.edge > 0.03 ? "text-green-400" : a.edge > 0 ? "text-yellow-400" : "text-muted-foreground"}`}>
                {(a.edge * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main PremiumMatchCard ─────────────────────────────────────────────

export function PremiumMatchCard({ match }: { match: Match & { [key: string]: any } }) {
  const [showPredict, setShowPredict] = useState(false);
  const [showInsights, setShowInsights] = useState(false);

  const confidence = match.confidence ?? match.avg_1x2_confidence ?? 0.65;
  const risk = Math.max(0, 1 - confidence);
  const homeProb = match.home_prob ?? match.model_consensus_probs?.home ?? 0;
  const drawProb = match.draw_prob ?? match.model_consensus_probs?.draw ?? 0;
  const awayProb = match.away_prob ?? match.model_consensus_probs?.away ?? 0;
  const isSettled = !!match.actual_outcome;

  // Detect live: explicit status OR kickoff in last 2.5h and not settled
  const kickoffMs = match.kickoff_time ? new Date(match.kickoff_time).getTime() : NaN;
  const nowMs = Date.now();
  const isLiveByTime = Number.isFinite(kickoffMs) && !isSettled && kickoffMs <= nowMs && nowMs - kickoffMs <= 2.5 * 3600 * 1000;
  const statusRaw = String(match.status ?? "").toLowerCase();
  const isLive = statusRaw === "live" || statusRaw === "in_play" || statusRaw === "playing" || isLiveByTime;
  const isUpcoming = !isSettled && !isLive && Number.isFinite(kickoffMs) && kickoffMs > nowMs;

  const quality = getQualityGrade(confidence, match.model_consensus);

  // Odds from bookmaker data
  const homeOdds = match.odds?.home ?? match.home_odds;
  const drawOdds = match.odds?.draw ?? match.draw_odds;
  const awayOdds = match.odds?.away ?? match.away_odds;
  const hasOdds = homeOdds != null && awayOdds != null;

  // Score display
  const liveScore = isLive && match.home_goals != null && match.away_goals != null
    ? `${match.home_goals} - ${match.away_goals}`
    : null;

  // Outcome colour for settled
  const outcomeColor = match.actual_outcome === "home" ? "text-primary"
    : match.actual_outcome === "away" ? "text-orange-400"
    : match.actual_outcome === "draw" ? "text-yellow-400"
    : "text-muted-foreground";

  return (
    <>
      <PredictionFlow
        match={{
          match_id: match.match_id,
          home_team: match.home_team,
          away_team: match.away_team,
          league: match.league,
          kickoff_time: match.kickoff_time,
          odds: match.odds ?? undefined,
          home_prob: homeProb || undefined,
          draw_prob: drawProb || undefined,
          away_prob: awayProb || undefined,
          confidence: confidence || undefined,
          bet_side: match.bet_side,
          edge: match.edge,
          over_25_prob: match.over_25_prob,
          under_25_prob: match.under_25_prob,
          btts_prob: match.btts_prob,
          no_btts_prob: match.no_btts_prob,
          enabled_markets: match.enabled_markets,
        }}
        open={showPredict}
        onClose={() => setShowPredict(false)}
      />

      <Card className={`
        bg-card/50 backdrop-blur border-border h-full flex flex-col
        transition-all duration-200 group
        hover:-translate-y-0.5
        ${isLive
          ? "border-green-500/40 hover:border-green-400/60 hover:shadow-[0_4px_24px_rgba(74,222,128,0.12)]"
          : "hover:border-primary/50 hover:shadow-[0_4px_20px_rgba(0,245,255,0.08)]"
        }
      `}>
        <CardContent className="p-0 flex flex-col h-full">
          <Link href={`/matches/${match.match_id}`} className="flex flex-col flex-1">

            {/* ── LIVE top bar ────────────────────────────── */}
            {isLive && (
              <div className="flex items-center justify-between px-3 py-1.5 bg-green-500/10 border-b border-green-500/20">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse shadow-[0_0_6px_rgba(74,222,128,0.8)]" />
                  <span className="text-[10px] font-mono font-bold text-green-400 uppercase tracking-wider">Live</span>
                  <LiveMinute kickoff={match.kickoff_time} />
                </div>
                {liveScore && (
                  <span className="font-mono font-bold text-base text-green-400 tabular-nums">
                    {liveScore}
                  </span>
                )}
              </div>
            )}

            {/* ── Header ──────────────────────────────────── */}
            <div className="p-4 border-b border-border/50">
              <div className="flex justify-between items-start mb-3">
                <Badge variant="outline" className="font-mono text-[10px] border-primary/20 text-muted-foreground max-w-[140px] truncate">
                  {match.league?.replace(/_/g, " ")}
                </Badge>
                <div className="flex items-center gap-1.5">
                  {/* Quality grade */}
                  <span className={`inline-flex items-center border rounded px-1.5 py-0.5 text-[9px] font-mono font-bold leading-none ${quality.bg} ${quality.color}`}
                    title={quality.label}>
                    {quality.grade}
                  </span>
                  {match.bet_side && (
                    <Badge className="font-mono text-[10px] uppercase bg-primary/10 text-primary border border-primary/20">
                      {match.bet_side}
                    </Badge>
                  )}
                  {isSettled ? (
                    <Badge variant="secondary" className={`font-mono text-[10px] ${outcomeColor}`}>
                      {match.actual_outcome?.toUpperCase() ?? "SETTLED"}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className={`font-mono text-[10px] ${isLive ? "border-green-500/40 text-green-400" : ""}`}>
                      {isLive ? "LIVE" : "UPCOMING"}
                    </Badge>
                  )}
                </div>
              </div>

              {/* ── Teams block ─────────────────────────── */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex-1 min-w-0 space-y-1">
                  <p className="font-bold text-sm truncate leading-tight">{match.home_team}</p>
                  <p className="text-xs text-muted-foreground font-mono">vs</p>
                  <p className="font-bold text-sm truncate leading-tight">{match.away_team}</p>
                </div>

                {/* Score / Odds / Countdown */}
                <div className="flex flex-col items-end gap-1 ml-2 flex-shrink-0">
                  {isSettled && match.ft_score ? (
                    <div className={`font-mono font-bold text-2xl bg-primary/10 px-3 py-1.5 rounded border border-primary/20 text-primary`}>
                      {match.ft_score}
                    </div>
                  ) : isLive && liveScore ? (
                    <div className="font-mono font-bold text-2xl bg-green-500/10 px-3 py-1.5 rounded border border-green-500/30 text-green-400">
                      {liveScore}
                    </div>
                  ) : hasOdds ? (
                    <div className="flex flex-col gap-0.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <span className="text-[9px] font-mono text-muted-foreground">H</span>
                        <span className="font-mono font-bold text-sm text-primary">{Number(homeOdds).toFixed(2)}</span>
                      </div>
                      {drawOdds != null && (
                        <div className="flex items-center justify-end gap-1">
                          <span className="text-[9px] font-mono text-muted-foreground">D</span>
                          <span className="font-mono font-bold text-sm text-yellow-400">{Number(drawOdds).toFixed(2)}</span>
                        </div>
                      )}
                      <div className="flex items-center justify-end gap-1">
                        <span className="text-[9px] font-mono text-muted-foreground">A</span>
                        <span className="font-mono font-bold text-sm text-orange-400">{Number(awayOdds).toFixed(2)}</span>
                      </div>
                    </div>
                  ) : match.entry_odds ? (
                    <div className="text-right">
                      <div className="font-mono font-bold text-primary">{Number(match.entry_odds).toFixed(2)}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">odds</div>
                    </div>
                  ) : null}

                  {isUpcoming && (
                    <CountdownTimer kickoff={match.kickoff_time} />
                  )}
                </div>
              </div>
            </div>

            {/* ── Probability row ──────────────────────── */}
            <div className="grid grid-cols-3 gap-px bg-border/30">
              <ProbBar label="Home" prob={homeProb} color="bg-primary" teamName={homeProb >= awayProb && homeProb >= drawProb ? match.home_team : undefined} />
              <ProbBar label="Draw" prob={drawProb} color="bg-yellow-400" />
              <ProbBar label="Away" prob={awayProb} color="bg-orange-500" teamName={awayProb > homeProb && awayProb > drawProb ? match.away_team : undefined} />
            </div>

            {/* ── Confidence + risk meters ──────────────── */}
            <div className="p-4 border-t border-border/50 bg-card/20">
              <ConfidenceMeter confidence={confidence} risk={risk} />

              {/* Quick stats */}
              <div className="grid grid-cols-3 gap-2 mt-3">
                <div className="text-center">
                  <div className="text-[9px] font-mono text-muted-foreground uppercase mb-0.5">O2.5</div>
                  <div className={`text-xs font-mono font-bold ${match.over_25_prob != null && match.over_25_prob > 0.5 ? "text-green-400" : "text-foreground"}`}>
                    {match.over_25_prob != null ? `${(match.over_25_prob * 100).toFixed(0)}%` : "—"}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[9px] font-mono text-muted-foreground uppercase mb-0.5">BTTS</div>
                  <div className={`text-xs font-mono font-bold ${match.btts_prob != null && match.btts_prob > 0.5 ? "text-green-400" : "text-foreground"}`}>
                    {match.btts_prob != null ? `${(match.btts_prob * 100).toFixed(0)}%` : "—"}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[9px] font-mono text-muted-foreground uppercase mb-0.5">Kelly</div>
                  <div className="text-xs font-mono font-bold text-foreground">
                    {match.recommended_stake != null ? `${(match.recommended_stake * 100).toFixed(1)}%` : "—"}
                  </div>
                </div>
              </div>
            </div>

            {/* ── Footer ──────────────────────────────── */}
            <div className="px-4 pb-3 flex justify-between items-center text-xs font-mono text-muted-foreground border-t border-border/30 pt-2">
              <span className="flex items-center gap-1.5">
                <Activity className="w-3 h-3" />
                {match.kickoff_time ? format(new Date(match.kickoff_time), "MMM dd HH:mm") : "—"}
                <SourceBadge source={(match as any).source} />
              </span>
              {match.edge != null && (
                <span className={`flex items-center gap-1 font-bold ${match.edge > 0.03 ? "text-green-400" : match.edge > 0 ? "text-primary" : "text-destructive"}`}>
                  <TrendingUp className="w-3 h-3" />
                  {(match.edge * 100).toFixed(1)}%
                </span>
              )}
              <span className="flex items-center gap-1 text-primary/60 group-hover:text-primary transition-colors">
                <BrainCircuit className="w-3 h-3" />
                View →
              </span>
            </div>
          </Link>

          {/* ── Action row ──────────────────────────────── */}
          <div className="px-4 pb-4 pt-0 space-y-2">
            <button
              className="w-full flex items-center justify-between text-xs font-mono text-muted-foreground hover:text-foreground transition-colors py-1 border-t border-border/20 pt-2"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); setShowInsights((s) => !s); }}
            >
              <span className="flex items-center gap-1.5">
                <Brain className="w-3 h-3 text-primary/70" />
                AI Insights
                {match.bet_side && (
                  <span className="text-[9px] text-primary/60 font-mono">· {match.bet_side.toUpperCase()}</span>
                )}
              </span>
              {showInsights ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showInsights && (
              <div className="bg-background/40 border border-border/30 rounded-md p-3">
                <AIInsightPanel match={match} />
              </div>
            )}

            {!isSettled && (
              <Button
                size="sm"
                variant="outline"
                className="w-full font-mono text-xs uppercase border-primary/30 hover:border-primary hover:bg-primary/10 text-primary transition-all"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowPredict(true);
                }}
              >
                <Zap className="w-3 h-3 mr-1.5" />
                Run ML Ensemble
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  );
}
