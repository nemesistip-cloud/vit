import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import {
  Users, Gift, Copy, Check, Share2, Trophy, Coins,
  Globe, Zap, ArrowUpRight, ChevronRight, UserPlus
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import MetricCard from "@/components/cards/MetricCard";
import { cn } from "@/lib/utils";

export default function ReferralPage() {
  const [copied, setCopied] = useState(false);
  const [applyCode, setApplyCode] = useState("");
  const qc = useQueryClient();

  const { data: myCode, isError: codeError } = useQuery<any>({
    queryKey: ["referral-code"],
    queryFn: () => apiGet("/api/referral/my-code"),
    retry: false,
  });

  const { data: stats } = useQuery<any>({
    queryKey: ["referral-stats"],
    queryFn: () => apiGet("/api/referral/stats"),
    retry: false,
  });

  const applyMutation = useMutation({
    mutationFn: (code: string) => apiPost("/api/referral/apply", { code }),
    onSuccess: () => {
      toast.success("Referral node established.");
      qc.invalidateQueries({ queryKey: ["referral-code"] });
      qc.invalidateQueries({ queryKey: ["referral-stats"] });
      setApplyCode("");
    },
  });

  const copyCode = () => {
    if (!myCode?.code) return;
    navigator.clipboard.writeText(myCode.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Node ID copied.");
  };

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Growth Protocol</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Network Expansion & Affiliate Ledger</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Referrals" value={myCode?.total_referrals || 0} icon={<Users size={14} />} />
        <MetricCard label="Yield Earned" value={`${myCode?.total_bonus_earned_vit || 0} VIT`} icon={<Coins size={14} />} />
        <MetricCard label="Node Bonus" value={`${myCode?.bonus_per_referral_vit || 50} VIT`} icon={<Gift size={14} />} />
        <MetricCard label="Rank" value="TOP 2%" icon={<Trophy size={14} />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           <Card className="border-primary/20 bg-primary/[0.02]">
              <CardContent className="p-8 space-y-6">
                 <div className="space-y-2">
                    <p className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-primary">Your Unique Node ID</p>
                    <div className="flex gap-3">
                       <div className="flex-1 bg-white/5 border border-white/5 rounded p-4 text-center">
                          <span className="font-mono text-3xl font-bold tracking-[0.3em] text-foreground">{myCode?.code || '------'}</span>
                       </div>
                       <Button variant="outline" size="icon" className="w-14 h-14 border-white/5" onClick={copyCode}>
                          {copied ? <Check size={20} className="text-vit-positive" /> : <Copy size={20} />}
                       </Button>
                    </div>
                 </div>
                 <p className="text-xs text-muted-foreground leading-relaxed">
                    Expand the VIT Network. For every analyst provisioned through your Node ID, both participants receive <span className="text-foreground">{myCode?.bonus_per_referral_vit || 50} VIT</span>.
                 </p>
              </CardContent>
           </Card>

           <Card className="border-white/5 bg-white/[0.01]">
              <CardHeader>
                 <CardTitle className="text-xs uppercase tracking-widest">Provision Referred Node</CardTitle>
              </CardHeader>
              <CardContent className="flex gap-3">
                 <Input
                   placeholder="ENTER EXTERNAL NODE ID..."
                   className="bg-white/5 border-white/5 font-mono uppercase tracking-widest"
                   value={applyCode}
                   onChange={(e) => setApplyCode(e.target.value.toUpperCase())}
                 />
                 <Button
                   className="h-10 px-8 uppercase tracking-widest text-[10px] font-bold"
                   onClick={() => applyMutation.mutate(applyCode)}
                 >
                    Establish
                 </Button>
              </CardContent>
           </Card>
        </div>

        <div className="space-y-6">
           <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4 text-primary">
                 <UserPlus size={16} />
                 <h4 className="font-display text-[10px] font-bold uppercase tracking-[0.2em]">Recent Provisions</h4>
              </div>
              <div className="space-y-4">
                 {(stats?.referrals || []).slice(0, 5).map((ref: any, i: number) => (
                    <div key={i} className="flex justify-between items-center">
                       <span className="text-sm font-bold text-foreground/80">{ref.referee_username}</span>
                       <Badge variant="outline" className="text-[8px] bg-white/5 border-white/10 uppercase">
                          {ref.bonus_paid ? 'SUCCESS' : 'PENDING'}
                       </Badge>
                    </div>
                 ))}
                 {(!stats?.referrals || stats.referrals.length === 0) && (
                    <p className="text-[10px] text-muted-foreground/40 uppercase text-center py-4">No active provisions</p>
                 )}
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
