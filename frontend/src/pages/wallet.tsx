import { useState, useEffect, useMemo } from "react";
import {
  useGetWallet, useListTransactions, useInitiateDeposit, useWithdraw, useConvertCurrency, useGetVitcoinPrice,
} from "@/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowUpRight, ArrowDownLeft, RefreshCcw, Landmark, ShieldCheck, AlertTriangle,
  BadgeCheck, Download, TrendingUp, TrendingDown, Coins, ArrowRight, Check,
  Search, Clock, ChevronDown, Wallet, BarChart3, History, Send,
  Zap, Globe, Info, ArrowLeftRight,
} from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { isTWA } from "@/lib/twa";
import { useTelegramStarsInvoice } from "@/api-client";
import { apiGet, apiPost } from "@/lib/apiClient";
import { usePublicConfig } from "@/lib/usePublicConfig";
import MetricCard from "@/components/cards/MetricCard";
import CategoryPills from "@/components/layout/CategoryPills";

const SYM: Record<string, string> = { NGN: "₦", USD: "$", USDT: "$", PI: "π", VITCoin: "◆" };

export default function WalletPage() {
  const queryClient = useQueryClient();
  const { data: wallet, isLoading: loadingWallet } = useGetWallet();
  const { data: transactions, isLoading: loadingTx } = useListTransactions();
  const [activeCategory, setActiveCategory] = useState("all");

  const balances = wallet?.balances || {};
  const txList = transactions?.transactions || [];

  const categories = [
    { id: "all", label: "Overview" },
    { id: "deposit", label: "Deposits" },
    { id: "withdrawal", label: "Withdrawals" },
    { id: "stake", label: "Activity" },
  ];

  const filteredTx = useMemo(() => {
    if (activeCategory === "all") return txList;
    return txList.filter(t => t.type === activeCategory);
  }, [txList, activeCategory]);

  if (loadingWallet) return <div className="p-8">Loading wallet...</div>;

  return (
    <div className="space-y-6 pb-20">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          variant="hero"
          label="Total Balance (USD)"
          value={`$${wallet?.total_balance_usd?.toLocaleString() || "0.00"}`}
          icon={<Wallet size={24} className="text-vit-green" />}
        />
        <div className="md:col-span-2 grid grid-cols-2 gap-4">
          <MetricCard
            label="VITCoin"
            value={balances.VITCoin?.toLocaleString() || "0"}
            subtitle="Native Utility"
            icon={<Coins size={16} className="text-secondary" />}
          />
          <MetricCard
            label="Naira (NGN)"
            value={`₦${balances.NGN?.toLocaleString() || "0"}`}
            subtitle="Local Fiat"
            icon={<Landmark size={16} className="text-vit-green" />}
          />
        </div>
      </div>

      <div className="flex items-center justify-between px-1">
        <CategoryPills
          items={categories}
          activeId={activeCategory}
          onSelect={setActiveCategory}
        />
        <div className="flex gap-2">
           <Button size="sm" className="bg-vit-green text-vit-text-inverse font-bold">DEPOSIT</Button>
           <Button size="sm" variant="outline" className="border-vit-border">SEND</Button>
        </div>
      </div>

      <div className="bg-vit-surface border-y border-vit-border">
        <div className="px-4 py-3 border-b border-vit-border bg-vit-surface-2">
           <h3 className="text-[10px] font-bold uppercase tracking-widest text-vit-text-3">Transaction Ledger</h3>
        </div>
        {loadingTx ? (
          <div className="p-10 text-center text-xs text-vit-text-3">Loading transactions...</div>
        ) : filteredTx.length === 0 ? (
          <div className="p-10 text-center text-xs text-vit-text-3 font-mono">No transaction records found.</div>
        ) : (
          <div className="divide-y divide-vit-border">
            {filteredTx.map((tx) => (
              <div key={tx.id} className="p-4 flex items-center justify-between hover:bg-vit-surface-2 transition-colors">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${
                    tx.type === 'deposit' ? 'bg-vit-green-glow border-vit-green/20 text-vit-green' : 'bg-vit-surface-3 border-vit-border text-vit-text-2'
                  }`}>
                    {tx.type === 'deposit' ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-vit-text-1 capitalize">{tx.type.replace('_', ' ')}</p>
                    <p className="text-[10px] text-vit-text-3">{formatDistanceToNow(new Date(tx.created_at), { addSuffix: true })}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-mono font-bold ${tx.amount > 0 ? 'text-vit-green' : 'text-vit-text-1'}`}>
                    {tx.amount > 0 ? '+' : ''}{tx.amount.toLocaleString()} {tx.currency}
                  </p>
                  <Badge className="text-[8px] bg-vit-surface-3 text-vit-text-3 border-vit-border">{tx.status.toUpperCase()}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
