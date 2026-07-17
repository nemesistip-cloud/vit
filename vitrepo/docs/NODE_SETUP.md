# VIT Node Setup & Configuration

This guide provides instructions for setting up and running a VIT Node to participate in the network as a storage contributor or validator.

## Prerequisites

- **Python:** 3.8 or higher.
- **Hardware:**
  - Storage Node: Minimum 10GB free space (cloud or disk).
  - Validator Node: Minimum 4 CPU cores, 8GB RAM.
- **Wallet:** A VIT wallet with a minimum stake (100 VIT for validators).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Value-analytics-trust/vit-network.git
   cd vit-network
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Initialize your configuration:
   ```bash
   vit-node init
   ```
   This will create a configuration directory at `~/.vit_node/`.

## Node Types

### 1. Storage Node (Tachyon)
Contribute storage to the Tachyon VESS and earn TSC (Tachyon Storage Credits).
- **Setup:**
  ```bash
  vit-node storage link gdrive
  ```
  Follow the OAuth2 flow to authorize Google Drive.

### 2. Validator Node (Blockchain)
Participate in block production and consensus.
- **Requirements:** Must have ≥100 VIT staked.
- **Registration:**
  ```bash
  vit-node register --type validator
  ```

## Running the Daemon

The `vit-node` daemon manages all node operations in the background.

```bash
vit-node run
```

## Monitoring & Earnings

- **Status Check:**
  ```bash
  vit-node status
  ```
- **View Earnings:**
  ```bash
  vit-node earnings
  ```
- **Claim Rewards:**
  ```bash
  vit-node claim
  ```

## Troubleshooting

- **Logs:** Check `~/.vit_node/logs/daemon.log`.
- **Identity:** If your Node ID is lost, restore it using your `keystore.json`.
- **Connection:** Ensure your node can reach `https://api.vitnetwork.app`.
