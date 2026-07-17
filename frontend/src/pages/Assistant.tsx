import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Send, Bot, User, Sparkles, Loader2, RefreshCw,
  ChevronRight, AlertCircle, Copy, CheckCircle2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Message {
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  ts: number
}

// ── Suggested prompts ──────────────────────────────────────────────────────────

const PROMPTS = [
  'What matches have the highest AI confidence today?',
  'Explain how the VIT Score is calculated',
  'What are the best DeFi pools for yield right now?',
  'How do I become a validator on VIT Network?',
  'Show me the leaderboard leaders this week',
  'What is expected value and why does it matter?',
]

// ── Markdown-lite renderer ────────────────────────────────────────────────────

function MessageContent({ text }: { text: string }) {
  // Very lightweight: bold, inline code, code blocks, bullet points
  const parts = text.split(/(```[\s\S]*?```|`[^`]+`|\*\*[^*]+\*\*)/g)
  return (
    <div className="text-sm leading-relaxed space-y-2">
      {parts.map((part, i) => {
        if (part.startsWith('```')) {
          const code = part.replace(/^```[^\n]*\n?/, '').replace(/```$/, '')
          return (
            <pre key={i} className="bg-black/30 rounded-lg p-3 text-xs text-emerald-300 font-mono overflow-x-auto whitespace-pre-wrap">
              {code}
            </pre>
          )
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return <code key={i} className="px-1.5 py-0.5 rounded bg-white/10 text-vit-300 text-xs font-mono">{part.slice(1, -1)}</code>
        }
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>
        }
        // Render newlines and bullets
        return (
          <span key={i}>
            {part.split('\n').map((line, j) => (
              <span key={j}>
                {line.startsWith('- ') || line.startsWith('• ')
                  ? <span className="block pl-3 before:content-['•'] before:-ml-3 before:mr-2 before:text-vit-400">{line.slice(2)}</span>
                  : line
                }
                {j < part.split('\n').length - 1 && <br />}
              </span>
            ))}
          </span>
        )
      })}
    </div>
  )
}

// ── Message bubble ─────────────────────────────────────────────────────────────

