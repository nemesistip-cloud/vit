import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import {
  Zap, Send, Search, Trophy, AlertTriangle, Wallet,
  CheckCircle, ChevronDown, ChevronUp, Target, TrendingUp, X,
} from "lucide-react";

const MAX_SELECTIONS = 12;
const SIDE_LABELS: Record<string, string> = { home: "HOME", draw: "DRAW", away: "AWAY" };
// CURRENCIES and LEAGUE_SHORT now come from /config/public via usePublicConfig().

function edgeLabel(e: number) {
  if (e >= 0.05) return "🔥🔥🔥 FIRE";
  if (e >= 0.03) return "🔥🔥 STRONG";
  if (e >= 0.01) return "🔥 GOOD";
  return "📊 MARGINAL";
}

function confidenceColor(c: number) {
  if (c >= 0.75) return "text-green-400";
  if (c >= 0.65) return "text-yellow-400";
  return "text-orange-400";
}

interface Candidate {
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff?: string;
  best_side: string;
  best_odds: number;
  confidence: number;
  edge: number;
}

interface Accumulator {
  n_legs: number;
  legs: Candidate[];
  combined_odds: number;
  combined_prob: number;
  fair_odds: number;
  adjusted_edge: number;
  correlation_penalty: number;
  avg_confidence: number;
  kelly_stake: number;
}

interface BetReceipt {
  transaction_id: string;
  stake: number;
  currency: string;
  n_legs: number;
  combined_odds: number;
  potential_payout: number;
  message: string;
}

