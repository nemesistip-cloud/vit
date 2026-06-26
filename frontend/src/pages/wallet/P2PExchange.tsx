import React, { useState } from "react";
import { AmountInput } from "@/components/wallet/AmountInput";
import {
  useP2POffers, useP2POrders, useCreateP2POffer, useCancelP2POffer,
  useCreateP2POrder, useP2PConfirmPayment, useP2PReleaseEscrow,
  useWalletOverview,
} from "@/hooks/useWallet";
import type { P2POffer, P2POrder } from "@/hooks/useWallet";
import { toast } from "sonner";

type Tab = "browse" | "my-offers" | "my-orders" | "create";

function OfferCard({ offer, onTrade }: { offer: P2POffer; onTrade: (offer: P2POffer) => void }) {
  const isBuy = offer.offer_type === "buy";
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <span className={`text-[9px] px-2 py-0.5 rounded-full font-['Outfit'] uppercase tracking-wide font-bold ${isBuy ? "bg-[#00E676]/10 text-[#00E676]" : "bg-red-500/10 text-red-400"}`}>
            {isBuy ? "Buy" : "Sell"}
          </span>
          <p className="text-sm font-['JetBrains_Mono'] text-white mt-1">
            ₦{offer.rate_ngn.toLocaleString("en", { minimumFractionDigits: 2 })} / VIT
          </p>
        </div>
        <div className="text-right">
          <p className="text-[9px] text-white/30 font-['Outfit'] uppercase">Available</p>
          <p className="font-['JetBrains_Mono'] text-sm text-white">{offer.available_amount.toFixed(4)} VIT</p>
        </div>
      </div>
      <div className="flex justify-between text-[10px] font-['Outfit'] text-white/30">
        <span>Min: {offer.min_order.toFixed(2)} VIT</span>
        <span>Max: {offer.max_order.toFixed(2)} VIT</span>
        <span className="capitalize">{offer.payment_method.replace("_", " ")}</span>
      </div>
      <button
        onClick={() => onTrade(offer)}
        className={`w-full py-2 rounded-lg font-['Barlow_Condensed'] font-bold uppercase tracking-wide text-sm transition-colors ${
          isBuy
            ? "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20"
            : "bg-[#00E676]/10 text-[#00E676] hover:bg-[#00E676]/20 border border-[#00E676]/20"
        }`}
      >
        {isBuy ? "Sell to this buyer" : "Buy from this seller"}
      </button>
    </div>
  );
}

function OrderCard({ order, onConfirmPayment, onRelease }: {
  order: P2POrder;
  onConfirmPayment: (id: string) => void;
  onRelease: (id: string) => void;
}) {
  const statusColors: Record<string, string> = {
    pending: "text-yellow-400",
    payment_sent: "text-blue-400",
    completed: "text-[#00E676]",
    disputed: "text-red-400",
    cancelled: "text-white/30",
  };
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[9px] text-white/30 font-['JetBrains_Mono'] uppercase">{order.id.slice(0, 8)}…</p>
          <p className="text-sm font-['JetBrains_Mono'] text-white mt-0.5">
            {order.amount.toFixed(4)} VIT
          </p>
          <p className="text-[10px] text-white/40 font-['Outfit']">
            ₦{order.fiat_total_ngn.toLocaleString("en", { minimumFractionDigits: 2 })} · Rate ₦{order.rate_ngn.toFixed(2)}
          </p>
        </div>
        <span className={`text-[10px] font-['Outfit'] font-medium ${statusColors[order.status] ?? "text-white/50"}`}>
          {order.status.replace("_", " ")}
        </span>
      </div>
      <div className="flex gap-2 text-[9px] text-white/30 font-['Outfit']">
        <span className="capitalize px-2 py-0.5 rounded bg-white/[0.04]">{order.my_role}</span>
        <span className="px-2 py-0.5 rounded bg-white/[0.04]">
          {new Date(order.created_at).toLocaleDateString("en", { month: "short", day: "numeric" })}
        </span>
      </div>
      <div className="flex gap-2">
        {order.status === "pending" && order.my_role === "buyer" && (
          <button
            onClick={() => onConfirmPayment(order.id)}
            className="flex-1 py-2 rounded-lg text-xs font-['Outfit'] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-colors uppercase tracking-wide"
          >
            Confirm Payment Sent
          </button>
        )}
        {order.status === "payment_sent" && order.my_role === "seller" && (
          <button
            onClick={() => onRelease(order.id)}
            className="flex-1 py-2 rounded-lg text-xs font-['Outfit'] font-medium bg-[#00E676]/10 text-[#00E676] border border-[#00E676]/20 hover:bg-[#00E676]/20 transition-colors uppercase tracking-wide"
          >
            Release VITCoin
          </button>
        )}
      </div>
    </div>
  );
}

