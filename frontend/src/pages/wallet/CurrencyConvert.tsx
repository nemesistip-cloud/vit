import React, { useState, useEffect } from "react";
import { AmountInput } from "@/components/wallet/AmountInput";
import { CurrencySelector, type CurrencyOption } from "@/components/wallet/CurrencySelector";
import { useConvertCurrency, useConversionQuote, useWalletOverview } from "@/hooks/useWallet";
import { toast } from "sonner";

export function CurrencyConvert() {
  const [from, setFrom] = useState<CurrencyOption>("NGN");
  const [to, setTo] = useState<CurrencyOption>("VITCoin");
  const [amount, setAmount] = useState("");

  const { data: wallet } = useWalletOverview();
  const { mutate: convert, isPending } = useConvertCurrency();

  const n = parseFloat(amount) || 0;
  const { data: quote } = useConversionQuote(from, to, n);

  const BALANCE_MAP: Record<string, number> = {
    NGN: wallet?.ngn_balance ?? 0,
    USD: wallet?.usd_balance ?? 0,
    USDT: wallet?.usdt_balance ?? 0,
    PI: wallet?.pi_balance ?? 0,
    VITCoin: wallet?.vitcoin_balance ?? 0,
  };
  const maxBalance = BALANCE_MAP[from] ?? 0;

  const swap = () => {
    setFrom(to);
    setTo(from);
    setAmount("");
  };

  const handleConvert = () => {
    if (!n || n <= 0) { toast.error("Enter a valid amount"); return; }
    if (n > maxBalance) { toast.error("Insufficient balance"); return; }
    if (from === to) { toast.error("Select different currencies"); return; }
    convert({ from_currency: from, to_currency: to, amount: n });
    setAmount("");
  };

  return (
    <div className="max-w-md mx-auto flex flex-col gap-5">
      <div>
        <h2 className="font-['Barlow_Condensed'] text-2xl font-bold uppercase text-white">Convert</h2>
        <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">Swap between currencies instantly</p>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4">
        <CurrencySelector
          value={from}
          onChange={(v) => { setFrom(v); if (v === to) setTo(from); }}
          label="From"
        />

        <AmountInput
          value={amount}
          onChange={setAmount}
          label="Amount"
          suffix={from}
          max={maxBalance}
          hint={`Balance: ${maxBalance.toLocaleString("en", { maximumFractionDigits: 6 })} ${from}`}
        />

        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-white/[0.06]" />
          <button
            onClick={swap}
            className="w-9 h-9 rounded-full border border-white/[0.08] bg-white/[0.03] flex items-center justify-center text-white/40 hover:text-[#00E676] hover:border-[#00E676]/30 transition-all"
          >
            ⇅
          </button>
          <div className="flex-1 h-px bg-white/[0.06]" />
        </div>

        <CurrencySelector
          value={to}
          onChange={(v) => { setTo(v); if (v === from) setFrom(to); }}
          label="To"
        />

        {quote && n > 0 && (
          <div className="flex flex-col gap-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <div className="flex justify-between text-xs font-['Outfit']">
              <span className="text-white/30">You receive</span>
              <span className="text-[#00E676] font-['JetBrains_Mono'] font-medium">
                {quote.received_amount.toLocaleString("en", { minimumFractionDigits: 4, maximumFractionDigits: 8 })} {to}
              </span>
            </div>
            <div className="flex justify-between text-xs font-['Outfit']">
              <span className="text-white/30">Fee ({quote.fee_pct}%)</span>
              <span className="text-white/50 font-['JetBrains_Mono']">
                {quote.fee.toLocaleString("en", { minimumFractionDigits: 4, maximumFractionDigits: 8 })} {from}
              </span>
            </div>
            <div className="flex justify-between text-xs font-['Outfit']">
              <span className="text-white/30">Rate</span>
              <span className="text-white/50 font-['JetBrains_Mono']">
                1 {from} = {quote.rate.toFixed(6)} USD
              </span>
            </div>
            <p className="text-[9px] text-white/20 font-['Outfit']">Rate expires in 30 seconds</p>
          </div>
        )}

        <button
          onClick={handleConvert}
          disabled={isPending || !amount || n <= 0 || from === to}
          className="w-full py-3 rounded-lg bg-[#8B5CF6] text-white font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-[#8B5CF6]/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isPending ? "Converting…" : `Convert ${from} → ${to}`}
        </button>
      </div>

      <div className="rounded-xl border border-white/[0.04] bg-white/[0.01] p-4 text-[10px] text-white/30 font-['Outfit']">
        Conversions are instant and final. A {1.5}% platform fee applies. Rates update every 30 seconds.
      </div>
    </div>
  );
}
