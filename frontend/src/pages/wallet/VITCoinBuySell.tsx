import React, { useState } from "react";
import { AmountInput } from "@/components/wallet/AmountInput";
import { PriceChart } from "@/components/wallet/PriceChart";
import { useBuyVITCoin, useSellVITCoin, useVITPrice, useVITPriceHistory, useWalletOverview } from "@/hooks/useWallet";
import { toast } from "sonner";

type Tab = "buy" | "sell";
type Days = 7 | 30 | 90;

function FeeRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs font-['Outfit']">
      <span className="text-white/30">{label}</span>
      <span className="text-white/70 font-['JetBrains_Mono']">{value}</span>
    </div>
  );
}

export function VITCoinBuySell() {
  const [tab, setTab] = useState<Tab>("buy");
  const [ngnAmount, setNgnAmount] = useState("");
  const [vitAmount, setVitAmount] = useState("");
  const [historyDays, setHistoryDays] = useState<Days>(7);

  const { data: wallet } = useWalletOverview();
  const { data: price } = useVITPrice();
  const { data: history } = useVITPriceHistory(historyDays);
  const { mutate: buy, isPending: buying } = useBuyVITCoin();
  const { mutate: sell, isPending: selling } = useSellVITCoin();

  const priceUsd = price?.price_usd ?? 0.1;
  const priceNgn = price?.price_ngn ?? 158;
  const FEE_PCT = 1.5;

  const ngn = parseFloat(ngnAmount) || 0;
  const vit = parseFloat(vitAmount) || 0;
  const estimatedVIT = ngn > 0 ? (ngn / priceNgn) * (1 - FEE_PCT / 100) : 0;
  const estimatedNGN = vit > 0 ? vit * priceNgn * (1 - FEE_PCT / 100) : 0;
  const feeNgn = ngn * FEE_PCT / 100;
  const feeNgnSell = vit * priceNgn * FEE_PCT / 100;

  const priceData = history?.history.map((h) => h.price_usd) ?? [];
  const change = price?.change_24h_pct ?? 0;
  const isUp = change >= 0;

  const handleBuy = () => {
    if (!ngn || ngn <= 0) { toast.error("Enter NGN amount"); return; }
    if (ngn > (wallet?.ngn_balance ?? 0)) { toast.error("Insufficient NGN balance"); return; }
    buy({ amount_ngn: ngn });
    setNgnAmount("");
  };

  const handleSell = () => {
    if (!vit || vit <= 0) { toast.error("Enter VITCoin amount"); return; }
    if (vit > (wallet?.vitcoin_balance ?? 0)) { toast.error("Insufficient VITCoin balance"); return; }
    sell(vit);
    setVitAmount("");
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
        <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-white/30 font-['Outfit']">VITCoin Price</p>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="font-['JetBrains_Mono'] text-2xl font-black text-white">
                ${priceUsd.toFixed(4)}
              </span>
              <span className={`text-xs px-1.5 py-0.5 rounded font-['Outfit'] font-medium ${isUp ? "bg-[#00E676]/10 text-[#00E676]" : "bg-red-500/10 text-red-400"}`}>
                {isUp ? "+" : ""}{change.toFixed(2)}%
              </span>
            </div>
            <p className="text-xs text-white/30 font-['JetBrains_Mono'] mt-0.5">₦{priceNgn.toFixed(2)}</p>
          </div>

          <div className="flex gap-1">
            {([7, 30, 90] as Days[]).map((d) => (
              <button
                key={d}
                onClick={() => setHistoryDays(d)}
                className={`px-2 py-1 rounded text-[9px] font-['Outfit'] uppercase tracking-wide transition-colors ${historyDays === d ? "bg-[#00E676]/10 text-[#00E676]" : "text-white/30 hover:text-white/60"}`}
              >
                {d}D
              </button>
            ))}
          </div>
        </div>

        <PriceChart data={priceData} height={72} showLabels />

        <div className="grid grid-cols-3 gap-3 mt-4 text-center">
          <div>
            <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">Mkt Cap</p>
            <p className="text-xs font-['JetBrains_Mono'] text-white/70">
              ${((price?.market_cap_usd ?? 0) / 1e6).toFixed(2)}M
            </p>
          </div>
          <div>
            <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">Supply</p>
            <p className="text-xs font-['JetBrains_Mono'] text-white/70">
              {((price?.circulating_supply ?? 0) / 1e6).toFixed(2)}M
            </p>
          </div>
          <div>
            <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">USDT</p>
            <p className="text-xs font-['JetBrains_Mono'] text-white/70">
              ${(price?.price_usdt ?? 0.1).toFixed(4)}
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4">
        <div className="flex gap-1 p-1 rounded-lg bg-white/[0.04]">
          {(["buy", "sell"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2 rounded-md text-xs font-['Barlow_Condensed'] font-bold uppercase tracking-wide transition-all ${
                tab === t
                  ? t === "buy"
                    ? "bg-[#00E676] text-[#080c12]"
                    : "bg-red-500 text-white"
                  : "text-white/40 hover:text-white/70"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "buy" ? (
          <>
            <AmountInput
              value={ngnAmount}
              onChange={setNgnAmount}
              label="Pay (NGN)"
              suffix="₦"
              max={wallet?.ngn_balance}
              hint={`Balance: ₦${(wallet?.ngn_balance ?? 0).toLocaleString("en", { minimumFractionDigits: 2 })}`}
            />
            <div className="flex flex-col gap-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
              <FeeRow label="Rate" value={`₦${priceNgn.toFixed(2)} / VIT`} />
              <FeeRow label="Fee (1.5%)" value={`₦${feeNgn.toFixed(2)}`} />
              <div className="border-t border-white/[0.06] pt-1.5 flex justify-between text-sm font-medium">
                <span className="text-white/50 font-['Outfit']">You receive</span>
                <span className="font-['JetBrains_Mono'] text-[#00E676]">
                  {estimatedVIT.toLocaleString("en", { minimumFractionDigits: 4, maximumFractionDigits: 6 })} VIT
                </span>
              </div>
            </div>
            <button
              onClick={handleBuy}
              disabled={buying || !ngnAmount}
              className="w-full py-3 rounded-lg bg-[#00E676] text-[#080c12] font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-[#00E676]/90 transition-colors disabled:opacity-40"
            >
              {buying ? "Processing…" : "Buy VITCoin"}
            </button>
          </>
        ) : (
          <>
            <AmountInput
              value={vitAmount}
              onChange={setVitAmount}
              label="Sell VITCoin"
              suffix="VIT"
              max={wallet?.vitcoin_balance}
              hint={`Balance: ${(wallet?.vitcoin_balance ?? 0).toLocaleString("en", { maximumFractionDigits: 4 })} VIT`}
            />
            <div className="flex flex-col gap-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
              <FeeRow label="Rate" value={`₦${priceNgn.toFixed(2)} / VIT`} />
              <FeeRow label="Fee (1.5%)" value={`₦${feeNgnSell.toFixed(2)}`} />
              <div className="border-t border-white/[0.06] pt-1.5 flex justify-between text-sm font-medium">
                <span className="text-white/50 font-['Outfit']">You receive</span>
                <span className="font-['JetBrains_Mono'] text-[#00E676]">
                  ₦{estimatedNGN.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>
            <button
              onClick={handleSell}
              disabled={selling || !vitAmount}
              className="w-full py-3 rounded-lg bg-red-500 text-white font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-red-500/90 transition-colors disabled:opacity-40"
            >
              {selling ? "Processing…" : "Sell VITCoin"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