export function P2PExchange() {
  const [tab, setTab] = useState<Tab>("browse");
  const [filterType, setFilterType] = useState<"" | "buy" | "sell">("");
  const [tradeOffer, setTradeOffer] = useState<P2POffer | null>(null);
  const [tradeAmount, setTradeAmount] = useState("");

  const [createType, setCreateType] = useState<"buy" | "sell">("sell");
  const [createAmount, setCreateAmount] = useState("");
  const [createRate, setCreateRate] = useState("");
  const [createMin, setCreateMin] = useState("");
  const [createMax, setCreateMax] = useState("");
  const [createPayment, setCreatePayment] = useState("bank_transfer");

  const { data: offersData } = useP2POffers(filterType || undefined);
  const { data: ordersData } = useP2POrders();
  const { data: wallet } = useWalletOverview();
  const { mutate: createOffer, isPending: creatingOffer } = useCreateP2POffer();
  const { mutate: cancelOffer } = useCancelP2POffer();
  const { mutate: createOrder, isPending: creatingOrder } = useCreateP2POrder();
  const { mutate: confirmPayment } = useP2PConfirmPayment();
  const { mutate: releaseEscrow } = useP2PReleaseEscrow();

  const handleTrade = () => {
    if (!tradeOffer || !tradeAmount) return;
    const n = parseFloat(tradeAmount);
    if (!n || n < tradeOffer.min_order || n > tradeOffer.max_order) {
      toast.error(`Amount must be between ${tradeOffer.min_order} and ${tradeOffer.max_order} VIT`);
      return;
    }
    createOrder({ offer_id: tradeOffer.id, amount: n }, {
      onSuccess: () => { setTradeOffer(null); setTradeAmount(""); },
    });
  };

  const handleCreateOffer = () => {
    const n = parseFloat(createAmount);
    const rate = parseFloat(createRate);
    const min = parseFloat(createMin);
    const max = parseFloat(createMax);
    if (!n || !rate || !min || !max) { toast.error("Fill all fields"); return; }
    if (min > max || max > n) { toast.error("Check min/max vs total amount"); return; }
    createOffer({
      offer_type: createType, amount: n, currency: "VITCoin",
      rate_ngn: rate, min_order: min, max_order: max,
      payment_method: createPayment,
    }, { onSuccess: () => { setTab("browse"); setCreateAmount(""); setCreateRate(""); setCreateMin(""); setCreateMax(""); } });
  };

  const TABS: { id: Tab; label: string }[] = [
    { id: "browse", label: "Browse" },
    { id: "my-orders", label: "My Orders" },
    { id: "create", label: "Create Offer" },
  ];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="font-['Barlow_Condensed'] text-2xl font-bold uppercase text-white">P2P Exchange</h2>
        <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">Peer-to-peer VITCoin trading with escrow protection</p>
      </div>

      <div className="flex gap-1">
        {TABS.map((t) => (
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

      {tab === "browse" && (
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            {(["", "sell", "buy"] as const).map((f) => (
              <button
                key={f || "all"}
                onClick={() => setFilterType(f)}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-['Outfit'] uppercase tracking-wide transition-all ${
                  filterType === f ? "bg-white/[0.08] text-white" : "text-white/30 hover:text-white/60"
                }`}
              >
                {f === "" ? "All" : f === "sell" ? "Buy VIT" : "Sell VIT"}
              </button>
            ))}
          </div>

          {tradeOffer ? (
            <div className="rounded-xl border border-[#00E676]/20 bg-[#00E676]/5 p-5 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-['Outfit'] text-white font-medium">Trading with offer</p>
                <button onClick={() => setTradeOffer(null)} className="text-white/30 hover:text-white text-xs">✕ Cancel</button>
              </div>
              <AmountInput
                value={tradeAmount}
                onChange={setTradeAmount}
                label={`VITCoin Amount (${tradeOffer.min_order}–${tradeOffer.max_order})`}
                suffix="VIT"
                min={tradeOffer.min_order}
                max={tradeOffer.max_order}
              />
              {tradeAmount && parseFloat(tradeAmount) > 0 && (
                <p className="text-xs font-['Outfit'] text-white/50">
                  You pay:{" "}
                  <span className="text-[#00E676] font-['JetBrains_Mono']">
                    ₦{(parseFloat(tradeAmount) * tradeOffer.rate_ngn).toLocaleString("en", { minimumFractionDigits: 2 })}
                  </span>
                </p>
              )}
              <button
                onClick={handleTrade}
                disabled={creatingOrder}
                className="w-full py-3 rounded-lg bg-[#00E676] text-[#080c12] font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide hover:bg-[#00E676]/90 disabled:opacity-40 transition-colors"
              >
                {creatingOrder ? "Placing Order…" : "Confirm Trade"}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {offersData?.offers.map((o) => (
                <OfferCard key={o.id} offer={o} onTrade={setTradeOffer} />
              ))}
              {!offersData?.offers.length && (
                <div className="col-span-2 rounded-xl border border-white/[0.04] p-8 text-center">
                  <p className="text-sm text-white/20 font-['Outfit']">No offers available</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === "my-orders" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {ordersData?.orders.map((o) => (
            <OrderCard key={o.id} order={o} onConfirmPayment={confirmPayment} onRelease={releaseEscrow} />
          ))}
          {!ordersData?.orders.length && (
            <div className="col-span-2 rounded-xl border border-white/[0.04] p-8 text-center">
              <p className="text-sm text-white/20 font-['Outfit']">No orders yet</p>
            </div>
          )}
        </div>
      )}

      {tab === "create" && (
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col gap-4 max-w-md">
          <div className="flex gap-1 p-1 rounded-lg bg-white/[0.04]">
            {(["sell", "buy"] as const).map((t) => (
              <button key={t} onClick={() => setCreateType(t)}
                className={`flex-1 py-2 rounded-md text-xs font-['Barlow_Condensed'] font-bold uppercase tracking-wide transition-all ${
                  createType === t ? (t === "sell" ? "bg-red-500 text-white" : "bg-[#00E676] text-[#080c12]") : "text-white/40 hover:text-white/70"
                }`}
              >
                {t === "sell" ? "Sell VIT" : "Buy VIT"}
              </button>
            ))}
          </div>

          <AmountInput value={createAmount} onChange={setCreateAmount} label="Total Amount (VIT)" suffix="VIT"
            max={createType === "sell" ? wallet?.vitcoin_balance : undefined}
            hint={createType === "sell" ? `Balance: ${(wallet?.vitcoin_balance ?? 0).toFixed(4)} VIT` : undefined}
          />
          <AmountInput value={createRate} onChange={setCreateRate} label="Rate (₦ per VIT)" suffix="₦" />
          <div className="grid grid-cols-2 gap-3">
            <AmountInput value={createMin} onChange={setCreateMin} label="Min Order (VIT)" suffix="VIT" />
            <AmountInput value={createMax} onChange={setCreateMax} label="Max Order (VIT)" suffix="VIT" />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">Payment Method</label>
            <select
              value={createPayment}
              onChange={(e) => setCreatePayment(e.target.value)}
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white font-['Outfit'] outline-none focus:border-[#00E676]/40"
            >
              <option value="bank_transfer">Bank Transfer</option>
              <option value="paystack">Paystack</option>
              <option value="opay">OPay</option>
              <option value="palmpay">PalmPay</option>
              <option value="kuda">Kuda</option>
              <option value="cash">Cash</option>
            </select>
          </div>

          <button
            onClick={handleCreateOffer}
            disabled={creatingOffer}
            className={`w-full py-3 rounded-lg font-['Barlow_Condensed'] font-bold text-lg uppercase tracking-wide transition-colors disabled:opacity-40 ${
              createType === "sell" ? "bg-red-500 text-white hover:bg-red-500/90" : "bg-[#00E676] text-[#080c12] hover:bg-[#00E676]/90"
            }`}
          >
            {creatingOffer ? "Creating…" : `Post ${createType === "sell" ? "Sell" : "Buy"} Offer`}
          </button>
        </div>
      )}
    </div>
  );
}
