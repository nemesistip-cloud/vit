import { useState } from "react";
import { useLocation, Link, useSearch } from "wouter";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useLogin, useRegister, useGoogleLogin } from "@/api-client";
import { useAuth } from "@/lib/auth";
import { apiPost } from "@/lib/apiClient";
import { auth, googleProvider, isFirebaseConfigured } from "@/lib/firebase";
import { signInWithPopup } from "firebase/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ArrowRight, Sparkles, Eye, EyeOff, Shield, Brain, Coins, Gift, Lock } from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { WelcomeModal, OnboardingTour } from "@/components/onboarding";
import { usePublicConfig } from "@/lib/usePublicConfig";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

const registerSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  company_name: z.string().optional(),
  phone: z.string().optional(),
  referral_code: z.string().optional(),
});

// FEATURE_ITEMS is now constructed inside the component using /config/public,
// so the model count and welcome bonus track the live platform settings.

export default function AuthPage() {
  const [, setLocation] = useLocation();
  const search = useSearch();
  const { data: publicCfg } = usePublicConfig();
  const FEATURE_ITEMS = [
    { icon: Brain,  text: `${publicCfg?.platform.model_count ?? 13}-Model AI Ensemble` },
    { icon: Coins,  text: `${publicCfg?.platform.welcome_bonus_vit ?? 100} VIT Welcome Bonus` },
    { icon: Shield, text: "Blockchain Verified Results" },
  ];
  const { login: setAuthToken } = useAuth();

  const refCode = new URLSearchParams(search).get("ref") ?? "";

  const loginMutation = useLogin();
  const googleLoginMutation = useGoogleLogin();
  const registerMutation = useRegister();

  const [showPasswordLogin, setShowPasswordLogin] = useState(false);
  const [showPasswordRegister, setShowPasswordRegister] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const [newUsername, setNewUsername] = useState("");

  // 2FA step state
  const [totpStep, setTotpStep] = useState(false);
  const [preAuthToken, setPreAuthToken] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [totpLoading, setTotpLoading] = useState(false);

  const loginForm = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const registerForm = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", email: "", password: "", referral_code: refCode },
  });

  const onLoginSubmit = async (data: z.infer<typeof loginSchema>) => {
    try {
      const res = await loginMutation.mutateAsync({ data });
      // Check if 2FA is required before issuing full tokens
      if ((res as any).requires_2fa) {
        setPreAuthToken((res as any).pre_auth_token);
        setTotpCode("");
        setTotpStep(true);
        return;
      }
      setAuthToken(res.access_token, res.refresh_token);
      toast.success("Welcome back!");
    } catch (error: any) {
      const msg = error?.response?.data?.detail || error.message || "Login failed";
      toast.error(msg);
    }
  };

  const onTotpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totpCode.replace(/\s/g, "").length !== 6) {
      toast.error("Enter the 6-digit code from your authenticator app.");
      return;
    }
    setTotpLoading(true);
    try {
      const res = await apiPost<{ access_token: string; refresh_token: string }>(
        "/auth/2fa/complete-login",
        {
          pre_auth_token: preAuthToken,
          totp_code: totpCode.replace(/\s/g, ""),
        },
      );
      setAuthToken(res.access_token, res.refresh_token);
      toast.success("Welcome back!");
    } catch (error: any) {
      const msg = error?.response?.data?.detail || error.message || "Invalid code";
      toast.error(msg);
    } finally {
      setTotpLoading(false);
    }
  };

  const onRegisterSubmit = async (data: z.infer<typeof registerSchema>) => {
    try {
      const referralCode = data.referral_code?.trim().toUpperCase();
      const res = await registerMutation.mutateAsync({
        data: {
          username: data.username,
          email: data.email,
          password: data.password,
          company_name: data.company_name,
          phone: data.phone,
          ...(referralCode ? { referral_code: referralCode } : {}),
        },
      });
      setAuthToken(res.access_token, res.refresh_token);
      if (referralCode) {
        toast.success(`Referral applied — you and your referrer both earned 50 VIT!`);
      }
      setNewUsername(data.username);
      setShowWelcome(true);
    } catch (error: any) {
      const msg = error?.response?.data?.detail || error.message || "Registration failed";
      toast.error(msg);
    }
  };

  const handleCloseWelcome = () => {
    setShowWelcome(false);
    setLocation("/dashboard");
  };

  const handleStartTour = () => {
    setShowWelcome(false);
    setShowTour(true);
  };

  const handleCompleteTour = () => {
    setShowTour(false);
    setLocation("/dashboard");
  };

  const handleTourNavigate = (path: string) => {
    setShowTour(false);
    setLocation(path);
  };

  const onGoogleLogin = async () => {
    if (!isFirebaseConfigured || !auth || !googleProvider) {
      toast.error("Google Login is not configured on this environment.");
      return;
    }
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const idToken = await result.user.getIdToken();
      const res = await googleLoginMutation.mutateAsync({ id_token: idToken });
      setAuthToken(res.access_token, res.refresh_token);
      toast.success("Welcome back!");
    } catch (error: any) {
      console.error("Google Auth error:", error);
      const msg = error?.response?.data?.detail || error.message || "Google sign in failed";
      toast.error(msg);
    }
  };

  return (
    <>
      <div className="min-h-screen w-full flex bg-background relative overflow-hidden">
        {/* ── Left panel (desktop) ──────────────────────── */}
        <div className="hidden lg:flex flex-col justify-center items-center w-1/2 relative p-12">
          {/* Background effects */}
          <div className="absolute inset-0 pointer-events-none" style={{
            backgroundImage: 'linear-gradient(to right, rgba(0,245,255,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,245,255,0.05) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
            maskImage: 'radial-gradient(ellipse at center, black, transparent 70%)',
          }} />

          <div className="relative max-w-xs text-center">
            <div className="flex justify-center mb-8">
              <BrandLogo size={80} withWordmark={false} />
            </div>
            <h1 className="text-3xl font-bold font-mono tracking-tight mb-3">
              VIT<span className="text-primary">_OS</span>
            </h1>
            <p className="text-muted-foreground text-sm mb-8 leading-relaxed">
              Institutional-grade sports intelligence powered by 13 AI models.
            </p>
            <div className="space-y-3 text-left">
              {FEATURE_ITEMS.map(({ icon: Icon, text }) => (
                <div key={text} className="flex items-center gap-3 px-4 py-3 rounded-lg border border-border/30 bg-card/30">
                  <Icon className="w-4 h-4 text-primary flex-shrink-0" />
                  <span className="text-sm font-mono text-muted-foreground">{text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Right panel (auth form) ──────────────────── */}
        <div className="flex-1 flex items-center justify-center p-4 md:p-8 relative">
          {/* Mobile header */}
          <div className="absolute top-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 lg:hidden">
            <BrandLogo size={36} withWordmark={true} />
          </div>

          <div className="w-full max-w-sm mt-16 lg:mt-0">
            <Card className="border-border/60 bg-card shadow-2xl">
              <Tabs defaultValue="login" className="w-full">
                <CardHeader className="pb-0 pt-6 px-6">
                  <TabsList className="grid w-full grid-cols-2 bg-background/60 border border-border/50">
                    <TabsTrigger value="login" className="font-mono uppercase text-xs">Sign In</TabsTrigger>
                    <TabsTrigger value="register" className="font-mono uppercase text-xs">Register</TabsTrigger>
                  </TabsList>
                </CardHeader>

                <CardContent className="p-6">
                  {/* ── Login Tab ────────────────────────── */}
                  <TabsContent value="login" className="mt-0">
                    {totpStep ? (
                      /* ── 2FA verification step ── */
                      <div>
                        <div className="mb-5 flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <Lock className="w-4 h-4 text-primary" />
                          </div>
                          <div>
                            <h2 className="text-lg font-bold font-mono">Two-Factor Auth</h2>
                            <p className="text-xs text-muted-foreground font-mono mt-0.5">Open your authenticator app and enter the 6-digit code</p>
                          </div>
                        </div>
                        <form onSubmit={onTotpSubmit} className="space-y-4">
                          <div>
                            <label className="font-mono text-xs text-muted-foreground uppercase block mb-1.5">
                              Authenticator Code
                            </label>
                            <Input
                              value={totpCode}
                              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                              placeholder="000000"
                              maxLength={6}
                              autoFocus
                              inputMode="numeric"
                              className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-11 text-center tracking-[0.4em] text-lg"
                            />
                          </div>
                          <Button
                            type="submit"
                            className="w-full font-mono h-11 gap-2"
                            disabled={totpLoading || totpCode.length < 6}
                          >
                            {totpLoading ? (
                              <span className="flex items-center gap-2">
                                <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                                Verifying...
                              </span>
                            ) : (
                              <>Verify & Sign In <ArrowRight className="w-4 h-4" /></>
                            )}
                          </Button>
                          <button
                            type="button"
                            onClick={() => { setTotpStep(false); setPreAuthToken(""); setTotpCode(""); }}
                            className="w-full text-xs font-mono text-muted-foreground hover:text-foreground transition-colors text-center"
                          >
                            ← Back to login
                          </button>
                        </form>
                      </div>
                    ) : (
                      /* ── Normal login form ── */
                      <div>
                        <div className="mb-5">
                          <h2 className="text-lg font-bold font-mono">Welcome back</h2>
                          <p className="text-xs text-muted-foreground font-mono mt-0.5">Enter your credentials to access your account</p>
                        </div>
                        <Form {...loginForm}>
                          <form onSubmit={loginForm.handleSubmit(onLoginSubmit)} className="space-y-4">
                            <FormField
                              control={loginForm.control}
                              name="email"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel className="font-mono text-xs text-muted-foreground uppercase">Email</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="you@example.com"
                                      className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-10"
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage className="text-xs" />
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={loginForm.control}
                              name="password"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel className="font-mono text-xs text-muted-foreground uppercase">Password</FormLabel>
                                  <FormControl>
                                    <div className="relative">
                                      <Input
                                        type={showPasswordLogin ? "text" : "password"}
                                        placeholder="••••••••"
                                        className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-10 pr-10"
                                        {...field}
                                      />
                                      <button
                                        type="button"
                                        onClick={() => setShowPasswordLogin((s) => !s)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                      >
                                        {showPasswordLogin ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                      </button>
                                    </div>
                                  </FormControl>
                                  <FormMessage className="text-xs" />
                                </FormItem>
                              )}
                            />
                            <div className="text-right -mt-1">
                              <Link href="/forgot-password">
                                <span className="text-xs font-mono text-muted-foreground hover:text-primary cursor-pointer transition-colors">
                                  Forgot password?
                                </span>
                              </Link>
                            </div>
                            <Button
                              type="submit"
                              className="w-full font-mono h-11 gap-2"
                              disabled={loginMutation.isPending}
                            >
                              {loginMutation.isPending ? (
                                <span className="flex items-center gap-2">
                                  <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                                  Authenticating...
                                </span>
                              ) : (
                                <>Sign In <ArrowRight className="w-4 h-4" /></>
                              )}
                            </Button>

                            <div className="relative my-4">
                              <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-border/50" />
                              </div>
                              <div className="relative flex justify-center text-[10px] uppercase">
                                <span className="bg-card px-2 text-muted-foreground font-mono">Or continue with</span>
                              </div>
                            </div>

                            <Button
                              type="button"
                              variant="outline"
                              className="w-full font-mono h-11 gap-2 bg-background/40"
                              onClick={onGoogleLogin}
                              disabled={googleLoginMutation.isPending}
                            >
                              <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 6.23l3.66 2.84c.87-2.6 3.3-4.53 12-4.53z" />
                              </svg>
                              Google
                            </Button>
                          </form>
                        </Form>
                      </div>
                    )}
                  </TabsContent>

                  {/* ── Register Tab ─────────────────────── */}
                  <TabsContent value="register" className="mt-0">
                    <div className="mb-5">
                      <h2 className="text-lg font-bold font-mono">Create account</h2>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5 flex items-center gap-1.5">
                        <Sparkles className="w-3 h-3 text-secondary" />
                        Get 100 VIT welcome bonus on signup
                      </p>
                    </div>
                    <Form {...registerForm}>
                      <form onSubmit={registerForm.handleSubmit(onRegisterSubmit)} className="space-y-4">
                        <FormField
                          control={registerForm.control}
                          name="username"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="font-mono text-xs text-muted-foreground uppercase">Username</FormLabel>
                              <FormControl>
                                <Input
                                  placeholder="yourname"
                                  className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-10"
                                  {...field}
                                />
                              </FormControl>
                              <FormMessage className="text-xs" />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={registerForm.control}
                          name="email"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="font-mono text-xs text-muted-foreground uppercase">Email</FormLabel>
                              <FormControl>
                                <Input
                                  placeholder="you@example.com"
                                  className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-10"
                                  {...field}
                                />
                              </FormControl>
                              <FormMessage className="text-xs" />
                            </FormItem>
                          )}
                        />
                        <div className="grid grid-cols-2 gap-4">
                          <FormField
                            control={registerForm.control}
                            name="company_name"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="font-mono text-xs text-muted-foreground uppercase">Company Name</FormLabel>
                                <FormControl>
                                  <Input
                                    placeholder="Optional"
                                    className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-10"
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage className="text-xs" />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={registerForm.control}
                            name="phone"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="font-mono text-xs text-muted-foreground uppercase">Contact (Phone)</FormLabel>
                                <FormControl>
                                  <Input
                                    placeholder="Optional"
                                    className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-10"
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage className="text-xs" />
                              </FormItem>
                            )}
                          />
                        </div>
                        <FormField
                          control={registerForm.control}
                          name="password"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="font-mono text-xs text-muted-foreground uppercase">Password</FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <Input
                                    type={showPasswordRegister ? "text" : "password"}
                                    placeholder="Min 8 characters"
                                    className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-10 pr-10"
                                    {...field}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => setShowPasswordRegister((s) => !s)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                  >
                                    {showPasswordRegister ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                  </button>
                                </div>
                              </FormControl>
                              <FormMessage className="text-xs" />
                            </FormItem>
                          )}
                        />
                        <div className="grid grid-cols-1">
                          <FormField
                            control={registerForm.control}
                            name="referral_code"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="font-mono text-xs text-muted-foreground uppercase flex items-center gap-1.5">
                                  <Gift className="w-3 h-3 text-secondary" />
                                  Referral Code <span className="text-muted-foreground/50">(optional)</span>
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    placeholder="e.g. VITX12345"
                                    className="bg-background/60 font-mono border-border/60 focus-visible:ring-primary/50 h-10 tracking-widest uppercase"
                                    maxLength={9}
                                    {...field}
                                    onChange={e => field.onChange(e.target.value.toUpperCase())}
                                  />
                                </FormControl>
                                <FormMessage className="text-xs" />
                              </FormItem>
                            )}
                          />
                        </div>
                        <Button
                          type="submit"
                          className="w-full font-mono h-11 gap-2"
                          disabled={registerMutation.isPending}
                        >
                          {registerMutation.isPending ? (
                            <span className="flex items-center gap-2">
                              <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                              Creating account...
                            </span>
                          ) : (
                            <>Create Account <ArrowRight className="w-4 h-4" /></>
                          )}
                        </Button>
                        <p className="text-center text-[10px] font-mono text-muted-foreground">
                          By registering you agree to our Terms of Service
                        </p>
                      </form>
                    </Form>
                  </TabsContent>
                </CardContent>
              </Tabs>
            </Card>
          </div>
        </div>
      </div>

      {/* ── Modals ──────────────────────────────────────── */}
      {showWelcome && (
        <WelcomeModal
          username={newUsername}
          onClose={handleCloseWelcome}
          onStartTour={handleStartTour}
        />
      )}
      {showTour && (
        <OnboardingTour
          onComplete={handleCompleteTour}
          onSkip={handleCompleteTour}
          onNavigate={handleTourNavigate}
        />
      )}
    </>
  );
}
