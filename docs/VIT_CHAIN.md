# VIT Chain: Architecture & Integration

VIT Chain is the native Layer 2 (L2) blockchain for the VIT Network, optimized for sports analytics, verifiable predictions, and decentralized storage incentives.

## Technical Specifications

- **Chain ID:** 7764 (0x1e54)
- **Block Time:** 15 seconds
- **Consensus:** Proof of Storage (PoS) + Verifiable Oracle Consensus
- **Currency Symbol:** VIT
- **Precision:** 18 decimals (Wei-equivalent)
- **Architecture:** EVM-compatible execution layer with custom storage-anchoring opcodes.

## Network Details

Parameter | Value
----------|-------
Network Name | VIT Chain
RPC URL | `https://api.vitnetwork.app/api/chain/rpc` (Production)
Chain ID | 7764
Currency Symbol | VIT
Block Explorer | `https://explorer.vitnetwork.app`

## MetaMask Setup Guide

Follow these steps to add VIT Chain to your MetaMask wallet:

1. Open MetaMask and click the **Network Selection** dropdown at the top.
2. Click **Add Network** → **Add a network manually**.
3. Fill in the following details:
   - **Network Name:** VIT Chain
   - **New RPC URL:** `https://api.vitnetwork.app/api/chain/rpc`
   - **Chain ID:** `7764`
   - **Currency Symbol:** `VIT`
   - **Block Explorer URL:** `https://explorer.vitnetwork.app`
4. Click **Save**.

## Core Components

### 1. JSON-RPC Interface
The chain supports standard Ethereum JSON-RPC 2.0 methods including:
- `eth_getBalance`
- `eth_sendRawTransaction`
- `eth_getBlockByNumber`
- `eth_getTransactionByHash`

### 2. Proof of Storage
Validators are selected based on their storage contribution to the Tachyon VESS. A valid block must include a storage challenge response verified by the network.

### 3. Oracle Integration
Match results are anchored on-chain via the `UniversalOracle` contract, allowing for trustless settlement of staked predictions.