function Bubble({ msg }: { msg: Message }) {
  const [copied, setCopied] = useState(false)
  const isUser = msg.role === 'user'

  function copy() {
    navigator.clipboard.writeText(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('flex gap-3 group', isUser ? 'flex-row-reverse' : 'flex-row')}
    >
      {/* Avatar */}
      <div className={cn(
        'w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5',
        isUser ? 'bg-vit-600' : 'bg-surface-700 border border-white/10',
      )}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-vit-400" />}
      </div>

      {/* Content */}
      <div className={cn('max-w-[80%] space-y-1.5', isUser ? 'items-end' : 'items-start')}>
        {msg.thinking && (
          <details className="text-xs text-white/30 cursor-pointer mb-1">
            <summary className="hover:text-white/50 transition-colors">Thinking chain</summary>
            <pre className="mt-1 text-[11px] font-mono bg-white/3 rounded p-2 whitespace-pre-wrap">{msg.thinking}</pre>
          </details>
        )}
        <div className={cn(
          'rounded-2xl px-4 py-3',
          isUser
            ? 'bg-vit-600 text-white rounded-tr-sm'
            : 'bg-surface-800/80 border border-white/8 text-white/85 rounded-tl-sm',
        )}>
          <MessageContent text={msg.content} />
        </div>
        <div className={cn('flex items-center gap-2 px-1', isUser ? 'flex-row-reverse' : 'flex-row')}>
          <span className="text-[10px] text-white/25">
            {new Date(msg.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {!isUser && (
            <button
              onClick={copy}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-white/25 hover:text-white/60"
            >
              {copied ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Assistant() {
  const navigate          = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState<string | null>(null)
  const bottomRef           = useRef<HTMLDivElement>(null)
  const inputRef            = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(text: string) {
    if (!text.trim() || loading) return
    const userMsg: Message = { role: 'user', content: text.trim(), ts: Date.now() }
    setMessages(m => [...m, userMsg])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const r = await fetch(`${ENDPOINTS.gateway}/api/ai/assistant/chat`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          history: messages.slice(-10).map(m => ({ role: m.role, content: m.content })),
        }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? d.message ?? `Error ${r.status}`)
      const assistantMsg: Message = {
        role: 'assistant',
        content: d.response ?? d.message ?? d.text ?? 'No response.',
        thinking: d.thinking_chain ?? d.reasoning,
        ts: Date.now(),
      }
      setMessages(m => [...m, assistantMsg])
    } catch (e: any) {
      setError(e.message || 'Failed to get a response. Please try again.')
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="pt-16 min-h-screen flex flex-col relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      {/* Header */}
      <div className="relative border-b border-white/8 bg-surface-900/60 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-vit-500/15 border border-vit-500/25 flex items-center justify-center">
            <Sparkles className="w-4.5 h-4.5 text-vit-400" />
          </div>
          <div>
            <h1 className="font-bold text-white text-sm">VIT AI Assistant</h1>
            <p className="text-[11px] text-white/40">Powered by the VIT Intelligence Layer</p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={() => { setMessages([]); setError(null) }}
              className="ml-auto flex items-center gap-1.5 text-xs text-white/35 hover:text-white/60 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              New chat
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="relative flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
          {isEmpty ? (
            <div className="text-center mt-8 mb-12 space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-vit-500/15 border border-vit-500/20 flex items-center justify-center mx-auto">
                <Bot className="w-8 h-8 text-vit-400" />
              </div>
              <h2 className="text-xl font-bold text-white">How can I help you?</h2>
              <p className="text-white/40 text-sm max-w-sm mx-auto">
                Ask me about matches, predictions, DeFi, governance, or anything on the VIT platform.
              </p>

              {/* Suggested prompts */}
              <div className="grid sm:grid-cols-2 gap-2.5 mt-8 text-left max-w-xl mx-auto">
                {PROMPTS.map(p => (
                  <button
                    key={p}
                    onClick={() => send(p)}
                    className="flex items-start gap-2.5 p-3 rounded-xl bg-surface-800/60 border border-white/8 text-xs text-white/60 hover:text-white hover:border-vit-500/30 hover:bg-surface-800/80 transition-all text-left"
                  >
                    <ChevronRight className="w-3.5 h-3.5 text-vit-400 mt-0.5 shrink-0" />
                    {p}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {messages.map((m, i) => <Bubble key={i} msg={m} />)}

              {loading && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3"
                >
                  <div className="w-8 h-8 rounded-full bg-surface-700 border border-white/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-4 h-4 text-vit-400" />
                  </div>
                  <div className="bg-surface-800/80 border border-white/8 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-vit-400 animate-spin" />
                    <span className="text-white/40 text-sm">Thinking…</span>
                  </div>
                </motion.div>
              )}

              {error && (
                <div className="flex items-start gap-2.5 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-red-400 text-sm">{error}</p>
                </div>
              )}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="relative border-t border-white/8 bg-surface-900/60 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          {!getAuthToken() && (
            <div className="flex items-center gap-2 text-xs text-amber-400 mb-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>Sign in for personalised AI responses.</span>
            </div>
          )}
          <div className="flex items-end gap-2.5">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
              placeholder="Ask anything about VIT Network… (Enter to send, Shift+Enter for new line)"
              className="flex-1 bg-surface-800/60 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/25 focus:outline-none focus:border-vit-500/50 focus:ring-1 focus:ring-vit-500/15 resize-none transition-colors"
              style={{ minHeight: '44px', maxHeight: '120px' }}
              onInput={e => {
                const t = e.currentTarget
                t.style.height = 'auto'
                t.style.height = `${Math.min(t.scrollHeight, 120)}px`
              }}
            />
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || loading}
              className="w-11 h-11 rounded-xl bg-vit-600 text-white flex items-center justify-center hover:bg-vit-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-[10px] text-white/20 mt-2 text-center">
            AI responses may be inaccurate. Always verify before placing predictions.
          </p>
        </div>
      </div>
    </div>
  )
}
