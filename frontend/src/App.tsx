import { Switch, Route, Router as WouterRouter, Redirect } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { AuthProvider, useAuth } from "@/lib/auth";
import { ThemeProvider } from "@/lib/theme";
import { Layout } from "@/components/layout";
import { ErrorBoundary } from "@/components/error-boundary";

import LandingPage from "@/pages/landing";
import AuthPage from "@/pages/auth";
import DashboardPage from "@/pages/dashboard";
import MatchesPage from "@/pages/matches";
import MatchDetailPage from "@/pages/match-detail";
import PredictionsPage from "@/pages/predictions";
import WalletPage from "@/pages/wallet";
import ValidatorsPage from "@/pages/validators";
import TrainingPage from "@/pages/training";
import AnalyticsPage from "@/pages/analytics";
import SubscriptionPage from "@/pages/subscription";
import AdminPage from "@/pages/admin";
import MarketplacePage from "@/pages/marketplace";
import TrustPage from "@/pages/trust";
import BridgePage from "@/pages/bridge";
import DeveloperPage from "@/pages/developer";
import GovernancePage from "@/pages/governance";
import AccumulatorPage from "@/pages/accumulator";
import OddsPage from "@/pages/odds";
import PaymentCallbackPage from "@/pages/payment-callback";
import LeaderboardPage from "@/pages/leaderboard";
import ReferralPage from "@/pages/referral";
import SettingsPage from "@/pages/settings";
import ForgotPasswordPage from "@/pages/forgot-password";
import ResetPasswordPage from "@/pages/reset-password";
import VerifyEmailPage from "@/pages/verify-email";
import InfoPage from "@/pages/info";

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
      <Route path="/forgot-password" component={ForgotPasswordPage} />
      <Route path="/reset-password" component={ResetPasswordPage} />
      <Route path="/verify-email" component={VerifyEmailPage} />
      <Route>
        <Layout><NotFound /></Layout>
      </Route>
    </Switch>
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
