import { useState, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Smartphone, Bell, BellRing, Send, Code2, Package, Database,
  Copy, CheckCircle2, Plus, Trash2, Eye, EyeOff, Key, Zap,
  Globe, Shield, Terminal, Webhook, ToggleLeft, ToggleRight,
  Download, Star, ChevronRight, ExternalLink, Link2, Unlink,
  Activity, BarChart3, Clock, AlertCircle, Wifi, WifiOff,
  MessageSquare, Bot,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

// ── Types ─────────────────────────────────────────────────────────────────────

interface NotifPrefs {
  prediction_alerts: boolean
  match_start_alerts: boolean
  match_end_alerts: boolean
  wallet_activity: boolean
  social_alerts: boolean
  marketing_emails: boolean
  telegram_enabled: boolean
  push_enabled: boolean
}

interface TelegramLinkInfo {
  linked: boolean
  chat_id?: string
  username?: string
  linked_at?: string
}

interface DevKey {
  id: number
  name: string
  key_prefix: string
  key?: string
  plan: string
  is_active: boolean
  created_at: string
  last_used_at?: string
  requests_today: number
  requests_month: number
}

interface DevPlan {
  name: string
  requests_per_day: number
  requests_per_month: number
  price_vit: number
  features: string[]
}

interface DevUsage {
  requests_today: number
  requests_month: number
  active_keys: number
  plan: string
}

// ── API helpers ───────────────────────────────────────────────────────────────

const GW = () => ENDPOINTS.gateway

function useNotifPrefs(enabled: boolean) {
  return useQuery<NotifPrefs>({
    queryKey: ['notif-prefs'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${GW()}/api/notifications/preferences`, { signal, headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load preferences')
      return r.json()
    },
    enabled,
  })
}

function useTelegramInfo(enabled: boolean) {
  return useQuery<TelegramLinkInfo>({
    queryKey: ['tg-link'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${GW()}/api/notifications/telegram/link-info`, { signal, headers: authHeaders() })
      if (!r.ok) return { linked: false }
      return r.json()
    },
    enabled,
  })
}

function useDevKeys(enabled: boolean) {
  return useQuery<DevKey[]>({
    queryKey: ['dev-keys'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${GW()}/api/developer/keys`, { signal, headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load API keys')
      return r.json()
    },
    enabled,
  })
}

function useDevPlans() {
  return useQuery<DevPlan[]>({
    queryKey: ['dev-plans'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${GW()}/api/developer/plans`, { signal })
      if (!r.ok) return []
      return r.json()
    },
    staleTime: 300_000,
  })
}

