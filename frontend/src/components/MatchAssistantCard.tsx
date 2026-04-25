import { useState, useRef, useEffect, FormEvent, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Send, AlertCircle, RotateCw, Bot, User as UserIcon, ChevronDown, ChevronUp } from "lucide-react";
import {
  useAssistantChat,
  useAssistantStatus,
  type AssistantTurn,
} from "@/api-client";
import { toast } from "sonner";

interface MatchAssistantCardProps {
  match: any;
  consensus?: any;
}

function pct(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return "n/a";
  return `${(n * 100).toFixed(1)}%`;
}

function buildContext(match: any, consensus: any): string {
  if (!match) return "";

  const lines: string[] = [];
  lines.push("=== Match Context ===");
  lines.push(`Fixture: ${match.home_team} vs ${match.away_team}`);
  if (match.league) lines.push(`League: ${match.league}`);
  if (match.kickoff_time) lines.push(`Kickoff: ${match.kickoff_time}`);
  if (match.ft_score) lines.push(`Full-time score: ${match.ft_score}`);
  if (match.actual_outcome) lines.push(`Settled outcome: ${match.actual_outcome}`);

  lines.push("");
  lines.push("=== Model Probabilities (1X2) ===");
  lines.push(`Home win: ${pct(match.home_prob)}`);
  lines.push(`Draw:     ${pct(match.draw_prob)}`);
  lines.push(`Away win: ${pct(match.away_prob)}`);

  if (match.over_25_prob !== undefined && match.over_25_prob !== null) {
    lines.push("");
    lines.push("=== Goals Markets ===");
    lines.push(`Over 2.5:  ${pct(match.over_25_prob)}`);
    if (match.under_25_prob !== undefined && match.under_25_prob !== null) {
      lines.push(`Under 2.5: ${pct(match.under_25_prob)}`);
    }
  }
  if (match.btts_prob !== undefined && match.btts_prob !== null) {
    if (!lines.includes("=== Goals Markets ===")) lines.push("");
    lines.push(`BTTS Yes:  ${pct(match.btts_prob)}`);
    if (match.no_btts_prob !== undefined && match.no_btts_prob !== null) {
      lines.push(`BTTS No:   ${pct(match.no_btts_prob)}`);
    }
  }

  if (match.confidence !== undefined && match.confidence !== null) {
    lines.push("");
    lines.push(`Model confidence: ${pct(match.confidence)}`);
  }

  if (match.market_odds && typeof match.market_odds === "object") {
    const o = match.market_odds;
    if (o.home || o.draw || o.away) {
      lines.push("");
      lines.push("=== Market Odds (decimal) ===");
      if (o.home) lines.push(`Home: ${o.home}`);
      if (o.draw) lines.push(`Draw: ${o.draw}`);
      if (o.away) lines.push(`Away: ${o.away}`);
    }
  }

  if (match.bet_side || match.recommended_stake) {
    lines.push("");
    lines.push("=== Best Bet (model recommendation) ===");
    if (match.bet_side) lines.push(`Side: ${match.bet_side}`);
    if (match.entry_odds) lines.push(`Odds: ${match.entry_odds}`);
    if (match.normalized_edge !== undefined && match.normalized_edge !== null) {
      lines.push(`Edge: ${pct(match.normalized_edge)}`);
    }
    if (match.recommended_stake) lines.push(`Recommended stake: ${match.recommended_stake}`);
  }

  if (consensus && Array.isArray(consensus.model_contributions) && consensus.model_contributions.length) {
    lines.push("");
    lines.push("=== Top model contributors ===");
    consensus.model_contributions.slice(0, 5).forEach((m: any) => {
      lines.push(`- ${m.model_key ?? m.name ?? "model"}: weight ${(m.weight ?? 0).toFixed(3)}`);
    });
  }

  lines.push("");
  lines.push("Answer the user's question using the figures above. If they ask for predictions, advice, or analysis, ground it in this match's numbers. Keep replies concise and use plain language.");

  return lines.join("\n");
}

function buildPrompts(match: any): string[] {
  const home = match?.home_team ?? "the home side";
  const away = match?.away_team ?? "the away side";
  return [
    `Why does the model favor ${
      (match?.home_prob ?? 0) >= (match?.away_prob ?? 0) ? home : away
    } here?`,
    `Is there value on Over 2.5 goals or BTTS in this match?`,
    `What's the safest bet for ${home} vs ${away}?`,
    `Summarise the key risks of betting on this fixture.`,
  ];
}

