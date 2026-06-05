import { useState, useEffect, useMemo } from "react";
import {
  useGetWallet, useListTransactions, useInitiateDeposit, useTransfer Out, useConvertCurrency, useGetVitcoinPrice,
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
import {
  AreaChart, Area, ResponsiveContainer, Tooltip as ReTooltip,
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Legend,
} from "recharts";

const CURRENCY_COLORS: Record<string, string> = {
  NGN: "text-green-400",
  USD: "text-blue-400",
  USDT: "text-teal-400",
  PI: "text-purple-400",
  VITCoin: "text-secondary",
};

const CURRENCY_BG: Record<string, string> = {
  NGN: "bg-green-500/10 border-green-500/20",
  USD: "bg-blue-500/10 border-blue-500/20",
  USDT: "bg-teal-500/10 border-teal-500/20",
  PI: "bg-purple-500/10 border-purple-500/20",
  VITCoin: "bg-secondary/10 border-secondary/20",
};

const PIE_COLORS = ["#00f5ff", "#ffd700", "#a855f7", "#3b82f6", "#14b8a6"];

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
  manual_review: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  auto_approved: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  approved: "bg-green-500/10 text-green-400 border-green-500/30",
  processed: "bg-green-500/10 text-green-400 border-green-500/30",
  rejected: "bg-destructive/10 text-destructive border-destructive/30",
  failed: "bg-destructive/10 text-destructive border-destructive/30",
  confirmed: "bg-green-500/10 text-green-400 border-green-500/30",
};

const TX_TYPE_ICON: Record<string, React.ReactNode> = {
  deposit: <ArrowDownLeft className="w-4 h-4 text-green-400" />,
  withdrawal: <ArrowUpRight className="w-4 h-4 text-destructive" />,
  conversion: <ArrowLeftRight className="w-4 h-4 text-blue-400" />,
  conversion_out: <ArrowLeftRight className="w-4 h-4 text-blue-400" />,
  conversion_in: <ArrowLeftRight className="w-4 h-4 text-blue-400" />,
  earn: <Zap className="w-4 h-4 text-secondary" />,
  reward: <Zap className="w-4 h-4 text-secondary" />,
  stake: <BarChart3 className="w-4 h-4 text-purple-400" />,
  subscription: <BadgeCheck className="w-4 h-4 text-blue-400" />,
  fee: <Coins className="w-4 h-4 text-muted-foreground" />,
};

function WalletSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-border p-4 space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-6 w-24" />
          </div>
        ))}
      </div>
      <Skeleton className="h-52 w-full rounded-xl" />
      <Skeleton className="h-80 w-full rounded-xl" />
    </div>
  );
}

