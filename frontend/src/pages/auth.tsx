import { useState } from "react";
import { useLocation, Link, useSearch } from "wouter";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useLogin, useRegister } from "@/api-client";
import { useAuth } from "@/lib/auth";
import { apiPost } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { ArrowRight, Eye, EyeOff, Lock, Gift, Brain, Shield, Coins, TrendingUp, BarChart2 } from "lucide-react";
import { FcGoogle } from "react-icons/fc";
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
  referral_code: z.string().optional(),
});

export default function AuthPage() {
  const [, setLocation] = useLocation();
  const search = useSearch();
  const { data: publicCfg } = usePublicConfig();

  const STATS = [
    { icon: Brain,     label: `${publicCfg?.platform.model_count ?? 13} AI Models`,    color: "text-primary"     },
    { icon: TrendingUp, label: "CLV Tracking",                                          color: "text-primary"     },
    { icon: Shield,    label: "Blockchain Verified",                                    color: "text-emerald-400" },
    { icon: Coins,     label: `${publicCfg?.platform.welcome_bonus_vit ?? 100} VIT Bonus`, color: "text-primary"     },
    { icon: BarChart2, label: "Bankroll Management",                                    color: "text-emerald-400" },
  ];

  const { login: setAuthToken, loginWithGoogle } = useAuth();
  const refCode = new URLSearchParams(search).get("ref") ?? "";

  const loginMutation    = useLogin();
  const registerMutation = useRegister();

  const [showPasswordLogin,    setShowPasswordLogin]    = useState(false);
  const [showPasswordRegister, setShowPasswordRegister] = useState(false);
  const [showWelcome,  setShowWelcome]  = useState(false);
  const [showTour,     setShowTour]     = useState(false);
  const [newUsername,  setNewUsername]  = useState("");

  const [totpStep,       setTotpStep]       = useState(false);
  const [preAuthToken,   setPreAuthToken]   = useState("");
  const [totpCode,       setTotpCode]       = useState("");
  const [totpLoading,    setTotpLoading]    = useState(false);

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
        { pre_auth_token: preAuthToken, totp_code: totpCode.replace(/\s/g, "") },
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
          ...(referralCode ? { referral_code: referralCode } : {}),
        },
      });
      setAuthToken((res as any).access_token, (res as any).refresh_token);
      setNewUsername(data.username);
      setShowWelcome(true);
    } catch (error: any) {
      const msg = error?.response?.data?.detail || error.message || "Registration failed";
      toast.error(msg);
    }
  };

  const handleCloseWelcome  = () => { setShowWelcome(false); setLocation("/dashboard"); };
  const handleStartTour     = () => { setShowWelcome(false); setShowTour(true); };
  const handleCompleteTour  = () => { setShowTour(false); setLocation("/dashboard"); };
  const handleTourNavigate  = (path: string) => { setShowTour(false); setLocation(path); };

  return (
    <>
      <div className="min-h-screen w-full flex bg-background vit-section-contained relative">

        {/* ── Background effects ──────────────────────── */}
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: 'linear-gradient(to right, rgba(0,245,255,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,245,255,0.03) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }} />
        {/* Glow orbs — radial-gradient only, no CSS filter blur (avoids GPU compositing artifacts) */}
        <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96" style={{ background: 'radial-gradient(ellipse at center, rgba(0,245,255,0.07) 0%, transparent 68%)' }} />
          <div className="absolute bottom-1/4 right-1/4 w-64 h-64" style={{ background: 'radial-gradient(ellipse at center, rgba(168,85,247,0.07) 0%, transparent 68%)' }} />
        </div>

        {/* ── Left panel (desktop) ──────────────────────── */}
        <div className="hidden lg:flex flex-col justify-between w-5/12 relative p-12 border-r border-white/5">
          {/* Logo */}
          <BrandLogo withWordmark size={32} />

          {/* Main content */}
          <div className="space-y-8">
            <div>
              <h1 className="text-4xl font-bold font-mono tracking-tight leading-tight mb-4">
                Institutional-grade<br />
                <span className="vit-gradient-text">Sports Intelligence</span>
              </h1>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
                {publicCfg?.platform.model_count ?? 13} AI models working in ensemble to give you a measurable edge in every prediction.
              </p>
            </div>

            <div className="space-y-2.5">
              {STATS.map(({ icon: Icon, label, color }) => (
                <div key={label} className="flex items-center gap-3 px-4 py-3 rounded-xl border border-white/5 bg-white/[0.02]">
                  <div className={`w-7 h-7 rounded-lg bg-white/5 border border-white/8 flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-3.5 h-3.5 ${color}`} />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground">{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Footer note */}
          <p className="text-[10px] font-mono text-muted-foreground/40">
            © {new Date().getFullYear()} VIT Network · Blockchain Verified
          </p>
        </div>

        {/* ── Right panel (auth form) ──────────────────── */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 md:p-10 relative">

          {/* Mobile logo */}
          <div className="mb-10 lg:hidden">
            <BrandLogo withWordmark size={32} />
          </div>

          <div className="w-full max-w-sm">
            <Tabs defaultValue="login" className="w-full">

              {/* Tab switcher */}
              <TabsList className="grid w-full grid-cols-2 bg-white/[0.04] border border-white/8 mb-8 h-10">
                <TabsTrigger value="login" className="font-mono uppercase text-[10px] tracking-widest data-[state=active]:bg-primary/10 data-[state=active]:text-primary">
                  Sign In
                </TabsTrigger>
                <TabsTrigger value="register" className="font-mono uppercase text-[10px] tracking-widest data-[state=active]:bg-primary/10 data-[state=active]:text-primary">
                  Register
                </TabsTrigger>
              </TabsList>

              {/* ── Login Tab ────────────────────────── */}
              <TabsContent value="login" className="mt-0 space-y-0">
                {totpStep ? (
                  <div className="space-y-6">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                        <Lock className="w-4.5 h-4.5 text-primary" style={{ width: 18, height: 18 }} />
                      </div>
                      <div>
                        <h2 className="text-base font-bold font-mono">Two-Factor Auth</h2>
                        <p className="text-[11px] text-muted-foreground font-mono mt-0.5">Enter the 6-digit code from your app</p>
                      </div>
                    </div>
                    <form onSubmit={onTotpSubmit} className="space-y-4">
                      <div>
                        <label className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest block mb-2">
                          Authenticator Code
                        </label>
                        <Input
                          value={totpCode}
                          onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                          placeholder="000000"
                          maxLength={6}
                          autoFocus
                          inputMode="numeric"
                          className="h-12 text-center tracking-[0.5em] text-lg font-mono bg-white/[0.04] border-white/10 focus-visible:border-primary/40 focus-visible:ring-primary/20"
                        />
                      </div>
                      <Button type="submit" className="w-full h-11 font-mono gap-2 vit-glow-cyan-s" disabled={totpLoading || totpCode.length < 6}>
                        {totpLoading ? (
                          <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                            Verifying...
                          </span>
                        ) : (
                          <>Verify & Sign In <ArrowRight className="w-4 h-4" /></>
                        )}
                      </Button>
                      <button type="button" onClick={() => { setTotpStep(false); setPreAuthToken(""); setTotpCode(""); }}
                        className="w-full text-[11px] font-mono text-muted-foreground/60 hover:text-muted-foreground transition-colors text-center py-1">
                        ← Back to login
                      </button>
                    </form>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-xl font-bold font-mono">Welcome back</h2>
                      <p className="text-[11px] text-muted-foreground font-mono mt-1">Enter your credentials to continue</p>
                    </div>

                    <div className="space-y-4">
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full h-11 font-mono gap-3 bg-white/[0.02] border-white/10 hover:bg-white/[0.05]"
                        onClick={() => loginWithGoogle()}
                      >
                        <FcGoogle className="w-5 h-5" />
                        Sign in with Google
                      </Button>

                      <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                          <span className="w-full border-t border-white/5"></span>
                        </div>
                        <div className="relative flex justify-center text-[10px] uppercase tracking-widest">
                          <span className="bg-background px-2 text-muted-foreground/40">Or continue with</span>
                        </div>
                      </div>

                      <Form {...loginForm}>
                      <form onSubmit={loginForm.handleSubmit(onLoginSubmit)} className="space-y-4">
                        <FormField
                          control={loginForm.control}
                          name="email"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">Email</FormLabel>
                              <FormControl>
                                <Input
                                  placeholder="you@example.com"
                                  type="email"
                                  autoComplete="email"
                                  className="h-10 font-mono bg-white/[0.04] border-white/10 focus-visible:border-primary/40 focus-visible:ring-primary/20"
                                  {...field}
                                />
                              </FormControl>
                              <FormMessage className="text-xs font-mono" />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={loginForm.control}
                          name="password"
                          render={({ field }) => (
                            <FormItem>
                              <div className="flex items-center justify-between">
                                <FormLabel className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">Password</FormLabel>
                                <Link href="/forgot-password">
                                  <span className="text-[10px] font-mono text-muted-foreground/60 hover:text-primary cursor-pointer transition-colors">
                                    Forgot password?
                                  </span>
                                </Link>
                              </div>
                              <FormControl>
                                <div className="relative">
                                  <Input
                                    type={showPasswordLogin ? "text" : "password"}
                                    placeholder="••••••••"
                                    autoComplete="current-password"
                                    className="h-10 font-mono bg-white/[0.04] border-white/10 focus-visible:border-primary/40 focus-visible:ring-primary/20 pr-10"
                                    {...field}
                                  />
                                  <button type="button" onClick={() => setShowPasswordLogin((s) => !s)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-muted-foreground transition-colors">
                                    {showPasswordLogin ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                  </button>
                                </div>
                              </FormControl>
                              <FormMessage className="text-xs font-mono" />
                            </FormItem>
                          )}
                        />
                        <Button type="submit" className="w-full h-11 font-mono gap-2 mt-2 vit-glow-cyan-s" disabled={loginMutation.isPending}>
                          {loginMutation.isPending ? (
                            <span className="flex items-center gap-2">
                              <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                              Authenticating...
                            </span>
                          ) : (
                            <>Sign In <ArrowRight className="w-4 h-4" /></>
                          )}
                        </Button>
                      </form>
                    </Form>
                    </div>
                  </div>
                )}
              </TabsContent>

              {/* ── Register Tab ─────────────────────── */}
              <TabsContent value="register" className="mt-0 space-y-0">
                <div className="space-y-6">
                  <div>
                    <h2 className="text-xl font-bold font-mono">Create account</h2>
                    <p className="text-[11px] text-muted-foreground font-mono mt-1">
                      Get {publicCfg?.platform.welcome_bonus_vit ?? 100} VIT welcome bonus on signup
                    </p>
                  </div>

                  <div className="space-y-4">
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full h-11 font-mono gap-3 bg-white/[0.02] border-white/10 hover:bg-white/[0.05]"
                      onClick={() => loginWithGoogle()}
                    >
                      <FcGoogle className="w-5 h-5" />
                      Register with Google
                    </Button>

                    <div className="relative">
                      <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t border-white/5"></span>
                      </div>
                      <div className="relative flex justify-center text-[10px] uppercase tracking-widest">
                        <span className="bg-background px-2 text-muted-foreground/40">Or continue with</span>
                      </div>
                    </div>

                  <Form {...registerForm}>
                    <form onSubmit={registerForm.handleSubmit(onRegisterSubmit)} className="space-y-4">
                      <FormField
                        control={registerForm.control}
                        name="username"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">Username</FormLabel>
                            <FormControl>
                              <Input placeholder="yourname" autoComplete="username"
                                className="h-10 font-mono bg-white/[0.04] border-white/10 focus-visible:border-primary/40 focus-visible:ring-primary/20"
                                {...field} />
                            </FormControl>
                            <FormMessage className="text-xs font-mono" />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={registerForm.control}
                        name="email"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">Email</FormLabel>
                            <FormControl>
                              <Input placeholder="you@example.com" type="email" autoComplete="email"
                                className="h-10 font-mono bg-white/[0.04] border-white/10 focus-visible:border-primary/40 focus-visible:ring-primary/20"
                                {...field} />
                            </FormControl>
                            <FormMessage className="text-xs font-mono" />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={registerForm.control}
                        name="password"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">Password</FormLabel>
                            <FormControl>
                              <div className="relative">
                                <Input type={showPasswordRegister ? "text" : "password"} placeholder="Min 8 characters" autoComplete="new-password"
                                  className="h-10 font-mono bg-white/[0.04] border-white/10 focus-visible:border-primary/40 focus-visible:ring-primary/20 pr-10"
                                  {...field} />
                                <button type="button" onClick={() => setShowPasswordRegister((s) => !s)}
                                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-muted-foreground transition-colors">
                                  {showPasswordRegister ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                              </div>
                            </FormControl>
                            <FormMessage className="text-xs font-mono" />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={registerForm.control}
                        name="referral_code"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                              <Gift className="w-3 h-3 text-yellow-400" />
                              Referral Code <span className="text-muted-foreground/40 normal-case">(optional)</span>
                            </FormLabel>
                            <FormControl>
                              <Input placeholder="e.g. VITX12345" maxLength={9}
                                className="h-10 font-mono bg-white/[0.04] border-white/10 focus-visible:border-primary/40 focus-visible:ring-primary/20 tracking-widest uppercase"
                                {...field}
                                onChange={e => field.onChange(e.target.value.toUpperCase())} />
                            </FormControl>
                            <FormMessage className="text-xs font-mono" />
                          </FormItem>
                        )}
                      />
                      <Button type="submit" className="w-full h-11 font-mono gap-2 mt-2 vit-glow-cyan-s" disabled={registerMutation.isPending}>
                        {registerMutation.isPending ? (
                          <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                            Creating account...
                          </span>
                        ) : (
                          <>Create Account <ArrowRight className="w-4 h-4" /></>
                        )}
                      </Button>
                      <p className="text-center text-[10px] font-mono text-muted-foreground/40 pt-1">
                        By registering you agree to our Terms of Service
                      </p>
                    </form>
                  </Form>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>

      {showWelcome && (
        <WelcomeModal username={newUsername} onClose={handleCloseWelcome} onStartTour={handleStartTour} />
      )}
      {showTour && (
        <OnboardingTour onComplete={handleCompleteTour} onSkip={handleCompleteTour} onNavigate={handleTourNavigate} />
      )}
    </>
  );
}
