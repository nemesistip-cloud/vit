import { useState, useRef, useEffect } from "react";
import { MarkdownContent } from "@/components/MarkdownContent";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkles, Send, RotateCw, Brain, User as UserIcon, Zap, Search, Activity } from "lucide-react";
import {
  useAssistantChat,
  useAssistantStatus,
  type AssistantTurn,
} from "@/api-client";
import { toast } from "sonner";

const SUGGESTED_PROMPTS = [
  "Show upcoming fixtures with high SVI.",
  "Audit system health and SVI status.",
  "What are the latest market trends and CLV stats?",
  "Give me insights for match ID 1.",
  "How does the VIT trust system work?",
];

const ASSISTANT_FEATURES = [
  "VIT Native Intelligence (v5.5.0)",
  "Real-time SVI and Market Monitoring",
  "Live score and fixture insights",
  "Internal Ensemble Predictions",
  "System health and agent status",
  "Market trends and CLV summaries",
  "Self-contained Neural Layer",
];

// Extend AssistantTurn to include thoughts
interface ExtendedAssistantTurn extends AssistantTurn {
  thoughts?: string[];
}

export default function AssistantPage() {
  const [input, setInput]     = useState("");
  const [messages, setMessages] = useState<ExtendedAssistantTurn[]>([]);
  const [isPending, setIsPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const status = useAssistantStatus();
  const chat   = useAssistantChat();

  const isReady = status.data?.available ?? false;

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isPending]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isPending) return;

    const nextHistory: ExtendedAssistantTurn[] = [
      ...messages,
      { role: "user", content: trimmed },
    ];
    setMessages(nextHistory);
    setInput("");

    setIsPending(true);
    try {
      const result = await chat.mutateAsync({
        message: trimmed,
        history: messages.map(m => ({ role: m.role, content: m.content }))
      }) as any;

      setMessages((prev) => [...prev, {
        role: "assistant",
        content: result.reply,
        thoughts: result.thoughts
      }]);

      if (result.error) toast.error(result.error);
    } catch (e: any) {
      const msg = e?.message || "Failed to reach the VIT Bot";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry — ${msg}. The internal neural layer might be recalibrating.`,
        },
      ]);
      toast.error(msg);
    } finally {
      setIsPending(false);
    }
  }

  const reset = () => setMessages([]);

  return (
    <div className="container max-w-5xl py-8 space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2.5">
            <Brain className="w-8 h-8 text-primary" />
            Intelligence Agent
          </h1>
          <p className="text-muted-foreground font-mono text-sm mt-1">
            v5.5.0 · Native Neural Layer · Decentralized Intelligence
          </p>
        </div>

        <div className="flex items-center gap-3">
          {status.isLoading ? (
            <Skeleton className="h-6 w-24" />
          ) : isReady ? (
            <Badge variant="outline" className="font-mono text-xs border-green-500/40 text-green-500 bg-green-500/5">
              ● Network Active
            </Badge>
          ) : (
            <Badge variant="outline" className="font-mono text-xs border-amber-500/40 text-amber-500">
              ● Recalibrating
            </Badge>
          )}

          {messages.length > 0 && (
            <Button variant="outline" size="sm" onClick={reset} className="font-mono">
              <RotateCw className="w-3.5 h-3.5 mr-1.5" />
              Reset Buffer
            </Button>
          )}
        </div>
      </div>

      {/* Info bar */}
      <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground px-1">
        <Zap className="w-3.5 h-3.5 text-primary flex-shrink-0" />
        <span>
          Powered by <span className="text-primary font-semibold">VIT Native Ensemble</span> · No external APIs · Privacy Guaranteed
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-background/90 p-4 text-xs font-mono text-muted-foreground">
          <p className="mb-2 text-[11px] uppercase tracking-[0.24em] text-muted-foreground font-semibold">
            Agent capabilities
          </p>
          <ul className="space-y-2">
            {ASSISTANT_FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-3">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-primary flex-shrink-0" />
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-border bg-background/90 p-4 text-xs font-mono text-muted-foreground">
          <p className="mb-2 text-[11px] uppercase tracking-[0.24em] text-muted-foreground font-semibold">
            Internal Node Status
          </p>
          <p>{status.data?.message ?? "Synchronizing nodes..."}</p>
          {status.data?.health?.ai_models_ready !== undefined && (
            <div className="mt-2 space-y-1">
              <p className="text-[11px]">Active ML Models: {status.data.health.ai_models_ready}</p>
              <p className="text-[11px]">SVI Stability: {status.data.health.svi?.toFixed(4)} ({status.data.health.svi_status})</p>
            </div>
          )}
        </div>
      </div>

      {/* Chat card */}
      <Card className="overflow-hidden rounded-2xl border-border/50 bg-card/60">
        <CardHeader className="border-b">
          <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">
            Neural Uplink
          </CardTitle>
          <CardDescription className="font-mono text-xs">
            Direct connection to the VIT Network ensemble.
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0">
          <div
            ref={scrollRef}
            className="h-[55vh] min-h-[420px] overflow-y-auto px-4 py-6 space-y-4 bg-muted/10"
          >
            {messages.length === 0 && !isPending && (
              <div className="h-full flex flex-col items-center justify-center text-center px-6 space-y-6">
                <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <Brain className="w-7 h-7 text-primary" />
                </div>
                <div className="space-y-1.5 max-w-md">
                  <p className="font-mono font-semibold text-sm">
                    VIT Intelligence Agent is Active.
                  </p>
                  <p className="font-mono text-xs text-muted-foreground">
                    I can autonomously fetch live matches, analyze system health, and track market trends using platform nodes.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center max-w-2xl">
                  {SUGGESTED_PROMPTS.map((p) => (
                    <button
                      key={p}
                      type="button"
                      disabled={!isReady || isPending}
                      onClick={() => send(p)}
                      className="text-xs font-mono px-3 py-1.5 rounded-full border border-border bg-background hover:bg-accent hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <MessageBubble key={i} role={m.role} content={m.content} thoughts={m.thoughts} />
            ))}

            {isPending && <MessageBubble role="assistant" content="" pending />}
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); send(input); }}
            className="border-t bg-background px-3 py-3 flex items-end gap-2"
          >
            <textarea
              name="assistant-message"
              autoComplete="off"
              spellCheck
              aria-label="Message the Intelligence Agent"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              rows={1}
              placeholder={
                isReady
                  ? "Query VIT Network nodes..."
                  : "Synchronizing with network..."
              }
              disabled={!isReady || isPending}
              className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50 max-h-32"
              style={{ minHeight: "40px" }}
            />
            <Button
              type="submit"
              disabled={!isReady || isPending || !input.trim()}
              className="font-mono"
            >
              <Send className="w-4 h-4 mr-1.5" />
              Transmit
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function MessageBubble({
  role,
  content,
  thoughts = [],
  pending = false,
}: {
  role: "user" | "assistant";
  content: string;
  thoughts?: string[];
  pending?: boolean;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser
            ? "bg-primary/10 border border-primary/30 text-primary"
            : "bg-secondary border border-border text-secondary-foreground"
        }`}
      >
        {isUser ? <UserIcon className="w-4 h-4" /> : <Brain className="w-4 h-4" />}
      </div>
      <div className="flex flex-col gap-2 max-w-[78%]">
        {/* Thought process display */}
        {thoughts.length > 0 && (
          <div className="bg-muted/30 border border-border/50 rounded-lg p-2.5 space-y-2">
            <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground flex items-center gap-1.5">
              <Activity className="w-3 h-3" />
              Node Processing
            </p>
            <div className="space-y-1.5">
              {thoughts.map((t, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs font-mono text-primary/80">
                  <div className="mt-1 w-1 h-1 rounded-full bg-primary" />
                  <span>{t}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div
          className={`rounded-xl px-4 py-3 text-sm font-mono leading-relaxed ${
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-card border border-border"
          }`}
        >
          {pending ? (
            <div className="space-y-3 py-1">
               <div className="flex items-center gap-2 text-xs text-muted-foreground animate-pulse">
                  <Search className="w-3 h-3" />
                  <span>Polling network nodes...</span>
               </div>
               <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" />
              </span>
            </div>
          ) : isUser ? (
            <span className="whitespace-pre-wrap break-words">{content}</span>
          ) : (
            <MarkdownContent content={content} />
          )}
        </div>
      </div>
    </div>
  );
}
