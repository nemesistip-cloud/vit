import { useState, useEffect } from "react";
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
import {
  ArrowUpRight, ArrowDownLeft, RefreshCcw, Landmark, ShieldCheck, AlertTriangle,
  BadgeCheck, Download, TrendingUp, TrendingDown, Coins, ArrowRight, ChevronDown, Check
} from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { usePublicConfig } from "@/lib/usePublicConfig";

// Per-currency tint stays in the UI layer (it's a presentation choice).
// Codes, symbols, and deposit presets all come from /config/public.
const CURRENCY_COLORS: Record<string, string> = {
  NGN: "text-green-400", USD: "text-blue-400", USDT: "text-teal-400",
  PI: "text-purple-400", VITCoin: "text-secondary",
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
      <Skeleton className="h-40 w-full rounded-xl" />
    </div>
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

  const initiateDeposit = useInitiateDeposit();
  const withdraw = useWithdraw();
  const convert = useConvertCurrency();

  const submitKyc = useMutation({
    mutationFn: () => apiPost<{ kyc_verified: boolean; message: string }>("/api/wallet/kyc/submit", {}),
    onSuccess: (data) => {
      toast.success(data.message || "KYC verified successfully");
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
    },
    onError: (e: any) => toast.error(e.message || "KYC submission failed"),
  });

  const { data: currenciesData } = useQuery<{ currencies: any[] }>({
    queryKey: ["admin-currencies"],
    queryFn: () => apiGet<{ currencies: any[] }>("/admin/currency"),
    staleTime: 5 * 60 * 1000,
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

  const [depositCurrency, setDepositCurrency] = useState("NGN");
  const [depositAmount, setDepositAmount] = useState("");
  const [depositMethod, setDepositMethod] = useState("paystack");

  useEffect(() => {
    if (depositCurrency === "NGN") setDepositMethod("paystack");
    else if (depositCurrency === "USD" || depositCurrency === "USDT") setDepositMethod("stripe");
    else setDepositMethod("manual");
  }, [depositCurrency]);

  const [withdrawCurrency, setWithdrawCurrency] = useState("NGN");
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [withdrawDest, setWithdrawDest] = useState("");
  const [withdrawDestType, setWithdrawDestType] = useState("bank_account");

  const [convertFrom, setConvertFrom] = useState("NGN");
  const [convertTo, setConvertTo] = useState("VITCoin");
  const [convertAmount, setConvertAmount] = useState("");
  const [txFilter, setTxFilter] = useState("all");

  const txList: any[] = Array.isArray(txData) ? txData : (txData as any)?.transactions ?? [];

  const filteredTx = txFilter === "all"
    ? txList
    : txList.filter((t: any) => t.type === txFilter || t.currency === txFilter.toUpperCase());

  if (loadingWallet) return <WalletSkeleton />;
  if (!wallet) return null;

  const balances = [
    { label: "VITCoin", currency: "VITCoin", value: Number(wallet.vitcoin_balance ?? 0), highlight: true },
    { label: "NGN", currency: "NGN", value: Number(wallet.ngn_balance ?? 0) },
    { label: "USD", currency: "USD", value: Number(wallet.usd_balance ?? 0) },
    { label: "USDT", currency: "USDT", value: Number(wallet.usdt_balance ?? 0) },
    { label: "PI", currency: "PI", value: Number(wallet.pi_balance ?? 0) },
  ];

  // Live values: prefer the wallet exchange-rates endpoint, then the
  // public-config endpoint, then the legacy admin/currency lookup.
  // We deliberately avoid hardcoded literals — if every source is missing,
  // we fall back to the configured public-config value (which itself
  // sources from PlatformConfig, not invented numbers).
  const vitPrice = exchangeRatesData?.vit_price_usd
    ?? vitcoinPriceData?.price
    ?? publicCfg?.fx.vit_usd
    ?? null;
  const ngnRateFromExchange = exchangeRatesData?.rates?.["NGN"]?.rate_to_usd;
  const ngnCurrency = currenciesData?.currencies?.find((c: any) => c.code === "NGN");
  const ngnRateToUSD = ngnRateFromExchange
    ?? ngnCurrency?.rate_to_usd
    ?? publicCfg?.fx.ngn_usd_rate
    ?? null;
  const ngnRate = exchangeRatesData?.ngn_per_usd
    ?? publicCfg?.fx.ngn_per_usd
    ?? (ngnRateToUSD && ngnRateToUSD > 0 ? 1 / ngnRateToUSD : null);
  // If a rate is genuinely unknown, contribute 0 instead of inventing one —
  // better to under-report than to mislead the user with a fake total.
  const totalUSD = (
    Number(wallet.usd_balance ?? 0) +
    Number(wallet.usdt_balance ?? 0) +
    (ngnRate ? Number(wallet.ngn_balance ?? 0) / ngnRate : 0) +
    (vitPrice ? Number(wallet.vitcoin_balance ?? 0) * vitPrice : 0)
  );

  const handleDeposit = async () => {
    if (!depositAmount || parseFloat(depositAmount) <= 0) {
      toast.error("Enter a valid amount");
      return;
    }
    try {
      const result = await initiateDeposit.mutateAsync({
        currency: depositCurrency,
        amount: parseFloat(depositAmount),
        method: depositMethod,
      });
      if (result.payment_link && !result.payment_link.includes("paystack.com/pay/vit-sports")) {
        window.open(result.payment_link, "_blank");
        toast.success("Redirecting to payment gateway...");
      } else {
        toast.success("Deposit request submitted");
      }
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
    } catch (e: any) {
      toast.error(e.message || "Deposit failed");
    }
  };

  const handleWithdraw = async () => {
    if (!withdrawAmount || !withdrawDest) {
      toast.error("Fill in amount and destination");
      return;
    }
    try {
      await withdraw.mutateAsync({
        currency: withdrawCurrency,
        amount: parseFloat(withdrawAmount),
        destination: withdrawDest,
        destination_type: withdrawDestType,
      });
      toast.success("Withdrawal request submitted");
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
    } catch (e: any) {
      toast.error(e.message || "Withdrawal failed");
    }
  };

  const handleConvert = async () => {
    if (!convertAmount || parseFloat(convertAmount) <= 0) {
      toast.error("Enter a valid amount");
      return;
    }
    try {
      const result = await convert.mutateAsync({
        from_currency: convertFrom,
        to_currency: convertTo,
        amount: parseFloat(convertAmount),
      });
      toast.success(`Converted: received ${result.to_amount} ${convertTo}`);
      queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
    } catch (e: any) {
      toast.error(e.message || "Conversion failed");
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Header ────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-mono font-bold tracking-tight">Wallet & Treasury</h1>
          <p className="text-muted-foreground font-mono text-xs mt-1">
            {wallet.kyc_verified ? (
              <span className="text-green-400 flex items-center gap-1"><BadgeCheck className="w-3 h-3" /> KYC Verified</span>
            ) : (
              <span className="text-yellow-400 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> KYC Pending</span>
            )}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="font-mono text-xs gap-1.5 hidden sm:flex"
          onClick={() => {
            if (txList.length === 0) { toast.info("No transactions to export"); return; }
            const headers = ["Date", "Type", "Amount", "Currency", "Direction", "Reference", "Status"];
            const rows = txList.map((t: any) => [
              t.created_at ? new Date(t.created_at).toLocaleString() : "",
              t.type ?? "", t.amount ?? "", t.currency ?? "",
              t.direction ?? "", t.reference ?? "", t.status ?? "completed",
            ]);
            const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url; a.download = "vit-transactions.csv"; a.click();
            URL.revokeObjectURL(url);
            toast.success("Statement exported");
          }}
        >
          <Download className="w-3 h-3" />
          Export Statement
        </Button>
      </div>

      {/* ── Total Balance Hero Card ──────────────────── */}
      <Card className="border-secondary/30 bg-gradient-to-br from-secondary/5 to-card vit-glow-gold">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <div className="text-xs font-mono text-muted-foreground uppercase mb-2 flex items-center gap-1.5">
                <Coins className="w-3 h-3 text-secondary" />
                Total Portfolio Value
              </div>
              <div className="text-4xl font-bold font-mono text-secondary mb-1">
                {SYM["VITCoin"]}{Number(wallet.vitcoin_balance ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </div>
              <div className="text-sm font-mono text-muted-foreground">
                ≈ ${totalUSD.toFixed(2)} USD equivalent
              </div>
            </div>
            <div className="flex flex-row sm:flex-col items-center sm:items-end gap-3 sm:gap-2">
              <div className="flex items-center gap-1.5 text-sm font-mono">
                {wallet.kyc_verified
                  ? <TrendingUp className="w-4 h-4 text-green-400" />
                  : <TrendingDown className="w-4 h-4 text-muted-foreground" />
                }
                <span className={wallet.kyc_verified ? "text-green-400" : "text-muted-foreground"}>
                  {wallet.kyc_verified ? "KYC verified" : "KYC pending"}
                </span>
              </div>
              {wallet.is_frozen && (
                <div className="flex items-center gap-1.5 text-sm font-mono text-destructive">
                  <ArrowUpRight className="w-4 h-4 rotate-180" />
                  <span>Wallet frozen</span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Balance Grid ────────────────────────────── */}
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
          </div>
        ))}
      </div>

      {/* ── KYC Banner ──────────────────────────────── */}
      {!wallet.kyc_verified && (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-yellow-500/30 bg-yellow-500/5 px-5 py-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0" />
            <div>
              <div className="text-sm font-mono font-medium">Complete KYC Verification</div>
              <div className="text-xs font-mono text-muted-foreground">Required for withdrawals above daily limits</div>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="font-mono text-xs border-yellow-500/40 text-yellow-400 hover:bg-yellow-500/10 flex-shrink-0"
            onClick={() => submitKyc.mutate()}
            disabled={submitKyc.isPending}
          >
            {submitKyc.isPending ? "Verifying..." : "Verify Now"}
          </Button>
        </div>
      )}

      {/* ── Action Dialogs Row ───────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">

        {/* Deposit */}
        <Dialog>
          <DialogTrigger asChild>
            <Button className="h-12 font-mono gap-2 w-full">
              <ArrowDownLeft className="w-4 h-4" />
              Deposit
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="font-mono">Quick Deposit</DialogTitle>
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
                    {depositCurrency === "NGN" && (
                      <SelectItem value="paystack" className="font-mono">Paystack (NGN)</SelectItem>
                    )}
                    {(depositCurrency === "USD" || depositCurrency === "USDT") && (
                      <SelectItem value="stripe" className="font-mono">Stripe (USD/Card)</SelectItem>
                    )}
                    {(depositCurrency === "PI" || depositCurrency === "VITCoin") && (
                      <SelectItem value="manual" className="font-mono">Manual / On-chain</SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
              {depositAmount && parseFloat(depositAmount) > 0 && (
                <div className="rounded-lg bg-muted/30 border border-border/50 p-3 text-xs font-mono space-y-1">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Amount</span>
                    <span>{SYM[depositCurrency] ?? ""}{parseFloat(depositAmount).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>Processing fee (1%)</span>
                    <span>{SYM[depositCurrency] ?? ""}{(parseFloat(depositAmount) * 0.01).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-foreground border-t border-border/50 pt-1 mt-1">
                    <span>You receive</span>
                    <span className="text-primary">{SYM[depositCurrency] ?? ""}{(parseFloat(depositAmount) * 0.99).toFixed(2)}</span>
                  </div>
                </div>
              )}
              <Button
                className="w-full font-mono h-11 gap-2"
                onClick={handleDeposit}
                disabled={initiateDeposit.isPending}
              >
                {initiateDeposit.isPending ? "Processing..." : "Deposit Now"}
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Withdraw */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="h-12 font-mono gap-2 w-full border-border/60">
              <ArrowUpRight className="w-4 h-4" />
              Withdraw
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="font-mono">Withdraw Funds</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Currency</div>
                  <Select value={withdrawCurrency} onValueChange={setWithdrawCurrency}>
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
                    onChange={(e) => setWithdrawAmount(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
              </div>
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Destination Type</div>
                <Select value={withdrawDestType} onValueChange={setWithdrawDestType}>
                  <SelectTrigger className="font-mono"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bank_account" className="font-mono">Bank Account</SelectItem>
                    <SelectItem value="crypto_wallet" className="font-mono">Crypto Wallet</SelectItem>
                    <SelectItem value="mobile_money" className="font-mono">Mobile Money</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="text-xs font-mono text-muted-foreground uppercase mb-2">Destination Address</div>
                <Input
                  placeholder={withdrawDestType === "bank_account" ? "Account number" : "Wallet address"}
                  value={withdrawDest}
                  onChange={(e) => setWithdrawDest(e.target.value)}
                  className="font-mono text-sm"
                />
              </div>
              <Button
                variant="outline"
                className="w-full font-mono h-11 gap-2 border-destructive/30 text-destructive hover:bg-destructive/10"
                onClick={handleWithdraw}
                disabled={withdraw.isPending || !wallet.kyc_verified}
              >
                {withdraw.isPending ? "Processing..." : !wallet.kyc_verified ? "KYC Required" : "Request Withdrawal"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Convert */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="h-12 font-mono gap-2 w-full border-border/60">
              <RefreshCcw className="w-4 h-4" />
              Convert
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="font-mono">Convert Currency</DialogTitle>
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
                <div className="w-8 h-8 rounded-full border border-border flex items-center justify-center">
                  <RefreshCcw className="w-4 h-4 text-muted-foreground" />
                </div>
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
              <div className="rounded-lg bg-muted/30 border border-border/50 p-3 text-xs font-mono text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>Conversion fee</span>
                  <span>0.5%</span>
                </div>
                {(convertFrom === "VITCoin" || convertTo === "VITCoin") && (
                  <div className="flex justify-between">
                    <span>VIT price</span>
                    <span className="text-secondary">${(vitPrice ?? 0).toFixed(4)} USD</span>
                  </div>
                )}
                {convertAmount && parseFloat(convertAmount) > 0 && (
                  <div className="flex justify-between border-t border-border/50 pt-1 mt-1 text-foreground">
                    <span>Est. received</span>
                    <span className="text-primary">
                      {(() => {
                        const amt = parseFloat(convertAmount);
                        const fee = amt * 0.005;
                        const net = amt - fee;
                        if (convertFrom === "VITCoin" && convertTo === "USD") return vitPrice ? `$${(net * vitPrice).toFixed(2)}` : "—";
                        if (convertFrom === "USD" && convertTo === "VITCoin") return vitPrice ? `VIT ${(net / vitPrice).toFixed(4)}` : "—";
                        if (convertFrom === "NGN" && convertTo === "USD") return ngnRate ? `$${(net / ngnRate).toFixed(2)}` : "—";
                        if (convertFrom === "USD" && convertTo === "NGN") return ngnRate ? `₦${(net * ngnRate).toFixed(2)}` : "—";
                        return `~${net.toFixed(4)}`;
                      })()}
                    </span>
                  </div>
                )}
              </div>
              <Button
                className="w-full font-mono h-11"
                onClick={handleConvert}
                disabled={convert.isPending}
              >
                {convert.isPending ? "Converting..." : `Convert ${convertFrom} → ${convertTo}`}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* ── Transaction History ──────────────────────── */}
      <Card className="bg-card/50 backdrop-blur border-border">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle className="font-mono uppercase text-sm flex items-center gap-2">
              <Landmark className="w-4 h-4 text-muted-foreground" />
              Transaction History
            </CardTitle>
            <div className="flex gap-1 flex-wrap">
              {["all", "deposit", "withdrawal", "conversion"].map((f) => (
                <button
                  key={f}
                  onClick={() => setTxFilter(f)}
                  className={`text-[10px] font-mono px-2 py-1 rounded border transition-all capitalize ${
                    txFilter === f ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-border/80"
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
              {Array.from({ length: 4 }).map((_, i) => (
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
              <p className="text-sm font-mono text-muted-foreground">No transactions yet</p>
              <p className="text-xs font-mono text-muted-foreground/60 mt-1">Deposit funds to get started</p>
            </div>
          ) : (
            <div className="divide-y divide-border/30">
              {filteredTx.slice(0, 20).map((tx: any, i: number) => {
                const isDebit = tx.direction === "debit" || ["withdrawal", "conversion_out", "stake"].includes(tx.type ?? "");
                const icon = isDebit ? <ArrowUpRight className="w-4 h-4 text-destructive" /> : <ArrowDownLeft className="w-4 h-4 text-green-400" />;
                return (
                  <div key={tx.id ?? i} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/20 transition-colors">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${isDebit ? "bg-destructive/10" : "bg-green-500/10"}`}>
                      {icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-mono font-medium capitalize text-foreground">
                        {(tx.type ?? "transaction").replace(/_/g, " ")}
                      </div>
                      <div className="text-[10px] font-mono text-muted-foreground">
                        {tx.created_at ? format(new Date(tx.created_at), "MMM d, HH:mm") : "–"}
                        {tx.status && <span className="ml-2">{tx.status}</span>}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className={`text-sm font-bold font-mono ${isDebit ? "text-destructive" : "text-green-400"}`}>
                        {isDebit ? "-" : "+"}{SYM[tx.currency] ?? ""}{Number(tx.amount ?? 0).toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      </div>
                      <div className="text-[10px] font-mono text-muted-foreground">{tx.currency}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
