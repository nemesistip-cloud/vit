import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import {
  Brain, Send, User as UserIcon, Activity, Search,
  RotateCw, Zap, Shield, Info, CheckCircle2, ChevronRight, Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { MarkdownContent } from "@/components/MarkdownContent";

const SUGGESTED_PROMPTS = [
  "What are the best value bets today?",
  "Analyze current ensemble accuracy",
  "How do I improve my merit score?",
  "Check system node health",
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [isPending, setIsPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const status = useQuery<any>({
    queryKey: ["/api/assistant/status"],
    queryFn: () => apiGet("/api/assistant/status"),
  });

  const isReady = status.data?.available;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isPending]);

  async function send(text: string) {
    if (!text.trim() || isPending) return;
    const userMsg = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsPending(true);

    try {
      const response = await apiPost("/api/assistant/chat", { message: text });
      setMessages(prev => [...prev, {
        role: "assistant",
        content: response.content,
        thoughts: response.thoughts
      }]);
    } catch (e: any) {
      toast.error(e.message || "Failed to transmit message");
    } finally {
      setIsPending(false);
    }
  }

  const reset = () => setMessages([]);

  return (
    <div className="space-y-6 pb-20 max-w-4xl mx-auto">
      <div className="flex items-center justify-between px-1">
         <div>
            <p className="text-[10px] font-bold text-vit-text-3 uppercase tracking-widest">v5.5.0 Ensemble</p>
            <h1 className="text-xl font-display font-bold text-vit-text-1 flex items-center gap-2">
               <Brain size={20} className="text-vit-green" /> NEURAL UPLINK
            </h1>
         </div>
         <div className="flex items-center gap-3">
            <Badge className={`text-[8px] ${isReady ? 'bg-vit-green-glow text-vit-green border-vit-green/20' : 'bg-vit-surface-3 text-vit-text-3 border-vit-border'}`}>
               {isReady ? 'NETWORK ACTIVE' : 'RECALIBRATING'}
            </Badge>
            {messages.length > 0 && (
               <Button variant="ghost" size="icon" className="w-8 h-8 rounded-full bg-vit-surface-2" onClick={reset}>
                  <RotateCw size={14} />
               </Button>
            )}
         </div>
      </div>

      <Card className="bg-vit-surface border-vit-border overflow-hidden flex flex-col h-[70vh]">
         <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-hide"
         >
            {messages.length === 0 && !isPending && (
               <div className="h-full flex flex-col items-center justify-center text-center space-y-6 py-10">
                  <div className="w-16 h-16 rounded-2xl bg-vit-green-glow border border-vit-green/20 flex items-center justify-center text-vit-green">
                     <Brain size={32} />
                  </div>
                  <div className="max-w-xs">
                     <h3 className="font-display font-bold text-vit-text-1">INTELLIGENCE AGENT</h3>
                     <p className="text-xs text-vit-text-3 mt-1">Direct access to the 13-model VIT ensemble. Query live markets, system health, and value trends.</p>
                  </div>
                  <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
                     {SUGGESTED_PROMPTS.map(p => (
                        <button key={p} onClick={() => send(p)} className="p-3 rounded-xl bg-vit-surface-2 border border-vit-border text-left hover:border-vit-green/30 transition-all group">
                           <div className="flex justify-between items-center">
                              <span className="text-xs font-medium text-vit-text-2 group-hover:text-vit-text-1">{p}</span>
                              <ChevronRight size={14} className="text-vit-text-3" />
                           </div>
                        </button>
                     ))}
                  </div>
               </div>
            )}

            {messages.map((m, i) => (
               <div key={i} className={`flex gap-4 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 border ${
                     m.role === 'user' ? 'bg-vit-surface-3 border-vit-border text-vit-text-2' : 'bg-vit-green-glow border-vit-green/20 text-vit-green'
                  }`}>
                     {m.role === 'user' ? <UserIcon size={14} /> : <Brain size={14} />}
                  </div>
                  <div className={`max-w-[85%] space-y-2 ${m.role === 'user' ? 'text-right' : ''}`}>
                     {m.thoughts && m.thoughts.length > 0 && (
                        <div className="inline-block p-2 rounded-lg bg-vit-void border border-vit-border text-[9px] font-mono text-vit-green/70">
                           {m.thoughts.map((t: string, idx: number) => (
                              <div key={idx}>[NODE] {t}</div>
                           ))}
                        </div>
                     )}
                     <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
                        m.role === 'user' ? 'bg-vit-surface-3 text-vit-text-1' : 'bg-vit-surface-2 border border-vit-border text-vit-text-2'
                     }`}>
                        {m.role === 'user' ? m.content : <MarkdownContent content={m.content} />}
                     </div>
                  </div>
               </div>
            ))}

            {isPending && (
               <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-lg bg-vit-green-glow border border-vit-green/20 flex items-center justify-center text-vit-green animate-pulse">
                     <Brain size={14} />
                  </div>
                  <div className="p-4 rounded-2xl bg-vit-surface-2 border border-vit-border flex items-center gap-2">
                     <span className="w-1.5 h-1.5 bg-vit-green rounded-full animate-bounce [animation-delay:-0.3s]" />
                     <span className="w-1.5 h-1.5 bg-vit-green rounded-full animate-bounce [animation-delay:-0.15s]" />
                     <span className="w-1.5 h-1.5 bg-vit-green rounded-full animate-bounce" />
                  </div>
               </div>
            )}
         </div>

         <div className="p-4 border-t border-vit-border bg-vit-surface-2">
            <div className="relative">
               <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send(input))}
                  placeholder="Query system nodes..."
                  className="w-full bg-vit-surface border border-vit-border rounded-xl px-4 py-3 pr-12 text-sm focus:outline-none focus:border-vit-green/50 resize-none h-12"
               />
               <Button
                  onClick={() => send(input)}
                  disabled={!input.trim() || isPending}
                  size="icon"
                  className="absolute right-2 top-2 w-8 h-8 bg-vit-green text-vit-text-inverse rounded-lg"
               >
                  <Send size={14} />
               </Button>
            </div>
         </div>
      </Card>
    </div>
  );
}
