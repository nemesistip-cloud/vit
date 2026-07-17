# VIT Network — Frontend Architecture

## Overview

The VIT Network frontend is a **React 18 + TypeScript + Vite** single-page application that serves as the presentation layer for the VIT platform gateway. It owns no business data — all live data is fetched from production services.

## Technology Decisions

| Concern         | Choice                  | Rationale |
|-----------------|-------------------------|-----------|
| Framework       | React 18                | Concurrent features, wide ecosystem |
| Language        | TypeScript              | Type safety across API boundaries |
| Build tool      | Vite 5                  | Sub-second HMR, fast builds |
| Styling         | TailwindCSS 3           | Utility-first, custom design tokens |
| Animations      | Framer Motion           | Declarative, performant |
| Routing         | React Router v6         | Declarative, nested routes |
| Data fetching   | TanStack Query v5       | Caching, background refetch, retry |
| Icons           | Lucide React            | Consistent, tree-shakeable |

## Directory Structure

```
src/
├── App.tsx                 # Route definitions
├── main.tsx                # Entry point, providers
├── index.css               # Tailwind layers + custom utilities
├── lib/
│   ├── api.ts              # Typed API clients for all 3 services
│   ├── queryClient.ts      # TanStack Query client config
│   └── utils.ts            # cn(), formatBytes(), formatUptime(), statusColor()
├── hooks/
│   ├── useHealth.ts        # Gateway, AI, Storage health hooks
│   ├── useAI.ts            # AI models + status hooks
│   └── useStorage.ts       # Storage list + metrics hooks
├── components/
│   ├── layout/
│   │   ├── Navbar.tsx      # Fixed nav, mobile menu, live status pill
│   │   └── Footer.tsx      # Links, social, system status
│   ├── ui/
│   │   ├── StatusBadge.tsx # Color-coded health badge
│   │   ├── Card.tsx        # Glass card primitives
│   │   └── Spinner.tsx     # Loading spinner
│   ├── ServiceCard.tsx     # Service overview card
│   └── StatCard.tsx        # Metric display card
└── pages/
    ├── Home.tsx            # Landing — hero, ecosystem, health, CTA
    ├── Platform.tsx        # Architecture, live service table
    ├── AI.tsx              # vit-ai health, providers, model registry
    ├── Storage.tsx         # vit-storage health, object browser
    ├── Status.tsx          # Full platform health dashboard
    ├── Developers.tsx      # API quick-start, endpoint reference
    ├── Documentation.tsx   # Full API reference, guides
    ├── Roadmap.tsx         # Phased development timeline
    └── About.tsx           # Mission, principles, infrastructure
```

## Data Flow

```
Production Service → fetch() → TanStack Query cache → React component
```

- All API calls are made with `AbortSignal` for clean cancellation
- Latency is measured per-request and exposed via `_latency` on responses
- Health queries refetch every 30 seconds automatically
- Query client defaults: `staleTime: 30s`, `gcTime: 5min`, `retry: 2`

## Design Tokens (Tailwind)

- `vit-*`: brand blue palette (50–950)
- `surface-*`: dark background layers (500–900)
- `glass` / `glass-hover`: backdrop-blur card utilities
- `gradient-text`: VIT brand gradient on text
- `section-grid`: subtle grid background pattern