export default function AccumulatorPage() {
  const { data: publicCfg } = usePublicConfig();
  const CURRENCIES = (publicCfg?.currencies ?? []).map((c) => c.code).filter(
    // accumulator stakes don't accept Pi for now (no settlement path)
    (c) => c !== "PI",
  );
  const LEAGUE_SHORT = publicCfg?.league_short ?? {};

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [candFilters, setCandFilters] = useState({ minConfidence: 0.60, minEdge: 0.01, count: 20 });
  const [accFilters, setAccFilters] = useState({ minLegs: 1, maxLegs: 5, topN: 10 });
  const [accumulators, setAccumulators] = useState<Accumulator[]>([]);
  const [expandedAcc, setExpandedAcc] = useState<number | null>(null);
  const [stakeCurrency, setStakeCurrency] = useState("USD");
  const [stakes, setStakes] = useState<Record<number, string>>({});
  const [receipts, setReceipts] = useState<Record<number, BetReceipt>>({});
  const [sendingTg, setSendingTg] = useState<number | null>(null);

  const candidatesQuery = useQuery<{ candidates: Candidate[] }>({
    queryKey: ["accumulator-candidates", candFilters],
    queryFn: () => apiGet<{ candidates: Candidate[] }>(
      `/admin/accumulator/candidates?min_confidence=${candFilters.minConfidence}&min_edge=${candFilters.minEdge}&count=${candFilters.count}`
    ),
    enabled: false,
  });

  const generateMutation = useMutation<{ accumulators: Accumulator[] }, Error, any>({
    mutationFn: (data) => apiPost<{ accumulators: Accumulator[] }>("/admin/accumulator/generate", data),
    onSuccess: (data) => {
      setAccumulators(data.accumulators || []);
      setExpandedAcc(0);
      toast.success(`Generated ${data.accumulators?.length ?? 0} accumulator combos`);
    },
    onError: (e) => toast.error(e.message),
  });

  const placeBetMutation = useMutation<BetReceipt, Error, { accIdx: number; acc: Accumulator; stake: number; currency: string }>({
    mutationFn: ({ acc, stake, currency }) =>
      apiPost<BetReceipt>("/admin/accumulator/place-bet", { accumulator: acc, stake, currency }),
    onSuccess: (receipt, vars) => {
      setReceipts((r) => ({ ...r, [vars.accIdx]: receipt }));
      toast.success(`✅ Bet placed! Potential payout: ${receipt.currency} ${receipt.potential_payout.toFixed(2)}`);
    },
    onError: (e) => toast.error(e.message ?? "Failed to place bet"),
  });

  const sendTgMutation = useMutation<{ sent: boolean }, Error, { acc: Accumulator; idx: number }>({
    mutationFn: ({ acc }) => apiPost<{ sent: boolean }>("/admin/accumulator/send", { accumulator: acc }),
    onSuccess: (data, vars) => {
      setSendingTg(null);
      toast.success(data.sent ? "Sent to Telegram!" : "Telegram send failed");
    },
    onError: (e) => { setSendingTg(null); toast.error(e.message); },
  });

  const candidates = candidatesQuery.data?.candidates ?? [];

  function toggleCandidate(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size >= MAX_SELECTIONS) {
          toast.warning(`Maximum ${MAX_SELECTIONS} selections allowed`);
          return prev;
        }
        next.add(id);
      }
      return next;
    });
  }

  function handleFetch() {
    candidatesQuery.refetch().then((result) => {
      if (result.data?.candidates) {
        // Auto-select top candidates up to MAX_SELECTIONS
        const topIds = result.data.candidates
          .slice(0, Math.min(MAX_SELECTIONS, result.data.candidates.length))
          .map((c) => c.match_id);
        setSelectedIds(new Set(topIds));
        setAccumulators([]);
      }
    });
  }

  function handleGenerate() {
    if (generateMutation.isPending) return;
    const selected = candidates.filter((c) => selectedIds.has(c.match_id));
    const minLegs = Math.max(1, accFilters.minLegs);
    if (selected.length < minLegs) {
      toast.error(`Select at least ${minLegs} ${minLegs === 1 ? "candidate" : "candidates"}`);
      return;
    }
    generateMutation.mutate({
      candidates: selected,
      min_legs: minLegs,
      max_legs: Math.max(minLegs, Math.min(accFilters.maxLegs, selected.length)),
      top_n: accFilters.topN,
    });
  }

  function handlePlaceBet(acc: Accumulator, idx: number) {
    const stakeStr = stakes[idx];
    if (!stakeStr || isNaN(Number(stakeStr)) || Number(stakeStr) <= 0) {
      toast.error("Enter a valid stake amount");
      return;
    }
    placeBetMutation.mutate({ accIdx: idx, acc, stake: Number(stakeStr), currency: stakeCurrency });
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-primary/10 border border-primary/20 rounded-xl flex items-center justify-center">
          <Zap className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight">Accumulator Engine</h1>
          <p className="text-muted-foreground font-mono text-sm">
            Kelly-optimised combos · wallet-integrated betting · Telegram alerts
          </p>
        </div>
      </div>

      {/* Step 1 — Fetch Candidates */}
      <Card className="border-border/50">
        <CardHeader className="border-b border-border/50 pb-4">
          <CardTitle className="font-mono text-sm flex items-center gap-2">
            <Search className="w-4 h-4 text-primary" /> Step 1 — Scan for Candidates
          </CardTitle>
          <CardDescription className="font-mono text-xs">
            Scan upcoming fixtures for positive-edge accumulator legs
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-5 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <Label className="font-mono text-xs uppercase">Min Confidence</Label>
              <Input
                type="number" min="0.5" max="0.99" step="0.05"
                className="font-mono bg-background/50"
                value={candFilters.minConfidence}
                onChange={(e) => setCandFilters((f) => ({ ...f, minConfidence: parseFloat(e.target.value) }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="font-mono text-xs uppercase">Min Edge</Label>
              <Input
                type="number" min="0" max="0.2" step="0.005"
                className="font-mono bg-background/50"
                value={candFilters.minEdge}
                onChange={(e) => setCandFilters((f) => ({ ...f, minEdge: parseFloat(e.target.value) }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="font-mono text-xs uppercase">Fixtures to scan</Label>
              <Input
                type="number" min="5" max="50"
                className="font-mono bg-background/50"
                value={candFilters.count}
                onChange={(e) => setCandFilters((f) => ({ ...f, count: parseInt(e.target.value) }))}
              />
            </div>
          </div>
          <Button
            onClick={handleFetch}
            disabled={candidatesQuery.isFetching}
            className="font-mono gap-2"
          >
            <Search className="w-4 h-4" />
            {candidatesQuery.isFetching ? "SCANNING..." : "SCAN FIXTURES"}
          </Button>

          {candidates.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-mono text-muted-foreground">
                  {candidates.length} candidates found · {selectedIds.size}/{MAX_SELECTIONS} selected
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline" size="sm" className="font-mono text-xs h-7"
                    onClick={() => setSelectedIds(new Set(candidates.slice(0, MAX_SELECTIONS).map(c => c.match_id)))}
                  >
                    Select all
                  </Button>
                  <Button
                    variant="outline" size="sm" className="font-mono text-xs h-7"
                    onClick={() => setSelectedIds(new Set())}
                  >
                    Clear
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-1 gap-1.5 max-h-72 overflow-y-auto pr-1">
                {candidates.map((c) => (
                  <div
                    key={c.match_id}
                    onClick={() => toggleCandidate(c.match_id)}
                    className={`flex items-center gap-3 rounded-md px-3 py-2 cursor-pointer transition-colors border ${
                      selectedIds.has(c.match_id)
                        ? "bg-primary/10 border-primary/30"
                        : "border-border/30 hover:bg-muted/30"
                    }`}
                  >
                    <Checkbox
                      checked={selectedIds.has(c.match_id)}
                      onCheckedChange={() => toggleCandidate(c.match_id)}
                      className="flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <span className="font-mono text-xs font-medium truncate block">
                        {c.home_team} vs {c.away_team}
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {LEAGUE_SHORT[c.league] ?? c.league}
                      </span>
                    </div>
                    <Badge variant="outline" className="font-mono text-[10px] flex-shrink-0">
                      {SIDE_LABELS[c.best_side]} @ {c.best_odds.toFixed(2)}
                    </Badge>
                    <span className={`font-mono text-[10px] flex-shrink-0 ${confidenceColor(c.confidence)}`}>
                      {(c.confidence * 100).toFixed(0)}%
                    </span>
                    <span className="font-mono text-[10px] text-primary flex-shrink-0">
                      +{(c.edge * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2 — Build */}
      {candidates.length > 0 && (
        <Card className="border-border/50">
          <CardHeader className="border-b border-border/50 pb-4">
            <CardTitle className="font-mono text-sm flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" /> Step 2 — Build Combinations
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-5 space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label className="font-mono text-xs uppercase">Min Legs</Label>
                <Input
                  type="number" min="1" max="8" className="font-mono bg-background/50"
                  value={accFilters.minLegs}
                  onChange={(e) => setAccFilters((f) => ({ ...f, minLegs: Math.max(1, parseInt(e.target.value) || 1) }))}
                  data-testid="input-min-legs"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="font-mono text-xs uppercase">Max Legs</Label>
                <Input
                  type="number" min="1" max="8" className="font-mono bg-background/50"
                  value={accFilters.maxLegs}
                  onChange={(e) => setAccFilters((f) => ({ ...f, maxLegs: Math.max(1, parseInt(e.target.value) || 1) }))}
                  data-testid="input-max-legs"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="font-mono text-xs uppercase">Top N Results</Label>
                <Input
                  type="number" min="1" max="20" className="font-mono bg-background/50"
                  value={accFilters.topN}
                  onChange={(e) => setAccFilters((f) => ({ ...f, topN: parseInt(e.target.value) }))}
                />
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Button
                onClick={handleGenerate}
                disabled={generateMutation.isPending || selectedIds.size < Math.max(1, accFilters.minLegs)}
                className="font-mono gap-2"
                data-testid="button-generate-accumulator"
              >
                <Trophy className="w-4 h-4" />
                {generateMutation.isPending
                  ? "GENERATING..."
                  : selectedIds.size === 1 && accFilters.minLegs <= 1
                    ? "PLACE SINGLE BET (1 selected)"
                    : `GENERATE (${selectedIds.size} selected)`}
              </Button>
              {selectedIds.size < Math.max(1, accFilters.minLegs) && (
                <p className="text-xs font-mono text-yellow-400 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  {candidates.length === 0
                    ? "Run a fixture scan first."
                    : candidates.length < accFilters.minLegs
                      ? `Only ${candidates.length} candidate${candidates.length === 1 ? "" : "s"} available — lower Min Legs to ${candidates.length}, lower Min Edge / Min Confidence, or scan more fixtures.`
                      : `Select at least ${accFilters.minLegs} ${accFilters.minLegs === 1 ? "candidate" : "candidates"}.`}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3 — Results */}
      {accumulators.length > 0 && (
        <Card className="border-border/50">
          <CardHeader className="border-b border-border/50 pb-4">
            <div className="flex justify-between items-center">
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" /> Top {accumulators.length} Accumulators
              </CardTitle>
              <div className="flex items-center gap-2">
                <Label className="font-mono text-xs text-muted-foreground">Bet currency:</Label>
                <Select value={stakeCurrency} onValueChange={setStakeCurrency}>
                  <SelectTrigger className="h-7 text-xs font-mono w-28">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map(c => <SelectItem key={c} value={c} className="font-mono text-xs">{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-5 space-y-3">
            {accumulators.map((acc, i) => (
              <div
                key={i}
                className={`rounded-lg border transition-colors ${
                  acc.adjusted_edge > 0.03
                    ? "border-primary/40 bg-primary/5"
                    : "border-border/50 bg-card/30"
                }`}
              >
                {/* Header row */}
                <div
                  className="flex items-center justify-between p-4 cursor-pointer"
                  onClick={() => setExpandedAcc(expandedAcc === i ? null : i)}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-sm">
                      {acc.n_legs}-Leg {edgeLabel(acc.adjusted_edge)}
                    </span>
                    <Badge variant="outline" className="font-mono text-xs">
                      @ {acc.combined_odds.toFixed(2)}
                    </Badge>
                    <Badge
                      className={`font-mono text-xs ${
                        acc.adjusted_edge > 0.03
                          ? "bg-primary/10 text-primary border-primary/20"
                          : "bg-muted/40 text-muted-foreground"
                      }`}
                    >
                      {(acc.adjusted_edge * 100).toFixed(2)}% edge
                    </Badge>
                  </div>
                  {expandedAcc === i
                    ? <ChevronUp className="w-4 h-4 text-muted-foreground" />
                    : <ChevronDown className="w-4 h-4 text-muted-foreground" />
                  }
                </div>

                {expandedAcc === i && (
                  <div className="border-t border-border/30 p-4 space-y-4">
                    {/* Legs */}
                    <div className="space-y-1.5">
                      {acc.legs.map((leg, j) => (
                        <div key={j} className="flex items-center gap-2 text-xs font-mono bg-background/40 rounded px-3 py-2">
                          <span className="text-muted-foreground w-4">{j + 1}.</span>
                          <span className="flex-1 truncate font-medium">{leg.home_team} vs {leg.away_team}</span>
                          <Badge variant="outline" className="text-[10px] flex-shrink-0">
                            {SIDE_LABELS[leg.best_side]}
                          </Badge>
                          <span className="text-muted-foreground flex-shrink-0">@ {leg.best_odds.toFixed(2)}</span>
                          <span className={`flex-shrink-0 ${confidenceColor(leg.confidence)}`}>
                            {(leg.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                      {[
                        { label: "Combined Prob", val: `${(acc.combined_prob * 100).toFixed(2)}%` },
                        { label: "Fair Odds", val: acc.fair_odds.toFixed(2) },
                        { label: "Avg Confidence", val: `${(acc.avg_confidence * 100).toFixed(0)}%` },
                        { label: "Kelly Stake %", val: `${(acc.kelly_stake * 100).toFixed(1)}%`, highlight: true },
                      ].map((stat) => (
                        <div key={stat.label} className="bg-background/50 rounded p-2">
                          <div className="text-muted-foreground uppercase mb-0.5">{stat.label}</div>
                          <div className={`font-bold ${stat.highlight ? "text-primary" : ""}`}>{stat.val}</div>
                        </div>
                      ))}
                    </div>

                    {acc.correlation_penalty > 0 && (
                      <p className="text-xs font-mono text-yellow-400 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        Correlation penalty: -{(acc.correlation_penalty * 100).toFixed(1)}% applied
                      </p>
                    )}

                    {/* Bet placement */}
                    {receipts[i] ? (
                      <div className="flex items-start gap-3 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                        <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                        <div className="font-mono text-xs text-green-300 space-y-0.5">
                          <div className="font-medium">Bet placed!</div>
                          <div>Stake: {receipts[i].currency} {receipts[i].stake}</div>
                          <div>Potential payout: {receipts[i].currency} {receipts[i].potential_payout.toFixed(2)}</div>
                          <div className="text-[10px] text-green-400/70">TX: {receipts[i].transaction_id}</div>
                        </div>
                        <button onClick={() => setReceipts(r => { const n = {...r}; delete n[i]; return n; })} className="ml-auto text-muted-foreground hover:text-foreground">
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <div className="relative flex-1 max-w-[120px]">
                          <Input
                            type="number"
                            min="0.01"
                            step="0.01"
                            placeholder="Stake"
                            value={stakes[i] ?? ""}
                            onChange={(e) => setStakes((s) => ({ ...s, [i]: e.target.value }))}
                            className="font-mono text-sm pl-8"
                          />
                          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground font-mono">
                            {stakeCurrency === "NGN" ? "₦" : stakeCurrency === "VITCoin" ? "V" : "$"}
                          </span>
                        </div>
                        {stakes[i] && Number(stakes[i]) > 0 && (
                          <span className="text-xs font-mono text-muted-foreground">
                            → {stakeCurrency} {(Number(stakes[i]) * acc.combined_odds).toFixed(2)} payout
                          </span>
                        )}
                        <Button
                          size="sm"
                          className="font-mono text-xs gap-1.5"
                          onClick={() => handlePlaceBet(acc, i)}
                          disabled={placeBetMutation.isPending || !stakes[i]}
                        >
                          <Wallet className="w-3.5 h-3.5" />
                          Place Bet
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="font-mono text-xs gap-1.5"
                          onClick={() => { setSendingTg(i); sendTgMutation.mutate({ acc, idx: i }); }}
                          disabled={sendTgMutation.isPending && sendingTg === i}
                        >
                          <Send className="w-3.5 h-3.5" />
                          Telegram
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
