import React, { useState } from "react";
import { AmountInput } from "@/components/wallet/AmountInput";
import { useBridgeLock, useBridgeUnlock, useBridgeTxHistory, useWalletOverview } from "@/hooks/useWallet";
import type { BridgeTx } from "@/hooks/useWallet";
import { toast } from "sonner";

type Tab = "lock" | "unlock" | "history";

function BridgeTxRow({ tx }: { tx: BridgeTx }) {
  const statusColor: Record<string, string> = {
    locked: "text-yellow-400",
    pending: "text-yellow-400",
    completed: "text-[#00E676]",
    failed: "text-red-400",
  };
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/[0.04] last:border-0 gap-3">
      <div className="min-w-0">
        <p className="text-xs font-['JetBrains_Mono'] text-white truncate">{tx.tx_hash.slice(0, 18)}…</p>
        <p className="text-[9px] text-white/30 font-['Outfit'] capitalize">{tx.direction} · {new Date(tx.created_at).toLocaleDateString("en", { month: "short", day: "numeric" })}</p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-xs font-['JetBrains_Mono'] text-white">{parseFloat(tx.amount_in).toFixed(4)} VIT</p>
        <p className={`text-[9px] font-['Outfit'] ${statusColor[tx.status] ?? "text-white/40"}`}>{tx.status}</p>
      </div>
    </div>
  );
}

