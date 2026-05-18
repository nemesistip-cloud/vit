import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useRealtimeTicker } from "@/hooks/useRealtimeTicker";
import { TrendingUp, TrendingDown, Activity, Users, Cpu, Zap, Globe, DollarSign, Shield } from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";

interface TickerItem {
  id: string;
  label: string;
  value: string;
  change?: string;
  up?: boolean;
  icon: React.ReactNode;
  color: string;
}

function TickerSegment({ items }: { items: TickerItem[] }) {
  return (
    <>
      {items.map((item) => (
        <span key={item.id} className="inline-flex items-center gap-1.5 px-5">
          <span className={`${item.color} flex items-center gap-1`}>
            {item.icon}
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70">
              {item.label}
            </span>
          </span>
          <span className={`font-mono text-xs font-semibold ${item.color}`}>{item.value}</span>
          {item.change !== undefined && (
            <span className={`font-mono text-[10px] flex items-center gap-0.5 ${item.up ? "text-emerald-400" : "text-rose-400"}`}>
              {item.up ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
              {item.change}
            </span>
          )}
          <span className="text-border/50 ml-3">·</span>
        </span>
      ))}
    </>
  );
}

export function EcosystemTicker() {
  const { data: realtime } = useRealtimeTicker();

  const { data: price } = useQuery<any>({
    queryKey: ["ticker-price"],
    queryFn: () => apiGet("/api/dashboard/vitcoin-price"),
    refetchInterval: 60_000,
    staleTime: 30_000,
    enabled: !realtime?.vit_price
  });

  const { data: system } = useQuery<any>({
    queryKey: ["ticker-system"],
    queryFn: () => apiGet("/system/status"),
    refetchInterval: 60_000,
    staleTime: 30_000,
    enabled: !realtime?.total_users
  });

  const { data: summary } = useQuery<any>({
    queryKey: ["ticker-summary"],
    queryFn: () => apiGet("/api/dashboard/summary"),
    refetchInterval: 60_000,
    staleTime: 30_000,
    enabled: !realtime?.total_predictions
  });

  const vitPrice   = realtime?.vit_price ?? price?.price ?? price?.price_usd ?? 0;
  const change24h  = realtime?.change_24h ?? price?.change_24h ?? 0;
  const totalUsers = realtime?.total_users ?? system?.total_users ?? 0;
  const activeUsers= realtime?.active_users_30d ?? system?.active_users_30d ?? 0;
  const validators = realtime?.active_validators ?? system?.active_validators ?? 0;
  const staked     = realtime?.total_staked_vit ?? system?.total_staked_vit ?? 0;
  const totalPreds = realtime?.total_predictions ?? summary?.total_predictions ?? 0;
  const accuracy   = ((realtime?.accuracy_rate ?? summary?.accuracy_rate ?? 0) * 100).toFixed(1);

  const items: TickerItem[] = [
    {
      id: "vit-price",
      label: "VIT/USD",
      value: `$${vitPrice.toFixed(4)}`,
      change: `${Math.abs(change24h).toFixed(2)}%`,
      up: change24h >= 0,
      icon: <BrandLogo iconOnly size={12} />,
      color: "text-primary",
    },
    {
      id: "users",
      label: "Users",
      value: totalUsers.toLocaleString(),
      icon: <Users className="w-3 h-3" />,
      color: "text-muted-foreground",
    },
    {
      id: "active",
      label: "Active 30d",
      value: activeUsers.toLocaleString(),
      icon: <Activity className="w-3 h-3" />,
      color: "text-emerald-400",
    },
    {
      id: "validators",
      label: "Validators",
      value: validators.toLocaleString(),
      icon: <Shield className="w-3 h-3" />,
      color: "text-primary",
    },
    {
      id: "staked",
      label: "Staked VIT",
      value: staked >= 1_000_000 ? `${(staked / 1_000_000).toFixed(2)}M` : staked.toLocaleString(),
      icon: <BrandLogo iconOnly size={12} />,
      color: "text-emerald-400",
    },
    {
      id: "predictions",
      label: "Predictions",
      value: totalPreds.toLocaleString(),
      icon: <Cpu className="w-3 h-3" />,
      color: "text-muted-foreground",
    },
    {
      id: "accuracy",
      label: "Accuracy",
      value: `${accuracy}%`,
      icon: <TrendingUp className="w-3 h-3" />,
      color: "text-primary",
    },
  ];

  return (
    <div className="border-b border-border/40 bg-sidebar overflow-hidden">
      <div className="flex items-center">
        <div className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 border-r border-primary/20">
          <span className="vit-live-dot" />
          <span className="font-mono text-[9px] font-bold uppercase tracking-widest text-primary">Live</span>
        </div>
        <div className="vit-ticker-wrap flex-1">
          <div className="vit-ticker-content py-1.5">
            <TickerSegment items={items} />
            <TickerSegment items={items} />
          </div>
        </div>
      </div>
    </div>
  );
}
