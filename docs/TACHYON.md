# Tachyon VESS: Verifiable Elastic Storage Swarm

Tachyon VESS is a decentralized storage layer for the VIT Network that shards data across multiple cloud providers and personal storage nodes. It uses Reed-Solomon erasure coding to ensure high availability and data integrity.

## How It Works

1. **Shredding:** Files are split into 4KB fragments.
2. **Erasure Coding:** Data fragments are encoded using Reed-Solomon (6 data shards, 3 parity shards by default).
3. **Distribution:** Shards are distributed across the Provider Pool (Google Drive, Dropbox, OneDrive, Disk, and independent nodes).
4. **Verification:** The network issues periodic storage challenges to nodes. Valid responses are anchored to the VIT Chain.

## Reed-Solomon Parameters

- **Data Shards (K):** 6
- **Parity Shards (M):** 3
- **Total Shards (N):** 9
- **Fault Tolerance:** Up to 3 shards can be lost without data loss.

## Provider Pool Setup

The `ProviderPool` (managed in `tachyon/core/providers/pool.py`) handles the orchestration of shards. It:
- Uses a round-robin strategy for load balancing.
- Automatically marks failing providers as 'degraded'.
- Enforces storage quotas (skips providers above 90% usage).

## Storage Contribution (Node Operators)

Users can contribute their personal cloud storage to the Tachyon swarm and earn VIT rewards.

### Linking a Provider
1. Navigate to the **Storage Nodes** section in the VIT Dashboard.
2. Select your provider (e.g., Google Drive).
3. Authenticate and authorize the VIT application.
4. Your node will begin receiving shards and responding to verification challenges.

### Manual Verification
Node operators can manually trigger a verification check for their stored shards:
`POST /api/tachyon/node/{node_id}/verify`

## S3-Compatible API

Tachyon provides an S3-compatible interface for developers.

### Authentication
Uses HMAC-SHA256 signing of (timestamp + method + path).
- **Headers:**
  - `X-VIT-Key`: Your API Key
  - `X-VIT-Timestamp`: Unix timestamp
  - `X-VIT-Signature`: HMAC signature

### Endpoints
- `GET /api/tachyon/s3/{bucket}/{key}`: Download object
- `PUT /api/tachyon/s3/{bucket}/{key}`: Upload object
- `DELETE /api/tachyon/s3/{bucket}/{key}`: Delete object