export function BridgePage() {
  const [tab, setTab] = useState<Tab>("lock");
  const [lockAmount, setLockAmount] = useState("");
  const [evmAddress, setEvmAddress] = useState("");
  const [unlockTxHash, setUnlockTxHash] = useState("");
  const [unlockAmount, setUnlockAmount] = useState("");

  const { data: wallet } = useWalletOverview();
  const { data: history } = useBridgeTxHistory();
  const { mutate: lock, isPending: locking } = useBridgeLock();
  const { mutate: unlock, isPending: unlocking } = useBridgeUnlock();

  const FEE_PCT = 1.0;
  const lockN = parseFloat(lockAmount) || 0;
  const fee = lockN * FEE_PCT / 100;
  const received = lockN - fee;

  const handleLock = () => {
    if (!lockN || lockN < 10) { toast.error("Minimum bridge amount is 10 VIT"); return; }
    if (lockN > (wallet?.vitcoin_balance ?? 0)) { toast.error("Insufficient VITCoin balance"); return; }
    if (!evmAddress.match(/^0x[0-9a-fA-F]{40}$/)) { toast.error("Invalid EVM address"); return; }
    lock({ amount: lockN, destination_address: evmAddress }, {
      onSuccess: () => { setLockAmount(""); setEvmAddress(""); },
    });
  };

  const handleUnlock = () => {
    if (!unlockTxHash || !unlockTxHash.startsWith("0x")) { toast.error("Invalid transaction hash"); return; }
    const n = parseFloat(unlockAmount);
    if (!n || n <= 0) { toast.error("Enter the amount"); return; }
    unlock({ tx_hash: unlockTxHash, amount: n }, {
      onSuccess: () => { setUnlockTxHash(""); setUnlockAmount(""); },
    });
  };

  const txArr = Array.isArray(history) ? history : [];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="font-['Barlow_Condensed'] text-2xl font-bold uppercase text-white">Bridge</h2>
        <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">VITCoin ↔ ERC-20 on Base L2</p>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 flex items-center gap-3">
        <div className="flex-1 text-center">
          <p className="text-[9px] text-white/30 font-['Outfit'] uppercase tracking-widest">VIT Network</p>
          <p className="text-xs font-['Outfit'] text-white mt-0.5">VITCoin</p>
        </div>
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-white/30 text-sm">⇌</span>
          <p className="text-[8px] text-white/20 font-['JetBrains_Mono']">1% fee</p>
        </div>
        <div className="flex-1 text-center">
          <p className="text-[9px] text-white/30 font-['Outfit'] uppercase tracking-widest">Base L2</p>
          <p className="text-xs font-['Outfit'] text-white mt-0.5">VIT ERC-20</p>
        </div>
      </div>

      <div className="flex gap-1">
        {([
          { id: "lock" as Tab, label: "Lock → Base" },
          { id: "unlock" as Tab, label: "Unlock ← Base" },
          { id: "history" as Tab, label: "History" },
        ]).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-xs font-['Outfit'] font-medium uppercase tracking-wide transition-all ${
              tab === t.id
                ? "bg-[#00E676]/10 text-[#00E676] border border-[#00E676]/30"
                : "text-white/40 hover:text-white/70 border border-transparent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "lock" && (
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4 max-w-md">
          <p className="text-xs text-white/50 font-['Outfit']">
            Lock VITCoin on VIT Network to receive VIT ERC-20 tokens on Base L2 (Coinbase).
          </p>
          <AmountInput
            value={lockAmount}
            onChange={setLockAmount}
            label="VITCoin to Lock"
            suffix="VIT"
            max={wallet?.vitcoin_balance}
            hint={`Balance: ${(wallet?.vitcoin_balance ?? 0).toFixed(4)} VIT · Min: 10 VIT`}
          />
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Base L2 Wallet Address</label>
            <input
              value={evmAddress}
              onChange={(e) => setEvmAddress(e.target.value)}
              placeholder="0x..."
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white font-['JetBrains_Mono'] outline-none focus:border-[#00E676]/40 placeholder:text-white/20"
            />
          </div>
          {lockN > 0 && (
            <div className="flex flex-col gap-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
              <div className="flex justify-between text-xs font-['Outfit']">
                <span className="text-white/30">Bridge Fee (1%)</span>
                <span className="text-white/50 font-['JetBrains_Mono']">{fee.toFixed(6)} VIT</span>
              </div>
              <div className="flex justify-between text-xs font-['Outfit']">
                <span className="text-white/30">You receive on Base L2</span>
                <span className="text-[#00E676] font-['JetBrains_Mono']">{received.toFixed(6)} VIT ERC-20</span>
              </div>
            </div>
          )}
          <button
            onClick={handleLock}
            disabled={locking || !lockAmount || !evmAddress}
            className="w-full py-3 rounded-lg bg-[#00E676] text-[#080c12] font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-[#00E676]/90 transition-colors disabled:opacity-40"
          >
            {locking ? "Locking…" : "Lock VITCoin → Base L2"}
          </button>
        </div>
      )}

      {tab === "unlock" && (
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4 max-w-md">
          <p className="text-xs text-white/50 font-['Outfit']">
            Provide your Base L2 burn transaction hash to unlock VITCoin on VIT Network.
          </p>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Base L2 Burn Transaction Hash</label>
            <input
              value={unlockTxHash}
              onChange={(e) => setUnlockTxHash(e.target.value)}
              placeholder="0x..."
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white font-['JetBrains_Mono'] outline-none focus:border-[#00E676]/40 placeholder:text-white/20"
            />
          </div>
          <AmountInput
            value={unlockAmount}
            onChange={setUnlockAmount}
            label="Amount Burned (VIT ERC-20)"
            suffix="VIT"
            hint="Must match the amount in your burn transaction"
          />
          <button
            onClick={handleUnlock}
            disabled={unlocking || !unlockTxHash || !unlockAmount}
            className="w-full py-3 rounded-lg bg-white/[0.08] text-white font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-white/[0.12] transition-colors disabled:opacity-40 border border-white/[0.12]"
          >
            {unlocking ? "Verifying…" : "Unlock VITCoin"}
          </button>
        </div>
      )}

      {tab === "history" && (
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-2">
          {txArr.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-white/20 font-['Outfit']">No bridge transactions</p>
            </div>
          ) : (
            txArr.map((tx) => <BridgeTxRow key={tx.id} tx={tx} />)
          )}
        </div>
      )}

      <div className="rounded-xl border border-white/[0.04] bg-white/[0.01] p-4 text-[10px] text-white/25 font-['Outfit'] leading-relaxed">
        Bridge transfers typically complete in 2–10 minutes. A 1% fee applies to both lock and unlock operations.
        Minimum bridge amount is 10 VIT. Only use Base L2 addresses you control. Transfers are irreversible.
      </div>
    </div>
  );
}
