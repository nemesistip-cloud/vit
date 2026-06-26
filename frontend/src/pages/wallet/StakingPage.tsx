import React, { useState } from "react";
import { AmountInput } from "@/components/wallet/AmountInput";
import { useStakeVITCoin, useUnstakeVITCoin, useStakeStatus, useWalletOverview } from "@/hooks/useWallet";
import { toast } from "sonner";

function StatCard({ label, value, sub, green }: { label: string; value: string; sub?: string; green?: boolean }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
      <p className="text-[9px] uppercase tracking-widest text-white/30 font-['Outfit']">{label}</p>
      <p className={`font-['JetBrains_Mono'] text-xl font-bold mt-1 ${green ? "text-[#00E676]" : "text-white"}`}>
        {value}
      </p>
      {sub && <p className="text-[10px] text-white/20 font-['Outfit'] mt-0.5">{sub}</p>}
    </div>
  );
}

export function StakingPage() {
  const [stakeAmount, setStakeAmount] = useState("");
  const [unstakeAmount, setUnstakeAmount] = useState("");
  const [tab, setTab] = useState<"stake" | "unstake">("stake");

  const { data: wallet } = useWalletOverview();
  const { data: stakeStatus } = useStakeStatus();
  const { mutate: stake, isPending: staking } = useStakeVITCoin();
  const { mutate: unstake, isPending: unstaking } = useUnstakeVITCoin();

  const handleStake = () => {
    const n = parseFloat(stakeAmount);
    if (!n || n < 10) { toast.error("Minimum stake is 10 VITCoin"); return; }
    if (n > (wallet?.vitcoin_balance ?? 0)) { toast.error("Insufficient VITCoin balance"); return; }
    stake(n, { onSuccess: () => setStakeAmount("") });
  };

  const handleUnstake = () => {
    const n = parseFloat(unstakeAmount);
    if (!n || n <= 0) { toast.error("Enter a valid amount"); return; }
    if (n > (stakeStatus?.staked_amount ?? 0)) { toast.error("Insufficient staked balance"); return; }
    unstake(n, { onSuccess: () => setUnstakeAmount("") });
  };

  const apy = stakeStatus?.apy_pct ?? 8;
  const staked = stakeStatus?.staked_amount ?? 0;
  const daily = stakeStatus?.estimated_daily_reward ?? 0;
  const annual = staked * apy / 100;

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="font-['Barlow_Condensed'] text-2xl font-bold uppercase text-white">VITCoin Staking</h2>
        <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">Stake VIT to earn rewards and unlock validator eligibility</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Staked" value={`${staked.toLocaleString("en", { maximumFractionDigits: 4 })} VIT`} green={staked > 0} />
        <StatCard label="APY" value={`${apy}%`} green />
        <StatCard label="Daily Reward" value={`${daily.toFixed(6)} VIT`} />
        <StatCard
          label="Validator Eligible"
          value={stakeStatus?.validator_eligible ? "YES" : "NO"}
          sub={stakeStatus?.validator_eligible ? undefined : "Stake 100+ VIT"}
          green={stakeStatus?.validator_eligible}
        />
      </div>

      {staked > 0 && (
        <div className="rounded-xl border border-[#00E676]/20 bg-[#00E676]/5 p-4">
          <div className="flex items-start justify-between flex-wrap gap-2">
            <div>
              <p className="text-xs text-[#00E676] font-['Outfit'] font-medium">Projected Annual Earnings</p>
              <p className="font-['JetBrains_Mono'] text-2xl font-black text-[#00E676] mt-1">
                {annual.toLocaleString("en", { minimumFractionDigits: 4, maximumFractionDigits: 4 })} VIT
              </p>
            </div>
            <div className="text-right">
              <p className="text-[9px] text-white/30 font-['Outfit'] uppercase tracking-widest">Est. USD Value</p>
              <p className="font-['JetBrains_Mono'] text-sm text-white/60">
                ≈ ${(annual * 0.10).toFixed(2)}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4">
        <div className="flex gap-1 p-1 rounded-lg bg-white/[0.04]">
          {(["stake", "unstake"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2 rounded-md text-xs font-['Barlow_Condensed'] font-bold uppercase tracking-wide transition-all ${
                tab === t ? "bg-[#00E676] text-[#080c12]" : "text-white/40 hover:text-white/70"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "stake" ? (
          <>
            <AmountInput
              value={stakeAmount}
              onChange={setStakeAmount}
              label="Amount to Stake"
              suffix="VIT"
              max={wallet?.vitcoin_balance}
              hint={`Available: ${(wallet?.vitcoin_balance ?? 0).toLocaleString("en", { maximumFractionDigits: 4 })} VIT · Min: 10 VIT`}
            />
            {stakeAmount && parseFloat(stakeAmount) > 0 && (
              <div className="text-xs text-white/40 font-['Outfit']">
                Projected daily reward:{" "}
                <span className="text-[#00E676] font-['JetBrains_Mono']">
                  +{((parseFloat(stakeAmount) * apy) / 365 / 100).toFixed(6)} VIT
                </span>
              </div>
            )}
            <button
              onClick={handleStake}
              disabled={staking || !stakeAmount}
              className="w-full py-3 rounded-lg bg-[#00E676] text-[#080c12] font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-[#00E676]/90 transition-colors disabled:opacity-40"
            >
              {staking ? "Staking…" : "Stake VITCoin"}
            </button>
          </>
        ) : (
          <>
            <AmountInput
              value={unstakeAmount}
              onChange={setUnstakeAmount}
              label="Amount to Unstake"
              suffix="VIT"
              max={stakeStatus?.staked_amount}
              hint={`Staked: ${staked.toLocaleString("en", { maximumFractionDigits: 4 })} VIT`}
            />
            <button
              onClick={handleUnstake}
              disabled={unstaking || !unstakeAmount || staked === 0}
              className="w-full py-3 rounded-lg bg-white/[0.08] text-white font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-white/[0.12] transition-colors disabled:opacity-40 border border-white/[0.12]"
            >
              {unstaking ? "Unstaking…" : "Unstake VITCoin"}
            </button>
          </>
        )}
      </div>

      <div className="rounded-xl border border-white/[0.04] bg-white/[0.01] p-4 text-[10px] text-white/25 font-['Outfit'] leading-relaxed">
        Staking rewards are estimated at {apy}% APY. Rewards accrue continuously and are credited to your VITCoin balance.
        Staking 100+ VIT makes you eligible to apply as a VIT Network validator and earn additional block rewards.
        Unstaking is instant — no lock-up period for standard staking.
      </div>
    </div>
  );
}
