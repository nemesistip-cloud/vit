import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Coins, Clock, CheckCircle, Trophy, Gift, TrendingUp, Zap, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface Offer {
  id: string;
  title: string;
  description: string;
  category: string;
  reward_vitcoin: number;
  difficulty: string;
  estimated_minutes: number;
  status: string;
}

interface EarnHistoryItem {
  id: number;
  provider: string;
  reward_type: string;
  status: string;
  amount: number;
  currency: string;
  created_at: string;
}

interface RewardsSummary {
  total_earned_vitcoin: number;
  completed_offers: number;
  available_offers: number;
}

const _CATEGORY_ICONS: Record<string, React.ReactNode> = {
  survey: <Gift className="w-4 h-4" />,
  quiz: <Trophy className="w-4 h-4" />,
  onboarding: <Zap className="w-4 h-4" />,
  referral: <TrendingUp className="w-4 h-4" />,
  activity: <Zap className="w-4 h-4" />,
  streak: <Trophy className="w-4 h-4" />,
  education: <Gift className="w-4 h-4" />,
};

const _DIFFICULTY_COLOUR: Record<string, string> = {
  easy: "text-green-400 border-green-400/30",
  medium: "text-yellow-400 border-yellow-400/30",
  hard: "text-red-400 border-red-400/30",
};


const EXTERNAL_PROVIDERS = [
  { id:"ayet",    name:"Ayet Studios",  icon:"🎮", color:"#f59e0b", desc:"Complete offers & surveys for VITCoin",  rate:"Up to 50 VIT/offer" },
  { id:"tapjoy",  name:"Tapjoy",        icon:"📱", color:"#10b981", desc:"Install apps and complete challenges",   rate:"Up to 30 VIT/install" },
  { id:"revu",    name:"RevU",          icon:"📊", color:"#6366f1", desc:"Market research & consumer surveys",    rate:"5–20 VIT/survey" },
  { id:"bitlabs", name:"BitLabs",       icon:"💡", color:"#ec4899", desc:"Premium targeted surveys",              rate:"10–40 VIT/survey" },
  { id:"cpx",     name:"CPX Research",  icon:"🔬", color:"#06b6d4", desc:"Academic & consumer research panels",  rate:"5–25 VIT/survey" },
];

