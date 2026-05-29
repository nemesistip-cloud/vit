# VIT Blockchain Integration Guide

## Overview
VIT Sports Intelligence Network is now the foundation for the VIT Blockchain. This upgrade introduces a monorepo structure with smart contracts (Foundry) and a TypeScript SDK.

## Core Components

### 1. Smart Contracts (`packages/contracts`)
- `VITToken.sol`: Main utility/governance token.
- `UniversalOracle.sol`: Stores AI-generated signals.
- `LoyaltyVault.sol`: Handles automated loyalty rewards.
- `ElectoralOracle.sol`: Verifiable polling insights.
- `ShopManager.sol`: Betting shop agent registry.

### 2. SDK (`packages/sdk`)
Use the SDK in frontend or external integrations:
```typescript
import { VITSDK } from '@vit/sdk';
const sdk = new VITSDK('https://sepolia.base.org');
```

### 3. Backend Integration
FastAPI now includes a `ContractService` that automatically pushes high-confidence predictions to the `UniversalOracle` on Base L2.

## Deployment
1. Set `ORACLE_PRIVATE_KEY` and `UNIVERSAL_ORACLE_ADDRESS` in `.env`.
2. Deploy contracts using Foundry:
   ```bash
   cd packages/contracts
   forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast
   ```
