import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Brain, CheckCircle2, AlertCircle, ArrowRight, Trophy } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface Question {
  id: number;
  q: string;
  options: string[];
}

interface QuestionsResponse {
  total: number;
  questions: Question[];
}

interface QuizResult {
  score: number;
  total: number;
  iq_score: number;
  label: string;
  results: Array<{
    id: number;
    correct: boolean;
    your_answer: number;
    right_answer: number;
    explanation: string;
  }>;
}

const IQ_LABEL_COLOR: Record<string, string> = {
  "Elite Analyst": "text-yellow-400",
  "Sharp Bettor":  "text-emerald-400",
  "Value Hunter":  "text-cyan-400",
  "Learning Edge": "text-blue-400",
  "Beginner":      "text-muted-foreground",
};

export default function IQTestPage() {
  const [step, setStep] = useState(0); // 0: intro, 1-N: questions, N+1: results
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { data, isLoading, isError } = useQuery<QuestionsResponse>({
    queryKey: ["iq-test-questions"],
    queryFn: () => apiGet("/api/freemium/iq-test/questions"),
    staleTime: Infinity,
  });

  const questions = data?.questions ?? [];
  const total     = data?.total ?? 0;
  const currentQ  = step >= 1 && step <= total ? questions[step - 1] : null;

  const handleAnswer = async (optionIdx: number) => {
    if (!currentQ) return;
    const updated = { ...answers, [currentQ.id]: optionIdx };
    setAnswers(updated);

    if (step < total) {
      setStep((s) => s + 1);
    } else {
      // Last question — submit
      setSubmitting(true);
      try {
        const res: QuizResult = await apiPost("/api/freemium/iq-test/submit", updated);
        setResult(res);
        setStep(total + 1);
      } catch {
        // Fallback: compute locally
        const localScore = Object.entries(updated).filter(([id, ans]) => {
          const q = questions.find((q) => q.id === parseInt(id));
          return q && (ans as any) === (q as any).correct;
        }).length;
        setResult({
          score: localScore,
          total,
          iq_score: Math.round((localScore / total) * 140 + 20),
          label: localScore === total ? "Elite Analyst" : localScore >= total * 0.8 ? "Sharp Bettor" : "Value Hunter",
          results: [],
        });
        setStep(total + 1);
      } finally {
        setSubmitting(false);
      }
    }
  };

  const handleRetake = () => {
    setStep(0);
    setAnswers({});
    setResult(null);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      {/* Intro screen */}
      {step === 0 && (
        <Card className="bg-card border-border/50 text-center p-8">
          <div className="w-20 h-20 bg-purple-500/10 rounded-3xl flex items-center justify-center mx-auto mb-6">
            <Brain className="w-10 h-10 text-purple-400" />
          </div>
          <CardTitle className="text-3xl font-bold">VIT Intelligence Assessment</CardTitle>
          <CardDescription className="mt-4 text-lg text-zinc-400">
            Assess your sports prediction aptitude. Wordle meets Mensa.
          </CardDescription>

          {isLoading ? (
            <Skeleton className="mt-8 h-14 w-full rounded-xl" />
          ) : isError ? (
            <p className="mt-6 text-sm text-destructive">Could not load questions. Please try again.</p>
          ) : (
            <Button
              className="mt-8 px-12 h-14 bg-purple-600 hover:bg-purple-500 text-lg font-bold rounded-xl"
              onClick={() => setStep(1)}
            >
              Start Test <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          )}
          <p className="mt-4 text-xs text-zinc-500 uppercase tracking-widest">
            {total} QUESTION{total !== 1 ? "S" : ""} · FREE
          </p>
        </Card>
      )}

      {/* Question screen */}
      {step >= 1 && step <= total && currentQ && (
        <div className="space-y-6">
          <div className="flex justify-between items-end mb-2">
            <span className="text-xs font-mono text-purple-400 uppercase tracking-tighter">
              Question {step} of {total}
            </span>
            <span className="text-xs text-zinc-500">
              {Math.round((step / total) * 100)}% Complete
            </span>
          </div>
          <Progress
            value={(step / total) * 100}
            className="h-1 bg-zinc-800 [&>div]:bg-purple-500"
          />

          <Card className="bg-card border-border/50 p-6">
            <h2 className="text-xl font-medium mb-8 leading-relaxed">
              {currentQ.q}
            </h2>
            <div className="grid gap-3">
              {currentQ.options.map((opt, i) => (
                <button
                  key={i}
                  onClick={() => !submitting && handleAnswer(i)}
                  disabled={submitting}
                  className="w-full text-left p-4 rounded-xl border border-border/50 hover:border-purple-500/50 hover:bg-purple-500/5 transition-all group flex justify-between items-center disabled:opacity-50"
                >
                  <span className="text-zinc-300 group-hover:text-white transition-colors">{opt}</span>
                  <div className="w-6 h-6 rounded-full border border-border group-hover:border-purple-500/50 flex items-center justify-center shrink-0">
                    <div className="w-2 h-2 rounded-full bg-purple-500 opacity-0 group-active:opacity-100 transition-opacity" />
                  </div>
                </button>
              ))}
            </div>
          </Card>

          {submitting && (
            <p className="text-center text-sm text-muted-foreground animate-pulse">Scoring your answers…</p>
          )}
        </div>
      )}

      {/* Results screen */}
      {step > total && result && (
        <div className="space-y-6">
          <Card className="bg-card border-border/50 text-center p-10 overflow-hidden relative">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-cyan-500" />
            <Trophy className="w-16 h-16 text-yellow-400 mx-auto mb-6" />
            <CardTitle className="text-4xl font-black italic uppercase tracking-tighter">Test Complete</CardTitle>

            <div className="mt-8 py-6 px-4 bg-zinc-900/50 rounded-2xl border border-border/50 inline-block min-w-[200px]">
              <p className="text-zinc-500 text-xs uppercase tracking-widest mb-1">Your VIT IQ Score</p>
              <p className="text-6xl font-black text-white">{result.iq_score}</p>
              <p className={`text-sm font-semibold mt-2 ${IQ_LABEL_COLOR[result.label] ?? "text-muted-foreground"}`}>
                {result.label}
              </p>
            </div>

            <p className="mt-6 text-zinc-400 max-w-sm mx-auto">
              You scored <strong className="text-white">{result.score}</strong> out of <strong className="text-white">{result.total}</strong>.
              {result.score === result.total
                ? " Excellent! You have the analytical mind of a professional bettor."
                : " Good effort! Keep using VIT to sharpen your edge."}
            </p>

            <div className="mt-10 flex gap-3 justify-center">
              <Button variant="outline" className="border-border px-8" onClick={handleRetake}>Retake</Button>
              <Button className="bg-white text-black hover:bg-zinc-200 px-8">Share Result</Button>
            </div>
          </Card>

          {/* Per-question breakdown */}
          {result.results.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-mono text-zinc-500 uppercase tracking-widest">Answer Breakdown</h3>
              {result.results.map((r, i) => {
                const q = questions.find((q) => q.id === r.id);
                return (
                  <Card key={r.id} className={`p-4 border ${r.correct ? "border-emerald-500/20 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5"}`}>
                    <div className="flex items-start gap-3">
                      {r.correct
                        ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                        : <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />}
                      <div className="space-y-1 flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground">{q?.q ?? `Question ${i + 1}`}</p>
                        {!r.correct && q && (
                          <p className="text-xs text-zinc-400">
                            Your answer: <span className="text-red-400">{q.options[r.your_answer]}</span>
                            {" · "}Correct: <span className="text-emerald-400">{q.options[r.right_answer]}</span>
                          </p>
                        )}
                        <p className="text-xs text-zinc-500 italic">{r.explanation}</p>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
