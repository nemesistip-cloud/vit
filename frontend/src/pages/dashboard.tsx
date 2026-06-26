import { usePublicConfig } from "@/lib/usePublicConfig";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useGetModelConfidence } from "@/api-client";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Trophy, TrendingUp, Activity, Coins, ArrowUpRight,
  Brain, ChevronRight, Zap, BarChart2, Flame, Sparkles,
  CheckCircle2, XCircle, Vote, Scale, ShoppingBag, Store,
  Radio, ArrowDownRight
} from "lucide-react";
import { format } from "date-fns";
import { Link } from "wouter";
import { LevelCard, AchievementBadges } from "@/components/gamification";
import { SignalMarketplace } from "@/components/super-app/SignalMarketplace";

function ActivityIcon({ type, outcome, betSide }: { type: string; outcome?: string; betSide?: string }) {
  if (type === "prediction_settled") {
    return outcome === betSide ? (
      <div className="w-8 h-8 rounded-lg bg-[#00E676]/10 flex items-center justify-center text-[#00E676] border border-[#00E676]/20 flex-shrink-0">
        <CheckCircle2 className="w-4 h-4" />
      </div>
    ) : (
      <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center text-red-400 border border-red-500/20 flex-shrink-0">
        <XCircle className="w-4 h-4" />
      </div>
    );
  }
  return (
    <div className="w-8 h-8 rounded-lg bg-[#00E676]/10 flex items-center justify-center text-[#00E676] border border-[#00E676]/20 flex-shrink-0">
      <Zap className="w-4 h-4" />
    </div>
  );
}

