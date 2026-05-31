import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Trophy, TrendingUp, Target, BarChart3, Share2, Sparkles, ChevronRight, ChevronLeft, Brain, Coins, Activity } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function PredictionWrappedPage() {
  const [slide, setSlide] = useState(0);
  const { user } = useAuth();

  const { data: summary, isLoading: loadingSummary } = useQuery<any>({
    queryKey: ["/api/dashboard/summary"],
    queryFn: () => apiGet("/api/dashboard/summary"),
    staleTime: 60_000,
  });

  const { data: analytics, isLoading: loadingAnalytics } = useQuery<any>({
    queryKey: ["/analytics/my"],
    queryFn: () => apiGet("/api/analytics/my"),
    staleTime: 60_000,
  });

  const { data: wallet, isLoading: loadingWallet } = useQuery<any>({
    queryKey: ["/api/wallet/me"],
    queryFn: () => apiGet("/api/wallet/me"),
    staleTime: 60_000,
  });

  const isLoading = loadingSummary || loadingAnalytics;

  const totalPredictions = summary?.total_predictions ?? 0;
  const accuracyRate = summary?.accuracy_rate ?? 0;
  const accuracyPct = (accuracyRate * 100).toFixed(1);
  const streak = summary?.streak ?? 0;
  const vitBalance = summary?.wallet_balance ?? wallet?.balance ?? 0;
  const roi = analytics?.roi ?? summary?.roi ?? 0;
  const username = user?.username ?? "Predictor";

  // Derive personality from real data
  const getPersonality = () => {
    if (accuracyRate >= 0.70) return { title: "The Sharp", sub: "Top-tier accuracy. You beat the market consistently." };
    if (accuracyRate >= 0.60) return { title: "The Analyst", sub: "Methodical, data-driven. You let the models work." };
    if (streak >= 5) return { title: "The Streaker", sub: "Hot hands. You ride momentum well." };
    if (totalPredictions >= 50) return { title: "The Volume Trader", sub: "High volume, consistent process." };
    return { title: "The Contender", sub: "Building your edge. The data is on your side." };
  };

  const personality = getPersonality();

  const data = [
    {
      title: `${username}'s Season`,
      main: totalPredictions > 0
        ? `${totalPredictions} Predictions Made`
        : "Your Season Begins",
      sub: totalPredictions > 0
        ? `${accuracyPct}% accuracy · ${streak > 0 ? `${streak} win streak` : "building momentum"}`
        : "Make your first prediction to start tracking your story.",
      icon: <Trophy className="w-14 h-14 text-yellow-400" />,
      color: "from-zinc-900 to-yellow-900/20",
      stat: totalPredictions > 0 ? accuracyPct + "%" : "—",
      stat_label: "Win Rate",
    },
    {
      title: "Your Edge",
      main: roi !== 0 ? `${roi > 0 ? "+" : ""}${(roi * 100).toFixed(1)}% ROI` : "Building ROI",
      sub: roi > 0
        ? "Positive expected value. You're beating the market."
        : roi < 0
        ? "ROI tracking active. Every data point sharpens the model."
        : "Run more predictions to populate your ROI curve.",
      icon: <TrendingUp className="w-14 h-14 text-primary" />,
      color: "from-zinc-900 to-cyan-900/20",
      stat: roi !== 0 ? `${roi > 0 ? "+" : ""}${(roi * 100).toFixed(1)}%` : "—",
      stat_label: "ROI",
    },
    {
      title: "Model Accuracy",
      main: accuracyRate > 0
        ? `${accuracyPct}% Win Rate`
        : "Calibrating...",
      sub: accuracyRate >= 0.65
        ? "Above market average. The ensemble is working for you."
        : accuracyRate > 0
        ? `${(accuracyRate * 100).toFixed(1)}% — against a raw market baseline of ~50%. Keep compounding.`
        : "Run predictions to see your accuracy vs the 50% market baseline.",
      icon: <Target className="w-14 h-14 text-emerald-400" />,
      color: "from-zinc-900 to-emerald-900/20",
      stat: totalPredictions > 0 ? accuracyPct + "%" : "—",
      stat_label: "Accuracy",
    },
    {
      title: "Your Profile",
      main: personality.title,
      sub: personality.sub,
      icon: <Brain className="w-14 h-14 text-purple-400" />,
      color: "from-zinc-900 to-purple-900/20",
      stat: vitBalance > 0 ? Math.round(vitBalance).toLocaleString() : "—",
      stat_label: "VIT Balance",
    },
  ];

  if (isLoading) {
    return (
      <div className="max-w-xl mx-auto px-4 py-12 space-y-4">
        <Skeleton className="h-8 w-48 mx-auto" />
        <Skeleton className="w-full aspect-[4/5] rounded-[2rem]" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-14 rounded-2xl" />
          <Skeleton className="h-14 rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto px-4 py-8 flex flex-col items-center space-y-6">
      {/* Progress dots */}
      <div className="w-full flex items-center justify-between px-2">
        <div className="flex gap-1.5">
          {data.map((_, i) => (
            <button
              key={i}
              onClick={() => setSlide(i)}
              className={`h-1 rounded-full transition-all ${
                i === slide ? "w-8 bg-primary" : i < slide ? "w-5 bg-primary/50" : "w-5 bg-muted/50"
              }`}
            />
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-[10px] border-primary/30 text-muted-foreground">
            #VITWRAPPED 2025
          </Badge>
        </div>
      </div>

      {/* Slide card */}
      <div className="w-full aspect-[4/5] relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={slide}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.25 }}
            className={`w-full h-full bg-gradient-to-b ${data[slide].color} border border-border/50 rounded-[2rem] p-8 flex flex-col items-center justify-center text-center space-y-6 shadow-2xl overflow-hidden relative`}
          >
            <div className="absolute inset-0 pointer-events-none opacity-10"
              style={{
                backgroundImage: "radial-gradient(circle at 50% 0%, rgba(0,245,255,0.3), transparent 60%)",
              }}
            />

            <div className="relative z-10 flex flex-col items-center space-y-6">
              <div className="p-5 bg-white/5 rounded-full backdrop-blur-xl">
                {data[slide].icon}
              </div>

              <div>
                <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-widest mb-3">{data[slide].title}</h3>
                <h2 className="text-3xl font-bold font-mono tracking-tight leading-tight vit-gradient-text">
                  {data[slide].main}
                </h2>
                <p className="mt-4 text-muted-foreground max-w-[280px] mx-auto text-sm leading-relaxed">
                  {data[slide].sub}
                </p>
              </div>

              {data[slide].stat !== "—" && (
                <div className="bg-white/5 border border-white/10 rounded-2xl px-6 py-3 backdrop-blur-sm">
                  <div className="text-2xl font-bold font-mono text-primary">{data[slide].stat}</div>
                  <div className="text-[10px] font-mono text-muted-foreground uppercase mt-0.5">{data[slide].stat_label}</div>
                </div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <div className="w-full grid grid-cols-2 gap-4">
        <Button
          variant="outline"
          className="h-12 border-border/50 font-mono text-sm rounded-2xl"
          onClick={() => setSlide(s => Math.max(0, s - 1))}
          disabled={slide === 0}
        >
          <ChevronLeft className="mr-2 w-4 h-4" /> Back
        </Button>
        {slide < data.length - 1 ? (
          <Button
            className="h-12 font-mono text-sm rounded-2xl vit-glow-cyan"
            onClick={() => setSlide(s => s + 1)}
          >
            Next <ChevronRight className="ml-2 w-4 h-4" />
          </Button>
        ) : (
          <Button
            className="h-12 font-mono text-sm rounded-2xl bg-primary/10 text-primary border border-primary/30 hover:bg-primary/20"
            variant="outline"
          >
            <Share2 className="mr-2 w-4 h-4" /> Share
          </Button>
        )}
      </div>

      {/* Quick stats strip */}
      {totalPredictions > 0 && (
        <div className="w-full grid grid-cols-3 gap-3 text-center">
          {[
            { label: "Predictions", value: totalPredictions.toLocaleString(), color: "text-primary" },
            { label: "Accuracy", value: accuracyPct + "%", color: "text-green-400" },
            { label: "VIT Balance", value: Math.round(vitBalance).toLocaleString(), color: "text-yellow-400" },
          ].map((s) => (
            <div key={s.label} className="bg-card/40 border border-border/30 rounded-xl px-2 py-3">
              <div className={`text-lg font-bold font-mono ${s.color}`}>{s.value}</div>
              <div className="text-[9px] font-mono text-muted-foreground uppercase mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
