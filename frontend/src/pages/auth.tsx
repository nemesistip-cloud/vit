import { useState } from "react";
import { useLocation, Link, useSearch } from "wouter";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useLogin, useRegister } from "@/api-client";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Trophy, ArrowRight, Sparkles, Eye, EyeOff, Shield, Brain, Coins, Gift } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { WelcomeModal, OnboardingTour } from "@/components/onboarding";

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

const FEATURE_ITEMS = [
  { icon: Brain,  text: "12-Model AI Ensemble" },
  { icon: Coins,  text: "100 VIT Welcome Bonus" },
  { icon: Shield, text: "Blockchain Verified Results" },
];

export default function AuthPage() {
  const [, setLocation] = useLocation();
  const search = useSearch();
  const { login: setAuthToken } = useAuth();

  const refCode = new URLSearchParams(search).get("ref") ?? "";

  const loginMutation = useLogin();
  const registerMutation = useRegister();

  const [showPasswordLogin, setShowPasswordLogin] = useState(false);
  const [showPasswordRegister, setShowPasswordRegister] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const [newUsername, setNewUsername] = useState("");

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
      setAuthToken(res.access_token, res.refresh_token);
      toast.success("Welcome back!");
    } catch (error: any) {
      const msg = error?.response?.data?.detail || error.message || "Login failed";
      toast.error(msg);
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
          <div className="absolute top-1/4 left-1/3 w-64 h-64 bg-primary/8 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-1/3 w-48 h-48 bg-purple-500/8 rounded-full blur-3xl pointer-events-none" />

          <div className="relative max-w-xs text-center">
            <div className="w-20 h-20 bg-primary/10 border-2 border-primary/30 rounded-2xl flex items-center justify-center mx-auto mb-8 vit-glow-cyan">
              <Trophy className="w-10 h-10 text-primary" />
            </div>
            <h1 className="text-3xl font-bold font-mono tracking-tight mb-3">
              VIT<span className="text-primary">_OS</span>
            </h1>
            <p className="text-muted-foreground text-sm mb-8 leading-relaxed">
              Institutional-grade sports intelligence powered by 12 AI models.
            </p>
            <div className="space-y-3 text-left">
              {FEATURE_ITEMS.map(({ icon: Icon, text }) => (
                <div key={text} className="flex items-center gap-3 px-4 py-3 rounded-lg border border-border/30 bg-card/30 backdrop-blur">
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
            <div className="w-10 h-10 bg-primary/10 border border-primary/30 rounded-xl flex items-center justify-center">
              <Trophy className="w-5 h-5 text-primary" />
            </div>
            <span className="font-bold font-mono text-sm">VIT<span className="text-primary">_OS</span></span>
          </div>

          <div className="w-full max-w-sm mt-16 lg:mt-0">
            <Card className="border-border/60 bg-card/60 backdrop-blur-md shadow-2xl">
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
                      </form>
                    </Form>
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