function StatTile({
  label, value, change, positive, accent, icon: Icon,
}: {
  label: string; value: string | number; change?: string; positive?: boolean;
  accent: "green" | "purple" | "orange" | "blue"; icon: React.ElementType;
}) {
  const colors = {
    green:  { bar: "bg-[#00E676]", text: "text-[#00E676]", bg: "bg-[#00E676]/8", border: "border-[#00E676]/12" },
    purple: { bar: "bg-[#8B5CF6]", text: "text-[#8B5CF6]", bg: "bg-[#8B5CF6]/8", border: "border-[#8B5CF6]/12" },
    orange: { bar: "bg-orange-400", text: "text-orange-400", bg: "bg-orange-400/8", border: "border-orange-400/12" },
    blue:   { bar: "bg-blue-400",  text: "text-blue-400",  bg: "bg-blue-400/8",  border: "border-blue-400/12"  },
  };
  const c = colors[accent];
  return (
    <div className={`relative rounded-xl border ${c.border} ${c.bg} p-3.5 overflow-hidden`}>
      {/* Left accent stripe */}
      <div className={`absolute inset-y-0 left-0 w-[3px] ${c.bar} rounded-l-xl`} />
      <div className="flex items-start justify-between mb-2 pl-1">
        <p className="font-['Outfit'] text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40 leading-none">{label}</p>
        <div className={`rounded-md p-1 ${c.bg}`}>
          <Icon size={11} className={c.text} />
        </div>
      </div>
      <p className={`font-['JetBrains_Mono'] text-xl font-bold leading-none ${c.text} tabular-nums pl-1`}>{value}</p>
      {change && (
        <div className={`flex items-center gap-0.5 mt-1.5 pl-1 ${positive ? "text-[#00E676]" : "text-red-400"}`}>
          {positive ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
          <span className="font-['JetBrains_Mono'] text-[10px]">{change}</span>
        </div>
      )}
    </div>
  );
}

function NavCard({
  href, icon: Icon, title, desc,
  accent = "green", badge,
}: {
  href: string; icon: React.ElementType; title: string; desc: string;
  accent?: "green" | "purple" | "blue" | "violet" | "teal" | "amber" | "rose";
  badge?: string;
}) {
  const colors = {
    green:  { border: "border-[#00E676]/20", bg: "bg-[#00E676]/8",  text: "text-[#00E676]",  hoverBorder: "hover:border-[#00E676]/40" },
    purple: { border: "border-[#8B5CF6]/20", bg: "bg-[#8B5CF6]/8",  text: "text-[#8B5CF6]",  hoverBorder: "hover:border-[#8B5CF6]/40" },
    blue:   { border: "border-blue-400/20",  bg: "bg-blue-400/8",   text: "text-blue-400",   hoverBorder: "hover:border-blue-400/40" },
    violet: { border: "border-violet-400/20",bg: "bg-violet-400/8", text: "text-violet-400", hoverBorder: "hover:border-violet-400/40" },
    teal:   { border: "border-teal-400/20",  bg: "bg-teal-400/8",   text: "text-teal-400",   hoverBorder: "hover:border-teal-400/40" },
    amber:  { border: "border-amber-400/20", bg: "bg-amber-400/8",  text: "text-amber-400",  hoverBorder: "hover:border-amber-400/40" },
    rose:   { border: "border-rose-400/20",  bg: "bg-rose-400/8",   text: "text-rose-400",   hoverBorder: "hover:border-rose-400/40" },
  };
  const c = colors[accent];
  return (
    <Link href={href}>
      <div className={`group rounded-xl border border-white/8 bg-white/3 p-4 transition-all duration-200 cursor-pointer ${c.hoverBorder} hover:bg-white/5`}>
        <div className="flex items-start justify-between mb-3">
          <div className={`w-9 h-9 rounded-lg border ${c.border} ${c.bg} flex items-center justify-center`}>
            <Icon size={16} className={c.text} />
          </div>
          {badge && (
            <span className="rounded-md border border-red-500/30 bg-red-500/10 px-1.5 py-0.5 font-['JetBrains_Mono'] text-[8px] font-bold uppercase tracking-wider text-red-400">
              {badge}
            </span>
          )}
        </div>
        <h3 className={`font-['Barlow_Condensed'] text-base font-bold uppercase tracking-wide ${c.text} mb-1 leading-tight`}>{title}</h3>
        <p className="font-['Outfit'] text-[11px] text-white/40 leading-relaxed">{desc}</p>
        <div className={`mt-3 flex items-center gap-1 font-['JetBrains_Mono'] text-[10px] ${c.text} opacity-0 group-hover:opacity-100 transition-opacity`}>
          Enter <ChevronRight size={11} />
        </div>
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const { data: config } = usePublicConfig();
  const { user } = useAuth();
  const { data: modelConfidence } = useGetModelConfidence();

  const { data: activityData, isLoading: isActivityLoading } = useQuery<any[]>({
    queryKey: ["/api/history?limit=6"],
    queryFn: () => apiGet("/api/history?limit=6"),
  });

  const ensembleAccuracy = modelConfidence?.ensemble_accuracy != null
    ? modelConfidence.ensemble_accuracy.toFixed(1) + "%"
    : "84.2%";

  const vitBalance = (user as any)?.vitcoin_balance?.toLocaleString() || "0";
  const streak     = (user as any)?.current_streak ?? 0;
  const meritTier  = ((user as any)?.tier?.toUpperCase() || "VIEWER");
  const meritXp    = ((user as any)?.merit_score ?? 0).toLocaleString();

  return (
    <div className="p-4 space-y-5 pb-8">

      {/* ── Greeting header ── */}
      <div className="pt-1">
        <div className="flex items-center gap-1.5 mb-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00E676] animate-pulse" />
          <span className="font-['JetBrains_Mono'] text-[9px] text-[#00E676]/70 uppercase tracking-[0.25em]">vit_network — online</span>
        </div>
        <h1 className="font-['Barlow_Condensed'] text-3xl font-bold uppercase tracking-[0.05em] text-white leading-none">
          {user?.username || "Analyst"}
          <span className="text-[#00E676] ml-1">↗</span>
        </h1>
        <p className="font-['Outfit'] text-xs text-white/35 mt-1">Intelligence platform · {new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "short" })}</p>
      </div>

      {/* ── Top Stats ── */}
      <div className="grid grid-cols-2 gap-2.5">
        <StatTile label="VITCoin"    value={vitBalance}        change="+120"  positive icon={Coins}  accent="green" />
        <StatTile label="AI Accuracy" value={ensembleAccuracy}  change="+1.2%" positive icon={Brain}  accent="purple" />
        <StatTile label="Streak"     value={streak}             icon={Flame}  accent="orange" />
        <StatTile label="Merit Tier" value={meritTier} change={meritXp + " XP"} positive={false} icon={Trophy} accent="blue" />
      </div>

      {/* ── Hub navigation tabs ── */}
      <Tabs defaultValue="sports" className="w-full">
        <div className="flex items-center justify-between mb-3">
          <TabsList className="h-8 p-0.5 bg-white/4 border border-white/8 gap-0.5 rounded-lg">
            {["Sports", "Niche", "Signals"].map(tab => (
              <TabsTrigger
                key={tab}
                value={tab.toLowerCase()}
                className="h-7 px-3 rounded-md font-['Barlow_Condensed'] text-[11px] font-bold uppercase tracking-wider text-white/35 data-[state=active]:bg-[#00E676]/15 data-[state=active]:text-[#00E676] data-[state=active]:border data-[state=active]:border-[#00E676]/25"
              >
                {tab}
              </TabsTrigger>
            ))}
          </TabsList>
          <Link href="/matches">
            <Button variant="ghost" size="sm" className="h-7 px-2 font-['JetBrains_Mono'] text-[9px] uppercase tracking-widest text-white/30 hover:text-[#00E676] gap-1">
              All Markets <ChevronRight size={10} />
            </Button>
          </Link>
        </div>

        {/* Sports Tab */}
        <TabsContent value="sports" className="mt-0 space-y-3">
          <div className="grid grid-cols-2 gap-2.5">
            <NavCard href="/matches"     icon={Trophy}   title="Sports Hub"   desc="AI-grade football & basketball analytics." badge="LIVE" accent="green" />
            <NavCard href="/accumulator" icon={Zap}      title="Predictions"  desc="13-model ensemble AI signal generator."              accent="purple" />
            <NavCard href="/analytics"   icon={BarChart2} title="Analytics"   desc="Deep performance & CLV tracking."                    accent="blue" />
            <NavCard href="/odds"        icon={TrendingUp} title="Odds"       desc="Real-time market & line movement."                   accent="violet" />
          </div>

          {/* Live Signals panel */}
          <div className="rounded-xl border border-[#00E676]/15 bg-[#00E676]/4 overflow-hidden">
            <div className="px-4 pt-4 pb-3">
              <div className="flex items-center gap-2 mb-3">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00E676] animate-pulse" />
                <span className="font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wider text-[#00E676]">Live Signals</span>
                <span className="ml-auto rounded-md border border-[#00E676]/25 bg-[#00E676]/10 px-1.5 py-0.5 font-['JetBrains_Mono'] text-[8px] font-bold uppercase tracking-wider text-[#00E676]">Active</span>
              </div>

              <div className="flex items-center gap-3">
                {/* Waveform */}
                <div className="flex items-end gap-[2px] h-9 flex-shrink-0">
                  {[3,7,4,9,5,11,4,8,5,10,6,9,4,7,5].map((h, i) => (
                    <div
                      key={i}
                      className="w-[2px] rounded-full bg-[#00E676]"
                      style={{ height: `${h * 3}px`, opacity: 0.3 + (i % 4) * 0.18 }}
                    />
                  ))}
                </div>

                {/* Stats */}
                <div className="flex-1 grid grid-cols-3 gap-1.5">
                  {[
                    { label: "Signals",  value: activityData?.length ?? 0,   color: "text-white" },
                    { label: "Accuracy", value: ensembleAccuracy,             color: "text-[#00E676]" },
                    { label: "Updated",  value: activityData?.[0]?.created_at ? format(new Date(activityData[0].created_at), "HH:mm") : "Live", color: "text-white" },
                  ].map(s => (
                    <div key={s.label} className="rounded-lg bg-black/20 border border-white/5 p-2 text-center">
                      <p className="font-['Outfit'] text-[8px] text-white/35 uppercase tracking-wider mb-0.5">{s.label}</p>
                      <p className={`font-['JetBrains_Mono'] text-sm font-bold ${s.color}`}>{s.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <Link href="/matches" className="block">
              <button className="w-full flex items-center justify-center gap-2 py-3 bg-[#00E676] font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wider text-black hover:bg-[#00c864] transition-colors">
                <Radio size={13} />
                Open Live Feed
              </button>
            </Link>
          </div>
        </TabsContent>

        {/* Niche Tab */}
        <TabsContent value="niche" className="mt-0 space-y-3">
          <div className="grid grid-cols-2 gap-2.5">
            <NavCard href="/governance"  icon={Scale}       title="Governance"  desc="Policy & legislative analytics."         accent="teal" />
            <NavCard href="/elections"   icon={Vote}        title="Elections"   desc="Sentiment & outcome prediction."         accent="violet" />
            <NavCard href="/marketplace" icon={ShoppingBag} title="Marketplace" desc="Buy and sell prediction signals."        accent="amber" />
            <NavCard href="/community"   icon={Store}       title="Community"   desc="Network with other analysts."            accent="rose" />
          </div>
          <div className="rounded-xl border border-white/6 bg-white/2 py-8 text-center">
            <Brain size={28} className="text-[#8B5CF6]/30 mx-auto mb-2" />
            <p className="font-['Outfit'] text-xs text-white/25">Niche intelligence markets processing community data</p>
          </div>
        </TabsContent>

        {/* Signals Tab */}
        <TabsContent value="signals" className="mt-0">
          <SignalMarketplace />
        </TabsContent>
      </Tabs>

      {/* ── Gamification ── */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <div className="h-px flex-1 bg-white/5" />
          <span className="font-['Barlow_Condensed'] text-[10px] font-semibold uppercase tracking-[0.2em] text-white/20 px-2">Progress</span>
          <div className="h-px flex-1 bg-white/5" />
        </div>
        <LevelCard xp={(user as any)?.merit_score ?? 0} streak={(user as any)?.current_streak ?? 0} />
        <AchievementBadges />
      </div>

      {/* ── Recent Intelligence ── */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-px w-4 bg-[#00E676]/40" />
            <h2 className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-white/35">
              Recent Intelligence
            </h2>
          </div>
          <Link href="/predictions">
            <Button variant="ghost" size="sm" className="h-6 px-2 font-['JetBrains_Mono'] text-[9px] uppercase tracking-widest text-white/25 hover:text-[#00E676] gap-1">
              View all <ChevronRight size={9} />
            </Button>
          </Link>
        </div>

        <div className="rounded-xl border border-white/8 bg-white/2 overflow-hidden divide-y divide-white/5">
          {isActivityLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="p-3.5 flex items-center gap-3">
                <Skeleton className="w-8 h-8 rounded-lg bg-white/5" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-2.5 w-2/3 bg-white/5" />
                  <Skeleton className="h-2 w-1/3 bg-white/5" />
                </div>
              </div>
            ))
          ) : !activityData?.length ? (
            <div className="py-10 text-center">
              <Sparkles size={22} className="text-white/10 mx-auto mb-2" />
              <p className="font-['Outfit'] text-xs text-white/20">No signals recorded yet.</p>
              <p className="font-['JetBrains_Mono'] text-[9px] text-white/12 mt-0.5 uppercase tracking-wider">make your first prediction to begin</p>
            </div>
          ) : (
            activityData.map((item: any) => (
              <div key={item.id} className="p-3 flex items-center gap-3 hover:bg-white/3 transition-colors">
                <ActivityIcon type={item.type || "prediction_settled"} outcome={item.outcome} betSide={item.prediction_side} />
                <div className="flex-1 min-w-0">
                  <p className="font-['Outfit'] text-sm font-medium text-white/75 truncate leading-none">
                    {item.match_name || "Match Settled"}
                  </p>
                  <p className="font-['JetBrains_Mono'] text-[9px] text-white/30 uppercase tracking-wider mt-0.5">
                    {item.type?.replace(/_/g, ' ') || 'Market Update'}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="font-['JetBrains_Mono'] text-xs font-bold text-white/60">{item.odds || '--'}</p>
                  {item.created_at && (
                    <p className="font-['JetBrains_Mono'] text-[9px] text-white/25 mt-0.5">
                      {format(new Date(item.created_at), 'HH:mm')}
                    </p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
