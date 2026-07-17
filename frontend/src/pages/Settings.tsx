import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  User, Shield, Bell, Trash2, Eye, EyeOff, CheckCircle2,
  AlertCircle, Lock, Mail, Save, Smartphone, LogOut,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken, clearAuth } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { toast } from 'sonner'

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/users/me`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    retry: false, staleTime: 60_000,
  })
}

function useTOTPSetup() {
  return useQuery({
    queryKey: ['totp-setup'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/2fa/setup`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    enabled: false, // triggered manually
    retry: false,
  })
}

// ── Tabs ───────────────────────────────────────────────────────────────────────

type Tab = 'profile' | 'security' | 'notifications'

const TABS: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: 'profile',       label: 'Profile',       icon: User    },
  { key: 'security',      label: 'Security',       icon: Shield  },
  { key: 'notifications', label: 'Notifications',  icon: Bell    },
]

// ── Profile Tab ────────────────────────────────────────────────────────────────

function ProfileTab({ profile }: { profile: any }) {
  const qc       = useQueryClient()
  const [form, setForm] = useState({
    username:   profile?.username ?? '',
    email:      profile?.email    ?? '',
    bio:        profile?.bio      ?? '',
    avatar_url: profile?.avatar_url ?? '',
  })
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: async (data: typeof form) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/users/me`, {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? d.message ?? 'Update failed')
      return d
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
      toast.success('Profile updated')
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <form
      onSubmit={e => { e.preventDefault(); mutation.mutate(form) }}
      className="space-y-5"
    >
      <Field label="Username" icon={<User className="w-4 h-4" />}>
        <input
          value={form.username}
          onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
          placeholder="@username"
          className={INPUT}
        />
      </Field>

      <Field label="Email" icon={<Mail className="w-4 h-4" />}>
        <input
          type="email"
          value={form.email}
          onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
          placeholder="you@example.com"
          className={INPUT}
        />
      </Field>

      <Field label="Bio">
        <textarea
          value={form.bio}
          onChange={e => setForm(f => ({ ...f, bio: e.target.value }))}
          rows={3}
          placeholder="Short bio visible on your public profile…"
          className={cn(INPUT, 'resize-none')}
        />
      </Field>

      <Field label="Avatar URL">
        <input
          value={form.avatar_url}
          onChange={e => setForm(f => ({ ...f, avatar_url: e.target.value }))}
          placeholder="https://…"
          className={INPUT}
        />
      </Field>

      <button
        type="submit"
        disabled={mutation.isPending}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 transition-colors"
      >
        {saved ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Save className="w-4 h-4" />}
        {mutation.isPending ? 'Saving…' : saved ? 'Saved' : 'Save Changes'}
      </button>
    </form>
  )
}

// ── Security Tab ───────────────────────────────────────────────────────────────

function SecurityTab({ profile }: { profile: any }) {
  const navigate = useNavigate()
  const qc       = useQueryClient()
  const [pw, setPw]           = useState({ current: '', next: '', confirm: '' })
  const [showPw, setShowPw]   = useState(false)
  const [totpQR, setTotpQR]   = useState<string | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [loadingQR, setLoadingQR] = useState(false)

  const pwMutation = useMutation({
    mutationFn: async () => {
      if (pw.next !== pw.confirm) throw new Error('New passwords do not match')
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/change-password`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: pw.current, new_password: pw.next }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? 'Change failed')
      return d
    },
    onSuccess: () => { toast.success('Password changed'); setPw({ current: '', next: '', confirm: '' }) },
    onError: (e: Error) => toast.error(e.message),
  })

  const totpMutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/2fa/enable`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: totpCode }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? 'Verification failed')
      return d
    },
    onSuccess: () => { toast.success('2FA enabled'); setTotpQR(null); setTotpCode(''); qc.invalidateQueries({ queryKey: ['profile'] }) },
    onError: (e: Error) => toast.error(e.message),
  })

  async function getQR() {
    setLoadingQR(true)
    try {
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/2fa/setup`, { headers: authHeaders() })
      const d = await r.json()
      if (r.ok) setTotpQR(d.qr_code_url || d.otpauth_url || null)
      else toast.error(d.detail ?? 'Could not fetch QR code')
    } finally {
      setLoadingQR(false)
    }
  }

  function logout() {
    clearAuth()
    qc.clear()
    navigate('/login')
  }

  return (
    <div className="space-y-8">
      {/* Change password */}
      <section>
        <h3 className="font-semibold text-white mb-4">Change Password</h3>
        <form
          onSubmit={e => { e.preventDefault(); pwMutation.mutate() }}
          className="space-y-4"
        >
          {(['current', 'next', 'confirm'] as const).map(k => (
            <Field key={k} label={k === 'current' ? 'Current password' : k === 'next' ? 'New password' : 'Confirm new password'} icon={<Lock className="w-4 h-4" />}>
              <input
                type={showPw ? 'text' : 'password'}
                value={pw[k]}
                onChange={e => setPw(p => ({ ...p, [k]: e.target.value }))}
                placeholder="••••••••"
                className={INPUT}
              />
            </Field>
          ))}
          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={pwMutation.isPending}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 transition-colors"
            >
              <Lock className="w-4 h-4" />
              {pwMutation.isPending ? 'Saving…' : 'Update Password'}
            </button>
            <button
              type="button"
              onClick={() => setShowPw(v => !v)}
              className="flex items-center gap-1.5 text-sm text-white/40 hover:text-white/70 transition-colors"
            >
              {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {showPw ? 'Hide' : 'Show'} passwords
            </button>
          </div>
        </form>
      </section>

      {/* 2FA */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-white">Two-Factor Authentication</h3>
            <p className="text-xs text-white/40 mt-0.5">Add an extra layer of security with an authenticator app.</p>
          </div>
          {profile?.totp_enabled ? (
            <span className="px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 text-xs font-medium">Enabled</span>
          ) : (
            <span className="px-2.5 py-1 rounded-full bg-white/8 text-white/40 text-xs">Disabled</span>
          )}
        </div>

        {!profile?.totp_enabled && (
          <>
            {!totpQR ? (
              <button
                onClick={getQR}
                disabled={loadingQR}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white hover:bg-white/10 disabled:opacity-50 transition-colors"
              >
                <Smartphone className="w-4 h-4" />
                {loadingQR ? 'Loading…' : 'Set up 2FA'}
              </button>
            ) : (
              <div className="space-y-4 p-4 rounded-xl bg-white/5 border border-white/10">
                <p className="text-sm text-white/70">
                  Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.), then enter the 6-digit code below.
                </p>
                {totpQR.startsWith('data:image') ? (
                  <img src={totpQR} alt="TOTP QR Code" className="w-40 h-40 rounded-lg border border-white/10" />
                ) : (
                  <div className="text-xs text-white/40 font-mono break-all">{totpQR}</div>
                )}
                <div className="flex gap-3">
                  <input
                    value={totpCode}
                    onChange={e => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxLength={6}
                    className="w-36 text-center bg-surface-900/60 border border-white/10 rounded-lg px-3 py-2.5 text-white font-mono text-lg tracking-widest focus:outline-none focus:border-vit-500/60"
                  />
                  <button
                    onClick={() => totpMutation.mutate()}
                    disabled={totpCode.length !== 6 || totpMutation.isPending}
                    className="px-4 py-2 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 transition-colors"
                  >
                    {totpMutation.isPending ? 'Verifying…' : 'Enable 2FA'}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>

      {/* Danger zone */}
      <section className="border-t border-white/6 pt-6">
        <h3 className="font-semibold text-red-400 mb-3">Danger Zone</h3>
        <button
          onClick={logout}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm hover:bg-red-500/15 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out of all devices
        </button>
      </section>
    </div>
  )
}

// ── Notifications Tab ──────────────────────────────────────────────────────────

function NotificationsTab() {
  const [prefs, setPrefs] = useState({
    predictions_resolved: true,
    governance_votes:     true,
    wallet_transactions:  true,
    leaderboard_updates:  false,
    marketing_emails:     false,
  })

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/users/me/notifications`, {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs),
      })
      if (!r.ok) throw new Error('Failed to update preferences')
      return r.json()
    },
    onSuccess: () => toast.success('Notification preferences saved'),
    onError: (e: Error) => toast.error(e.message),
  })

  const ITEMS: { key: keyof typeof prefs; label: string; desc: string }[] = [
    { key: 'predictions_resolved', label: 'Prediction resolved',   desc: 'When a match you predicted on is settled'    },
    { key: 'governance_votes',     label: 'Governance activity',   desc: 'New proposals and vote results'               },
    { key: 'wallet_transactions',  label: 'Wallet transactions',   desc: 'Deposits, withdrawals and sends'              },
    { key: 'leaderboard_updates',  label: 'Leaderboard changes',   desc: 'When your rank changes'                       },
    { key: 'marketing_emails',     label: 'Product updates',       desc: 'Feature announcements and newsletters'        },
  ]

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {ITEMS.map(item => (
          <label
            key={item.key}
            className="flex items-center justify-between p-4 rounded-xl bg-white/3 border border-white/8 cursor-pointer hover:bg-white/5 transition-colors"
          >
            <div>
              <p className="text-sm font-medium text-white">{item.label}</p>
              <p className="text-xs text-white/40 mt-0.5">{item.desc}</p>
            </div>
            <div
              onClick={() => setPrefs(p => ({ ...p, [item.key]: !p[item.key] }))}
              className={cn(
                'relative w-10 h-5.5 rounded-full transition-colors cursor-pointer shrink-0',
                prefs[item.key] ? 'bg-vit-600' : 'bg-white/10',
              )}
              style={{ height: '22px', width: '40px' }}
            >
              <span
                className={cn(
                  'absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform',
                  prefs[item.key] ? 'translate-x-[18px]' : 'translate-x-0',
                )}
              />
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 transition-colors"
      >
        <Save className="w-4 h-4" />
        {mutation.isPending ? 'Saving…' : 'Save Preferences'}
      </button>
    </div>
  )
}

// ── Shared UI helpers ──────────────────────────────────────────────────────────

const INPUT = 'w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm placeholder-white/25 focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-colors'

function Field({ label, icon, children }: { label: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-white/60 mb-1.5">{label}</label>
      {icon ? (
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none">{icon}</span>
          <div className="[&>*]:pl-9">{children}</div>
        </div>
      ) : children}
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Settings() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('profile')
  const { data: profile, isLoading } = useProfile()

  useEffect(() => {
    if (!isLoading && profile === null) navigate('/login')
  }, [isLoading, profile, navigate])

  if (isLoading) {
    return (
      <div className="pt-24 min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="pt-20 pb-20 min-h-screen relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      <div className="relative max-w-3xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-2xl font-bold text-white">Account Settings</h1>
          <p className="text-white/45 text-sm mt-1">Manage your profile, security and preferences.</p>
        </motion.div>

        <div className="flex flex-col sm:flex-row gap-6">
          {/* Sidebar tabs */}
          <motion.nav
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.05 }}
            className="sm:w-44 shrink-0"
          >
            <ul className="space-y-1">
              {TABS.map(t => (
                <li key={t.key}>
                  <button
                    onClick={() => setTab(t.key)}
                    className={cn(
                      'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left',
                      tab === t.key
                        ? 'bg-vit-500/15 text-vit-400'
                        : 'text-white/50 hover:text-white hover:bg-white/5',
                    )}
                  >
                    <t.icon className="w-4 h-4 shrink-0" />
                    {t.label}
                  </button>
                </li>
              ))}
            </ul>
          </motion.nav>

          {/* Content panel */}
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex-1 bg-surface-800/60 border border-white/8 rounded-2xl p-6"
          >
            {tab === 'profile'       && <ProfileTab profile={profile} />}
            {tab === 'security'      && <SecurityTab profile={profile} />}
            {tab === 'notifications' && <NotificationsTab />}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
