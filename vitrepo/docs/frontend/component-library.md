# VIT Network — Component Library

## UI Primitives

### `<StatusBadge status={} size={} pulse={} />`
- `status`: any string — mapped to color via `statusColor()` util
- `size`: `"sm"` | `"md"` (default `"md"`)
- `pulse`: boolean — animates the dot for live statuses

### `<Card hover glow className>`
Glass card wrapper. `hover` adds border/shadow transition on hover.

### `<CardHeader>` / `<CardBody>`
Padding wrappers for Card composition.

### `<Spinner className />`
Animated ring spinner. Use inside cards while loading.

## Domain Components

### `<ServiceCard>`
```tsx
<ServiceCard
  name="vit-ai"
  description="Multi-provider AI inference"
  icon={Brain}
  status={health?.status}
  version={health?.version}
  latency={health?._latency}
  isLoading={isLoading}
  href="/ai"
  index={0}            // for staggered entrance animation
/>
```

### `<StatCard>`
```tsx
<StatCard
  label="Latency"
  value="42ms"
  sub="Gateway response"
  icon={Zap}
  index={0}
/>
```

## Layout Components

### `<Navbar />`
- Fixed top bar with scroll-reactive blur
- Mobile hamburger menu with AnimatePresence
- Live status pill from `useGatewayHealth()`

### `<Footer />`
- Link grid (Platform / Developers / Company)
- GitHub link
- System status indicator

## Hooks

| Hook | Returns | Refetch |
|------|---------|---------|
| `useGatewayHealth()` | `GatewayHealth` | 30s |
| `useAIHealth()` | `AIHealth` | 30s |
| `useStorageHealth()` | `StorageHealth` | 30s |
| `useAllHealth()` | all three + `overallStatus` | 30s |
| `useAIModels()` | `AIModels` | 60s |
| `useStorageList()` | `StorageList` | 15s |
| `useStorageMetrics()` | metrics | 60s |