function useDevUsage(enabled: boolean) {
  return useQuery<DevUsage>({
    queryKey: ['dev-usage'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${GW()}/api/developer/usage/summary`, { signal, headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load usage')
      return r.json()
    },
    enabled,
  })
}

// ── Generic helpers ───────────────────────────────────────────────────────────

function CopyBtn({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [done, setDone] = useState(false)
  const go = async () => {
    await navigator.clipboard.writeText(text).catch(() => {})
    setDone(true)
    setTimeout(() => setDone(false), 2000)
  }
  return (
    <button onClick={go}
      className={cn('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all',
        done ? 'bg-green-400/10 text-green-300 border-green-400/30' : 'bg-white/5 text-white/50 border-white/10 hover:text-white hover:bg-white/10')}>
      {done ? <CheckCircle2 className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
      {done ? 'Copied' : label}
    </button>
  )
}

function Toggle({ on, onChange, disabled }: { on: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button disabled={disabled} onClick={() => onChange(!on)}
      className={cn('w-10 h-6 rounded-full transition-all flex items-center px-0.5 flex-shrink-0 disabled:opacity-40',
        on ? 'bg-vit-400' : 'bg-white/20')}>
      <div className={cn('w-5 h-5 rounded-full bg-white shadow transition-transform', on ? 'translate-x-4' : 'translate-x-0')} />
    </button>
  )
}

function SectionHeader({ icon, title, desc }: { icon: ReactNode; title: string; desc?: string }) {
  return (
    <div className="flex items-start gap-3 mb-6">
      <div className="p-2.5 bg-vit-400/10 border border-vit-400/20 rounded-xl text-vit-400 flex-shrink-0">{icon}</div>
      <div>
        <h2 className="text-lg font-bold text-white">{title}</h2>
        {desc && <p className="text-sm text-white/40 mt-0.5">{desc}</p>}
      </div>
    </div>
  )
}

// ── Section 1: Mobile App ─────────────────────────────────────────────────────

const MOBILE_FEATURES = [
  { icon: <Zap className="w-4 h-4" />,      title: 'Real-time alerts',  desc: 'Instant push for every match event & prediction result' },
  { icon: <Shield className="w-4 h-4" />,   title: 'Biometric login',   desc: 'Face ID / fingerprint — no password needed' },
  { icon: <Activity className="w-4 h-4" />, title: 'Live match feed',   desc: 'In-app live scores with embedded commentary AI' },
  { icon: <Star className="w-4 h-4" />,     title: 'Offline tips',      desc: 'Browse saved predictions without connectivity' },
  { icon: <Zap className="w-4 h-4" />,      title: 'VIT wallet',        desc: 'Deposit, withdraw & swap on the go' },
  { icon: <Globe className="w-4 h-4" />,    title: 'Multi-language',    desc: 'EN, FR, PT, AR and 12 more at launch' },
]

function MobileSection() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return
    // Save to localStorage as a lightweight waitlist
    const existing = JSON.parse(localStorage.getItem('mobile-waitlist') ?? '[]') as string[]
    if (!existing.includes(email)) localStorage.setItem('mobile-waitlist', JSON.stringify([...existing, email]))
    setSubmitted(true)
  }

  return (
    <section className="mb-14">
      <SectionHeader icon={<Smartphone className="w-5 h-5" />} title="vit-mobile" desc="React Native app for iOS & Android — launching Q4 2026" />
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Phone mockup */}
        <div className="lg:col-span-2 flex items-center justify-center">
          <div className="relative w-52">
            <div className="w-52 h-96 bg-gradient-to-b from-[#1a1d2e] to-[#0d0f1a] rounded-[2.5rem] border-2 border-white/15 shadow-2xl flex flex-col items-center justify-start pt-8 px-4 overflow-hidden">
              {/* Notch */}
              <div className="w-20 h-5 bg-black rounded-full mb-6" />
              {/* Fake screen content */}
              <div className="w-full space-y-2">
                <div className="h-2 w-3/4 bg-vit-400/30 rounded" />
                <div className="h-2 w-1/2 bg-white/10 rounded" />
                <div className="h-16 w-full bg-vit-400/10 rounded-xl border border-vit-400/20 mt-4 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-vit-400 opacity-60" />
                </div>
                <div className="grid grid-cols-2 gap-1.5 pt-2">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-12 bg-white/5 rounded-lg border border-white/10" />
                  ))}
                </div>
              </div>
              {/* Glow */}
              <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-vit-400/10 to-transparent" />
            </div>
            {/* Floating badges */}
            <div className="absolute -right-6 top-16 bg-green-400/10 border border-green-400/30 rounded-xl px-3 py-1.5 text-xs font-medium text-green-300 shadow-lg whitespace-nowrap">
              +50 VIT 🎉
            </div>
            <div className="absolute -left-8 bottom-20 bg-vit-400/10 border border-vit-400/30 rounded-xl px-3 py-1.5 text-xs font-medium text-vit-300 shadow-lg whitespace-nowrap">
              🔔 Match starts
            </div>
          </div>
        </div>

        <div className="lg:col-span-3 space-y-5">
          {/* Feature grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {MOBILE_FEATURES.map(f => (
              <div key={f.title} className="flex items-start gap-3 bg-white/[0.03] border border-white/10 rounded-xl p-3.5">
                <div className="p-1.5 bg-vit-400/10 rounded-lg text-vit-400 flex-shrink-0">{f.icon}</div>
                <div>
                  <p className="text-sm font-semibold text-white">{f.title}</p>
                  <p className="text-xs text-white/40 mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Waitlist */}
          <div className="bg-gradient-to-r from-vit-400/10 to-transparent border border-vit-400/20 rounded-2xl p-5">
            <p className="font-semibold text-white mb-1">Join the waitlist</p>
            <p className="text-sm text-white/40 mb-4">Early access + 200 VIT airdrop on launch day.</p>
            {submitted ? (
              <div className="flex items-center gap-2 text-green-300 text-sm">
                <CheckCircle2 className="w-4 h-4" /> You're on the list — we'll email you before launch.
              </div>
            ) : (
              <form onSubmit={submit} className="flex gap-2">
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-400/50 min-w-0" />
                <button type="submit"
                  className="px-4 py-2 bg-vit-400 hover:bg-vit-300 text-black font-semibold rounded-xl transition-colors text-sm whitespace-nowrap">
                  Notify me
                </button>
              </form>
            )}
          </div>

          {/* Store buttons */}
          <div className="flex gap-3">
            {[{ icon: '🍎', label: 'App Store', sub: 'iOS — Coming Q4 2026' }, { icon: '🤖', label: 'Google Play', sub: 'Android — Coming Q4 2026' }].map(s => (
              <div key={s.label} className="flex-1 flex items-center gap-3 bg-white/[0.03] border border-white/10 rounded-xl px-4 py-3 cursor-not-allowed opacity-50">
                <span className="text-2xl">{s.icon}</span>
                <div>
                  <p className="text-xs text-white/40">{s.sub}</p>
                  <p className="text-sm font-semibold text-white">{s.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Section 2: Push Notifications ────────────────────────────────────────────

const PREF_LABELS: Record<string, { label: string; desc: string; icon: ReactNode }> = {
  prediction_alerts:  { label: 'Prediction results',  desc: 'Win/loss alerts when predictions resolve',  icon: <Zap className="w-3.5 h-3.5" /> },
  match_start_alerts: { label: 'Match start',         desc: 'Reminder when followed matches kick off',   icon: <Bell className="w-3.5 h-3.5" /> },
  match_end_alerts:   { label: 'Match end',           desc: 'Full-time scores and result summary',        icon: <BellRing className="w-3.5 h-3.5" /> },
  wallet_activity:    { label: 'Wallet activity',     desc: 'Deposits, withdrawals and rewards received', icon: <Zap className="w-3.5 h-3.5" /> },
  social_alerts:      { label: 'Social',              desc: 'Follows, likes, and tip-sharing mentions',   icon: <MessageSquare className="w-3.5 h-3.5" /> },
  marketing_emails:   { label: 'Marketing emails',    desc: 'Platform news, promotions and updates',      icon: <Globe className="w-3.5 h-3.5" /> },
}

function NotifSection({ isAuth }: { isAuth: boolean }) {
  const qc = useQueryClient()
  const { data: prefs, isLoading } = useNotifPrefs(isAuth)
  const [saving, setSaving] = useState(false)
  const [pushStatus, setPushStatus] = useState<'idle'|'granted'|'denied'|'pending'>('idle')

  const toggle = async (key: keyof NotifPrefs) => {
    if (!prefs) return
    const updated = { ...prefs, [key]: !prefs[key] }
    setSaving(true)
    await fetch(`${GW()}/api/notifications/preferences`, {
      method: 'PATCH',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: updated[key] }),
    }).catch(() => {})
    qc.setQueryData(['notif-prefs'], updated)
    setSaving(false)
  }

  const requestWebPush = async () => {
    if (!('Notification' in window)) { setPushStatus('denied'); return }
    setPushStatus('pending')
    const perm = await Notification.requestPermission()
    if (perm === 'granted') {
      // Subscribe and send to backend
      await fetch(`${GW()}/api/notifications/push/subscribe`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform: 'web', token: 'browser' }),
      }).catch(() => {})
      setPushStatus('granted')
    } else {
      setPushStatus('denied')
    }
  }

  return (
    <section className="mb-14">
      <SectionHeader icon={<Bell className="w-5 h-5" />} title="Push Notifications" desc="Choose exactly what alerts you receive, across every channel." />

      {!isAuth ? (
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-8 text-center text-white/40">
          <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>Sign in to manage notification preferences.</p>
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-12"><Spinner className="w-6 h-6" /></div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Preference toggles */}
          <div className="lg:col-span-2 bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/10 flex items-center justify-between">
              <p className="text-sm font-semibold text-white">Alert preferences</p>
              {saving && <Spinner className="w-4 h-4" />}
            </div>
            <div className="divide-y divide-white/5">
              {(Object.keys(PREF_LABELS) as (keyof NotifPrefs)[]).map(key => {
                const meta = PREF_LABELS[key]
                const val = prefs?.[key] ?? false
                return (
                  <div key={key} className="flex items-center gap-4 px-5 py-4">
                    <div className="p-1.5 bg-white/5 rounded-lg text-white/40">{meta.icon}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white">{meta.label}</p>
                      <p className="text-xs text-white/40 mt-0.5">{meta.desc}</p>
                    </div>
                    <Toggle on={val} onChange={() => toggle(key)} disabled={saving} />
                  </div>
                )
              })}
            </div>
          </div>

          {/* Web push card */}
          <div className="space-y-4">
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                {pushStatus === 'granted'
                  ? <Wifi className="w-4 h-4 text-green-400" />
                  : pushStatus === 'denied'
                  ? <WifiOff className="w-4 h-4 text-red-400" />
                  : <BellRing className="w-4 h-4 text-vit-400" />}
                <p className="text-sm font-semibold text-white">Browser Push</p>
              </div>
              <p className="text-xs text-white/40 mb-4 leading-relaxed">
                Receive real-time alerts in your browser even when the tab is in the background.
              </p>
              {pushStatus === 'granted' ? (
                <div className="flex items-center gap-2 text-green-300 text-sm">
                  <CheckCircle2 className="w-4 h-4" /> Enabled
                </div>
              ) : pushStatus === 'denied' ? (
                <div className="flex items-center gap-2 text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4" /> Blocked by browser settings
                </div>
              ) : (
                <button onClick={requestWebPush} disabled={pushStatus === 'pending'}
                  className="w-full py-2 bg-vit-400/10 hover:bg-vit-400/20 text-vit-300 border border-vit-400/20 rounded-xl text-sm font-medium transition-colors disabled:opacity-60">
                  {pushStatus === 'pending' ? 'Requesting…' : 'Enable browser push'}
                </button>
              )}
            </div>

            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5">
              <p className="text-sm font-semibold text-white mb-2">Firebase (mobile)</p>
              <p className="text-xs text-white/40 leading-relaxed mb-3">
                Mobile push will be active automatically once you install vit-mobile and sign in with this account.
              </p>
              <div className="flex items-center gap-2 text-white/30 text-xs">
                <Clock className="w-3.5 h-3.5" /> Available Q4 2026
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

// ── Section 3: Telegram Bot ───────────────────────────────────────────────────

const BOT_COMMANDS = [
  { cmd: '/start',      desc: 'Link your VitNetwork account' },
  { cmd: '/tips',       desc: 'Latest AI prediction tips' },
  { cmd: '/balance',    desc: 'Check your VIT wallet balance' },
  { cmd: '/matches',    desc: 'Live match scores right now' },
  { cmd: '/subscribe',  desc: 'Enable alert categories' },
  { cmd: '/help',       desc: 'Full command reference' },
]

function TelegramSection({ isAuth }: { isAuth: boolean }) {
  const qc = useQueryClient()
  const { data: tgInfo, isLoading } = useTelegramInfo(isAuth)
  const [chatId, setChatId] = useState('')
  const [linking, setLinking] = useState(false)
  const [linkError, setLinkError] = useState('')

  const handleLink = async (e: React.FormEvent) => {
    e.preventDefault()
    setLinking(true); setLinkError('')
    const r = await fetch(`${GW()}/api/notifications/telegram/link-manual`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId }),
    })
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      setLinkError((err as { detail?: string }).detail ?? 'Linking failed')
    } else {
      qc.invalidateQueries({ queryKey: ['tg-link'] })
    }
    setLinking(false)
  }

  const handleUnlink = useMutation({
    mutationFn: async () => {
      await fetch(`${GW()}/api/notifications/telegram/unlink`, { method: 'POST', headers: authHeaders() })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tg-link'] }),
  })

  return (
    <section className="mb-14">
      <SectionHeader icon={<Bot className="w-5 h-5" />} title="Telegram Bot" desc="Get prediction alerts, live scores, and wallet updates directly in Telegram." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Connection card */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-12 h-12 rounded-2xl bg-[#229ed9]/10 border border-[#229ed9]/20 flex items-center justify-center">
              <Send className="w-6 h-6 text-[#229ed9]" />
            </div>
            <div>
              <p className="font-semibold text-white">@VitNetworkBot</p>
              <p className="text-xs text-white/40">Official VitNetwork Telegram bot</p>
            </div>
            <a href="https://t.me/VitNetworkBot" target="_blank" rel="noopener noreferrer"
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#229ed9]/10 hover:bg-[#229ed9]/20 text-[#229ed9] border border-[#229ed9]/20 rounded-lg transition-colors">
              Open <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          {!isAuth ? (
            <p className="text-sm text-white/40">Sign in to link your Telegram account.</p>
          ) : isLoading ? (
            <Spinner className="w-5 h-5" />
          ) : tgInfo?.linked ? (
            <div>
              <div className="flex items-center gap-2 text-green-300 mb-4">
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-sm font-medium">Linked{tgInfo.username ? ` as @${tgInfo.username}` : ''}</span>
              </div>
              <p className="text-xs text-white/30 mb-4">Chat ID: <span className="font-mono">{tgInfo.chat_id}</span></p>
              <button onClick={() => handleUnlink.mutate()} disabled={handleUnlink.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-400/10 hover:bg-red-400/20 text-red-400 border border-red-400/20 rounded-xl text-sm transition-colors disabled:opacity-60">
                {handleUnlink.isPending ? <Spinner className="w-4 h-4" /> : <Unlink className="w-4 h-4" />} Unlink Telegram
              </button>
            </div>
          ) : (
            <div>
              <div className="bg-white/5 border border-white/10 rounded-xl p-4 mb-4">
                <p className="text-xs text-white/40 mb-2 font-medium uppercase tracking-wider">Steps to link</p>
                <ol className="space-y-2 text-sm text-white/60">
                  <li className="flex items-start gap-2"><span className="text-vit-400 font-bold">1.</span> Open @VitNetworkBot and send <code className="bg-white/10 px-1 rounded text-xs">/start</code></li>
                  <li className="flex items-start gap-2"><span className="text-vit-400 font-bold">2.</span> Copy your Chat ID from the bot's response</li>
                  <li className="flex items-start gap-2"><span className="text-vit-400 font-bold">3.</span> Paste it below and click Link</li>
                </ol>
              </div>
              <form onSubmit={handleLink} className="flex gap-2">
                <input value={chatId} onChange={e => setChatId(e.target.value)} required placeholder="Your Chat ID (e.g. 123456789)"
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white font-mono placeholder:text-white/30 focus:outline-none focus:border-vit-400/50 min-w-0" />
                <button type="submit" disabled={linking}
                  className="px-4 py-2 bg-vit-400 hover:bg-vit-300 text-black font-semibold rounded-xl text-sm transition-colors disabled:opacity-60 flex items-center gap-2">
                  {linking ? <Spinner className="w-4 h-4" /> : <Link2 className="w-4 h-4" />} Link
                </button>
              </form>
              {linkError && <p className="text-red-400 text-xs mt-2">{linkError}</p>}
            </div>
          )}
        </div>

        {/* Bot commands */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-white/10">
            <p className="text-sm font-semibold text-white">Bot commands</p>
          </div>
          <div className="divide-y divide-white/5">
            {BOT_COMMANDS.map(({ cmd, desc }) => (
              <div key={cmd} className="flex items-center gap-4 px-5 py-3.5">
                <code className="text-sm font-mono text-vit-300 bg-vit-400/10 px-2 py-0.5 rounded w-32 flex-shrink-0">{cmd}</code>
                <p className="text-sm text-white/50">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Section 4: SDK & Developer API ────────────────────────────────────────────

function DevApiSection({ isAuth }: { isAuth: boolean }) {
  const qc = useQueryClient()
  const { data: keys = [], isLoading: keysLoading } = useDevKeys(isAuth)
  const { data: plans = [] } = useDevPlans()
  const { data: usage } = useDevUsage(isAuth)
  const [newKeyName, setNewKeyName] = useState('')
  const [creating, setCreating] = useState(false)
  const [revealed, setRevealed] = useState<Record<number, string>>({})
  const [showCreate, setShowCreate] = useState(false)

  const createKey = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    const r = await fetch(`${GW()}/api/developer/keys`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newKeyName }),
    })
    if (r.ok) {
      const key: DevKey = await r.json()
      if (key.key) setRevealed(rv => ({ ...rv, [key.id]: key.key! }))
      qc.invalidateQueries({ queryKey: ['dev-keys'] })
      setNewKeyName(''); setShowCreate(false)
    }
    setCreating(false)
  }

  const revokeKey = async (id: number) => {
    await fetch(`${GW()}/api/developer/keys/${id}/revoke`, { method: 'PATCH', headers: authHeaders() })
    qc.invalidateQueries({ queryKey: ['dev-keys'] })
  }

  const SDK_SNIPPETS = [
    {
      lang: 'cURL',
      icon: <Terminal className="w-3.5 h-3.5" />,
      code: `curl -X GET "${GW()}/api/predictions/today" \\
  -H "X-API-Key: vit_live_sk_..." \\
  -H "Content-Type: application/json"`,
    },
    {
      lang: 'Python',
      icon: <Code2 className="w-3.5 h-3.5" />,
      code: `import httpx
KEY = "vit_live_sk_..."
BASE = "${GW()}"
tips = httpx.get(f"{BASE}/api/predictions/today",
    headers={"X-API-Key": KEY}).json()`,
    },
    {
      lang: 'JavaScript',
      icon: <Globe className="w-3.5 h-3.5" />,
      code: `const res = await fetch(
  '${GW()}/api/predictions/today',
  { headers: { 'X-API-Key': 'vit_live_sk_...' } }
);
const tips = await res.json();`,
    },
  ]
  const [activeSnippet, setActiveSnippet] = useState(0)

  return (
    <section className="mb-14">
      <SectionHeader icon={<Code2 className="w-5 h-5" />} title="SDK & Developer API" desc="Build on VitNetwork — access predictions, wallets, and marketplace models." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API keys panel */}
        <div>
          <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden mb-4">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/10">
              <p className="text-sm font-semibold text-white">API Keys</p>
              {isAuth && (
                <button onClick={() => setShowCreate(s => !s)}
                  className="flex items-center gap-1.5 text-xs font-medium text-vit-300 bg-vit-400/10 hover:bg-vit-400/20 border border-vit-400/20 px-2.5 py-1 rounded-lg transition-colors">
                  <Plus className="w-3.5 h-3.5" /> New key
                </button>
              )}
            </div>

            {showCreate && (
              <form onSubmit={createKey} className="flex gap-2 px-5 py-3.5 border-b border-white/10 bg-vit-400/5">
                <input value={newKeyName} onChange={e => setNewKeyName(e.target.value)} required placeholder="Key name (e.g. my-bot)"
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-400/50 min-w-0" />
                <button type="submit" disabled={creating}
                  className="px-4 py-2 bg-vit-400 hover:bg-vit-300 text-black font-semibold rounded-xl text-sm transition-colors disabled:opacity-60">
                  {creating ? <Spinner className="w-4 h-4" /> : 'Create'}
                </button>
              </form>
            )}

            {!isAuth ? (
              <p className="px-5 py-8 text-center text-sm text-white/40">Sign in to manage API keys.</p>
            ) : keysLoading ? (
              <div className="flex items-center justify-center py-8"><Spinner className="w-5 h-5" /></div>
            ) : keys.length === 0 ? (
              <div className="px-5 py-8 text-center">
                <Key className="w-8 h-8 mx-auto mb-2 text-white/20" />
                <p className="text-sm text-white/40">No API keys yet. Create one to get started.</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {keys.map(k => (
                  <div key={k.id} className="px-5 py-4">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-sm font-semibold text-white">{k.name}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full border',
                            k.is_active ? 'bg-green-400/10 text-green-300 border-green-400/20' : 'bg-white/5 text-white/30 border-white/10')}>
                            {k.is_active ? 'Active' : 'Revoked'}
                          </span>
                          <span className="text-[10px] text-white/30 uppercase tracking-wider">{k.plan}</span>
                        </div>
                      </div>
                      {k.is_active && (
                        <button onClick={() => revokeKey(k.id)}
                          className="p-1.5 text-white/30 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                    <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2">
                      <Key className="w-3.5 h-3.5 text-white/30 flex-shrink-0" />
                      <code className="text-xs text-white/60 flex-1 font-mono truncate">
                        {revealed[k.id] ?? `${k.key_prefix}${'•'.repeat(24)}`}
                      </code>
                      {revealed[k.id] ? (
                        <>
                          <CopyBtn text={revealed[k.id]} />
                          <button onClick={() => setRevealed(rv => { const n = { ...rv }; delete n[k.id]; return n })} className="text-white/30 hover:text-white">
                            <EyeOff className="w-3.5 h-3.5" />
                          </button>
                        </>
                      ) : (
                        <button onClick={() => setRevealed(rv => ({ ...rv, [k.id]: `${k.key_prefix}...hidden` }))} className="text-white/30 hover:text-white">
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                    <div className="flex gap-4 mt-2 text-xs text-white/30">
                      <span>{k.requests_today.toLocaleString()} today</span>
                      <span>{k.requests_month.toLocaleString()} this month</span>
                      {k.last_used_at && <span>Last: {new Date(k.last_used_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Usage summary */}
          {isAuth && usage && (
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Today', value: usage.requests_today.toLocaleString() },
                { label: 'This month', value: usage.requests_month.toLocaleString() },
                { label: 'Plan', value: usage.plan },
              ].map(({ label, value }) => (
                <div key={label} className="bg-white/[0.03] border border-white/10 rounded-xl p-3 text-center">
                  <p className="text-xs text-white/30 mb-1">{label}</p>
                  <p className="text-sm font-bold text-white">{value}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Code snippets + plans */}
        <div className="space-y-4">
          {/* Code playground */}
          <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
            <div className="flex border-b border-white/10">
              {SDK_SNIPPETS.map((s, i) => (
                <button key={s.lang} onClick={() => setActiveSnippet(i)}
                  className={cn('flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-all',
                    activeSnippet === i ? 'text-white border-b-2 border-vit-400 -mb-px bg-vit-400/5' : 'text-white/40 hover:text-white/70')}>
                  {s.icon} {s.lang}
                </button>
              ))}
              <div className="ml-auto flex items-center px-3">
                <CopyBtn text={SDK_SNIPPETS[activeSnippet].code} />
              </div>
            </div>
            <pre className="px-5 py-4 text-xs text-green-300 font-mono overflow-x-auto leading-relaxed bg-black/20">
              {SDK_SNIPPETS[activeSnippet].code}
            </pre>
          </div>

          {/* Developer plans */}
          {plans.length > 0 && (
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-white/10">
                <p className="text-sm font-semibold text-white">Developer Plans</p>
              </div>
              <div className="divide-y divide-white/5">
                {plans.slice(0, 3).map(plan => (
                  <div key={plan.name} className="flex items-center gap-4 px-5 py-3.5">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-white capitalize">{plan.name}</p>
                      <p className="text-xs text-white/40">{(plan.requests_per_day ?? 0).toLocaleString()}/day · {(plan.requests_per_month ?? 0).toLocaleString()}/mo</p>
                    </div>
                    <span className="font-mono text-sm text-vit-300">{plan.price_vit === 0 ? 'Free' : `${plan.price_vit} VIT/mo`}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick links */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { icon: <Webhook className="w-4 h-4" />,   label: 'Webhooks',      href: '/developers', desc: 'Configure event callbacks' },
              { icon: <BarChart3 className="w-4 h-4" />, label: 'API Docs',      href: '/documentation', desc: 'Full endpoint reference' },
              { icon: <Shield className="w-4 h-4" />,    label: 'Rate limits',   href: '/developers', desc: 'Usage limits & throttling' },
              { icon: <Package className="w-4 h-4" />,   label: 'SDKs',          href: '/developers', desc: 'Node.js · Python · Go' },
            ].map(link => (
              <a key={link.label} href={link.href}
                className="flex items-start gap-3 bg-white/[0.03] border border-white/10 hover:border-white/25 rounded-xl p-3.5 transition-colors group">
                <div className="p-1.5 bg-white/5 rounded-lg text-white/40 group-hover:text-vit-400 transition-colors">{link.icon}</div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-white group-hover:text-vit-300 transition-colors flex items-center gap-1">
                    {link.label} <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </p>
                  <p className="text-xs text-white/40">{link.desc}</p>
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Section 5: vit-storage CDN ────────────────────────────────────────────────

const CDN_FEATURES = [
  { icon: <Globe className="w-4 h-4" />,    title: 'Global edge CDN',   desc: 'Assets served from 40+ PoPs worldwide' },
  { icon: <Shield className="w-4 h-4" />,   title: 'On-chain hashes',   desc: 'Integrity proofs anchored to VitNetwork chain' },
  { icon: <Zap className="w-4 h-4" />,      title: '<10ms TTFB',        desc: 'Optimised for low-latency real-time apps' },
  { icon: <Database className="w-4 h-4" />, title: 'S3-compatible API', desc: 'Drop-in replacement for existing S3 clients' },
]

function StorageCDNSection() {
  return (
    <section className="mb-6">
      <SectionHeader icon={<Database className="w-5 h-5" />} title="vit-storage CDN" desc="Decentralised asset storage with on-chain integrity verification." />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 grid grid-cols-2 gap-3">
          {CDN_FEATURES.map(f => (
            <div key={f.title} className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex items-start gap-3">
              <div className="p-2 bg-vit-400/10 rounded-lg text-vit-400 flex-shrink-0">{f.icon}</div>
              <div>
                <p className="text-sm font-semibold text-white">{f.title}</p>
                <p className="text-xs text-white/40 mt-0.5">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-white/10">
            <p className="text-sm font-semibold text-white">Quick upload</p>
          </div>
          <div className="p-5 space-y-3">
            <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center hover:border-vit-400/30 transition-colors cursor-pointer">
              <Download className="w-6 h-6 mx-auto mb-2 text-white/30" />
              <p className="text-sm text-white/40">Drop files or click to browse</p>
              <p className="text-xs text-white/20 mt-1">Max 100 MB · Any file type</p>
            </div>
            <a href="/storage"
              className="flex items-center justify-center gap-2 w-full py-2.5 bg-vit-400/10 hover:bg-vit-400/20 text-vit-300 border border-vit-400/20 rounded-xl text-sm font-medium transition-colors">
              Open Storage Manager <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      </div>

      {/* API snippet */}
      <div className="mt-4 bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <p className="text-xs font-mono text-white/40">S3-compatible upload example</p>
          <CopyBtn text={`import boto3
s3 = boto3.client('s3',
    endpoint_url='${GW()}/s3',
    aws_access_key_id='vit_access_key',
    aws_secret_access_key='your_secret')
s3.upload_file('photo.jpg', 'my-bucket', 'photo.jpg')`} />
        </div>
        <pre className="px-5 py-4 text-xs font-mono text-green-300 overflow-x-auto bg-black/20 leading-relaxed">{`import boto3
s3 = boto3.client('s3',
    endpoint_url='${GW()}/s3',
    aws_access_key_id='vit_access_key',
    aws_secret_access_key='your_secret')
s3.upload_file('photo.jpg', 'my-bucket', 'photo.jpg')`}</pre>
      </div>
    </section>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Ecosystem() {
  const isAuth = !!getAuthToken()

  return (
    <div className="min-h-screen bg-[#07090f] text-white pt-20 pb-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">

        {/* Hero */}
        <div className="mb-12">
          <div className="flex items-center gap-2 text-vit-400 text-sm font-semibold mb-3">
            <Smartphone className="w-4 h-4" /> Phase VII — Mobile & Ecosystem
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">Ecosystem Expansion</h1>
          <p className="text-white/50 max-w-2xl">
            VIT Network delivers Value · Intelligence · Transparency beyond the browser — a native mobile app, real-time push alerts, Telegram bot, developer SDK, and decentralised asset storage.
          </p>
          <div className="flex flex-wrap gap-3 mt-5">
            {[
              { icon: <Smartphone className="w-3.5 h-3.5" />, label: 'vit-mobile' },
              { icon: <Bell className="w-3.5 h-3.5" />,       label: 'Push Notifications' },
              { icon: <Bot className="w-3.5 h-3.5" />,        label: 'Telegram Bot' },
              { icon: <Code2 className="w-3.5 h-3.5" />,      label: 'Developer SDK' },
              { icon: <Database className="w-3.5 h-3.5" />,   label: 'vit-storage CDN' },
            ].map(tag => (
              <span key={tag.label}
                className="flex items-center gap-1.5 text-xs font-medium px-3 py-1 bg-vit-400/10 text-vit-300 border border-vit-400/20 rounded-full">
                {tag.icon} {tag.label}
              </span>
            ))}
          </div>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
          <MobileSection />
          <NotifSection isAuth={isAuth} />
          <TelegramSection isAuth={isAuth} />
          <DevApiSection isAuth={isAuth} />
          <StorageCDNSection />
        </motion.div>

      </div>
    </div>
  )
}
