# VIT Network UI/UX Inventory (v5.5.0)

This document provides a comprehensive inventory of the current VIT Network frontend architecture, components, and design systems.

---

## 1. Screen Inventory

| Route | Page Title | Primary Purpose | Roles/Tiers |
|-------|------------|-----------------|-------------|
| `/` | Landing | Marketing, high-level stats, plan overview | Unauthenticated |
| `/login` / `/register` | Auth | User authentication and onboarding | Unauthenticated |
| `/dashboard` | Dashboard | Overview of signals, AI confidence, and gamification | Authenticated |
| `/matches` | Matches | List of live and upcoming sports fixtures with AI insights | Authenticated |
| `/matches/:id` | Match Detail | Deep dive into specific match stats and AI breakdown | Authenticated |
| `/predictions` | Predictions | History of user predictions and settlement status | Authenticated |
| `/wallet` | Wallet | Manage VITCoin, staking, and transaction history | Authenticated |
| `/merit` | Merit | Reputation, XP tracking, and level progression | Authenticated |
| `/leaderboard` | Leaderboard | Global user rankings based on XP and win rate | Authenticated |
| `/identity` | Identity | Decentralized Identity (DID) and profile management | Authenticated |
| `/elections` | Elections | Niche prediction market for political events | Authenticated |
| `/policy` | Policy | Niche market for policy and governance forecasting | Authenticated |
| `/validators` | Validators | Network node status and validator activities | Authenticated (Min: Validator) |
| `/marketplace` | Marketplace | Trading of signals and AI model access | Authenticated |
| `/assistant` | AI Assistant | LLM-powered assistant for market analysis | Authenticated (Pro/Elite) |
| `/training` | Training | Model retraining status and job monitoring | Authenticated (Pro/Elite) |
| `/admin` | Admin Panel | Platform management and agent controls | Admin |

---

## 2. Component Library

### Reusable UI Elements (Radix-based)
*Found in `frontend/src/components/ui/`*
- **Layout & Containers**: `Card`, `Accordion`, `Tabs`, `ScrollArea`, `Sheet`, `Resizable`.
- **Inputs**: `Button`, `Input`, `Select`, `Slider`, `Switch`, `Checkbox`, `ToggleGroup`.
- **Feedback**: `Toast`, `Alert`, `Progress`, `Skeleton`, `Badge`, `Tooltip`.
- **Overlays**: `Dialog` (Modal), `Popover`, `ContextMenu`, `HoverCard`.

### Application-Specific Components
- **`PremiumMatchCard`**: (`src/components/PremiumMatchCard.tsx`) Used in Matches page to display fixture with AI edge.
- **`PredictionFlow`**: (`src/components/PredictionFlow.tsx`) Multi-step modal for placing predictions.
- **`EnsembleLeaderboard`**: (`src/components/EnsembleLeaderboard.tsx`) Displays AI model performance ranking.
- **`SignalMarketplace`**: (`src/components/super-app/SignalMarketplace.tsx`) Widget for signal discovery.
- **`AgentPortal`**: (`src/components/super-app/AgentPortal.tsx`) Interface for interacting with network agents.
- **`VITScoreCard`**: (`src/components/VITScoreCard.tsx`) Visual representation of prediction value.

---

## 3. Design Tokens

### Color Palette (from `tokens.css`)
- **Brand Blue**: `#00C8FF` (--vit-brand-blue)
- **Brand Green**: `#00F5C8` (--vit-brand-green)
- **Brand Gold**: `#D4AF37` (--vit-brand-gold)
- **Brand Orange**: `#FF8C00` (--vit-brand-orange)
- **Background**: `240 14% 3%` (Deep space HSL)
- **Primary**: `183 100% 50%` (Neon Cyan)
- **Secondary**: `51 100% 50%` (VITCoin Gold)

### Typography
- **Sans**: 'Inter', system-ui
- **Mono**: 'Space Mono', monospace
- **Weights**: Normal (400), Medium (500), Bold (700), Black (900)

### Spacing & Radius
- **Spacing Scale**: `0.25rem` (xs), `0.5rem` (sm), `1rem` (md), `1.5rem` (lg), `2rem` (xl)
- **Border Radius**: `0.25rem` (sm), `0.375rem` (default), `0.5rem` (md), `0.75rem` (lg)

---

## 4. Navigation & Information Architecture

### Hierarchy (Sidebar)
- **Signal**
  - Dashboard, Project Teams, Matches, Value Analytics, Predictions, Accumulator, Odds Intel, Backtest, Bankroll.
- **Earn**
  - Wallet, Watchlist, Tasks, Offers, Merit, Leaderboard, Referral.
- **Pro**
  - AI Assistant, Training, Performance Analytics, Model Performance, Intel Reports, Research, Marketplace, Validators.
- **Network**
  - VIT Analytics, Node Network, Smart Contracts, Treasury, Trust & Safety, Security, Bridge, Governance, Developer, Roadmap.
- **You**
  - My Identity, KYC Verify, Subscription, Settings.

---

## 5. Interaction Patterns

- **Modals**: Triggered via Radix `Dialog`. Standard behavior: Click outside to close, ESC key support. Often contains complex multi-step flows (e.g., PredictionFlow).
- **Toasts**: Handled by `sonner`. Appear in bottom-right. Pattern: `toast.success("...")` or `toast.error("...")`.
- **Forms**: Managed by `react-hook-form` with `zod` validation. Errors appear inline below inputs.
- **Loading States**: Shimmer skeletons (`Skeleton` component) used for content blocks. Spinning spinner for page transitions.
- **Animations**: CSS keyframes (`vit-fade-in`, `vit-slide-up`) and `framer-motion` for micro-interactions.

---

## 6. Mobile Responsiveness

- **Breakpoints**: Single primary breakpoint at `768px` (`useIsMobile` hook).
- **Mobile Patterns**:
  - Desktop sidebar hides; replaced by a mobile bottom navigation bar (5 primary items).
  - Mobile top bar contains logo, theme toggle, and hamburger menu (slide-over drawer).
- **PWA**: `manifest.json` configured with standalone display and `#00f5ff` theme color.

---

## 7. Gamification & VITCoin UI

- **XP & Levels**: `LevelCard` in Dashboard shows XP, current level (Novice to Legend), and progress to next level.
- **Merit System**: Detailed in `merit.tsx`. Tracks peak tier and reputation components.
- **Streak Counter**: Visual flame icon with numeric count for consecutive successful prediction days.
- **Leaderboard**: Rank-based list (`🥇`, `🥈`, `🥉`) with username, level, and win rate.
- **Prophecy Chain**: (`prophecy.tsx`) Visual progress through "Chapters" based on prediction volume and accuracy.

---

## 8. Known UI Debt

- **Corrupted CSS**: `tokens.css` contains corrupted selectors (`., ., ., ., ., ., .`) likely due to automated search/replace operations on "bot".
- **Hardcoded Inline Styles**: Found in `layout.tsx` (sidebar background) and `PremiumMatchCard.tsx` (progress bar widths).
- **Placeholders**: "Coming Soon" label on Accumulator placement in `bet-slip.tsx`.
- **Duplicate Declarations**: `App.tsx` previously had duplicate lazy imports for DashboardPage and AuthPage (Fixed during inventory audit).
- **Inconsistent Hook Usage**: Usage of `useToast` (shadcn pattern) mixed with direct `toast` (sonner pattern).
