import React, { Suspense, useState, useEffect } from "react";
import { Switch, Route, Redirect, Router as WouterRouter, useLocation } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/lib/theme";
import { AuthProvider, useAuth } from "@/lib/auth";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ErrorBoundary } from "@/components/error-boundary";
import { Layout } from "@/components/layout";
import { GamblingAgeDisclaimer } from "@/components/gambling-age-disclaimer";
import { wagmiConfig } from "@/lib/web3";
import { WagmiProvider } from "wagmi";
import { lazyRetry } from "@/lib/lazy-retry";
import { usePublicConfig } from "@/lib/usePublicConfig";
import { RouteProgressBar } from "@/components/RouteProgressBar";
import { WelcomeModal, OnboardingTour } from "@/components/onboarding";

// Lazy-loaded pages with retry logic

function ConfigInitializer({ children }: { children: React.ReactNode }) {
  const { data } = usePublicConfig();
  React.useEffect(() => {
    if (data) { (window as any)._VIT_CONFIG = data; }
  }, [data]);
  return <>{children}</>;
}

const DashboardPage = lazyRetry(() => import("@/pages/dashboard"));
const AuthPage = lazyRetry(() => import("@/pages/auth"));
const LandingPage = lazyRetry(() => import("@/pages/landing"));
const MatchesPage = lazyRetry(() => import("@/pages/matches"));
const MatchDetailPage = lazyRetry(() => import("@/pages/match-detail"));
const PredictionsPage = lazyRetry(() => import("@/pages/predictions"));
const WalletRoot = lazyRetry(() => import("@/pages/wallet"));
const ValidatorsPage = lazyRetry(() => import("@/pages/validators"));
const TrainingPage = lazyRetry(() => import("@/pages/training"));
const AnalyticsPage = lazyRetry(() => import("@/pages/analytics"));
const SubscriptionPage = lazyRetry(() => import("@/pages/subscription"));
const MarketplacePage = lazyRetry(() => import("@/pages/marketplace"));
const TrustPage = lazyRetry(() => import("@/pages/trust"));
const BridgePage = lazyRetry(() => import("@/pages/bridge"));
const DeveloperPage = lazyRetry(() => import("@/pages/developer"));
const GovernancePage = lazyRetry(() => import("@/pages/governance"));
const AdminDashboardPage  = lazyRetry(() => import("@/pages/admin/AdminDashboard"));
const AdminUsersPage      = lazyRetry(() => import("@/pages/admin/AdminUsers"));
const AdminWalletPage     = lazyRetry(() => import("@/pages/admin/AdminWallet"));
const AdminMatchesPage    = lazyRetry(() => import("@/pages/admin/AdminMatches"));
const AdminValidatorsPage = lazyRetry(() => import("@/pages/admin/AdminValidators"));
const AdminModelsPage     = lazyRetry(() => import("@/pages/admin/AdminModels"));
const AdminMarketplacePage= lazyRetry(() => import("@/pages/admin/AdminMarketplace"));
const AdminConfigPage     = lazyRetry(() => import("@/pages/admin/AdminConfig"));
const AdminAuditLogPage   = lazyRetry(() => import("@/pages/admin/AdminAuditLog"));
const AdminSystemPage     = lazyRetry(() => import("@/pages/admin/AdminSystemHealth"));
const AccumulatorPage = lazyRetry(() => import("@/pages/accumulator"));
const RolloverPage    = lazyRetry(() => import("@/pages/rollover"));
const BacktestPage = lazyRetry(() => import("@/pages/backtest"));
const OddsPage = lazyRetry(() => import("@/pages/odds"));
const PaymentCallbackPage = lazyRetry(() => import("@/pages/payment-callback"));
const LeaderboardPage = lazyRetry(() => import("@/pages/leaderboard"));
const ReferralPage = lazyRetry(() => import("@/pages/referral"));
const SettingsPage = lazyRetry(() => import("@/pages/settings"));
const TasksPage = lazyRetry(() => import("@/pages/tasks"));
const AssistantPage = lazyRetry(() => import("@/pages/assistant"));
const OfferwallPage = lazyRetry(() => import("@/pages/offerwall"));
const AgentsPage = lazyRetry(() => import("@/pages/agents"));
const ReportsPage = lazyRetry(() => import("@/pages/reports"));
const OraclePage = lazyRetry(() => import("@/pages/oracle"));
const NetworkPage = lazyRetry(() => import("@/pages/network"));
const ResearchPage = lazyRetry(() => import("@/pages/research"));
const SmartContractsPage = lazyRetry(() => import("@/pages/smart-contracts"));
const TreasuryPage = lazyRetry(() => import("@/pages/treasury"));
const MeritPage = lazyRetry(() => import("@/pages/merit"));
const SecurityLayerPage = lazyRetry(() => import("@/pages/security"));
const RoadmapPage = lazyRetry(() => import("@/pages/roadmap"));
const IdentityPage = lazyRetry(() => import("@/pages/identity"));
const KYCPage = lazyRetry(() => import("@/pages/kyc"));
const IDLookupPage = lazyRetry(() => import("@/pages/id-lookup"));
const ModelPerformancePage = lazyRetry(() => import("@/pages/model-performance"));
const BankrollPage = lazyRetry(() => import("@/pages/bankroll"));
const WatchlistPage = lazyRetry(() => import("@/pages/watchlist"));
const StoragePage = lazyRetry(() => import("@/pages/storage"));
const ValueAnalyticsPage = lazyRetry(() => import("@/pages/value-intelligence"));
const ElectionsPage = lazyRetry(() => import("@/pages/elections"));
const PolicyPage = lazyRetry(() => import("@/pages/policy"));
const RemittancePage = lazyRetry(() => import("@/pages/remittance"));
const CommunityPage = lazyRetry(() => import("@/pages/community"));
const CampusPage = lazyRetry(() => import("@/pages/campus"));
const ProphecyPage = lazyRetry(() => import("@/pages/prophecy"));
const ExchangePage = lazyRetry(() => import("@/pages/exchange"));

