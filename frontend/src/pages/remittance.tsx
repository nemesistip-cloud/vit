import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Send, Download, RefreshCw, ArrowUpRight, ArrowDownLeft, Globe, Coins, Clock } from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";
import MetricCard from "@/components/cards/MetricCard";

const SYM: Record<string, string> = { NGN: "₦", USD: "$", USDT: "$", VITCoin: "◆", GBP: "£", EUR: "€" };

export default function RemittancePage() {
  const [sendAmount, setSendAmount] = useState("");
  const [sendCurrency, setSendCurrency] = useState("NGN");

  const { data: wallet, isLoading: walletLoading } = useQuery<any>({
    queryKey: ["/api/wallet"],
    queryFn: () => apiGet("/api/wallet"),
  });

  const { data: transactions, isLoading: txLoading } = useQuery<any>({
    queryKey: ["/api/wallet/transactions?limit=10"],
    queryFn: () => apiGet("/api/wallet/transactions?limit=10"),
  });

  const balances = wallet?.balances ?? {};
  const vitBalance = balances.VITCoin ?? wallet?.vitcoin_balance ?? 0;
  const ngnBalance = balances.NGN ?? 0;
  const usdBalance = balances.USD ?? balances.USDT ?? 0;

  const txList: any[] = transactions?.transactions ?? [];
  const remittanceTx = txList.filter((t: any) =>
    ["deposit", "withdrawal", "transfer", "remittance"].includes(t.type ?? t.transaction_type)
  );

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="VITCoin Balance"
          value={walletLoading ? "..." : vitBalance.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          icon={<Coins size={16} className="text-vit-green" />}
        />
        <MetricCard
          label="NGN Balance"
          value={walletLoading ? "..." : `₦${ngnBalance.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
          icon={<Globe size={16} className="text-secondary" />}
        />
        <MetricCard
          label="USD / USDT"
          value={walletLoading ? "..." : `$${usdBalance.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
          icon={<Globe size={16} className="text-vit-green" />}
        />
        <MetricCard
          label="Total Transfers"
          value={String(remittanceTx.length)}
          icon={<RefreshCw size={16} className="text-vit-purple" />}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-vit-surface border-vit-border">
          <CardHeader className="pb-3 border-b border-vit-border bg-vit-surface-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 flex items-center gap-2">
              <Send size={12} className="text-vit-green" /> Send Value
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-3">
            {walletLoading ? (
              <>
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-9 w-full" />
              </>
            ) : (
              <>
                <div>
                  <p className="text-[9px] font-mono text-vit-text-3 uppercase mb-1">Available</p>
                  <p className="text-2xl font-display font-black text-vit-text-1">
                    {SYM[sendCurrency] || ""}{(balances[sendCurrency] ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </p>
                  <p className="text-[9px] font-mono text-vit-text-3 mt-0.5">
                    ≈ {vitBalance.toLocaleString(undefined, { maximumFractionDigits: 0 })} VIT
                  </p>
                </div>
                <Select value={sendCurrency} onValueChange={setSendCurrency}>
                  <SelectTrigger className="h-9 bg-vit-surface-2 border-vit-border text-xs font-mono">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys({ VITCoin: 1, NGN: 1, USD: 1, USDT: 1 }).map(c => (
                      <SelectItem key={c} value={c} className="font-mono text-xs">{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  type="number"
                  placeholder="Amount to send"
                  value={sendAmount}
                  onChange={e => setSendAmount(e.target.value)}
                  className="h-9 bg-vit-surface-2 border-vit-border text-xs font-mono"
                />
                <div className="flex gap-2">
                  <Button className="flex-1 h-9 bg-vit-green text-vit-text-inverse font-black text-xs gap-1.5">
                    <Send size={12} /> SEND
                  </Button>
                  <Button variant="outline" className="flex-1 h-9 font-mono text-xs gap-1.5 border-vit-border">
                    <Download size={12} /> RECEIVE
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-2 bg-vit-surface border-vit-border">
          <CardHeader className="pb-3 border-b border-vit-border bg-vit-surface-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3 flex items-center gap-2">
              <RefreshCw size={12} className="text-vit-green" /> Transfer History
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {txLoading ? (
              <div className="divide-y divide-vit-border">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Skeleton className="h-8 w-8 rounded-full" />
                      <div className="space-y-1">
                        <Skeleton className="h-3 w-32" />
                        <Skeleton className="h-2.5 w-20" />
                      </div>
                    </div>
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))}
              </div>
            ) : remittanceTx.length === 0 ? (
              <div className="py-12 text-center">
                <Clock size={24} className="mx-auto text-vit-text-3 opacity-40 mb-2" />
                <p className="text-sm text-vit-text-3 font-mono">No transfer history yet</p>
                <p className="text-[10px] text-vit-text-3 mt-1">Deposits and withdrawals will appear here</p>
              </div>
            ) : (
              <div className="divide-y divide-vit-border">
                {remittanceTx.map((tx: any) => {
                  const isCredit = tx.direction === "credit" || ["deposit", "remittance"].includes(tx.type);
                  const sym = SYM[tx.currency] || "";
                  const date = tx.created_at || tx.processed_at;
                  return (
                    <div key={tx.id} className="p-4 flex items-center justify-between hover:bg-vit-surface-2 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${isCredit ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"}`}>
                          {isCredit ? <ArrowDownLeft size={14} /> : <ArrowUpRight size={14} />}
                        </div>
                        <div>
                          <p className="text-xs font-bold text-vit-text-1">{tx.type?.replace(/_/g, " ").toUpperCase() ?? "TRANSFER"}</p>
                          <p className="text-[9px] font-mono text-vit-text-3">
                            {date ? format(new Date(date), "MMM d, yyyy · HH:mm") : "Processing"}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-mono font-bold ${isCredit ? "text-emerald-400" : "text-rose-400"}`}>
                          {isCredit ? "+" : "-"}{sym}{Number(tx.amount ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                        </p>
                        <Badge className={`text-[8px] mt-0.5 ${tx.status === "confirmed" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-vit-surface-3 text-vit-text-3 border-vit-border"}`}>
                          {tx.status?.toUpperCase() ?? "PENDING"}
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
