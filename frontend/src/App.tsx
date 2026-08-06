import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom'
import { AppShell, PublicShell } from '@/components/shell/AppShell'
import { getAuthToken } from '@/hooks/useAuth'
import { RouteErrorBoundary } from '@/components/ErrorBoundary'
import { Spinner } from '@/components/ui/Spinner'

// ── Page-level loading fallback ───────────────────────────────────────────────

function PageLoader() {
  return (
    <div className="pt-16 min-h-screen flex items-center justify-center">
      <Spinner className="w-8 h-8 text-vit-400" />
    </div>
  )
}

// ── Per-route wrapper: Suspense + isolated ErrorBoundary ──────────────────────
// A crash in one page never propagates to another page.

function wrap(element: React.ReactElement) {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        {element}
      </Suspense>
    </RouteErrorBoundary>
  )
}

// ── RequireAuth ───────────────────────────────────────────────────────────────

/**
 * RequireAuth — wraps every protected route.
 * Redirects unauthenticated users to /login while preserving the
 * intended destination so we can return them after login.
 * This is the single authoritative auth gate for all AppShell routes;
 * individual pages do not need to implement their own token checks.
 */
function RequireAuth() {
  const token    = getAuthToken()
  const location = useLocation()
  if (!token) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  return <Outlet />
}

// ── Public / marketing (lazy) ─────────────────────────────────────────────────
const Home          = lazy(() => import('@/pages/Home'))
const Platform      = lazy(() => import('@/pages/Platform'))
const AI            = lazy(() => import('@/pages/AI'))
const Storage       = lazy(() => import('@/pages/Storage'))
const Status        = lazy(() => import('@/pages/Status'))
const Developers    = lazy(() => import('@/pages/Developers'))
const Documentation = lazy(() => import('@/pages/Documentation'))
const Roadmap       = lazy(() => import('@/pages/Roadmap'))
const About         = lazy(() => import('@/pages/About'))

// ── Auth (lazy) ───────────────────────────────────────────────────────────────
const Login          = lazy(() => import('@/pages/Login'))
const ForgotPassword = lazy(() => import('@/pages/ForgotPassword'))
const ResetPassword  = lazy(() => import('@/pages/ResetPassword'))
const VerifyEmail    = lazy(() => import('@/pages/VerifyEmail'))

// ── Core app (lazy) ───────────────────────────────────────────────────────────
const Dashboard       = lazy(() => import('@/pages/Dashboard'))
const Workspace       = lazy(() => import('@/pages/Workspace'))
const Settings        = lazy(() => import('@/pages/Settings'))
const Subscription    = lazy(() => import('@/pages/Subscription'))
const Matches         = lazy(() => import('@/pages/Matches'))
const MatchDetail     = lazy(() => import('@/pages/MatchDetail'))
const Predictions     = lazy(() => import('@/pages/Predictions'))
const Odds            = lazy(() => import('@/pages/Odds'))
const Leaderboard     = lazy(() => import('@/pages/Leaderboard'))
const Analytics       = lazy(() => import('@/pages/Analytics'))
const AnalyticsStudio = lazy(() => import('@/pages/AnalyticsStudio'))
const Assistant       = lazy(() => import('@/pages/Assistant'))
const Tasks           = lazy(() => import('@/pages/Tasks'))

// ── Finance (lazy) ────────────────────────────────────────────────────────────
const Wallet      = lazy(() => import('@/pages/Wallet'))
const DeFi        = lazy(() => import('@/pages/DeFi'))
const InPlay      = lazy(() => import('@/pages/InPlay'))
const Marketplace = lazy(() => import('@/pages/Marketplace'))
const Referral    = lazy(() => import('@/pages/Referral'))

// ── Governance & network (lazy) ───────────────────────────────────────────────
const Governance = lazy(() => import('@/pages/Governance'))
const Treasury   = lazy(() => import('@/pages/Treasury'))
const Validators = lazy(() => import('@/pages/Validators'))
const Explorer   = lazy(() => import('@/pages/Explorer'))

// ── Social & ecosystem (lazy) ─────────────────────────────────────────────────
const Social     = lazy(() => import('@/pages/Social'))
const Ecosystem  = lazy(() => import('@/pages/Ecosystem'))
const Enterprise = lazy(() => import('@/pages/Enterprise'))

// ── Betting tools (lazy) ──────────────────────────────────────────────────────
const Accumulator = lazy(() => import('@/pages/Accumulator'))
const Rollover    = lazy(() => import('@/pages/Rollover'))
const Backtest    = lazy(() => import('@/pages/Backtest'))
const Bankroll    = lazy(() => import('@/pages/Bankroll'))