// Simple components
const InfoPage = lazyRetry(() => import("@/pages/info"));
const ForgotPasswordPage = lazyRetry(() => import("@/pages/forgot-password"));
const ResetPasswordPage = lazyRetry(() => import("@/pages/reset-password"));
const VerifyEmailPage = lazyRetry(() => import("@/pages/verify-email"));
const NotFound = lazyRetry(() => import("@/pages/not-found"));
const DesignSystemTest = lazyRetry(() => import("@/pages/design-system-test"));

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

function OnboardingController() {
  const { user } = useAuth();
  const [, navigate] = useLocation();
  const [showWelcome, setShowWelcome] = useState(false);
  const [showTour, setShowTour] = useState(false);

  useEffect(() => {
    if (user && !localStorage.getItem("vit_welcomed")) {
      const timer = setTimeout(() => setShowWelcome(true), 800);
      return () => clearTimeout(timer);
    }
  }, [user]);

  const handleClose = () => {
    localStorage.setItem("vit_welcomed", "1");
    setShowWelcome(false);
    setShowTour(false);
  };

  const handleStartTour = () => {
    setShowWelcome(false);
    setShowTour(true);
  };

  if (!user) return null;

  return (
    <>
      {showWelcome && (
        <WelcomeModal
          username={(user as any).username ?? (user as any).email ?? "Explorer"}
          onClose={handleClose}
          onStartTour={handleStartTour}
        />
      )}
      {showTour && (
        <OnboardingTour
          onComplete={handleClose}
          onSkip={handleClose}
          onNavigate={(path) => { navigate(path); handleClose(); }}
        />
      )}
    </>
  );
}

