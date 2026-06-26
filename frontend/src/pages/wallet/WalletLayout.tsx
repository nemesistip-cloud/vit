import React from "react";
import { useLocation, Link } from "wouter";

const TABS = [
  { path: "/wallet", label: "Overview", exact: true },
  { path: "/wallet/buy-sell", label: "Buy / Sell" },
  { path: "/wallet/deposit", label: "Deposit" },
  { path: "/wallet/withdraw", label: "Withdraw" },
  { path: "/wallet/convert", label: "Convert" },
  { path: "/wallet/stake", label: "Stake" },
  { path: "/wallet/vaults", label: "Vaults" },
  { path: "/wallet/p2p", label: "P2P" },
  { path: "/wallet/bridge", label: "Bridge" },
  { path: "/wallet/history", label: "History" },
];

interface WalletLayoutProps {
  children: React.ReactNode;
}

export function WalletLayout({ children }: WalletLayoutProps) {
  const [location] = useLocation();

  const isActive = (tab: (typeof TABS)[0]) => {
    if (tab.exact) return location === tab.path || location === "/wallet/";
    return location.startsWith(tab.path);
  };

  return (
    <div className="min-h-screen bg-[#080c12] text-white">
      <div className="max-w-5xl mx-auto px-4 pt-6 pb-24">
        <div className="mb-6">
          <h1 className="font-['Barlow_Condensed'] text-3xl font-bold uppercase tracking-wide text-white">
            Wallet
          </h1>
          <p className="text-xs text-white/30 font-['Outfit'] mt-0.5">
            VIT Network · Multi-currency wallet & DeFi hub
          </p>
        </div>

        <div className="overflow-x-auto scrollbar-hide mb-6">
          <div className="flex gap-1 min-w-max">
            {TABS.map((tab) => (
              <Link key={tab.path} href={tab.path}>
                <button
                  className={`
                    px-3 py-1.5 rounded-lg text-xs font-['Outfit'] font-medium uppercase tracking-wide
                    whitespace-nowrap transition-all
                    ${
                      isActive(tab)
                        ? "bg-[#00E676]/10 text-[#00E676] border border-[#00E676]/30"
                        : "text-white/40 hover:text-white/70 border border-transparent hover:border-white/10"
                    }
                  `}
                >
                  {tab.label}
                </button>
              </Link>
            ))}
          </div>
        </div>

        <div>{children}</div>
      </div>
    </div>
  );
}
