import { useState } from "react";
import {
  useAccount,
  useConnect,
  useDisconnect,
  useBalance,
  useChainId,
  useSwitchChain,
} from "wagmi";
import { formatUnits } from "viem";
import { base, baseSepolia } from "wagmi/chains";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import {
  Wallet,
  ChevronDown,
  Copy,
  LogOut,
  ExternalLink,
  AlertTriangle,
  Zap,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";

// ── Helpers ───────────────────────────────────────────────────────────────────

function shortAddr(address: string) {
  return `${address.slice(0, 6)}…${address.slice(-4)}`;
}

function chainLabel(chainId: number | undefined) {
  if (chainId === base.id)        return { label: "Base",         color: "text-blue-400",   dot: "bg-blue-400" };
  if (chainId === baseSepolia.id) return { label: "Base Sepolia", color: "text-amber-400",  dot: "bg-amber-400" };
  return                                 { label: "Unknown",       color: "text-red-400",    dot: "bg-red-400" };
}

// ── Connector picker dialog ────────────────────────────────────────────────────

function ConnectorDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { connect, connectors, isPending, error } = useConnect();

  const ICONS: Record<string, string> = {
    injected:         "🦊",
    "coinbaseWallet": "🔵",
    walletConnect:    "🔗",
  };

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-sm border-primary/20 bg-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-foreground">
            <Wallet className="w-5 h-5 text-primary" />
            Connect Wallet
          </DialogTitle>
        </DialogHeader>

        <p className="text-xs text-muted-foreground -mt-2">
          Connect a wallet to interact with Base L2 and VITCoin on-chain features.
        </p>

        <div className="space-y-2 mt-2">
          {connectors.map(connector => (
            <button
              key={connector.uid}
              onClick={() => {
                connect({ connector });
                onClose();
              }}
              disabled={isPending}
              className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors text-left group"
            >
              <span className="text-2xl">{ICONS[connector.id] ?? "💼"}</span>
              <div className="flex-1">
                <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                  {connector.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {connector.id === "injected" ? "Browser extension" : "Mobile & desktop"}
                </p>
              </div>
              <Zap className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </button>
          ))}
        </div>

        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            {error.message}
          </div>
        )}

        <p className="text-[10px] text-muted-foreground text-center">
          By connecting you agree to the VIT Terms of Service.
          We never request seed phrases or private keys.
        </p>
      </DialogContent>
    </Dialog>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface WalletConnectButtonProps {
  size?: "sm" | "default";
  showBalance?: boolean;
  className?: string;
}

export function WalletConnectButton({
  size = "default",
  showBalance = true,
  className = "",
}: WalletConnectButtonProps) {
  const { address, isConnected, connector } = useAccount();
  const { disconnect } = useDisconnect();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();
  const [open, setOpen] = useState(false);

  const { data: ethBalance } = useBalance({
    address,
    query: { enabled: isConnected && !!address },
  });

  const chain = chainLabel(chainId);
  const isWrongChain = isConnected && chainId !== base.id && chainId !== baseSepolia.id;

  function copyAddr() {
    if (!address) return;
    navigator.clipboard.writeText(address);
    toast.success("Address copied");
  }

  function openExplorer() {
    if (!address) return;
    const base = chainId === baseSepolia.id
      ? "https://sepolia.basescan.org/address/"
      : "https://basescan.org/address/";
    window.open(base + address, "_blank", "noopener,noreferrer");
  }

  if (!isConnected) {
    return (
      <>
        <Button
          variant="outline"
          size={size}
          onClick={() => setOpen(true)}
          className={`border-primary/30 hover:border-primary/60 hover:bg-primary/5 font-mono ${className}`}
        >
          <Wallet className="w-4 h-4 mr-2 text-primary" />
          Connect Wallet
        </Button>
        <ConnectorDialog open={open} onClose={() => setOpen(false)} />
      </>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size={size}
          className={`border-primary/30 hover:border-primary/60 font-mono gap-2 ${isWrongChain ? "border-destructive/40" : ""} ${className}`}
        >
          {isWrongChain ? (
            <AlertTriangle className="w-4 h-4 text-destructive" />
          ) : (
            <span className={`w-2 h-2 rounded-full ${chain.dot}`} />
          )}

          <span className="text-foreground">{shortAddr(address!)}</span>

          {showBalance && ethBalance && (
            <Badge
              variant="secondary"
              className="font-mono text-[10px] px-1.5 py-0 h-4 hidden sm:flex"
            >
              {parseFloat(formatUnits(ethBalance.value, ethBalance.decimals)).toFixed(4)} ETH
            </Badge>
          )}

          <ChevronDown className="w-3 h-3 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56 border-border bg-card">
        {/* Chain + address header */}
        <div className="px-3 py-2.5 border-b border-border">
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2 h-2 rounded-full ${chain.dot}`} />
            <span className={`text-xs font-semibold ${chain.color}`}>{chain.label}</span>
            <CheckCircle2 className="w-3 h-3 text-emerald-400 ml-auto" />
          </div>
          <p className="font-mono text-xs text-muted-foreground">{shortAddr(address!)}</p>
          {ethBalance && (
            <p className="font-mono text-xs text-foreground mt-0.5">
              {parseFloat(formatUnits(ethBalance.value, ethBalance.decimals)).toFixed(6)} ETH
            </p>
          )}
          {connector && (
            <p className="text-[10px] text-muted-foreground mt-1">via {connector.name}</p>
          )}
        </div>

        {isWrongChain && (
          <DropdownMenuItem
            className="text-destructive focus:text-destructive focus:bg-destructive/10"
            onClick={() => switchChain({ chainId: base.id })}
          >
            <AlertTriangle className="w-4 h-4 mr-2" />
            Switch to Base
          </DropdownMenuItem>
        )}

        <DropdownMenuItem onClick={copyAddr}>
          <Copy className="w-4 h-4 mr-2" />
          Copy address
        </DropdownMenuItem>

        <DropdownMenuItem onClick={openExplorer}>
          <ExternalLink className="w-4 h-4 mr-2" />
          View on BaseScan
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          className="text-destructive focus:text-destructive focus:bg-destructive/10"
          onClick={() => disconnect()}
        >
          <LogOut className="w-4 h-4 mr-2" />
          Disconnect
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ── Compact inline wallet panel (used inside pages) ───────────────────────────

export function WalletPanel() {
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { data: ethBalance } = useBalance({
    address,
    query: { enabled: isConnected && !!address },
  });

  const chain = chainLabel(chainId);

  if (!isConnected) {
    return (
      <div className="rounded-xl border border-dashed border-primary/20 bg-primary/3 p-5 flex flex-col items-center gap-3 text-center">
        <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
          <Wallet className="w-5 h-5 text-primary" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">No wallet connected</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Connect MetaMask or Coinbase Wallet to access on-chain features
          </p>
        </div>
        <WalletConnectButton size="sm" showBalance={false} />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${chain.dot}`} />
          <span className={`text-xs font-semibold ${chain.color}`}>{chain.label}</span>
        </div>
        <WalletConnectButton size="sm" showBalance={false} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-background/60 rounded-lg p-2.5 border border-border">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Address</p>
          <p className="font-mono text-xs text-foreground">{shortAddr(address!)}</p>
        </div>
        <div className="bg-background/60 rounded-lg p-2.5 border border-border">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">ETH Balance</p>
          <p className="font-mono text-xs text-foreground">
            {ethBalance ? `${parseFloat(formatUnits(ethBalance.value, ethBalance.decimals)).toFixed(4)} ETH` : "—"}
          </p>
        </div>
      </div>
    </div>
  );
}