function AdminGuard({ component: Component }: { component: React.ComponentType }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#080c12]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-[#00E676]/30 border-t-[#00E676] rounded-full animate-spin" />
          <span className="font-mono text-xs text-white/30 uppercase tracking-widest">Loading…</span>
        </div>
      </div>
    );
  }

  if (!user) return <Redirect to="/login" />;
  if (user.role !== "admin") return <Redirect to="/dashboard" />;

  return (
    <ErrorBoundary>
      <Component />
    </ErrorBoundary>
  );
}

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
      <Route path="/elections">
        <Layout><ProtectedRoute component={ElectionsPage} /></Layout>
      </Route>
      <Route path="/policy">
        <Layout><ProtectedRoute component={PolicyPage} /></Layout>
      </Route>
      <Route path="/finance">
        <Layout><ProtectedRoute component={RemittancePage} /></Layout>
      </Route>
      <Route path="/community">
        <Layout><ProtectedRoute component={CommunityPage} /></Layout>
      </Route>
      <Route path="/campus">
        <Layout><ProtectedRoute component={CampusPage} /></Layout>
      </Route>
      <Route path="/prophecy">
        <Layout><ProtectedRoute component={ProphecyPage} /></Layout>
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
      <Route path="/wallet/:rest*">
        <ProtectedRoute component={WalletRoot} />
      </Route>
      <Route path="/wallet">
        <ProtectedRoute component={WalletRoot} />
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
      <Route path="/admin/users">
        <AdminGuard component={AdminUsersPage} />
      </Route>
      <Route path="/admin/wallet">
        <AdminGuard component={AdminWalletPage} />
      </Route>
      <Route path="/admin/matches">
        <AdminGuard component={AdminMatchesPage} />
      </Route>
      <Route path="/admin/validators">
        <AdminGuard component={AdminValidatorsPage} />
      </Route>
      <Route path="/admin/models">
        <AdminGuard component={AdminModelsPage} />
      </Route>
      <Route path="/admin/marketplace">
        <AdminGuard component={AdminMarketplacePage} />
      </Route>
      <Route path="/admin/config">
        <AdminGuard component={AdminConfigPage} />
      </Route>
      <Route path="/admin/audit">
        <AdminGuard component={AdminAuditLogPage} />
      </Route>
      <Route path="/admin/system">
        <AdminGuard component={AdminSystemPage} />
      </Route>
      <Route path="/admin">
        <AdminGuard component={AdminDashboardPage} />
      </Route>
      <Route path="/accumulator">
        <Layout><ProtectedRoute component={AccumulatorPage} /></Layout>
      </Route>
      <Route path="/rollover">
        <Layout><ProtectedRoute component={RolloverPage} /></Layout>
      </Route>
      <Route path="/backtest">
        <Layout><ProtectedRoute component={BacktestPage} /></Layout>
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
      <Route path="/assistant">
        <Layout><ProtectedRoute component={AssistantPage} /></Layout>
      </Route>
      <Route path="/earn">
        <Layout><ProtectedRoute component={OfferwallPage} /></Layout>
      </Route>
      <Route path="/agents">
        <Layout><ProtectedRoute component={AgentsPage} /></Layout>
      </Route>
      <Route path="/reports">
        <Layout><ProtectedRoute component={ReportsPage} /></Layout>
      </Route>
      <Route path="/oracle">
        <Layout><ProtectedRoute component={OraclePage} /></Layout>
      </Route>
      <Route path="/network">
        <Layout><ProtectedRoute component={NetworkPage} /></Layout>
      </Route>
      <Route path="/research">
        <Layout><ProtectedRoute component={ResearchPage} /></Layout>
      </Route>
      <Route path="/smart-contracts">
        <Layout><ProtectedRoute component={SmartContractsPage} /></Layout>
      </Route>
      <Route path="/treasury">
        <Layout><ProtectedRoute component={TreasuryPage} /></Layout>
      </Route>
      <Route path="/merit">
        <Layout><ProtectedRoute component={MeritPage} /></Layout>
      </Route>
      <Route path="/security">
        <Layout><ProtectedRoute component={SecurityLayerPage} /></Layout>
      </Route>
      <Route path="/roadmap">
        <Layout><ProtectedRoute component={RoadmapPage} /></Layout>
      </Route>
      <Route path="/identity">
        <Layout><ProtectedRoute component={IdentityPage} /></Layout>
      </Route>
      <Route path="/kyc">
        <Layout><ProtectedRoute component={KYCPage} /></Layout>
      </Route>
      <Route path="/id/:sid" component={IDLookupPage} />
      <Route path="/id" component={IDLookupPage} />
      <Route path="/model-performance">
        <Layout><ProtectedRoute component={ModelPerformancePage} /></Layout>
      </Route>
      <Route path="/bankroll">
        <Layout><ProtectedRoute component={BankrollPage} /></Layout>
      </Route>
      <Route path="/watchlist">
        <Layout><ProtectedRoute component={WatchlistPage} /></Layout>
      </Route>
      <Route path="/storage">
        <Layout><ProtectedRoute component={StoragePage} /></Layout>
      </Route>
      <Route path="/exchange">
        <Layout><ProtectedRoute component={ExchangePage} /></Layout>
      </Route>
      <Route path="/value-intelligence">
        <Layout><ProtectedRoute component={ValueAnalyticsPage} /></Layout>
      </Route>
      <Route path="/forgot-password" component={ForgotPasswordPage} />
      <Route path="/reset-password" component={ResetPasswordPage} />
      <Route path="/verify-email" component={VerifyEmailPage} />
      <Route path="/design-system" component={DesignSystemTest} />
      <Route>
        <Layout><NotFound /></Layout>
      </Route>
    </Switch>
    </Suspense>
  );
}

function App() {
  return (
    <WagmiProvider config={wagmiConfig}>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
              <ConfigInitializer><AuthProvider>
                <RouteProgressBar />
                <GamblingAgeDisclaimer />
                <OnboardingController />
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
              </AuthProvider></ConfigInitializer>
            </WouterRouter>
          </TooltipProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </WagmiProvider>
  );
}

export default App;