// ── Financial flows (lazy) ────────────────────────────────────────────────────
const VITCoin  = lazy(() => import('@/pages/VITCoin'))
const Exchange = lazy(() => import('@/pages/Exchange'))
const Vaults   = lazy(() => import('@/pages/Vaults'))
const Bridge   = lazy(() => import('@/pages/Bridge'))

// ── Admin & 404 (lazy) ────────────────────────────────────────────────────────
const Admin    = lazy(() => import('@/pages/Admin'))
const NotFound = lazy(() => import('@/pages/NotFound'))

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <Routes>
      {/* ── Public / marketing ─────────────────────────────────────────────── */}
      <Route element={<PublicShell />}>
        <Route path="/"                element={wrap(<Home />)}          />
        <Route path="/platform"        element={wrap(<Platform />)}       />
        <Route path="/ai"              element={wrap(<AI />)}             />
        <Route path="/storage"         element={wrap(<Storage />)}        />
        <Route path="/status"          element={wrap(<Status />)}         />
        <Route path="/developers"      element={wrap(<Developers />)}     />
        <Route path="/docs"            element={wrap(<Documentation />)}  />
        <Route path="/roadmap"         element={wrap(<Roadmap />)}        />
        <Route path="/about"           element={wrap(<About />)}          />
        <Route path="/login"           element={wrap(<Login />)}          />
        <Route path="/register"        element={wrap(<Login />)}          />
        <Route path="/forgot-password" element={wrap(<ForgotPassword />)} />
        <Route path="/reset-password"  element={wrap(<ResetPassword />)}  />
        <Route path="/verify-email"    element={wrap(<VerifyEmail />)}    />
      </Route>

      {/* ── Authenticated app ──────────────────────────────────────────────── */}
      <Route element={<RequireAuth />}>
      <Route element={<AppShell />}>
        <Route path="/dashboard"        element={wrap(<Dashboard />)}       />
        <Route path="/workspace"        element={wrap(<Workspace />)}       />
        <Route path="/settings"         element={wrap(<Settings />)}        />
        <Route path="/subscription"     element={wrap(<Subscription />)}    />
        <Route path="/matches"          element={wrap(<Matches />)}         />
        <Route path="/matches/:id"      element={wrap(<MatchDetail />)}     />
        <Route path="/predictions"      element={wrap(<Predictions />)}     />
        <Route path="/odds"             element={wrap(<Odds />)}            />
        <Route path="/leaderboard"      element={wrap(<Leaderboard />)}     />
        <Route path="/analytics"        element={wrap(<Analytics />)}       />
        <Route path="/analytics-studio" element={wrap(<AnalyticsStudio />)} />
        <Route path="/assistant"        element={wrap(<Assistant />)}       />
        <Route path="/tasks"            element={wrap(<Tasks />)}           />
        <Route path="/wallet"           element={wrap(<Wallet />)}          />
        <Route path="/defi"             element={wrap(<DeFi />)}            />
        <Route path="/inplay"           element={wrap(<InPlay />)}          />
        <Route path="/marketplace"      element={wrap(<Marketplace />)}     />
        <Route path="/referral"         element={wrap(<Referral />)}        />
        <Route path="/governance"       element={wrap(<Governance />)}      />
        <Route path="/treasury"         element={wrap(<Treasury />)}        />
        <Route path="/validators"       element={wrap(<Validators />)}      />
        <Route path="/chain"            element={wrap(<Explorer />)}        />
        <Route path="/explorer"         element={<Navigate to="/chain" replace />} />
        <Route path="/social"           element={wrap(<Social />)}          />
        <Route path="/ecosystem"        element={wrap(<Ecosystem />)}       />
        <Route path="/enterprise"       element={wrap(<Enterprise />)}      />
        <Route path="/accumulator"      element={wrap(<Accumulator />)}     />
        <Route path="/rollover"         element={wrap(<Rollover />)}        />
        <Route path="/backtest"         element={wrap(<Backtest />)}        />
        <Route path="/bankroll"         element={wrap(<Bankroll />)}        />
        <Route path="/vitcoin"          element={wrap(<VITCoin />)}         />
        <Route path="/exchange"         element={wrap(<Exchange />)}        />
        <Route path="/vaults"           element={wrap(<Vaults />)}          />
        <Route path="/bridge"           element={wrap(<Bridge />)}          />
        <Route path="/admin"            element={wrap(<Admin />)}           />
        <Route path="*"                 element={wrap(<NotFound />)}        />
      </Route>
      </Route>
    </Routes>
  )
}
