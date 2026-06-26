import React, { useState } from "react";
import { AmountInput } from "@/components/wallet/AmountInput";
import { CurrencySelector, type CurrencyOption } from "@/components/wallet/CurrencySelector";
import { useWithdraw, useWalletOverview, useTransactions } from "@/hooks/useWallet";
import { TransactionRow } from "@/components/wallet/TransactionRow";
import { toast } from "sonner";

export function WalletWithdraw() {
  const [currency, setCurrency] = useState<CurrencyOption>("NGN");
  const [amount, setAmount] = useState("");
  const [bankCode, setBankCode] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [accountName, setAccountName] = useState("");
  const [destinationType, setDestinationType] = useState("bank_account");
  const [destAddress, setDestAddress] = useState("");

  const { data: wallet } = useWalletOverview();
  const { data: txs } = useTransactions(1);
  const { mutate: withdraw, isPending } = useWithdraw();

  const BALANCE_MAP: Record<string, number> = {
    NGN: wallet?.ngn_balance ?? 0,
    USD: wallet?.usd_balance ?? 0,
    USDT: wallet?.usdt_balance ?? 0,
    PI: wallet?.pi_balance ?? 0,
    VITCoin: wallet?.vitcoin_balance ?? 0,
  };
  const maxBalance = BALANCE_MAP[currency] ?? 0;

  const handleWithdraw = () => {
    const n = parseFloat(amount);
    if (!n || n <= 0) { toast.error("Enter a valid amount"); return; }
    if (n > maxBalance) { toast.error("Insufficient balance"); return; }

    const isBank = destinationType === "bank_account";
    if (isBank && (!bankCode || !accountNumber)) {
      toast.error("Bank code and account number are required");
      return;
    }
    if (!isBank && !destAddress) {
      toast.error("Destination address is required");
      return;
    }

    withdraw({
      amount: n,
      currency,
      bank_code: isBank ? bankCode : undefined,
      account_number: isBank ? accountNumber : undefined,
      account_name: isBank ? accountName : undefined,
      destination_type: destinationType,
    });
  };

  return (
    <div className="max-w-md mx-auto flex flex-col gap-5">
      <div>
        <h2 className="font-['Barlow_Condensed'] text-2xl font-bold uppercase text-white">Withdraw</h2>
        <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">Send funds to your bank or wallet</p>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4">
        <CurrencySelector value={currency} onChange={setCurrency} label="Currency" />
        <AmountInput
          value={amount}
          onChange={setAmount}
          label="Amount"
          suffix={currency}
          max={maxBalance}
          hint={`Available: ${maxBalance.toLocaleString("en", { maximumFractionDigits: 6 })} ${currency}`}
        />

        <div className="flex flex-col gap-1">
          <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Destination Type</label>
          <select
            value={destinationType}
            onChange={(e) => setDestinationType(e.target.value)}
            className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white font-['Outfit'] outline-none focus:border-[#00E676]/40"
          >
            <option value="bank_account">Bank Account (NGN)</option>
            <option value="usdt_address">USDT Wallet Address</option>
            <option value="pi_wallet">Pi Network Wallet</option>
            <option value="paypal">PayPal</option>
          </select>
        </div>

        {destinationType === "bank_account" ? (
          <>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Bank Code</label>
              <input
                value={bankCode}
                onChange={(e) => setBankCode(e.target.value)}
                placeholder="e.g. 058"
                className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white font-['JetBrains_Mono'] outline-none focus:border-[#00E676]/40 placeholder:text-white/20"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Account Number</label>
              <input
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder="10-digit account number"
                maxLength={10}
                className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white font-['JetBrains_Mono'] outline-none focus:border-[#00E676]/40 placeholder:text-white/20"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Account Name</label>
              <input
                value={accountName}
                onChange={(e) => setAccountName(e.target.value)}
                placeholder="Account holder name"
                className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white font-['Outfit'] outline-none focus:border-[#00E676]/40 placeholder:text-white/20"
              />
            </div>
          </>
        ) : (
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Destination Address</label>
            <input
              value={destAddress}
              onChange={(e) => setDestAddress(e.target.value)}
              placeholder="Enter destination address"
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white font-['JetBrains_Mono'] outline-none focus:border-[#00E676]/40 placeholder:text-white/20"
            />
          </div>
        )}

        <button
          onClick={handleWithdraw}
          disabled={isPending || !amount}
          className="w-full py-3 rounded-lg bg-white/[0.08] text-white font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-white/[0.12] transition-colors disabled:opacity-40 disabled:cursor-not-allowed border border-white/[0.12]"
        >
          {isPending ? "Submitting…" : "Request Withdrawal"}
        </button>
      </div>

      {!wallet?.kyc_verified && (
        <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-4 text-xs text-yellow-400 font-['Outfit']">
          ⚠ KYC required for withdrawals above ₦50,000. Complete verification in{" "}
          <a href="/kyc" className="underline">Settings → KYC</a>.
        </div>
      )}

      {txs && txs.transactions.filter((t) => t.type === "withdrawal").length > 0 && (
        <div>
          <h3 className="text-sm text-white/60 font-['Outfit'] uppercase tracking-widest mb-2">Recent Withdrawals</h3>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-2">
            {txs.transactions.filter((t) => t.type === "withdrawal").slice(0, 3).map((tx) => (
              <TransactionRow key={tx.id} tx={tx} compact />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
