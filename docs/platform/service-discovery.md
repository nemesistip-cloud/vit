# VIT Platform — Service Discovery

## Overview

The VIT gateway implements automatic service discovery. Every registered service exposes a standard interface consumed by the frontend.

## Service Contract

Each discovered service exposes:

| Field           | Type    | Description |
|-----------------|---------|-------------|
| `name`          | string  | Service identifier |
| `version`       | string  | Semver version |
| `health`        | string  | `healthy` \| `degraded` \| `unhealthy` |
| `responseTime`  | number  | Milliseconds |
| `dependencies`  | string[]| Service names this service depends on |
| `lastHeartbeat` | string  | ISO 8601 timestamp |
| `url`           | string  | Service base URL |

## Discovery Endpoint

```
GET /api/services  →  vitnetwork gateway
```

## Frontend Integration

The `Platform` page and `Status` page both consume discovered service data. The `useAllHealth()` hook polls the three known service health endpoints every 30 seconds.

Future services register with the gateway and immediately appear in:
- The Platform page service table
- The Status page health grid
- The Navbar status pill (aggregate)

## Registered Services (Current)

| Name         | URL |
|--------------|-----|
| vitnetwork   | https://vitnetwork-nls4.onrender.com |
| vit-ai       | https://vit-ai.onrender.com |
| vit-storage  | https://vit-storage-4trt.onrender.com |
