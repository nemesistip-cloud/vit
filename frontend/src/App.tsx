import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { Navbar }        from '@/components/layout/Navbar'
import { Footer }        from '@/components/layout/Footer'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import Home              from '@/pages/Home'
import Platform          from '@/pages/Platform'
import AI                from '@/pages/AI'
import Storage           from '@/pages/Storage'
import Status            from '@/pages/Status'
import Developers        from '@/pages/Developers'
import Documentation     from '@/pages/Documentation'
import Roadmap           from '@/pages/Roadmap'
import About             from '@/pages/About'
import Login             from '@/pages/Login'
import Matches           from '@/pages/Matches'
import Admin             from '@/pages/Admin'
import Dashboard         from '@/pages/Dashboard'
import Leaderboard       from '@/pages/Leaderboard'
import Wallet            from '@/pages/Wallet'
import Predictions       from '@/pages/Predictions'
import Explorer          from '@/pages/Explorer'
import Governance        from '@/pages/Governance'
import Treasury          from '@/pages/Treasury'
import Marketplace       from '@/pages/Marketplace'
import Referral          from '@/pages/Referral'
import Ecosystem         from '@/pages/Ecosystem'
import Social           from '@/pages/Social'
import DeFi             from '@/pages/DeFi'
import InPlay           from '@/pages/InPlay'
import AnalyticsStudio  from '@/pages/AnalyticsStudio'
import Enterprise       from '@/pages/Enterprise'
import NotFound         from '@/pages/NotFound'

export default function App() {
  return (
    <ErrorBoundary>
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/"             element={<Home />} />
            <Route path="/platform"     element={<Platform />} />
            <Route path="/ai"           element={<AI />} />
            <Route path="/storage"      element={<Storage />} />
            <Route path="/status"       element={<Status />} />
            <Route path="/developers"   element={<Developers />} />
            <Route path="/docs"         element={<Documentation />} />
            <Route path="/roadmap"      element={<Roadmap />} />
            <Route path="/about"        element={<About />} />
            <Route path="/login"        element={<Login />} />
            <Route path="/register"     element={<Login />} />
            <Route path="/matches"      element={<Matches />} />
            <Route path="/admin"        element={<Admin />} />
            <Route path="/dashboard"    element={<Dashboard />} />
            <Route path="/leaderboard"  element={<Leaderboard />} />
            <Route path="/wallet"       element={<Wallet />} />
            <Route path="/predictions"  element={<Predictions />} />
            <Route path="/chain"        element={<Explorer />} />
            {/* Legacy /explorer redirect — keeps old links working */}
            <Route path="/explorer"     element={<Navigate to="/chain" replace />} />
            <Route path="/governance"   element={<Governance />} />
            <Route path="/treasury"     element={<Treasury />} />
            <Route path="/marketplace"  element={<Marketplace />} />
            <Route path="/referral"     element={<Referral />} />
            <Route path="/ecosystem"    element={<Ecosystem />} />
            <Route path="/social"       element={<Social />} />
            <Route path="/defi"         element={<DeFi />} />
            <Route path="/inplay"       element={<InPlay />} />
            <Route path="/analytics-studio" element={<AnalyticsStudio />} />
            <Route path="/enterprise"   element={<Enterprise />} />
            {/* 404 — must be last */}
            <Route path="*"             element={<NotFound />} />
          </Routes>
        </main>
        <Footer />
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'hsl(var(--surface-800, 220 20% 14%))',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#fff',
            },
          }}
        />
      </div>
    </ErrorBoundary>
  )
}
