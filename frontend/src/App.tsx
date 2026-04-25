import { lazy, Suspense } from "react";
import { Switch, Route, Router as WouterRouter, Redirect } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { AuthProvider, useAuth } from "@/lib/auth";
import { ThemeProvider } from "@/lib/theme";
import { Layout } from "@/components/layout";
import { ErrorBoundary } from "@/components/error-boundary";

// Eager — first-paint surfaces (landing + auth) and the tiny info page used for legal routes.
import LandingPage from "@/pages/landing";
import AuthPage from "@/pages/auth";
import InfoPage from "@/pages/info";

// Lazy — every authenticated/secondary route ships in its own chunk.
const DashboardPage       = lazy(() => import("@/pages/dashboard"));
const MatchesPage         = lazy(() => import("@/pages/matches"));
const MatchDetailPage     = lazy(() => import("@/pages/match-detail"));
const PredictionsPage     = lazy(() => import("@/pages/predictions"));
const WalletPage          = lazy(() => import("@/pages/wallet"));
const ValidatorsPage      = lazy(() => import("@/pages/validators"));
const TrainingPage        = lazy(() => import("@/pages/training"));
const AnalyticsPage       = lazy(() => import("@/pages/analytics"));
const SubscriptionPage    = lazy(() => import("@/pages/subscription"));
const AdminPage           = lazy(() => import("@/pages/admin"));
const MarketplacePage     = lazy(() => import("@/pages/marketplace"));
const TrustPage           = lazy(() => import("@/pages/trust"));
const BridgePage          = lazy(() => import("@/pages/bridge"));
const DeveloperPage       = lazy(() => import("@/pages/developer"));
const GovernancePage      = lazy(() => import("@/pages/governance"));
const AccumulatorPage     = lazy(() => import("@/pages/accumulator"));
const OddsPage            = lazy(() => import("@/pages/odds"));
const PaymentCallbackPage = lazy(() => import("@/pages/payment-callback"));
const LeaderboardPage     = lazy(() => import("@/pages/leaderboard"));
const ReferralPage        = lazy(() => import("@/pages/referral"));
const SettingsPage        = lazy(() => import("@/pages/settings"));
const TasksPage           = lazy(() => import("@/pages/tasks"));
const ForgotPasswordPage  = lazy(() => import("@/pages/forgot-password"));
const ResetPasswordPage   = lazy(() => import("@/pages/reset-password"));
const VerifyEmailPage     = lazy(() => import("@/pages/verify-email"));

function RouteFallback() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        <span className="font-mono text-xs text-muted-foreground uppercase tracking-widest">Loading…</span>
      </div>
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        if (error?.message?.includes("401") || error?.message?.includes("Session expired")) return false;
        return failureCount < 2;
      },
      staleTime: 15_000,
    },
  },
});

function ProtectedRoute({ component: Component }: { component: React.ComponentType }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span className="font-mono text-xs text-muted-foreground uppercase tracking-widest">Initializing...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Redirect to="/login" />;
  }

  return (
    <ErrorBoundary>
      <Component />
    </ErrorBoundary>
  );
}

function Router() {
  const { user } = useAuth();

  return (
    <Suspense fallback={<RouteFallback />}>
    <Switch>
      <Route path="/">
        {user ? <Redirect to="/dashboard" /> : <LandingPage />}
      </Route>
      <Route path="/login" component={AuthPage} />
      <Route path="/register" component={AuthPage} />
      <Route path="/about"><InfoPage type="about" /></Route>
      <Route path="/terms"><InfoPage type="terms" /></Route>
      <Route path="/privacy"><InfoPage type="privacy" /></Route>
      <Route path="/contact"><InfoPage type="contact" /></Route>
      <Route path="/dashboard">
        <Layout>
          <ProtectedRoute component={DashboardPage} />
        </Layout>
      </Route>
      <Route path="/matches">
        <Layout><ProtectedRoute component={MatchesPage} /></Layout>
      </Route>
      <Route path="/matches/:id">
        <Layout><ProtectedRoute component={MatchDetailPage} /></Layout>
      </Route>
      <Route path="/predictions">
        <Layout><ProtectedRoute component={PredictionsPage} /></Layout>
      </Route>
      <Route path="/wallet">
        <Layout><ProtectedRoute component={WalletPage} /></Layout>
      </Route>
      <Route path="/validators">
        <Layout><ProtectedRoute component={ValidatorsPage} /></Layout>
      </Route>
      <Route path="/training">
        <Layout><ProtectedRoute component={TrainingPage} /></Layout>
      </Route>
      <Route path="/analytics">
        <Layout><ProtectedRoute component={AnalyticsPage} /></Layout>
      </Route>
      <Route path="/subscription">
        <Layout><ProtectedRoute component={SubscriptionPage} /></Layout>
      </Route>
      <Route path="/marketplace">
        <Layout><ProtectedRoute component={MarketplacePage} /></Layout>
      </Route>
      <Route path="/trust">
        <Layout><ProtectedRoute component={TrustPage} /></Layout>
      </Route>
      <Route path="/bridge">
        <Layout><ProtectedRoute component={BridgePage} /></Layout>
      </Route>
      <Route path="/developer">
        <Layout><ProtectedRoute component={DeveloperPage} /></Layout>
      </Route>
      <Route path="/governance">
        <Layout><ProtectedRoute component={GovernancePage} /></Layout>
      </Route>
      <Route path="/admin">
        <Layout><ProtectedRoute component={AdminPage} /></Layout>
      </Route>
      <Route path="/accumulator">
        <Layout><ProtectedRoute component={AccumulatorPage} /></Layout>
      </Route>
      <Route path="/odds">
        <Layout><ProtectedRoute component={OddsPage} /></Layout>
      </Route>
      <Route path="/payment/callback" component={PaymentCallbackPage} />
      <Route path="/leaderboard">
        <Layout><ProtectedRoute component={LeaderboardPage} /></Layout>
      </Route>
      <Route path="/referral">
        <Layout><ProtectedRoute component={ReferralPage} /></Layout>
      </Route>
      <Route path="/settings">
        <Layout><ProtectedRoute component={SettingsPage} /></Layout>
      </Route>
      <Route path="/tasks">
        <Layout><ProtectedRoute component={TasksPage} /></Layout>
      </Route>
      <Route path="/forgot-password" component={ForgotPasswordPage} />
      <Route path="/reset-password" component={ResetPasswordPage} />
      <Route path="/verify-email" component={VerifyEmailPage} />
      <Route>
        <Layout><NotFound /></Layout>
      </Route>
    </Switch>
    </Suspense>
  );
}

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
            <AuthProvider>
              <ErrorBoundary>
                <Router />
              </ErrorBoundary>
              <Toaster
                position="bottom-right"
                toastOptions={{
                  classNames: {
                    toast: "font-mono text-xs",
                    title: "font-mono text-sm",
                    description: "font-mono text-xs",
                  },
                }}
              />
            </AuthProvider>
          </WouterRouter>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
