import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trophy, TrendingUp, Target, BarChart3, Share2, Sparkles, ChevronRight, ChevronLeft } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function PredictionWrappedPage() {
  const [slide, setSlide] = useState(0);

  const data = [
    {
      title: "Your 2024 Story",
      main: "You're in the top 5% of all predictors",
      sub: "Analytical mind. Calculated risks.",
      icon: <Trophy className="w-16 h-16 text-yellow-400" />,
      color: "from-zinc-900 to-yellow-900/20"
    },
    {
      title: "The Big Win",
      main: "Lakers vs Celtics @ 4.50",
      sub: "Your most profitable call of the season. Pure intuition.",
      icon: <Sparkles className="w-16 h-16 text-cyan-400" />,
      color: "from-zinc-900 to-cyan-900/20"
    },
    {
      title: "Accuracy Profile",
      main: "58.4% Win Rate",
      sub: "Against a market average of 42.1%. You found the edge.",
      icon: <Target className="w-16 h-16 text-emerald-400" />,
      color: "from-zinc-900 to-emerald-900/20"
    },
    {
      title: "Your Personality",
      main: "The Calculated Aggressor",
      sub: "You thrive on high-confidence underdogs.",
      icon: <TrendingUp className="w-16 h-16 text-purple-400" />,
      color: "from-zinc-900 to-purple-900/20"
    }
  ];

  return (
    <div className="max-w-xl mx-auto px-4 py-12 flex flex-col items-center">
      <div className="w-full flex justify-between mb-8 px-2">
        <div className="flex gap-1">
          {data.map((_, i) => (
            <div key={i} className={`h-1 w-8 rounded-full ${i <= slide ? "bg-white" : "bg-zinc-800"}`} />
          ))}
        </div>
        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">#VITWRAPPED 2024</span>
      </div>

      <div className="w-full aspect-[4/5] relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={slide}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className={`w-full h-full bg-gradient-to-b ${data[slide].color} border border-border/50 rounded-[2rem] p-8 flex flex-col items-center justify-center text-center space-y-8 shadow-2xl overflow-hidden relative`}
          >
            <div className="absolute inset-0 bg-zinc-950/20 opacity-20" />

            <div className="relative z-10">
              <div className="mb-6 p-6 bg-white/5 rounded-full backdrop-blur-xl inline-block">
                {data[slide].icon}
              </div>
              <h3 className="text-sm font-mono text-zinc-400 uppercase tracking-widest mb-4">{data[slide].title}</h3>
              <h2 className="text-4xl font-black italic uppercase leading-tight tracking-tighter">
                {data[slide].main}
              </h2>
              <p className="mt-6 text-zinc-400 max-w-[280px] mx-auto text-lg leading-relaxed">
                {data[slide].sub}
              </p>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="w-full grid grid-cols-2 gap-4 mt-8">
        <Button
          variant="outline"
          className="h-14 border-zinc-800 bg-zinc-900/50 rounded-2xl"
          onClick={() => setSlide(s => Math.max(0, s - 1))}
          disabled={slide === 0}
        >
          <ChevronLeft className="mr-2" /> Back
        </Button>
        {slide < data.length - 1 ? (
          <Button
            className="h-14 bg-white text-black hover:bg-zinc-200 rounded-2xl"
            onClick={() => setSlide(s => s + 1)}
          >
            Next <ChevronRight className="ml-2" />
          </Button>
        ) : (
          <Button
            className="h-14 bg-cyan-600 hover:bg-cyan-500 rounded-2xl"
          >
            <Share2 className="mr-2 w-5 h-5" /> Share Wrapped
          </Button>
        )}
      </div>
    </div>
  );
}
