import React, { useState } from "react";
import { AmountInput } from "@/components/wallet/AmountInput";
import { CurrencySelector, type CurrencyOption } from "@/components/wallet/CurrencySelector";
import { useInitiateDeposit } from "@/hooks/useWallet";
import { toast } from "sonner";

const METHODS = [
  { value: "paystack", label: "Paystack", desc: "Card / Bank Transfer (NGN)", icon: "🏦" },
  { value: "momo", label: "Mobile Money", desc: "MTN, M-Pesa, Airtel", icon: "📱" },
  { value: "pi", label: "Pi Network", desc: "Pi Browser SDK", icon: "π" },
  { value: "crypto", label: "Crypto / USDT", desc: "On-chain wallet", icon: "🔗" },
];

export function WalletDeposit() {
  const [currency, setCurrency] = useState<CurrencyOption>("NGN");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("paystack");
  const { mutate: initiate, isPending } = useInitiateDeposit();
  const [result, setResult] = useState<{ payment_link: string; reference: string } | null>(null);

  const handleDeposit = () => {
    const n = parseFloat(amount);
    if (!n || n <= 0) { toast.error("Enter a valid amount"); return; }
    initiate(
      { currency, amount: n, method },
      {
        onSuccess: (data: any) => {
          setResult(data);
          if (data.payment_link && method === "paystack") {
            window.open(data.payment_link, "_blank");
          }
        },
      }
    );
  };

  return (
    <div className="max-w-md mx-auto flex flex-col gap-5">
      <div>
        <h2 className="font-['Barlow_Condensed'] text-2xl font-bold uppercase text-white">Deposit Funds</h2>
        <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">Add money to your VIT wallet</p>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4">
        <CurrencySelector value={currency} onChange={setCurrency} label="Currency" />
        <AmountInput
          value={amount}
          onChange={setAmount}
          label="Amount"
          suffix={currency}
          placeholder="0.00"
        />

        <div className="flex flex-col gap-2">
          <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Payment Method</label>
          {METHODS.filter((m) => {
            if (currency === "PI") return m.value === "pi";
            if (currency === "USDT") return m.value === "crypto";
            if (["KES", "GHS", "UGX"].includes(currency)) return m.value === "momo";
            return m.value === "paystack" || m.value === "momo";
          }).map((m) => (
            <label
              key={m.value}
              className={`
                flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition-all
                ${method === m.value ? "border-[#00E676]/40 bg-[#00E676]/5" : "border-white/[0.06] bg-transparent hover:border-white/20"}
              `}
            >
              <input
                type="radio"
                name="method"
                value={m.value}
                checked={method === m.value}
                onChange={() => setMethod(m.value)}
                className="sr-only"
              />
              <span className="text-lg">{m.icon}</span>
              <div>
                <p className="text-sm font-['Outfit'] text-white">{m.label}</p>
                <p className="text-[10px] text-white/30 font-['Outfit']">{m.desc}</p>
              </div>
              {method === m.value && (
                <span className="ml-auto text-[#00E676] text-xs">✓</span>
              )}
            </label>
          ))}
        </div>

        <button
          onClick={handleDeposit}
          disabled={isPending || !amount}
          className="w-full py-3 rounded-lg bg-[#00E676] text-[#080c12] font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-[#00E676]/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isPending ? "Processing…" : "Initiate Deposit"}
        </button>

        {result && (
          <div className="rounded-lg border border-[#00E676]/20 bg-[#00E676]/5 p-4 flex flex-col gap-2">
            <p className="text-xs text-[#00E676] font-['Outfit'] font-medium">Deposit Initiated</p>
            <p className="text-[10px] text-white/50 font-['JetBrains_Mono']">Ref: {result.reference}</p>
            {result.payment_link && (
              <a
                href={result.payment_link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#00E676] underline font-['Outfit']"
              >
                Open Payment Page →
              </a>
            )}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/[0.04] bg-white/[0.01] p-4">
        <p className="text-[10px] text-white/30 font-['Outfit']">
          Deposits are credited automatically after confirmation. NGN deposits via Paystack are instant.
          Crypto deposits require 3+ confirmations. Pi Network deposits are credited after webhook confirmation.
        </p>
      </div>
    </div>
  );
}
