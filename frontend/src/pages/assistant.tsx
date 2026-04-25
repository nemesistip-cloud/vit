import { useState, useRef, useEffect, FormEvent } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkles, Send, AlertCircle, RotateCw, Bot, User as UserIcon } from "lucide-react";
import {
  useAssistantChat,
  useAssistantStatus,
  type AssistantTurn,
} from "@/api-client";
import { toast } from "sonner";

const SUGGESTED_PROMPTS = [
  "How does the trust score system work?",
  "Explain CLV and why it matters for my predictions.",
  "What's the difference between the model markets and the accumulator builder?",
  "Walk me through how to start training a custom model.",
  "How do I become a validator?",
];

export default function AssistantPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AssistantTurn[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const status = useAssistantStatus();
  const chat = useAssistantChat();

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, chat.isPending]);

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
      });

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.reply },
      ]);

      if (result.error) {
        toast.error(result.error);
      }
    } catch (e: any) {
      const msg = e?.message || "Failed to reach the assistant";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry — I couldn't get a response (${msg}). Please try again.`,
        },
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
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary" />
            AI Assistant
          </h1>
          <p className="text-sm text-muted-foreground font-mono mt-1">
            Conversational copilot for the VIT Sports Intelligence Network.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {status.isLoading ? (
            <Skeleton className="h-6 w-24" />
          ) : ready ? (
            <Badge variant="outline" className="font-mono text-xs border-green-500/40 text-green-500">
              ● Ready
            </Badge>
          ) : (
            <Badge variant="outline" className="font-mono text-xs border-amber-500/40 text-amber-500">
              ● Not configured
            </Badge>
          )}
          {messages.length > 0 && (
            <Button variant="outline" size="sm" onClick={reset} className="font-mono">
              <RotateCw className="w-3.5 h-3.5 mr-1.5" />
              New chat
            </Button>
          )}
        </div>
      </div>

      {!ready && status.data && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="pt-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
            <div className="text-sm font-mono">
              <p className="font-medium text-amber-500">Assistant unavailable</p>
              <p className="text-muted-foreground mt-1">{status.data.message}</p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="overflow-hidden">
        <CardHeader className="border-b">
          <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">
            Conversation
          </CardTitle>
          <CardDescription className="font-mono text-xs">
            Powered by {status.data?.provider ?? "Gemini"} · context window: last 12 turns
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div
            ref={scrollRef}
            className="h-[55vh] min-h-[420px] overflow-y-auto px-4 py-6 space-y-4 bg-muted/10"
          >
            {messages.length === 0 && !chat.isPending && (
              <div className="h-full flex flex-col items-center justify-center text-center px-6 space-y-6">
                <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <Bot className="w-7 h-7 text-primary" />
                </div>
                <div className="space-y-1.5 max-w-md">
                  <p className="font-mono font-semibold text-sm">
                    Ask me anything about VIT Sports.
                  </p>
                  <p className="font-mono text-xs text-muted-foreground">
                    Models, predictions, ROI/CLV, the wallet, training, validators,
                    governance — pick a topic or type your own question.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center max-w-2xl">
                  {SUGGESTED_PROMPTS.map((p) => (
                    <button
                      key={p}
                      type="button"
                      disabled={!ready || chat.isPending}
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
              <MessageBubble key={i} role={m.role} content={m.content} />
            ))}

            {chat.isPending && (
              <MessageBubble role="assistant" content="" pending />
            )}
          </div>

          <form onSubmit={onSubmit} className="border-t bg-background px-3 py-3 flex items-end gap-2">
            <textarea
              name="assistant-message"
              autoComplete="off"
              spellCheck
              aria-label="Message the AI Assistant"
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
                  ? "Ask about a feature, fixture, or model output…"
                  : "Assistant is not configured yet"
              }
              disabled={!ready || chat.isPending}
              className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50 max-h-32"
              style={{ minHeight: "40px" }}
            />
            <Button
              type="submit"
              disabled={!ready || chat.isPending || !input.trim()}
              className="font-mono"
            >
              <Send className="w-4 h-4 mr-1.5" />
              Send
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
  pending = false,
}: {
  role: "user" | "assistant";
  content: string;
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
        {isUser ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div
        className={`max-w-[78%] rounded-lg px-3.5 py-2.5 text-sm font-mono leading-relaxed ${
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
