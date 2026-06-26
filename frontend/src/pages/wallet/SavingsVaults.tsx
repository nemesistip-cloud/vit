import React, { useState } from "react";
import { AmountInput } from "@/components/wallet/AmountInput";
import { CurrencySelector, type CurrencyOption } from "@/components/wallet/CurrencySelector";
import { useVaults, useCreateVault, useWithdrawVault, useWalletOverview } from "@/hooks/useWallet";
import type { SavingsVault } from "@/hooks/useWallet";
import { toast } from "sonner";

const LOCK_TIERS = [
  { days: 30, apy: "5%", label: "1 Month" },
  { days: 90, apy: "8%", label: "3 Months" },
  { days: 180, apy: "12%", label: "6 Months" },
  { days: 365, apy: "18%", label: "1 Year" },
] as const;

function VaultCard({ vault, onWithdraw }: { vault: SavingsVault; onWithdraw: (id: string) => void }) {
  const lockedUntil = vault.locked_until ? new Date(vault.locked_until) : null;
  const now = new Date();
  const isUnlocked = !lockedUntil || lockedUntil <= now;
  const daysLeft = lockedUntil ? Math.max(0, Math.ceil((lockedUntil.getTime() - now.getTime()) / 86400000)) : 0;

  return (
    <div className={`rounded-xl border p-4 flex flex-col gap-3 transition-all ${isUnlocked ? "border-[#00E676]/30 bg-[#00E676]/5" : "border-white/[0.06] bg-white/[0.02]"}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-['Outfit'] text-white font-medium">{vault.name}</p>
          <p className="text-[10px] text-white/30 font-['Outfit'] mt-0.5">{vault.lock_period_days}d lock · {vault.apy_pct}% APY</p>
        </div>
        <span className={`text-[9px] px-2 py-0.5 rounded-full font-['Outfit'] uppercase tracking-wide ${isUnlocked ? "bg-[#00E676]/10 text-[#00E676]" : "bg-white/[0.08] text-white/40"}`}>
          {isUnlocked ? "Unlocked" : `${daysLeft}d left`}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div>
          <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">Balance</p>
          <p className="font-['JetBrains_Mono'] text-sm text-white">{vault.amount.toFixed(4)}</p>
          <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">{vault.currency}</p>
        </div>
        <div>
          <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">Yield</p>
          <p className="font-['JetBrains_Mono'] text-sm text-[#00E676]">+{vault.projected_yield.toFixed(6)}</p>
          <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">{vault.currency}</p>
        </div>
        <div>
          <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">APY</p>
          <p className="font-['JetBrains_Mono'] text-sm text-white">{vault.apy_pct}%</p>
        </div>
      </div>

      {lockedUntil && (
        <p className="text-[9px] text-white/20 font-['Outfit']">
          {isUnlocked ? "Matured" : `Unlocks`} {lockedUntil.toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" })}
        </p>
      )}

      {isUnlocked && (
        <button
          onClick={() => onWithdraw(vault.id)}
          className="w-full py-2 rounded-lg bg-[#00E676] text-[#080c12] font-['Barlow_Condensed'] font-bold uppercase tracking-wide text-sm hover:bg-[#00E676]/90 transition-colors"
        >
          Withdraw + Yield
        </button>
      )}
    </div>
  );
}

export function SavingsVaults() {
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState<CurrencyOption>("VITCoin");
  const [lockDays, setLockDays] = useState<30 | 90 | 180 | 365>(90);

  const { data: vaultsData, isLoading } = useVaults();
  const { data: wallet } = useWalletOverview();
  const { mutate: createVault, isPending: creating } = useCreateVault();
  const { mutate: withdrawVault, isPending: withdrawing } = useWithdrawVault();

  const BALANCE_MAP: Record<string, number> = {
    VITCoin: wallet?.vitcoin_balance ?? 0,
    NGN: wallet?.ngn_balance ?? 0,
    USDT: wallet?.usdt_balance ?? 0,
    USD: wallet?.usd_balance ?? 0,
    PI: wallet?.pi_balance ?? 0,
  };
  const maxBalance = BALANCE_MAP[currency] ?? 0;
  const selectedTier = LOCK_TIERS.find((t) => t.days === lockDays)!;
  const n = parseFloat(amount) || 0;
  const estimatedYield = n * parseFloat(selectedTier.apy) / 100 * lockDays / 365;

  const handleCreate = () => {
    if (!n || n <= 0) { toast.error("Enter an amount"); return; }
    if (n > maxBalance) { toast.error("Insufficient balance"); return; }
    createVault({ amount: n, currency, lock_period_days: lockDays }, {
      onSuccess: () => setAmount(""),
    });
  };

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="font-['Barlow_Condensed'] text-2xl font-bold uppercase text-white">Savings Vaults</h2>
        <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">Lock funds and earn guaranteed yield</p>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4">
        <h3 className="text-sm font-['Outfit'] font-medium text-white/70 uppercase tracking-wide">Create New Vault</h3>

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
          <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Lock Period</label>
          <div className="grid grid-cols-4 gap-2">
            {LOCK_TIERS.map((tier) => (
              <button
                key={tier.days}
                onClick={() => setLockDays(tier.days)}
                className={`rounded-lg border p-2 text-center transition-all ${
                  lockDays === tier.days
                    ? "border-[#8B5CF6]/50 bg-[#8B5CF6]/10 text-[#8B5CF6]"
                    : "border-white/[0.06] text-white/40 hover:border-white/20"
                }`}
              >
                <p className="text-xs font-['Outfit'] font-medium">{tier.label}</p>
                <p className="font-['JetBrains_Mono'] text-sm font-bold mt-0.5">{tier.apy}</p>
                <p className="text-[8px] text-white/30 font-['Outfit'] uppercase">APY</p>
              </button>
            ))}
          </div>
        </div>

        {n > 0 && (
          <div className="flex flex-col gap-1 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <div className="flex justify-between text-xs font-['Outfit']">
              <span className="text-white/30">Projected Yield</span>
              <span className="text-[#00E676] font-['JetBrains_Mono']">
                +{estimatedYield.toFixed(6)} {currency}
              </span>
            </div>
            <div className="flex justify-between text-xs font-['Outfit']">
              <span className="text-white/30">Total at Maturity</span>
              <span className="text-white font-['JetBrains_Mono']">
                {(n + estimatedYield).toFixed(6)} {currency}
              </span>
            </div>
            <div className="flex justify-between text-xs font-['Outfit']">
              <span className="text-white/30">Unlocks</span>
              <span className="text-white/50 font-['JetBrains_Mono']">
                {new Date(Date.now() + lockDays * 86400000).toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" })}
              </span>
            </div>
          </div>
        )}

        <button
          onClick={handleCreate}
          disabled={creating || !amount || n <= 0}
          className="w-full py-3 rounded-lg bg-[#8B5CF6] text-white font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-[#8B5CF6]/90 transition-colors disabled:opacity-40"
        >
          {creating ? "Creating Vault…" : `Lock ${currency} for ${selectedTier.apy} APY`}
        </button>
      </div>

      <div>
        <h3 className="text-sm text-white/60 font-['Outfit'] uppercase tracking-widest mb-3">Active Vaults</h3>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="w-6 h-6 border-2 border-[#8B5CF6]/20 border-t-[#8B5CF6] rounded-full animate-spin" />
          </div>
        ) : !vaultsData?.vaults.length ? (
          <div className="rounded-xl border border-white/[0.04] bg-white/[0.01] p-8 text-center">
            <p className="text-sm text-white/20 font-['Outfit']">No active vaults</p>
            <p className="text-[10px] text-white/10 font-['Outfit'] mt-1">Create your first vault to start earning yield</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {vaultsData.vaults.map((vault) => (
              <VaultCard key={vault.id} vault={vault} onWithdraw={withdrawVault} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
