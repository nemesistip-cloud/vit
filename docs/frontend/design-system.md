# VIT Network — Design System

## Design Language

**Dark-first, glass-morphism, high-density.** Inspired by Vercel, Linear, and Stripe's dashboard aesthetics.

## Color Palette

### Brand (VIT Blue)
| Token         | Hex       | Usage |
|---------------|-----------|-------|
| `vit-300`     | #93b4ff   | Text gradients, links |
| `vit-400`     | #5f8aff   | Icons, accents, labels |
| `vit-500`     | #3b65ff   | Primary actions |
| `vit-600`     | #2247f5   | Buttons, CTAs |
| `vit-700`     | #1a35e1   | Hover states |

### Surface (Dark Backgrounds)
| Token           | Hex       | Usage |
|-----------------|-----------|-------|
| `surface-900`   | #0a0d14   | Page background |
| `surface-800`   | #0f1520   | Section backgrounds |
| `surface-700`   | #141c2e   | Cards |
| `surface-600`   | #1a2540   | Elevated cards |

### Status Colors
| Status     | Color    | Usage |
|------------|----------|-------|
| healthy    | emerald  | Operational services |
| degraded   | yellow   | Partial outage |
| unhealthy  | red      | Service down |
| unknown    | white/30 | No data |

## Typography

- **Font**: Inter (weights 300–800)
- **Mono**: JetBrains Mono (latency, API paths, code)
- **Scale**: Tailwind defaults with `tracking-tight` on headings

## Components

### StatusBadge
Colored pill with dot indicator. Supports `pulse` animation for live statuses.

### Card / CardHeader / CardBody
Glass-morphism card with optional `hover` and `glow` variants.

### ServiceCard
Icon + name + description + live status + latency. Used in ecosystem grids.

### StatCard
Metric display with label, large value, optional sub-text and icon.

## Layout

- Max content width: `max-w-7xl` (1280px)
- Section padding: `px-4 sm:px-6`
- Navbar: `h-16`, fixed, `z-50`
- Grid gaps: `gap-4` to `gap-6`