function OfferCard({
  offer,
  onClaim,
  isClaiming,
  isCompleted,
}: {
  offer: Offer;
  onClaim: (id: string) => void;
  isClaiming: boolean;
  isCompleted: boolean;
}) {
  const icon = _CATEGORY_ICONS[offer.category] ?? <Gift className="w-4 h-4" />;
  const diffColour = _DIFFICULTY_COLOUR[offer.difficulty] ?? "text-muted-foreground";

  return (
    <Card
      className={`rounded-2xl border-border/50 hover:border-primary/50 transition-all hover:shadow-xl bg-card/60 backdrop-blur-md ${
        isCompleted ? "opacity-60" : ""
      }`}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-primary">{icon}</span>
            <CardTitle className="text-sm font-mono">{offer.title}</CardTitle>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <Coins className="w-3.5 h-3.5 text-yellow-400" />
            <span className="text-yellow-400 font-mono text-sm font-semibold">
              +{offer.reward_vitcoin.toFixed(0)} VIT
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground font-mono">{offer.description}</p>
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className={`text-xs font-mono ${diffColour}`}>
            {offer.difficulty}
          </Badge>
          <Badge variant="outline" className="text-xs font-mono text-muted-foreground">
            <Clock className="w-3 h-3 mr-1" />
            {offer.estimated_minutes > 0 ? `${offer.estimated_minutes} min` : "Ongoing"}
          </Badge>
          <Badge variant="outline" className="text-xs font-mono capitalize text-muted-foreground">
            {offer.category}
          </Badge>
        </div>
        <div className="pt-1">
          {isCompleted ? (
            <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-400">
              <CheckCircle className="w-3.5 h-3.5" />
              Completed
            </div>
          ) : (
            <Button
              size="sm"
              className="h-7 text-xs font-mono w-full"
              onClick={() => onClaim(offer.id)}
              disabled={isClaiming}
            >
              {isClaiming ? (
                <>
                  <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                  Claiming…
                </>
              ) : (
                <>
                  <Zap className="w-3 h-3 mr-1.5" />
                  Claim {offer.reward_vitcoin.toFixed(0)} VIT
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}


function ProviderCard({ provider }: { provider: typeof EXTERNAL_PROVIDERS[0] }) {
  return (
    <Card className="border-border/50 hover:border-primary/40 transition-all hover:shadow-lg group overflow-hidden bg-card/40 backdrop-blur-sm">
      <CardContent className="p-4 flex items-center gap-4">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shadow-inner shrink-0"
          style={{ backgroundColor: `${provider.color}20`, border: `1px solid ${provider.color}40` }}
        >
          {provider.icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-mono font-bold text-sm text-foreground group-hover:text-primary transition-colors">
            {provider.name}
          </h3>
          <p className="text-[10px] text-muted-foreground font-mono truncate">{provider.desc}</p>
          <div className="flex items-center gap-1.5 mt-1">
            <Coins className="w-3 h-3 text-yellow-400" />
            <span className="text-[10px] font-mono text-yellow-500 font-bold">{provider.rate}</span>
          </div>
        </div>
        <Button size="sm" variant="outline" className="h-8 font-mono text-[10px] uppercase border-primary/20 hover:bg-primary/10">
          Open
        </Button>
      </CardContent>
    </Card>
  );
}

function HistoryRow({ item }: { item: EarnHistoryItem }) {
  const date = new Date(item.created_at);
  const statusColour =
    item.status === "confirmed" ? "text-green-400 border-green-400/30" :
    item.status === "pending" ? "text-yellow-400 border-yellow-400/30" :
    "text-red-400 border-red-400/30";

  return (
    <div className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
      <div className="flex items-center gap-3">
        <CheckCircle className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        <div>
          <p className="text-xs font-mono capitalize">{item.reward_type.replace("_", " ")} — {item.provider}</p>
          <p className="text-[10px] text-muted-foreground font-mono">{date.toLocaleDateString()}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-yellow-400 font-mono text-xs">+{item.amount.toFixed(2)} {item.currency}</span>
        <Badge variant="outline" className={`text-[10px] font-mono ${statusColour}`}>
          {item.status}
        </Badge>
      </div>
    </div>
  );
}

export default function OfferwallPage() {
  const qc = useQueryClient();
  const [claimingId, setClaimingId] = useState<string | null>(null);
  const [completedIds, setCompletedIds] = useState<Set<string>>(new Set());

  const { data: summary, isLoading: summaryLoading } = useQuery<RewardsSummary>({
    queryKey: ["rewards-summary"],
    queryFn: () => apiGet("/api/rewards/summary"),
  });

  const { data: offers, isLoading: offersLoading } = useQuery<Offer[]>({
    queryKey: ["rewards-offers"],
    queryFn: () => apiGet("/api/rewards/offers"),
  });

  const { data: history, isLoading: historyLoading } = useQuery<EarnHistoryItem[]>({
    queryKey: ["rewards-history"],
    queryFn: () => apiGet("/api/rewards/history"),
  });

  const claimMutation = useMutation({
    mutationFn: (offerId: string) =>
      apiPost<{ offer_id: string; vitcoin_earned: number; message: string }>(
        `/api/rewards/complete/${offerId}`
      ),
    onSuccess: (data) => {
      toast.success(data.message ?? `Earned ${data.vitcoin_earned} VITCoin!`, {
        icon: <Coins className="w-4 h-4 text-yellow-400" />,
      });
      setCompletedIds((prev) => new Set([...prev, data.offer_id]));
      qc.invalidateQueries({ queryKey: ["rewards-summary"] });
      qc.invalidateQueries({ queryKey: ["rewards-history"] });
      setClaimingId(null);
    },
    onError: (err: any) => {
      const msg = err?.message ?? "Failed to claim offer";
      if (msg.includes("already completed")) {
        toast.info("You've already claimed this offer.");
        setCompletedIds((prev) => new Set([...prev, claimingId ?? ""]));
      } else {
        toast.error(msg);
      }
      setClaimingId(null);
    },
  });

  const handleClaim = (offerId: string) => {
    setClaimingId(offerId);
    claimMutation.mutate(offerId);
  };

  return (
    <div className="space-y-6 p-4 max-w-4xl mx-auto">
      <div>
        <h1 className="text-xl font-mono font-semibold">Earn VITCoin</h1>
        <p className="text-sm text-muted-foreground font-mono mt-1">
          Complete tasks and offers to earn VITCoin rewards.
        </p>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-3">
        {summaryLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))
        ) : (
          <>
            <Card className="border-border/50">
              <CardContent className="pt-4 pb-3">
                <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-1">Total Earned</p>
                <div className="flex items-center gap-1.5">
                  <Coins className="w-4 h-4 text-yellow-400" />
                  <span className="text-lg font-mono font-bold text-yellow-400">
                    {summary?.total_earned_vitcoin.toFixed(2) ?? "0.00"}
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground font-mono">VITCoin</p>
              </CardContent>
            </Card>
            <Card className="border-border/50">
              <CardContent className="pt-4 pb-3">
                <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-1">Completed</p>
                <span className="text-lg font-mono font-bold">{summary?.completed_offers ?? 0}</span>
                <p className="text-[10px] text-muted-foreground font-mono">offers</p>
              </CardContent>
            </Card>
            <Card className="border-border/50">
              <CardContent className="pt-4 pb-3">
                <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-1">Available</p>
                <span className="text-lg font-mono font-bold">{summary?.available_offers ?? 0}</span>
                <p className="text-[10px] text-muted-foreground font-mono">offers</p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Offer catalog */}

      {/* External Offerwalls */}
      <div>
        <h2 className="text-sm font-mono font-semibold mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-primary" />
          Partner Offer Walls
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {EXTERNAL_PROVIDERS.map((p) => (
            <ProviderCard key={p.id} provider={p} />
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-sm font-mono font-semibold mb-3 flex items-center gap-2">
          <Gift className="w-4 h-4 text-primary" />
          Available Offers
        </h2>
        {offersLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-40 rounded-lg" />
            ))}
          </div>
        ) : offers && offers.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {offers.map((offer) => (
              <OfferCard
                key={offer.id}
                offer={offer}
                onClaim={handleClaim}
                isClaiming={claimingId === offer.id}
                isCompleted={completedIds.has(offer.id)}
              />
            ))}
          </div>
        ) : (
          <Card className="border-border/50">
            <CardContent className="py-8 text-center">
              <p className="text-muted-foreground font-mono text-sm">No offers available right now. Check back soon.</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Earn history */}
      <div>
        <h2 className="text-sm font-mono font-semibold mb-3 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-primary" />
          Earn History
        </h2>
        <Card className="border-border/50">
          <CardContent className="pt-4">
            {historyLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 rounded" />
                ))}
              </div>
            ) : history && history.length > 0 ? (
              <div>
                {history.map((item) => (
                  <HistoryRow key={item.id} item={item} />
                ))}
              </div>
            ) : (
              <p className="text-center text-muted-foreground font-mono text-sm py-6">
                No completed offers yet. Start earning above!
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