export function MatchAssistantCard({ match, consensus }: MatchAssistantCardProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AssistantTurn[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const status = useAssistantStatus();
  const chat = useAssistantChat();

  const context = useMemo(() => buildContext(match, consensus), [match, consensus]);
  const prompts = useMemo(() => buildPrompts(match), [match]);

  useEffect(() => {
    if (open) {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, chat.isPending, open]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || chat.isPending) return;

    const nextHistory: AssistantTurn[] = [
      ...messages,
      { role: "user", content: trimmed },
    ];
    setMessages(nextHistory);
    setInput("");

    try {
      const result = await chat.mutateAsync({
        message: trimmed,
        history: messages,
        context,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: result.reply }]);
      if (result.error) toast.error(result.error);
    } catch (e: any) {
      const msg = e?.message || "Failed to reach the assistant";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Sorry — I couldn't get a response (${msg}). Please try again.` },
      ]);
      toast.error(msg);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    send(input);
  }

  function reset() {
    setMessages([]);
    setInput("");
  }

  const ready = status.data?.available ?? false;

  return (
    <Card className="border-primary/20 bg-card/80 backdrop-blur">
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <CardTitle className="text-sm font-mono uppercase tracking-wider">
              Ask the AI Assistant about this match
            </CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {ready ? (
              <Badge variant="outline" className="font-mono text-[10px] border-green-500/40 text-green-500">
                ● Ready
              </Badge>
            ) : (
              <Badge variant="outline" className="font-mono text-[10px] border-amber-500/40 text-amber-500">
                ● Off
              </Badge>
            )}
            {open ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </div>
        </div>
        <CardDescription className="font-mono text-xs mt-1">
          The model's probabilities, odds and best-bet for {match?.home_team} vs {match?.away_team} are pre-loaded as context.
        </CardDescription>
      </CardHeader>

      {open && (
        <CardContent className="p-0 border-t">
          {!ready && status.data && (
            <div className="px-4 py-3 flex items-start gap-2 bg-amber-500/5 border-b border-amber-500/20">
              <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <div className="text-xs font-mono text-muted-foreground">{status.data.message}</div>
            </div>
          )}

          <div
            ref={scrollRef}
            className="h-[40vh] min-h-[280px] max-h-[480px] overflow-y-auto px-4 py-4 space-y-3 bg-muted/10"
          >
            {messages.length === 0 && !chat.isPending && (
              <div className="h-full flex flex-col items-center justify-center text-center px-2 space-y-4">
                <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-primary" />
                </div>
                <div className="font-mono text-xs text-muted-foreground max-w-md">
                  Try one of these match-specific questions, or type your own.
                </div>
                <div className="flex flex-wrap gap-1.5 justify-center max-w-2xl">
                  {prompts.map((p) => (
                    <button
                      key={p}
                      type="button"
                      disabled={!ready || chat.isPending}
                      onClick={() => send(p)}
                      className="text-[11px] font-mono px-2.5 py-1 rounded-full border border-border bg-background hover:bg-accent hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-left"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <Bubble key={i} role={m.role} content={m.content} />
            ))}

            {chat.isPending && <Bubble role="assistant" content="" pending />}
          </div>

          <form
            onSubmit={onSubmit}
            className="border-t bg-background px-3 py-2.5 flex items-end gap-2"
          >
            <textarea
              name="match-assistant-message"
              autoComplete="off"
              spellCheck
              aria-label={`Ask the AI Assistant about ${match?.home_team} vs ${match?.away_team}`}
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
                ready
                  ? `Ask about ${match?.home_team ?? "the match"}…`
                  : "Assistant is not configured yet"
              }
              disabled={!ready || chat.isPending}
              className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50 max-h-32"
              style={{ minHeight: "38px" }}
            />
            {messages.length > 0 && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={reset}
                className="font-mono"
                title="Reset conversation"
              >
                <RotateCw className="w-3.5 h-3.5" />
              </Button>
            )}
            <Button
              type="submit"
              size="sm"
              disabled={!ready || chat.isPending || !input.trim()}
              className="font-mono"
            >
              <Send className="w-3.5 h-3.5 mr-1.5" />
              Send
            </Button>
          </form>
        </CardContent>
      )}
    </Card>
  );
}

function Bubble({
  role,
  content,
  pending = false,
}: {
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser
            ? "bg-primary/10 border border-primary/30 text-primary"
            : "bg-secondary border border-border text-secondary-foreground"
        }`}
      >
        {isUser ? <UserIcon className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
      </div>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm font-mono leading-relaxed ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-card border border-border"
        }`}
      >
        {pending ? (
          <span className="inline-flex items-center gap-1.5 text-muted-foreground">
            <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.15s]" />
            <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" />
          </span>
        ) : (
          <span className="whitespace-pre-wrap break-words">{content}</span>
        )}
      </div>
    </div>
  );
}
