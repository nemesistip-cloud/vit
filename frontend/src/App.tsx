import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate, Outlet, useLocation, useParams } from 'react-router-dom'
import { AppShell, PublicShell } from '@/components/shell/AppShell'
import { getAuthToken } from '@/hooks/useAuth'
import { RouteErrorBoundary } from '@/components/ErrorBoundary'
import { Spinner } from '@/components/ui/Spinner'
import { VITPredictShell } from '@/components/shell/VITPredictShell'
import { ROUTES } from '@/lib/navigation'

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
    return <Navigate to={ROUTES.login} state={{ from: location.pathname }} replace />
  }
  return <Outlet />
}

function RequireGuest() {
  const token    = getAuthToken()
  const location = useLocation()
  if (token) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from && from.startsWith('/') ? from : ROUTES.dashboard} replace />
  }
  return <Outlet />
}


function PublicHomeGate() {
  return getAuthToken() ? <Navigate to={ROUTES.dashboard} replace /> : <NetworkOverview />
}

function LegacyMatchRedirect() {
  const { id } = useParams()
  return <Navigate to={`${ROUTES.vitpredictMatches}/${id ?? ''}`} replace />
}

function ValidatorsShell() {
  return getAuthToken() ? <AppShell /> : <PublicShell />
}

// ── Public / marketing (lazy) ─────────────────────────────────────────────────
const Platform      = lazy(() => import('@/pages/Platform'))
const AI            = lazy(() => import('@/pages/AI'))
const Storage       = lazy(() => import('@/pages/Storage'))
const Status        = lazy(() => import('@/pages/Status'))
const Verification  = lazy(() => import('@/pages/Verification'))
const Developers    = lazy(() => import('@/pages/Developers'))
const Documentation = lazy(() => import('@/pages/Documentation'))
const Roadmap       = lazy(() => import('@/pages/Roadmap'))
const About         = lazy(() => import('@/pages/About'))
const ResponsibleUse = lazy(() => import('@/pages/ResponsibleUse'))
const Applications = lazy(() => import('@/pages/Applications'))
const NetworkOverview = lazy(() => import('@/pages/NetworkOverview'))
const Home = lazy(() => import('@/pages/Home'))

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
const Genesis     = lazy(() => import('@/pages/Genesis'))
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
const VITPredictApp = lazy(() => import('@/pages/VITPredictApp'))

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <Routes>
      {/* ── Public / marketing ─────────────────────────────────────────────── */}
      <Route element={<PublicShell />}>
        <Route path={ROUTES.home}           element={wrap(<PublicHomeGate />)} />
        <Route path={ROUTES.platform}       element={wrap(<Platform />)} />
        <Route path={ROUTES.ai}             element={wrap(<AI />)} />
        <Route path={ROUTES.storage}        element={wrap(<Storage />)} />
        <Route path={ROUTES.status}         element={wrap(<Status />)} />
        <Route path={ROUTES.verification}   element={<Navigate to={ROUTES.vitpredictVerification} replace />} />
        <Route path={ROUTES.developers}     element={wrap(<Developers />)} />
        <Route path={ROUTES.docs}           element={wrap(<Documentation />)} />
        <Route path={ROUTES.responsibleUse} element={wrap(<ResponsibleUse />)} />
        <Route path={ROUTES.roadmap}        element={wrap(<Roadmap />)} />
        <Route path={ROUTES.about}          element={wrap(<About />)} />
        <Route path={ROUTES.applications}   element={wrap(<Applications />)} />
        {/* Legacy product URLs remain compatible while the app owns its routes. */}
        <Route path={ROUTES.matches}       element={<Navigate to={ROUTES.vitpredictMatches} replace />} />
        <Route path="/matches/:id"     element={<LegacyMatchRedirect />} />
        <Route path={ROUTES.predictions} element={<Navigate to={ROUTES.vitpredictPredictions} replace />} />
        <Route path={ROUTES.odds}        element={<Navigate to={ROUTES.vitpredictOdds} replace />} />
        <Route path={ROUTES.analyticsStudio} element={<Navigate to={ROUTES.vitpredictAnalytics} replace />} />
        <Route path="/leaderboard"     element={wrap(<Leaderboard />)}    />
        <Route path={ROUTES.governance} element={wrap(<Governance />)} />
        <Route path={ROUTES.marketplace} element={wrap(<Marketplace />)} />
        <Route path={ROUTES.explorer} element={wrap(<Explorer />)} />
        <Route path="/validators/:validatorId"     element={wrap(<Validators />)} />
        <Route path="/validators/:validatorId/:tab" element={wrap(<Validators />)} />
        <Route path="/network/validators"          element={wrap(<Validators />)} />
        <Route path="/explorer"        element={<Navigate to={ROUTES.explorer} replace />} />
        <Route element={<RequireGuest />}>
          <Route path={ROUTES.login}    element={wrap(<Login />)} />
          <Route path={ROUTES.register} element={wrap(<Login />)} />
        </Route>
        <Route path={ROUTES.forgotPassword} element={wrap(<ForgotPassword />)} />
        <Route path={ROUTES.resetPassword}  element={wrap(<ResetPassword />)} />
        <Route path={ROUTES.verifyEmail}    element={wrap(<VerifyEmail />)} />
      </Route>

      <Route element={<ValidatorsShell />}>
        <Route path={ROUTES.validators} element={wrap(<Validators />)} />
      </Route>

      <Route path={ROUTES.vitpredict} element={<VITPredictShell />}>
        <Route index element={wrap(<VITPredictApp />)} />
        <Route path="home" element={wrap(<Home />)} />
        <Route path="verification" element={wrap(<Verification />)} />
        <Route element={<RequireAuth />}>
          <Route path="dashboard" element={wrap(<Dashboard />)} />
        </Route>
        <Route path="matches" element={wrap(<Matches />)} />
        <Route path="matches/:id" element={wrap(<MatchDetail />)} />
        <Route element={<RequireAuth />}>
          <Route path="predictions" element={wrap(<Predictions />)} />
          <Route path="odds" element={wrap(<Odds />)} />
          <Route path="analytics" element={wrap(<AnalyticsStudio />)} />
        </Route>
      </Route>

      {/* ── Authenticated app ──────────────────────────────────────────────── */}
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
            <Route path={ROUTES.dashboard}      element={wrap(<NetworkOverview />)} />
            <Route path={ROUTES.workspace}      element={wrap(<Workspace />)} />
            <Route path={ROUTES.settings}       element={wrap(<Settings />)} />
            <Route path={ROUTES.subscription}   element={wrap(<Subscription />)} />
            <Route path={ROUTES.analytics}      element={wrap(<Analytics />)} />
            <Route path={ROUTES.assistant}      element={wrap(<Assistant />)} />
            <Route path={ROUTES.tasks}          element={wrap(<Tasks />)} />
            <Route path={ROUTES.wallet}         element={wrap(<Wallet />)} />
            <Route path={ROUTES.defi}           element={wrap(<DeFi />)} />
            <Route path={ROUTES.inPlay}         element={wrap(<InPlay />)} />
            <Route path={ROUTES.genesis}        element={wrap(<Genesis />)} />
            <Route path={ROUTES.referral}       element={wrap(<Referral />)} />
            <Route path={ROUTES.treasury}       element={wrap(<Treasury />)} />
            <Route path={ROUTES.social}         element={wrap(<Social />)} />
            <Route path={ROUTES.ecosystem}      element={wrap(<Ecosystem />)} />
            <Route path={ROUTES.enterprise}     element={wrap(<Enterprise />)} />
            <Route path="/accumulator"      element={wrap(<Accumulator />)}     />
            <Route path="/rollover"         element={wrap(<Rollover />)}        />
            <Route path="/backtest"         element={wrap(<Backtest />)}        />
            <Route path="/bankroll"         element={wrap(<Bankroll />)}        />
            <Route path="/vitcoin"          element={wrap(<VITCoin />)}         />
            <Route path="/exchange"         element={wrap(<Exchange />)}        />
            <Route path="/vaults"           element={wrap(<Vaults />)}          />
            <Route path="/bridge"           element={wrap(<Bridge />)}          />
            <Route path={ROUTES.admin}      element={wrap(<Admin />)} />
            <Route path={`${ROUTES.admin}/:tab`} element={wrap(<Admin />)} />
            <Route path="*"                 element={wrap(<NotFound />)}        />
          </Route>
      </Route>
    </Routes>
  )
}
