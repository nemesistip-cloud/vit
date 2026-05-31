import { createPublicClient, createWalletClient, http, custom, type Address, type Hash } from 'viem';
import { baseSepolia, base } from 'viem/chains';

export const VIT_TOKEN_ABI = [
  "function balanceOf(address owner) view returns (uint256)",
  "function transfer(address to, uint256 amount) returns (bool)",
  "function mint(address to, uint256 amount) external",
] as const;

export const UNIVERSAL_ORACLE_ABI = [
  "function publishSignal(string category, string externalId, bytes data, uint8 confidence) external",
  "function signals(bytes32 signalId) view returns (string, string, bytes, uint8, uint256, address)",
] as const;

export class VITSDK {
  public client;

  constructor(rpcUrl?: string) {
    this.client = createPublicClient({
      chain: baseSepolia,
      transport: http(rpcUrl)
    });
  }

  async getBalance(address: Address, tokenAddress: Address) {
    const balance = await this.client.readContract({
      address: tokenAddress,
      abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'owner', type: 'address' }], outputs: [{ name: 'balance', type: 'uint256' }] }],
      functionName: 'balanceOf',
      args: [address]
    });
    return balance;
  }
}
