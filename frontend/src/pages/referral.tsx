import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Users, Gift, Copy, Check, Share2, Trophy, Coins } from "lucide-react";

interface MyCode {
  code: string;
  total_referrals: number;
  total_bonus_earned_vit: number;
  bonus_per_referral_vit: number;
  share_url: string;
}

interface ReferralStats {
  referrals: Array<{
    referee_username: string;
    bonus_paid: boolean;
    bonus_amount: number;
    joined_at: string;
  }>;
  total: number;
  pending_bonuses: number;
}

interface LeaderboardEntry {
  rank: number;
  username: string;
  referrals: number;
  earned_vit: number;
}

export default function ReferralPage() {
  const [copied, setCopied] = useState(false);
  const [applyCode, setApplyCode] = useState("");
  const qc = useQueryClient();

  const { data: myCode, isLoading: loadingCode, isError: codeError, error: referralError } = useQuery<MyCode>({
    queryKey: ["referral-code"],
    queryFn: () => apiGet("/api/referral/my-code"),
    retry: false,
  });

  const { data: stats, isLoading: loadingStats } = useQuery<ReferralStats>({
    queryKey: ["referral-stats"],
    queryFn: () => apiGet("/api/referral/stats"),
    retry: false,
  });

  const { data: leaderboard } = useQuery<{ leaderboard: LeaderboardEntry[] }>({
    queryKey: ["referral-leaderboard"],
    queryFn: () => apiGet("/api/referral/leaderboard"),
    staleTime: 120_000,
    retry: false,
  });

  const applyMutation = useMutation({
    mutationFn: (code: string) => apiPost("/api/referral/apply", { code }),
    onSuccess: (data: any) => {
      toast.success(data.message ?? "Referral code applied!");
      qc.invalidateQueries({ queryKey: ["referral-code"] });
      qc.invalidateQueries({ queryKey: ["referral-stats"] });
      setApplyCode("");
    },
    onError: (err: any) => toast.error(err.message ?? "Failed to apply code"),
  });

  const copyCode = () => {
    if (!myCode?.code) return;
    navigator.clipboard.writeText(myCode.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Code copied!");
  };

  const shareLink = () => {
    if (!myCode) return;
    const url = `${window.location.origin}${myCode.share_url}`;
    navigator.clipboard.writeText(url);
    toast.success("Share link copied!");
  };

  if (codeError) {
    return (
      <div className="p-6 max-w-3xl mx-auto space-y-6">
        <Card className="border-border/50">
          <CardContent className="py-10 text-center space-y-3">
            <Gift className="w-10 h-10 text-muted-foreground mx-auto" />
            <h1 className="text-xl font-bold font-mono tracking-tight">Referral Program Disabled</h1>
            <p className="text-sm text-muted-foreground font-mono">
              {(referralError as Error)?.message ?? "Referrals are currently unavailable."}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center justify-center">
          <Users className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight">Referral Program</h1>
          <p className="text-sm text-muted-foreground font-mono">
            Invite friends — earn VITCoin bonuses for every successful referral
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Referrals", value: myCode?.total_referrals ?? 0, icon: Users, color: "text-blue-400" },
          { label: "VIT Earned", value: `${myCode?.total_bonus_earned_vit ?? 0}`, icon: Coins, color: "text-yellow-400" },
          { label: "Per Referral", value: `${myCode?.bonus_per_referral_vit ?? 50} VIT`, icon: Gift, color: "text-green-400" },
        ].map((stat) => (
          <Card key={stat.label} className="border-border/50">
            <CardContent className="pt-4 pb-3">
              <stat.icon className={`w-4 h-4 ${stat.color} mb-2`} />
              <div className="text-xl font-bold font-mono">{stat.value}</div>
              <div className="text-xs text-muted-foreground font-mono">{stat.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <Gift className="w-4 h-4 text-primary" />
            Your Referral Code
          </CardTitle>
          <CardDescription className="font-mono text-xs">
            Share this code with friends. Both of you get {myCode?.bonus_per_referral_vit ?? 50} VITCoin when they sign up.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loadingCode ? (
            <div className="h-12 rounded-md bg-muted/30 animate-pulse" />
          ) : (
            <div className="flex gap-2">
              <div className="flex-1 font-mono text-2xl font-bold tracking-[0.3em] bg-muted/30 rounded-lg px-4 py-3 border border-border/50 text-center text-primary">
                {myCode?.code ?? "------"}
              </div>
              <Button variant="outline" size="icon" onClick={copyCode} className="h-auto px-4">
                {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
              </Button>
              <Button variant="outline" size="icon" onClick={shareLink} className="h-auto px-4">
                <Share2 className="w-4 h-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono">Apply a Referral Code</CardTitle>
          <CardDescription className="font-mono text-xs">
            Were you referred by someone? Apply their code to give them a bonus.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Enter referral code..."
              value={applyCode}
              onChange={(e) => setApplyCode(e.target.value.toUpperCase())}
              className="font-mono tracking-widest uppercase"
              maxLength={9}
            />
            <Button
              onClick={() => applyCode && applyMutation.mutate(applyCode)}
              disabled={!applyCode || applyMutation.isPending}
              className="font-mono"
            >
              Apply
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Users className="w-4 h-4 text-muted-foreground" />
              My Referrals
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingStats ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => <div key={i} className="h-8 bg-muted/30 rounded animate-pulse" />)}
              </div>
            ) : (stats?.referrals ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground font-mono py-4 text-center">
                No referrals yet. Share your code!
              </p>
            ) : (
              <div className="space-y-2">
                {(stats?.referrals ?? []).map((ref, i) => (
                  <div key={i} className="flex items-center justify-between py-1.5">
                    <span className="font-mono text-sm">{ref.referee_username}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={ref.bonus_paid ? "default" : "outline"} className="text-xs font-mono">
                        {ref.bonus_paid ? `+${ref.bonus_amount} VIT` : "pending"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Trophy className="w-4 h-4 text-yellow-400" />
              Top Referrers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(leaderboard?.leaderboard ?? []).slice(0, 5).map((entry) => (
                <div key={entry.rank} className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground font-mono w-5">#{entry.rank}</span>
                    <span className="font-mono text-sm">{entry.username}</span>
                  </div>
                  <span className="font-mono text-xs text-primary">{entry.referrals} refs</span>
                </div>
              ))}
              {(leaderboard?.leaderboard ?? []).length === 0 && (
                <p className="text-sm text-muted-foreground font-mono py-4 text-center">No referrers yet.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