function SparklineChart({ data }: { data: { price_usd: number; calculated_at: string }[] }) {
  if (!data || data.length < 2) {
    return (
      <div className="flex items-center justify-center h-16 text-[10px] font-mono text-muted-foreground/50">
        Insufficient price data
      </div>
    );
  }
  const chartData = data.map((d) => ({
    t: format(new Date(d.calculated_at), "MM/dd HH:mm"),
    v: d.price_usd,
  }));
  const min = Math.min(...chartData.map((d) => d.v));
  const max = Math.max(...chartData.map((d) => d.v));
  const trend = chartData[chartData.length - 1].v >= chartData[0].v;
  return (
    <ResponsiveContainer width="100%" height={64}>
      <AreaChart data={chartData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="vitGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={trend ? "#ffd700" : "#ef4444"} stopOpacity={0.3} />
            <stop offset="95%" stopColor={trend ? "#ffd700" : "#ef4444"} stopOpacity={0} />
          </linearGradient>
        </defs>
        <ReTooltip
          contentStyle={{ background: "#0a0a0a", border: "1px solid #1a1a2e", fontFamily: "monospace", fontSize: 10 }}
          formatter={(v: number) => [`$${v.toFixed(4)}`, "VIT"]}
          labelFormatter={(l) => l}
        />
        <Area
          type="monotone"
          dataKey="v"
          stroke={trend ? "#ffd700" : "#ef4444"}
          strokeWidth={1.5}
          fill="url(#vitGrad)"
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function ExchangeRatePanel({
  rates, ngnRate, vitPrice,
}: {
  rates?: Record<string, { rate_to_usd: number; symbol: string; label: string }>;
  ngnRate: number | null;
  vitPrice: number | null;
}) {
  const items = [
    { label: "VIT/USD", value: vitPrice ? `$${Number(vitPrice).toFixed(4)}` : "—", color: "text-secondary" },
    { label: "NGN/USD", value: ngnRate ? `₦${Number(ngnRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—", color: "text-green-400" },
    { label: "PI/USD", value: rates?.PI ? `$${rates.PI.rate_to_usd.toFixed(4)}` : "—", color: "text-purple-400" },
    { label: "USDT/USD", value: "$1.0000", color: "text-teal-400" },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
      {items.map((item) => (
        <div key={item.label} className="rounded-lg border border-border/40 bg-muted/10 px-3 py-2 flex flex-col gap-0.5">
          <div className="text-[10px] font-mono text-muted-foreground uppercase">{item.label}</div>
          <div className={`text-sm font-bold font-mono ${item.color}`}>{item.value}</div>
        </div>
      ))}
    </div>
  );
}

function SpendingPieChart({ txList }: { txList: any[] }) {
  const byType = useMemo(() => {
    const acc: Record<string, number> = {};
    for (const tx of txList) {
      const t = tx.type ?? "other";
      acc[t] = (acc[t] ?? 0) + Number(tx.amount ?? 0);
    }
    return Object.entries(acc)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value]) => ({ name: name.replace(/_/g, " "), value: Number(value.toFixed(2)) }));
  }, [txList]);

  if (byType.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm font-mono text-muted-foreground">
        No transaction data yet
      </div>
    );
  }

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      <ResponsiveContainer width={180} height={180}>
        <PieChart>
          <Pie
            data={byType}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
            isAnimationActive={false}
          >
            {byType.map((_, i) => (
              <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
            ))}
          </Pie>
          <ReTooltip
            contentStyle={{ background: "#0a0a0a", border: "1px solid #1a1a2e", fontFamily: "monospace", fontSize: 10 }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-col gap-2 flex-1">
        {byType.map((item, i) => (
          <div key={item.name} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
            <div className="flex-1 text-xs font-mono capitalize text-muted-foreground">{item.name}</div>
            <div className="text-xs font-mono font-bold">{item.value.toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PortfolioAllocationBar({
  balances,
  totalUSD,
  rates,
}: {
  balances: { currency: string; valueUSD: number; label: string }[];
  totalUSD: number;
  rates: Record<string, number>;
}) {
  const bars = balances.filter((b) => b.valueUSD > 0);
  if (bars.length === 0 || totalUSD <= 0) return null;
  return (
    <div className="space-y-3">
      <div className="h-3 rounded-full overflow-hidden flex">
        {bars.map((b, i) => (
          <div
            key={b.currency}
            className="h-full transition-all"
            style={{
              width: `${(b.valueUSD / totalUSD) * 100}%`,
              background: PIE_COLORS[i % PIE_COLORS.length],
            }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        {bars.map((b, i) => (
          <div key={b.currency} className="flex items-center gap-1.5 text-xs font-mono">
            <div className="w-2 h-2 rounded-sm" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
            <span className="text-muted-foreground">{b.label}</span>
            <span className="font-bold">{((b.valueUSD / totalUSD) * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function VolumeBarChart({ txList, SYM }: { txList: any[]; SYM: Record<string, string> }) {
  const byCurrency = useMemo(() => {
    const acc: Record<string, { credit: number; debit: number }> = {};
    for (const tx of txList) {
      const c = tx.currency ?? "?";
      if (!acc[c]) acc[c] = { credit: 0, debit: 0 };
      const isCredit = tx.direction === "credit";
      acc[c][isCredit ? "credit" : "debit"] += Number(tx.amount ?? 0);
    }
    return Object.entries(acc)
      .map(([name, { credit, debit }]) => ({ name, credit: Number(credit.toFixed(2)), debit: Number(debit.toFixed(2)) }))
      .sort((a, b) => b.credit + b.debit - (a.credit + a.debit));
  }, [txList]);

  if (byCurrency.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm font-mono text-muted-foreground">
        No transaction data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={byCurrency} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <XAxis dataKey="name" tick={{ fontSize: 10, fontFamily: "monospace", fill: "#6b7280" }} />
        <YAxis tick={{ fontSize: 9, fontFamily: "monospace", fill: "#6b7280" }} />
        <ReTooltip
          contentStyle={{ background: "#0a0a0a", border: "1px solid #1a1a2e", fontFamily: "monospace", fontSize: 10 }}
        />
        <Legend wrapperStyle={{ fontSize: 10, fontFamily: "monospace" }} />
        <Bar dataKey="credit" name="In" fill="#22c55e" radius={[2, 2, 0, 0]} />
        <Bar dataKey="debit" name="Out" fill="#ef4444" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function WalletPage() {
  const queryClient = useQueryClient();
  const { data: wallet, isLoading: loadingWallet } = useGetWallet();
  const { data: publicCfg } = usePublicConfig();
  const CURRENCIES = publicCfg?.currencies.map((c) => c.code) ?? ["NGN", "USD", "USDT", "PI", "VITCoin"];
  const SYM: Record<string, string> = Object.fromEntries(
    (publicCfg?.currencies ?? []).map((c) => [c.code, c.symbol])
  );
  const DEPOSIT_PRESETS: Record<string, number[]> = publicCfg?.deposit_presets ?? {};

  const { data: txData, isLoading: loadingTx } = useListTransactions({ limit: 50 });
  const { data: vitcoinPriceData } = useGetVitcoinPrice();

  const { data: vitPriceHistory } = useQuery<{ history: { price_usd: number; calculated_at: string }[] }>({
    queryKey: ["vit-price-history"],
    queryFn: () => apiGet("/api/wallet/vitcoin-price/history?days=7"),
    staleTime: 10 * 60 * 1000,
  });

  const { data: withdrawalsData, isLoading: loadingTransfers } = useQuery<{
    withdrawals: {
      id: string; currency: string; amount: number; fee: number; net_amount: number;
      destination: string; destination_type: string; status: string; auto_approved: boolean;
      review_note: string | null; requested_at: string; processed_at: string | null;
    }[];
    total: number;
  }>({
    queryKey: ["my-withdrawals"],
    queryFn: () => apiGet("/api/wallet/withdrawals?limit=30"),
    staleTime: 30_000,
    retry: false,
  });

  const { data: exchangeRatesData } = useQuery<{
    rates: Record<string, { rate_to_usd: number; symbol: string; label: string }>;
    ngn_per_usd: number;
    vit_price_usd: number;
  }>({
    queryKey: ["exchange-rates"],
    queryFn: () => apiGet("/api/wallet/exchange-rates"),
    staleTime: 2 * 60 * 1000,
  });

  const { mutate: getStarsInvoice, isPending: gettingInvoice } = useTelegramStarsInvoice();
  const initiateDeposit = useInitiateDeposit();
  const withdraw = useTransfer Out();
  const convert = useConvertCurrency();

  const [kycOpen, setKycOpen] = useState(false);
  const [kycForm, setKycForm] = useState({
    full_name: "", date_of_birth: "", document_type: "national_id", document_number: "", nationality: "",
  });

  const submitKyc = useMutation({
    mutationFn: (payload: typeof kycForm) =>
      apiPost<{ kyc_verified: boolean; message: string }>("/api/wallet/kyc/submit", payload),
    onSuccess: (data) => {
      toast.success(data.message || "KYC submitted — pending admin review");
      setKycOpen(false);
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
    },
    onError: (e: any) => toast.error(e?.detail || e.message || "KYC submission failed"),
  });

  const [depositCurrency, setDepositCurrency] = useState("NGN");
  const [depositAmount, setDepositAmount] = useState("");
  const [depositMethod, setDepositMethod] = useState("paystack");
  const [withdrawCurrency, setTransfer OutCurrency] = useState("NGN");
  const [withdrawAmount, setTransfer OutAmount] = useState("");
  const [withdrawDest, setTransfer OutDest] = useState("");
  const [withdrawDestType, setTransfer OutDestType] = useState("bank_account");
  const [convertFrom, setConvertFrom] = useState("NGN");
  const [convertTo, setConvertTo] = useState("VITCoin");
  const [convertAmount, setConvertAmount] = useState("");
  const [txFilter, setTxFilter] = useState("all");
  const [txSearch, setTxSearch] = useState("");
  const [txPage, setTxPage] = useState(1);
  const TX_PAGE_SIZE = 15;

  useEffect(() => {
    if (depositCurrency === "NGN") setDepositMethod("paystack");
    else if (depositCurrency === "USD" || depositCurrency === "USDT") setDepositMethod("stripe");
    else setDepositMethod("manual");
  }, [depositCurrency]);

  const txList: any[] = Array.isArray(txData) ? txData : (txData as any)?.transactions ?? [];

  const filteredTx = useMemo(() => {
    let list = txList;
    if (txFilter !== "all") {
      list = list.filter((t: any) => (t.type ?? "").startsWith(txFilter) || t.currency === txFilter.toUpperCase());
    }
    if (txSearch.trim()) {
      const q = txSearch.toLowerCase();
      list = list.filter((t: any) =>
        (t.reference ?? "").toLowerCase().includes(q) ||
        (t.type ?? "").toLowerCase().includes(q) ||
        (t.currency ?? "").toLowerCase().includes(q)
      );
    }
    return list;
  }, [txList, txFilter, txSearch]);

  const pagedTx = filteredTx.slice(0, txPage * TX_PAGE_SIZE);
  const hasMore = pagedTx.length < filteredTx.length;

  if (loadingWallet) return <WalletSkeleton />;
  if (!wallet) return null;

  const vitPrice = exchangeRatesData?.vit_price_usd
    ?? vitcoinPriceData?.price
    ?? publicCfg?.fx.vit_usd
    ?? null;
  const ngnRate = exchangeRatesData?.ngn_per_usd
    ?? publicCfg?.fx.ngn_per_usd
    ?? null;
  const piRate = exchangeRatesData?.rates?.["PI"]?.rate_to_usd
    ?? publicCfg?.fx.pi_usd_rate
    ?? null;

  const totalUSD = (
    Number(wallet.usd_balance ?? 0) +
    Number(wallet.usdt_balance ?? 0) +
    (ngnRate ? Number(wallet.ngn_balance ?? 0) / ngnRate : 0) +
    (vitPrice ? Number(wallet.vitcoin_balance ?? 0) * vitPrice : 0) +
    (piRate ? Number(wallet.pi_balance ?? 0) * piRate : 0)
  );
  const totalVIT = vitPrice && vitPrice > 0 ? totalUSD / vitPrice : Number(wallet.vitcoin_balance ?? 0);

  const portfolioBalances = [
    { currency: "VITCoin", label: "VITCoin", valueUSD: vitPrice ? Number(wallet.vitcoin_balance) * vitPrice : 0 },
    { currency: "USD", label: "USD", valueUSD: Number(wallet.usd_balance) },
    { currency: "USDT", label: "USDT", valueUSD: Number(wallet.usdt_balance) },
    { currency: "NGN", label: "NGN", valueUSD: ngnRate ? Number(wallet.ngn_balance) / ngnRate : 0 },
    { currency: "PI", label: "PI", valueUSD: piRate ? Number(wallet.pi_balance) * piRate : 0 },
  ];

  const balances = [
    { label: "VITCoin", currency: "VITCoin", value: Number(wallet.vitcoin_balance ?? 0), highlight: true },
    { label: "NGN", currency: "NGN", value: Number(wallet.ngn_balance ?? 0) },
    { label: "USD", currency: "USD", value: Number(wallet.usd_balance ?? 0) },
    { label: "USDT", currency: "USDT", value: Number(wallet.usdt_balance ?? 0) },
    { label: "PI", currency: "PI", value: Number(wallet.pi_balance ?? 0) },
  ];

  const estConvert = (() => {
    if (!convertAmount || parseFloat(convertAmount) <= 0) return null;
    const amt = parseFloat(convertAmount);
    const fee = amt * 0.005;
    const net = amt - fee;
    if (convertFrom === "VITCoin" && convertTo === "USD") return vitPrice ? `$${(net * vitPrice).toFixed(2)} USD` : null;
    if (convertFrom === "USD" && convertTo === "VITCoin") return vitPrice ? `${(net / vitPrice).toFixed(4)} VIT` : null;
    if (convertFrom === "NGN" && convertTo === "USD") return ngnRate ? `$${(net / ngnRate).toFixed(2)} USD` : null;
    if (convertFrom === "USD" && convertTo === "NGN") return ngnRate ? `₦${(net * ngnRate).toFixed(2)} NGN` : null;
    if (convertFrom === "NGN" && convertTo === "VITCoin") return (ngnRate && vitPrice) ? `${(net / ngnRate / vitPrice).toFixed(4)} VIT` : null;
    if (convertFrom === "VITCoin" && convertTo === "NGN") return (ngnRate && vitPrice) ? `₦${(net * vitPrice * ngnRate).toFixed(2)} NGN` : null;
    return `~${net.toFixed(4)} ${convertTo}`;
  })();

  const handleDeposit = async () => {
    if (!depositAmount || parseFloat(depositAmount) <= 0) { toast.error("Invalid amount"); return; }
    try {
      if (depositMethod === "telegram_stars") {
        getStarsInvoice({ stars_amount: Math.round(parseFloat(depositAmount)) }, {
          onSuccess: (data) => {
            if (window.Telegram?.WebApp) {
              window.Telegram.WebApp.openInvoice(data.invoice_link, (status: string) => {
                if (status === "paid") {
                  toast.success("Signal registered");
                  queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
                } else if (status === "failed") {
                  toast.error("Payment failed");
                }
              });
            }
          }
        });
        return;
      }
      const result = await initiateDeposit.mutateAsync({
        currency: depositCurrency,
        amount: parseFloat(depositAmount),
        method: depositMethod,
      });
      if (result.payment_link && !result.payment_link.includes("paystack.com/pay/vit-sports")) {
        window.open(result.payment_link, "_blank");
        toast.success("Redirecting to payment gateway…");
      } else {
        toast.success("Deposit request submitted — ref: " + result.reference);
      }
      setDepositAmount("");
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/transactions"] });
    } catch (e: any) {
      toast.error(e.message || "Deposit failed");
    }
  };

  const handleTransfer Out = async () => {
    if (!withdrawAmount || !withdrawDest) { toast.error("Fill in amount and destination"); return; }
    try {
      const result = await withdraw.mutateAsync({
        currency: withdrawCurrency,
        amount: parseFloat(withdrawAmount),
        destination: withdrawDest,
        destination_type: withdrawDestType,
      });
      toast.success(`Transfer of ${withdrawAmount} ${withdrawCurrency} submitted — ID: ${result.request_id?.slice(0, 8)}…`);
      setTransfer OutAmount(""); setTransfer OutDest("");
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
      queryClient.invalidateQueries({ queryKey: ["my-withdrawals"] });
    } catch (e: any) {
      toast.error(e.message || "Transfer failed");
    }
  };

  const handleConvert = async () => {
    if (!convertAmount || parseFloat(convertAmount) <= 0) { toast.error("Invalid amount"); return; }
    try {
      const result = await convert.mutateAsync({
        from_currency: convertFrom,
        to_currency: convertTo,
        amount: parseFloat(convertAmount),
      });
      toast.success(`Converted — received ${result.to_amount.toFixed(4)} ${convertTo}`);
      setConvertAmount("");
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
    } catch (e: any) {
      toast.error(e.message || "Conversion failed");
    }
  };

  const exportCSV = () => {
    if (txList.length === 0) { toast.info("No transactions to export"); return; }
    const headers = ["Date", "Type", "Amount", "Currency", "Direction", "Reference", "Status", "Fee"];
    const rows = txList.map((t: any) => [
      t.created_at ? new Date(t.created_at).toLocaleString() : "",
      t.type ?? "", t.amount ?? "", t.currency ?? "",
      t.direction ?? "", t.reference ?? "", t.status ?? "completed", t.fee_amount ?? "0",
    ]);
    const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "vit-transactions.csv"; a.click();
    URL.revokeObjectURL(url);
    toast.success("Statement exported");
  };

  const vitHistory = vitPriceHistory?.history ?? [];
  const vitTrend = vitHistory.length >= 2
    ? vitHistory[vitHistory.length - 1].price_usd >= vitHistory[0].price_usd
    : true;
  const vitChange = vitHistory.length >= 2
    ? (((vitHistory[vitHistory.length - 1].price_usd - vitHistory[0].price_usd) / vitHistory[0].price_usd) * 100).toFixed(2)
    : null;

  return (
    <div className="space-y-6 pb-24 lg:pb-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-mono font-bold tracking-tight flex items-center gap-2">
            <Wallet className="w-6 h-6 text-secondary" />
            Network Wallet
          </h1>
          <p className="text-muted-foreground font-mono text-xs mt-1">
            {wallet.kyc_verified ? (
              <span className="text-green-400 flex items-center gap-1"><BadgeCheck className="w-3 h-3" /> KYC Verified</span>
            ) : (
              <span className="text-yellow-400 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> KYC Pending</span>
            )}
          </p>
        </div>
        <Button variant="outline" size="sm" className="font-mono text-xs gap-1.5" onClick={exportCSV}>
          <Download className="w-3 h-3" />
          Export CSV
        </Button>
      </div>

      {/* ── Wallet Protection Layer Notice ── */}
      <div className="rounded-xl border border-blue-500/30 bg-blue-500/5 px-4 py-3 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="text-sm font-mono font-bold text-blue-400 uppercase tracking-wider">Wallet Protection Layer Active</div>
          <p className="text-[10px] font-mono text-muted-foreground leading-normal">
            Financial infrastructure is strictly limited to <span className="text-secondary font-bold">Niche Prediction Markets</span> (Governance, Elections, Merit).
            <br />
            Sports markets function as analytics-only infrastructure with affiliate-redirection. No sports wagering funds are held or processed here.
          </p>
        </div>
      </div>

      {/* ── Hero Card: Portfolio + VIT Sparkline ── */}
      <Card className="border-secondary/30 bg-gradient-to-br from-secondary/5 to-card vit-glow-gold overflow-hidden">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-6">
            <div className="flex-1">
              <div className="text-xs font-mono text-muted-foreground uppercase mb-2 flex items-center gap-1.5">
                <Coins className="w-3 h-3 text-secondary" />
                Total Portfolio Value
              </div>
              <div className="text-4xl font-bold font-mono text-secondary mb-1">
                ${totalUSD.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className="text-sm font-mono text-muted-foreground">
                ≈ {SYM["VITCoin"] ?? "VIT"}{totalVIT.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                {vitPrice && (
                  <span className="ml-2 text-[10px] opacity-70">@ ${Number(vitPrice).toFixed(4)}/VIT</span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-3">
                <div className="flex items-center gap-1.5 text-sm font-mono">
                  {wallet.kyc_verified
                    ? <TrendingUp className="w-4 h-4 text-green-400" />
                    : <TrendingDown className="w-4 h-4 text-muted-foreground" />
                  }
                  <span className={wallet.kyc_verified ? "text-green-400" : "text-muted-foreground"}>
                    {wallet.kyc_verified ? "Verified account" : "KYC pending"}
                  </span>
                </div>
                {wallet.is_frozen && (
                  <span className="text-xs font-mono text-destructive border border-destructive/30 rounded px-1.5 py-0.5">
                    Wallet frozen
                  </span>
                )}
              </div>
            </div>
            {/* VIT Price Sparkline */}
            <div className="sm:w-64 space-y-1">
              <div className="flex items-center justify-between">
                <div className="text-[10px] font-mono text-muted-foreground uppercase">VIT 7-Day Price</div>
                {vitChange && (
                  <span className={`text-[10px] font-mono font-bold ${vitTrend ? "text-green-400" : "text-destructive"}`}>
                    {vitTrend ? "+" : ""}{vitChange}%
                  </span>
                )}
              </div>
              <SparklineChart data={vitHistory} />
              <div className="flex justify-between text-[10px] font-mono text-muted-foreground/60">
                <span>7d ago</span>
                <span>Now</span>
              </div>
            </div>
          </div>
          {/* Portfolio allocation bar */}
          <div className="mt-5 pt-4 border-t border-border/30">
            <div className="text-[10px] font-mono text-muted-foreground uppercase mb-2">Portfolio Allocation</div>
            <PortfolioAllocationBar balances={portfolioBalances} totalUSD={totalUSD} rates={{}} />
          </div>
        </CardContent>
      </Card>

      {/* ── Balance Grid ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        {balances.map((b) => (
          <div
            key={b.currency}
            className={`rounded-xl border p-4 space-y-1.5 transition-all ${
              b.highlight
                ? "border-secondary/40 bg-secondary/5 vit-glow-gold"
                : "border-border/60 bg-card/40 hover:border-border"
            }`}
          >
            <div className="text-[10px] font-mono text-muted-foreground uppercase">{b.label}</div>
            <div className={`text-lg font-bold font-mono ${b.highlight ? "text-secondary" : CURRENCY_COLORS[b.currency] ?? ""}`}>
              {SYM[b.currency] ?? ""}{b.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
            </div>
            {b.currency !== "USD" && b.currency !== "USDT" && (
              <div className="text-[10px] font-mono text-muted-foreground/50">
                {b.currency === "VITCoin" && vitPrice ? `≈ $${(b.value * vitPrice).toFixed(2)}` :
                 b.currency === "NGN" && ngnRate ? `≈ $${(b.value / ngnRate).toFixed(2)}` :
                 b.currency === "PI" && piRate ? `≈ $${(b.value * piRate).toFixed(2)}` : ""}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── KYC Banner ── */}
      {!wallet.kyc_verified && (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-yellow-500/30 bg-yellow-500/5 px-5 py-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0" />
            <div>
              <div className="text-sm font-mono font-medium">Complete KYC Verification</div>
              <div className="text-xs font-mono text-muted-foreground">Required for withdrawals above daily limits</div>
            </div>
          </div>
          <Dialog open={kycOpen} onOpenChange={setKycOpen}>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline" className="font-mono text-xs border-yellow-500/40 text-yellow-400 hover:bg-yellow-500/10 flex-shrink-0">
                Verify Now
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-border max-w-md">
              <DialogHeader>
                <DialogTitle className="font-mono flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-yellow-400" /> Identity Verification
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-2">
                <p className="text-xs text-muted-foreground font-mono">
                  Your identity details are stored securely and reviewed by our compliance team. Never shared with third parties.
                </p>
                <div className="space-y-3">
                  {[
                    { key: "full_name", label: "Full Legal Name *", placeholder: "As it appears on your ID", type: "text" },
                    { key: "date_of_birth", label: "Date of Birth *", placeholder: "", type: "date" },
                    { key: "document_number", label: "Document Number *", placeholder: "ID / Passport number", type: "text" },
                    { key: "nationality", label: "Nationality", placeholder: "e.g. Nigerian", type: "text" },
                  ].map(({ key, label, placeholder, type }) => (
                    <div key={key}>
                      <label className="text-xs font-mono text-muted-foreground mb-1 block">{label}</label>
                      <Input
                        type={type}
                        placeholder={placeholder}
                        value={(kycForm as any)[key]}
                        onChange={e => setKycForm(f => ({ ...f, [key]: e.target.value }))}
                        className="font-mono text-sm"
                      />
                    </div>
                  ))}
                  <div>
                    <label className="text-xs font-mono text-muted-foreground mb-1 block">Document Type *</label>
                    <Select value={kycForm.document_type} onValueChange={v => setKycForm(f => ({ ...f, document_type: v }))}>
                      <SelectTrigger className="font-mono text-sm"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="national_id">National ID</SelectItem>
                        <SelectItem value="passport">International Passport</SelectItem>
                        <SelectItem value="drivers_license">Driver's License</SelectItem>
                        <SelectItem value="voters_card">Voter's Card</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button
                  className="w-full font-mono"
                  disabled={submitKyc.isPending || !kycForm.full_name || !kycForm.date_of_birth || !kycForm.document_number}
                  onClick={() => submitKyc.mutate(kycForm)}
                >
                  {submitKyc.isPending ? "Submitting…" : "Submit for Review"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      )}

      {/* ── Action Buttons Row ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Deposit */}
        <Dialog>
          <DialogTrigger asChild>
            <Button className="h-12 font-mono gap-2 w-full">
              <ArrowDownLeft className="w-4 h-4" /> Deposit
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="font-mono flex items-center gap-2"><ArrowDownLeft className="w-4 h-4 text-primary" /> Quick Deposit</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Currency</div>
                <Select value={depositCurrency} onValueChange={setDepositCurrency}>
                  <SelectTrigger className="font-mono"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((c) => <SelectItem key={c} value={c} className="font-mono">{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Amount</div>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  className="font-mono"
                />
                <div className="flex gap-2 mt-2">
                  {(DEPOSIT_PRESETS[depositCurrency] ?? []).map((p) => (
                    <button
                      key={p}
                      onClick={() => setDepositAmount(String(p))}
                      className={`flex-1 text-xs font-mono rounded py-1.5 border transition-all ${
                        depositAmount === String(p) ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-border/80"
                      }`}
                    >
                      {SYM[depositCurrency] ?? ""}{p.toLocaleString()}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Payment Method</div>
                <Select value={depositMethod} onValueChange={setDepositMethod}>
                  <SelectTrigger className="font-mono"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {depositCurrency === "NGN" && <SelectItem value="paystack" className="font-mono">Paystack (NGN)</SelectItem>}
                    {(depositCurrency === "USD" || depositCurrency === "USDT") && <SelectItem value="stripe" className="font-mono">Stripe (USD/Card)</SelectItem>}
                                        {(depositCurrency === "PI" || depositCurrency === "VITCoin") && <SelectItem value="manual" className="font-mono">Manual / On-chain</SelectItem>}
                    {isTWA() && <SelectItem value="telegram_stars" className="font-mono">Telegram Stars</SelectItem>}
                  </SelectContent>
                </Select>
              </div>
              {depositAmount && parseFloat(depositAmount) > 0 && (
                <div className="rounded-lg bg-muted/30 border border-border/50 p-3 text-xs font-mono space-y-1.5">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Amount</span>
                    <span>{SYM[depositCurrency] ?? ""}{parseFloat(depositAmount).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>Processing fee (1%)</span>
                    <span>{SYM[depositCurrency] ?? ""}{(parseFloat(depositAmount) * 0.01).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-foreground border-t border-border/50 pt-1.5">
                    <span>You receive</span>
                    <span className="text-primary">{SYM[depositCurrency] ?? ""}{(parseFloat(depositAmount) * 0.99).toFixed(2)}</span>
                  </div>
                </div>
              )}
              <Button className="w-full font-mono h-11 gap-2" onClick={handleDeposit} disabled={initiateDeposit.isPending}>
                {initiateDeposit.isPending ? "Processing…" : "Deposit Now"}
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Transfer Out */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="h-12 font-mono gap-2 w-full border-border/60">
              <Send className="w-4 h-4" /> Transfer Out
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="font-mono flex items-center gap-2"><Send className="w-4 h-4" /> Transfer Out Funds</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              {!wallet.kyc_verified && (
                <div className="flex items-start gap-2 rounded-lg bg-yellow-500/5 border border-yellow-500/20 p-3 text-xs font-mono text-yellow-400">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>KYC verification is required for withdrawals. Complete it above first.</span>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Currency</div>
                  <Select value={withdrawCurrency} onValueChange={setTransfer OutCurrency}>
                    <SelectTrigger className="font-mono text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {CURRENCIES.map((c) => <SelectItem key={c} value={c} className="font-mono">{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Amount</div>
                  <Input
                    type="number"
                    placeholder="0.00"
                    value={withdrawAmount}
                    onChange={(e) => setTransfer OutAmount(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
              </div>
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Destination Type</div>
                <Select value={withdrawDestType} onValueChange={setTransfer OutDestType}>
                  <SelectTrigger className="font-mono"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bank_account" className="font-mono">Bank Account</SelectItem>
                    <SelectItem value="crypto_wallet" className="font-mono">Crypto Wallet</SelectItem>
                    <SelectItem value="mobile_money" className="font-mono">Mobile Money</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Destination</div>
                <Input
                  placeholder={withdrawDestType === "bank_account" ? "Account number" : "Wallet address"}
                  value={withdrawDest}
                  onChange={(e) => setTransfer OutDest(e.target.value)}
                  className="font-mono text-sm"
                />
              </div>
              {withdrawAmount && parseFloat(withdrawAmount) > 0 && (
                <div className="rounded-lg bg-muted/30 border border-border/50 p-3 text-xs font-mono space-y-1.5">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Transfer fee (1.5%)</span>
                    <span>{SYM[withdrawCurrency] ?? ""}{(parseFloat(withdrawAmount) * 0.015).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-foreground border-t border-border/50 pt-1.5">
                    <span>You receive</span>
                    <span className="text-primary">{SYM[withdrawCurrency] ?? ""}{(parseFloat(withdrawAmount) * 0.985).toFixed(2)}</span>
                  </div>
                  <div className="text-muted-foreground/60 text-[10px] pt-0.5">Processing: 24–48 hours</div>
                </div>
              )}
              <Button
                variant="outline"
                className="w-full font-mono h-11 gap-2 border-destructive/30 text-destructive hover:bg-destructive/10"
                onClick={handleTransfer Out}
                disabled={withdraw.isPending || !wallet.kyc_verified}
              >
                {withdraw.isPending ? "Processing…" : !wallet.kyc_verified ? "KYC Required" : "Request Transfer"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Convert */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="h-12 font-mono gap-2 w-full border-border/60">
              <ArrowLeftRight className="w-4 h-4" /> Convert
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="font-mono flex items-center gap-2"><ArrowLeftRight className="w-4 h-4" /> Convert Currency</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">From</div>
                <Select value={convertFrom} onValueChange={setConvertFrom}>
                  <SelectTrigger className="font-mono"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.filter((c) => c !== convertTo).map((c) => (
                      <SelectItem key={c} value={c} className="font-mono">{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex justify-center">
                <button
                  onClick={() => { const tmp = convertFrom; setConvertFrom(convertTo); setConvertTo(tmp); }}
                  className="w-8 h-8 rounded-full border border-border flex items-center justify-center hover:bg-muted/40 transition-colors"
                >
                  <RefreshCcw className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">To</div>
                <Select value={convertTo} onValueChange={setConvertTo}>
                  <SelectTrigger className="font-mono"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.filter((c) => c !== convertFrom).map((c) => (
                      <SelectItem key={c} value={c} className="font-mono">{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Amount ({convertFrom})</div>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={convertAmount}
                  onChange={(e) => setConvertAmount(e.target.value)}
                  className="font-mono"
                />
              </div>
              <div className="rounded-lg bg-muted/30 border border-border/50 p-3 text-xs font-mono space-y-1.5">
                <div className="flex justify-between text-muted-foreground">
                  <span>Conversion fee</span>
                  <span>0.5%</span>
                </div>
                {(convertFrom === "VITCoin" || convertTo === "VITCoin") && vitPrice && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>VIT price</span>
                    <span className="text-secondary">${Number(vitPrice).toFixed(4)}</span>
                  </div>
                )}
                {(convertFrom === "NGN" || convertTo === "NGN") && ngnRate && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>NGN/USD rate</span>
                    <span className="text-green-400">₦{ngnRate.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                  </div>
                )}
                {estConvert && (
                  <div className="flex justify-between font-bold text-foreground border-t border-border/50 pt-1.5">
                    <span>You receive ~</span>
                    <span className="text-primary">{estConvert}</span>
                  </div>
                )}
              </div>
              <Button className="w-full font-mono h-11" onClick={handleConvert} disabled={convert.isPending}>
                {convert.isPending ? "Converting…" : `Convert ${convertFrom} → ${convertTo}`}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* ── Live Exchange Rates ── */}
      <div>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground uppercase mb-2">
          <Globe className="w-3 h-3" /> Live Exchange Rates
        </div>
        <ExchangeRatePanel rates={exchangeRatesData?.rates} ngnRate={ngnRate} vitPrice={vitPrice} />
      </div>

      {/* ── Tabs: Transactions | Transfers | Analytics ── */}
      <Tabs defaultValue="transactions">
        <TabsList className="font-mono text-xs gap-1 h-9">
          <TabsTrigger value="transactions" className="gap-1.5 text-xs">
            <Landmark className="w-3 h-3" />
            Transactions
            {txList.length > 0 && (
              <span className="text-[9px] opacity-60 ml-0.5">({txList.length})</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="withdrawals" className="gap-1.5 text-xs">
            <History className="w-3 h-3" />
            Transfers
          </TabsTrigger>
          <TabsTrigger value="analytics" className="gap-1.5 text-xs">
            <BarChart3 className="w-3 h-3" />
            Analytics
          </TabsTrigger>
        </TabsList>

        {/* ── Transactions Tab ── */}
        <TabsContent value="transactions" className="mt-3">
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-3 border-b border-border/40">
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Search by reference, type, currency…"
                    value={txSearch}
                    onChange={(e) => { setTxSearch(e.target.value); setTxPage(1); }}
                    className="pl-9 font-mono text-xs h-8"
                  />
                </div>
                <div className="flex gap-1 flex-wrap">
                  {["all", "deposit", "withdrawal", "conversion", "earn", "reward"].map((f) => (
                    <button
                      key={f}
                      onClick={() => { setTxFilter(f); setTxPage(1); }}
                      className={`text-[10px] font-mono px-2.5 py-1 rounded-md border transition-all capitalize ${
                        txFilter === f
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border text-muted-foreground hover:border-border/80 hover:text-foreground"
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {loadingTx ? (
                <div className="p-4 space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <Skeleton className="w-8 h-8 rounded-lg flex-shrink-0" />
                      <div className="flex-1 space-y-1">
                        <Skeleton className="h-3 w-32" />
                        <Skeleton className="h-2.5 w-20" />
                      </div>
                      <Skeleton className="h-4 w-20" />
                    </div>
                  ))}
                </div>
              ) : filteredTx.length === 0 ? (
                <div className="py-12 text-center">
                  <div className="text-4xl mb-3">💳</div>
                  <p className="text-sm font-mono text-muted-foreground">No transactions found</p>
                  <p className="text-xs font-mono text-muted-foreground/60 mt-1">
                    {txSearch || txFilter !== "all" ? "Try clearing your search or filter" : "Deposit funds to get started"}
                  </p>
                </div>
              ) : (
                <>
                  <div className="divide-y divide-border/30">
                    {pagedTx.map((tx: any, i: number) => {
                      const isDebit = tx.direction === "debit" || ["withdrawal", "conversion_out", "stake", "fee", "subscription"].includes(tx.type ?? "");
                      const icon = TX_TYPE_ICON[tx.type ?? ""] ?? (isDebit
                        ? <ArrowUpRight className="w-4 h-4 text-destructive" />
                        : <ArrowDownLeft className="w-4 h-4 text-green-400" />
                      );
                      const statusClass = STATUS_BADGE[tx.status ?? "confirmed"] ?? "bg-muted/10 text-muted-foreground border-border";
                      return (
                        <div key={tx.id ?? i} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/20 transition-colors">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                            isDebit ? "bg-destructive/10" : "bg-green-500/10"
                          }`}>
                            {icon}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-sm font-mono font-medium capitalize text-foreground">
                                {(tx.type ?? "transaction").replace(/_/g, " ")}
                              </span>
                              {tx.status && tx.status !== "confirmed" && (
                                <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border capitalize ${statusClass}`}>
                                  {tx.status.replace(/_/g, " ")}
                                </span>
                              )}
                            </div>
                            <div className="text-[10px] font-mono text-muted-foreground flex items-center gap-2 mt-0.5">
                              <span>{tx.created_at ? format(new Date(tx.created_at), "MMM d, HH:mm") : "–"}</span>
                              {tx.reference && (
                                <span className="text-muted-foreground/40 truncate max-w-[120px]">{tx.reference}</span>
                              )}
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className={`text-sm font-bold font-mono ${isDebit ? "text-destructive" : "text-green-400"}`}>
                              {isDebit ? "−" : "+"}{SYM[tx.currency] ?? ""}{Number(tx.amount ?? 0).toLocaleString(undefined, { maximumFractionDigits: 4 })}
                            </div>
                            <div className="text-[10px] font-mono text-muted-foreground">{tx.currency}</div>
                            {tx.fee_amount > 0 && (
                              <div className="text-[9px] font-mono text-muted-foreground/40">
                                fee {Number(tx.fee_amount).toFixed(4)}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {hasMore && (
                    <div className="p-4 text-center border-t border-border/30">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="font-mono text-xs gap-1.5"
                        onClick={() => setTxPage((p) => p + 1)}
                      >
                        <ChevronDown className="w-3 h-3" />
                        Load more ({filteredTx.length - pagedTx.length} remaining)
                      </Button>
                    </div>
                  )}
                  {!hasMore && filteredTx.length > TX_PAGE_SIZE && (
                    <div className="px-4 py-3 text-center text-[10px] font-mono text-muted-foreground/50 border-t border-border/30">
                      All {filteredTx.length} transactions shown
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Transfers Tab ── */}
        <TabsContent value="withdrawals" className="mt-3">
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-3 border-b border-border/40">
              <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                <History className="w-4 h-4 text-muted-foreground" />
                Transfer History
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {loadingTransfers ? (
                <div className="p-4 space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <Skeleton className="w-8 h-8 rounded-lg" />
                      <div className="flex-1 space-y-1">
                        <Skeleton className="h-3 w-40" />
                        <Skeleton className="h-2.5 w-24" />
                      </div>
                      <Skeleton className="h-4 w-16" />
                    </div>
                  ))}
                </div>
              ) : !withdrawalsData || withdrawalsData.withdrawals.length === 0 ? (
                <div className="py-12 text-center">
                  <div className="text-4xl mb-3">📤</div>
                  <p className="text-sm font-mono text-muted-foreground">No withdrawal requests yet</p>
                  <p className="text-xs font-mono text-muted-foreground/60 mt-1">Your withdrawal history will appear here</p>
                </div>
              ) : (
                <div className="divide-y divide-border/30">
                  {withdrawalsData.withdrawals.map((w) => {
                    const statusClass = STATUS_BADGE[w.status] ?? "bg-muted/10 text-muted-foreground border-border";
                    const isProcessed = ["processed", "approved", "auto_approved"].includes(w.status);
                    const isFailed = ["rejected", "failed"].includes(w.status);
                    return (
                      <div key={w.id} className="px-4 py-4 hover:bg-muted/20 transition-colors">
                        <div className="flex items-start gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
                            isProcessed ? "bg-green-500/10" : isFailed ? "bg-destructive/10" : "bg-yellow-500/10"
                          }`}>
                            {isProcessed
                              ? <Check className="w-4 h-4 text-green-400" />
                              : isFailed
                              ? <AlertTriangle className="w-4 h-4 text-destructive" />
                              : <Clock className="w-4 h-4 text-yellow-400" />
                            }
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-sm font-mono font-bold text-foreground">
                                {SYM[w.currency] ?? ""}{w.amount.toLocaleString(undefined, { maximumFractionDigits: 4 })} {w.currency}
                              </span>
                              <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border capitalize ${statusClass}`}>
                                {w.status.replace(/_/g, " ")}
                              </span>
                            </div>
                            <div className="text-[10px] font-mono text-muted-foreground mt-1 space-y-0.5">
                              <div className="flex items-center gap-1.5">
                                <span className="capitalize">{w.destination_type.replace(/_/g, " ")}</span>
                                <span className="opacity-40">·</span>
                                <span className="truncate max-w-[160px] opacity-60">{w.destination}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span>Fee: {SYM[w.currency] ?? ""}{w.fee.toFixed(4)}</span>
                                <span className="text-muted-foreground/60">
                                  Net: {SYM[w.currency] ?? ""}{w.net_amount.toFixed(4)}
                                </span>
                              </div>
                              <div className="text-muted-foreground/50">
                                Requested {formatDistanceToNow(new Date(w.requested_at), { addSuffix: true })}
                                {w.processed_at && (
                                  <span className="ml-2">· Processed {format(new Date(w.processed_at), "MMM d, HH:mm")}</span>
                                )}
                              </div>
                              {w.review_note && (
                                <div className="flex items-start gap-1 text-muted-foreground/70 mt-1">
                                  <Info className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                  <span>{w.review_note}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Analytics Tab ── */}
        <TabsContent value="analytics" className="mt-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-card/50 backdrop-blur border-border">
              <CardHeader className="pb-3 border-b border-border/40">
                <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                  <Coins className="w-4 h-4 text-muted-foreground" />
                  Transaction Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <SpendingPieChart txList={txList} />
              </CardContent>
            </Card>
            <Card className="bg-card/50 backdrop-blur border-border">
              <CardHeader className="pb-3 border-b border-border/40">
                <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-muted-foreground" />
                  Volume by Currency
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <VolumeBarChart txList={txList} SYM={SYM} />
              </CardContent>
            </Card>
            <Card className="bg-card/50 backdrop-blur border-border md:col-span-2">
              <CardHeader className="pb-3 border-b border-border/40">
                <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-muted-foreground" />
                  Summary Statistics
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {[
                    {
                      label: "Total Deposited",
                      value: txList.filter(t => t.type === "deposit" && t.status === "confirmed").reduce((s: number, t: any) => s + Number(t.amount ?? 0), 0),
                      color: "text-green-400",
                      prefix: "",
                    },
                    {
                      label: "Total Transfer Outn",
                      value: txList.filter(t => t.type === "withdrawal").reduce((s: number, t: any) => s + Number(t.amount ?? 0), 0),
                      color: "text-destructive",
                      prefix: "",
                    },
                    {
                      label: "Fees Paid",
                      value: txList.reduce((s: number, t: any) => s + Number(t.fee_amount ?? 0), 0),
                      color: "text-muted-foreground",
                      prefix: "",
                    },
                    {
                      label: "Total Transactions",
                      value: txList.length,
                      color: "text-primary",
                      prefix: "#",
                      noDecimals: true,
                    },
                  ].map(({ label, value, color, prefix, noDecimals }) => (
                    <div key={label} className="space-y-1">
                      <div className="text-[10px] font-mono text-muted-foreground uppercase">{label}</div>
                      <div className={`text-xl font-bold font-mono ${color}`}>
                        {prefix}{noDecimals ? value : value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
