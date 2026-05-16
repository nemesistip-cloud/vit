import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Brain, CheckCircle2, AlertCircle, ArrowRight, Trophy } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function IQTestPage() {
  const [step, setStep] = useState(0); // 0: intro, 1-3: questions, 4: results
  const [score, setScore] = useState(0);

  const questions = [
    {
      q: "A team has a 60% win probability. What are the 'fair' decimal odds?",
      options: ["1.40", "1.67", "2.10", "1.50"],
      correct: 1, // 1/0.6 = 1.666
    },
    {
      q: "If you bet on a +EV edge of 5% consistently with proper bankroll management, your long-term outcome is most likely:",
      options: ["Guaranteed profit every week", "Growth with variance/drawdowns", "Break-even after fees", "Ruin within 100 bets"],
      correct: 1,
    },
    {
      q: "Which metric is the best indicator of a prediction model's 'truth' vs the market?",
      options: ["ROI", "Win Rate", "CLV (Closing Line Value)", "Yield"],
      correct: 2,
    }
  ];

  const handleAnswer = (idx: number) => {
    if (idx === questions[step - 1].correct) {
      setScore(s => s + 1);
    }
    setStep(s => s + 1);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      {step === 0 && (
        <Card className="bg-card border-border/50 text-center p-8">
          <div className="w-20 h-20 bg-purple-500/10 rounded-3xl flex items-center justify-center mx-auto mb-6">
            <Brain className="w-10 h-10 text-purple-400" />
          </div>
          <CardTitle className="text-3xl font-bold">VIT IQ Test</CardTitle>
          <CardDescription className="mt-4 text-lg text-zinc-400">
            Assess your sports prediction aptitude. Wordle meets Mensa.
          </CardDescription>
          <Button
            className="mt-8 px-12 h-14 bg-purple-600 hover:bg-purple-500 text-lg font-bold rounded-xl"
            onClick={() => setStep(1)}
          >
            Start Test <ArrowRight className="ml-2 w-5 h-5" />
          </Button>
          <p className="mt-4 text-xs text-zinc-500 uppercase tracking-widest">10 MINUTES · 3 QUESTIONS · FREE</p>
        </Card>
      )}

      {step > 0 && step <= questions.length && (
        <div className="space-y-6">
          <div className="flex justify-between items-end mb-2">
            <span className="text-xs font-mono text-purple-400 uppercase tracking-tighter">Question {step} of {questions.length}</span>
            <span className="text-xs text-zinc-500">{Math.round((step/questions.length)*100)}% Complete</span>
          </div>
          <Progress value={(step/questions.length)*100} className="h-1 bg-zinc-800" />

          <Card className="bg-card border-border/50 p-6">
            <h2 className="text-xl font-medium mb-8 leading-relaxed">
              {questions[step - 1].q}
            </h2>
            <div className="grid gap-3">
              {questions[step - 1].options.map((opt, i) => (
                <button
                  key={i}
                  onClick={() => handleAnswer(i)}
                  className="w-full text-left p-4 rounded-xl border border-border/50 hover:border-purple-500/50 hover:bg-purple-500/5 transition-all group flex justify-between items-center"
                >
                  <span className="text-zinc-300 group-hover:text-white transition-colors">{opt}</span>
                  <div className="w-6 h-6 rounded-full border border-border group-hover:border-purple-500/50 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-purple-500 opacity-0 group-active:opacity-100" />
                  </div>
                </button>
              ))}
            </div>
          </Card>
        </div>
      )}

      {step > questions.length && (
        <Card className="bg-card border-border/50 text-center p-10 overflow-hidden relative">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-cyan-500" />
          <Trophy className="w-16 h-16 text-yellow-400 mx-auto mb-6" />
          <CardTitle className="text-4xl font-black italic uppercase tracking-tighter">Test Complete</CardTitle>
          <div className="mt-8 py-6 px-4 bg-zinc-900/50 rounded-2xl border border-border/50 inline-block min-w-[200px]">
            <p className="text-zinc-500 text-xs uppercase tracking-widest mb-1">Your VIT IQ Score</p>
            <p className="text-6xl font-black text-white">{Math.round((score/questions.length) * 140 + 20)}</p>
          </div>
          <p className="mt-6 text-zinc-400 max-w-sm mx-auto">
            You scored {score} out of {questions.length} correct.
            {score === questions.length ? " Excellent! You have the analytical mind of a professional bettor." : " Good effort! Keep using VIT to sharpen your edge."}
          </p>
          <div className="mt-10 flex gap-3 justify-center">
            <Button variant="outline" className="border-border px-8" onClick={() => setStep(0)}>Retake</Button>
            <Button className="bg-white text-black hover:bg-zinc-200 px-8">Share Result</Button>
          </div>
        </Card>
      )}
    </div>
  );
}
