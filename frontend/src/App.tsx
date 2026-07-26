import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell, PublicShell } from '@/components/shell/AppShell'

// ── Public / marketing ────────────────────────────────────────────────────────
import Home              from '@/pages/Home'
import Platform          from '@/pages/Platform'
import AI                from '@/pages/AI'
import Storage           from '@/pages/Storage'
import Status            from '@/pages/Status'
import Developers        from '@/pages/Developers'
import Documentation     from '@/pages/Documentation'
import Roadmap           from '@/pages/Roadmap'
import About             from '@/pages/About'

// ── Auth ─────────────────────────────────────────────────────────────────────
import Login             from '@/pages/Login'
import ForgotPassword    from '@/pages/ForgotPassword'
import ResetPassword     from '@/pages/ResetPassword'
import VerifyEmail       from '@/pages/VerifyEmail'

// ── Core app ──────────────────────────────────────────────────────────────────
import Dashboard         from '@/pages/Dashboard'
import Workspace         from '@/pages/Workspace'
import Settings          from '@/pages/Settings'
import Subscription      from '@/pages/Subscription'
import Matches           from '@/pages/Matches'
import MatchDetail       from '@/pages/MatchDetail'
import Predictions       from '@/pages/Predictions'
import Odds              from '@/pages/Odds'
import Leaderboard       from '@/pages/Leaderboard'
import Analytics         from '@/pages/Analytics'
import AnalyticsStudio   from '@/pages/AnalyticsStudio'
import Assistant         from '@/pages/Assistant'
import Tasks             from '@/pages/Tasks'

// ── Finance ───────────────────────────────────────────────────────────────────
import Wallet            from '@/pages/Wallet'
import DeFi              from '@/pages/DeFi'
import InPlay            from '@/pages/InPlay'
import Marketplace       from '@/pages/Marketplace'
import Referral          from '@/pages/Referral'

// ── Governance & network ──────────────────────────────────────────────────────
import Governance        from '@/pages/Governance'
import Treasury          from '@/pages/Treasury'
import Validators        from '@/pages/Validators'
import Explorer          from '@/pages/Explorer'

// ── Social & ecosystem ────────────────────────────────────────────────────────
import Social            from '@/pages/Social'
import Ecosystem         from '@/pages/Ecosystem'
import Enterprise        from '@/pages/Enterprise'

// ── Betting tools ─────────────────────────────────────────────────────────────
import Accumulator       from '@/pages/Accumulator'
import Rollover          from '@/pages/Rollover'
import Backtest          from '@/pages/Backtest'
import Bankroll          from '@/pages/Bankroll'

// ── Financial flows ────────────────────────────────────────────────────────────
import VITCoin           from '@/pages/VITCoin'
import Exchange          from '@/pages/Exchange'
import Vaults            from '@/pages/Vaults'
import Bridge            from '@/pages/Bridge'

// ── Admin & 404 ───────────────────────────────────────────────────────────────
import Admin             from '@/pages/Admin'
import NotFound          from '@/pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route element={<PublicShell />}>
        <Route path="/" element={<Home />} />
        <Route path="/platform" element={<Platform />} />
        <Route path="/ai" element={<AI />} />
        <Route path="/storage" element={<Storage />} />
        <Route path="/status" element={<Status />} />
        <Route path="/developers" element={<Developers />} />
        <Route path="/docs" element={<Documentation />} />
        <Route path="/roadmap" element={<Roadmap />} />
        <Route path="/about" element={<About />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
      </Route>

      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/workspace" element={<Workspace />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/subscription" element={<Subscription />} />
        <Route path="/matches" element={<Matches />} />
        <Route path="/matches/:id" element={<MatchDetail />} />
        <Route path="/predictions" element={<Predictions />} />
        <Route path="/odds" element={<Odds />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/analytics-studio" element={<AnalyticsStudio />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/wallet" element={<Wallet />} />
        <Route path="/defi" element={<DeFi />} />
        <Route path="/inplay" element={<InPlay />} />
        <Route path="/marketplace" element={<Marketplace />} />
        <Route path="/referral" element={<Referral />} />
        <Route path="/governance" element={<Governance />} />
        <Route path="/treasury" element={<Treasury />} />
        <Route path="/validators" element={<Validators />} />
        <Route path="/chain" element={<Explorer />} />
        <Route path="/explorer" element={<Navigate to="/chain" replace />} />
        <Route path="/social" element={<Social />} />
        <Route path="/ecosystem" element={<Ecosystem />} />
        <Route path="/enterprise" element={<Enterprise />} />
        <Route path="/accumulator" element={<Accumulator />} />
        <Route path="/rollover" element={<Rollover />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/bankroll" element={<Bankroll />} />
        <Route path="/vitcoin" element={<VITCoin />} />
        <Route path="/exchange" element={<Exchange />} />
        <Route path="/vaults" element={<Vaults />} />
        <Route path="/bridge" element={<Bridge />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
