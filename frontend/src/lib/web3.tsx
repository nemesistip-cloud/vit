import { createConfig, http } from "wagmi";
import { base, baseSepolia } from "wagmi/chains";
import { injected, coinbaseWallet, walletConnect } from "wagmi/connectors";

// ── Chain selection ──────────────────────────────────────────────────────────
// Defaults to Base mainnet (8453). Set VITE_BASE_CHAIN=sepolia for testnet.
const isTestnet = import.meta.env.VITE_BASE_CHAIN === "sepolia";
const activeChain = isTestnet ? baseSepolia : base;

// ── WalletConnect project ID (optional — set VITE_WALLETCONNECT_PROJECT_ID) ──
const wcProjectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID as string | undefined;

// ── Connectors — WalletConnect is only added when a project ID is configured ─
const connectors = [
  injected({ shimDisconnect: true }),
  coinbaseWallet({
    appName: "VIT Sports Intelligence",
    appLogoUrl: "https://vitcoin.network/logo.png",
  }),
  ...(wcProjectId
    ? [
        walletConnect({
          projectId: wcProjectId,
          metadata: {
            name: "VIT Sports Intelligence",
            description: "AI-native sports prediction and analytics platform",
            url: "https://vitcoin.network",
            icons: ["https://vitcoin.network/logo.png"],
          },
        }),
      ]
    : []),
];

// ── Wagmi config ─────────────────────────────────────────────────────────────
export const wagmiConfig = createConfig({
  chains: [base, baseSepolia],
  connectors,
  transports: {
    [base.id]:        http(import.meta.env.VITE_BASE_RPC_URL || "https://mainnet.base.org"),
    [baseSepolia.id]: http(import.meta.env.VITE_BASE_SEPOLIA_RPC_URL || "https://sepolia.base.org"),
  },
});

// ── VITCoin ERC-20 ABI (minimal — balanceOf + transfer + decimals + symbol) ─
export const VIT_ERC20_ABI = [
  {
    inputs: [{ name: "account", type: "address" }],
    name: "balanceOf",
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ name: "to", type: "address" }, { name: "amount", type: "uint256" }],
    name: "transfer",
    outputs: [{ name: "", type: "bool" }],
    stateMutability: "nonpayable",
    type: "function",
  },
  {
    inputs: [],
    name: "decimals",
    outputs: [{ name: "", type: "uint8" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "symbol",
    outputs: [{ name: "", type: "string" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "totalSupply",
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
] as const;

// ── VIT contract address (from env or placeholder) ────────────────────────────
export const VIT_CONTRACT_ADDRESS = (
  import.meta.env.VITE_VIT_CONTRACT_ADDRESS || ""
) as `0x${string}` | "";

export { activeChain };
