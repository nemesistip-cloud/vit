import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  User, Shield, Bell, Eye, EyeOff, CheckCircle2,
  Lock, Mail, Save, Smartphone, LogOut, Monitor,
  Trash2, Globe, Clock, Key, ShieldCheck, AlertTriangle,
  Laptop, RefreshCw, CheckCheck, Wallet, Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken, clearAuth } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { toast } from 'sonner'

// ── Shared helpers ─────────────────────────────────────────────────────────────

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

function SectionHead({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-5">
      <h3 className="font-semibold text-white">{title}</h3>
      {subtitle && <p className="text-xs text-white/40 mt-0.5">{subtitle}</p>}
    </div>
  )
}

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

function useSecurityOverview() {
  return useQuery({
    queryKey: ['security-overview'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/identity/me/security-overview`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    retry: false, staleTime: 30_000,
  })
}

function useSessions() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/identity/me/sessions`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : []
    },
    retry: false, staleTime: 20_000,
  })
}

function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/identity/me/devices`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : []
    },
    retry: false, staleTime: 20_000,
  })
}

function useLoginHistory() {
  return useQuery({
    queryKey: ['login-history'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/identity/me/login-history?limit=40`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : []
    },
    retry: false, staleTime: 30_000,
  })
}

function usePermissions() {
  return useQuery({
    queryKey: ['permissions'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/identity/me/permissions`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : []
    },
    retry: false, staleTime: 60_000,
  })
}

// ── Tabs ───────────────────────────────────────────────────────────────────────

type Tab = 'profile' | 'security' | 'sessions' | 'devices' | 'history' | 'permissions' | 'notifications'

const TABS: { key: Tab; label: string; icon: React.ElementType; authOnly?: boolean }[] = [
  { key: 'profile',       label: 'Profile',        icon: User        },
  { key: 'security',      label: 'Security',        icon: Shield      },
  { key: 'sessions',      label: 'Sessions',        icon: Monitor,    authOnly: true },
  { key: 'devices',       label: 'Devices',         icon: Laptop,     authOnly: true },
  { key: 'history',       label: 'Login History',   icon: Clock,      authOnly: true },
  { key: 'permissions',   label: 'Permissions',     icon: Key,        authOnly: true },
  { key: 'notifications', label: 'Notifications',   icon: Bell        },
]

// ── Profile Tab ────────────────────────────────────────────────────────────────

function ProfileTab({ profile }: { profile: any }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    username:   profile?.username   ?? '',
    email:      profile?.email      ?? '',
    bio:        profile?.bio        ?? '',
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
    <form onSubmit={e => { e.preventDefault(); mutation.mutate(form) }} className="space-y-5">
      <Field label="Username" icon={<User className="w-4 h-4" />}>
        <input value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} placeholder="@username" className={INPUT} />
      </Field>
      <Field label="Email" icon={<Mail className="w-4 h-4" />}>
        <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} placeholder="you@example.com" className={INPUT} />
      </Field>
      <Field label="Bio">
        <textarea value={form.bio} onChange={e => setForm(f => ({ ...f, bio: e.target.value }))} rows={3} placeholder="Short bio…" className={cn(INPUT, 'resize-none')} />
      </Field>
      <Field label="Avatar URL">
        <input value={form.avatar_url} onChange={e => setForm(f => ({ ...f, avatar_url: e.target.value }))} placeholder="https://…" className={INPUT} />
      </Field>
      <button type="submit" disabled={mutation.isPending}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 transition-colors">
        {saved ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Save className="w-4 h-4" />}
        {mutation.isPending ? 'Saving…' : saved ? 'Saved' : 'Save Changes'}
      </button>
    </form>
  )
}

// ── Security Tab ───────────────────────────────────────────────────────────────

function SecurityTab({ profile }: { profile: any }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: overview } = useSecurityOverview()
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' })
  const [showPw, setShowPw] = useState(false)
  const [totpQR, setTotpQR] = useState<string | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [loadingQR, setLoadingQR] = useState(false)

  const pwMutation = useMutation({
    mutationFn: async () => {
      if (pw.next !== pw.confirm) throw new Error('New passwords do not match')
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/change-password`, {
        method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
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
        method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ totp_code: totpCode }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? 'Verification failed')
      return d
    },
    onSuccess: () => {
      toast.success('2FA enabled')
      setTotpQR(null); setTotpCode('')
      qc.invalidateQueries({ queryKey: ['profile'] })
      qc.invalidateQueries({ queryKey: ['security-overview'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  async function getQR() {
    setLoadingQR(true)
    try {
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/2fa/setup`, { headers: authHeaders() })
      const d = await r.json()
      if (r.ok) setTotpQR(d.qr_code || d.qr_code_url || d.otpauth_url || null)
      else toast.error(d.detail ?? 'Could not fetch QR code')
    } finally { setLoadingQR(false) }
  }

  const securityScore = overview ? [
    overview.mfa_enabled,
    overview.wallet_linked,
    overview.email_verified,
  ].filter(Boolean).length * 33 : 0

  return (
    <div className="space-y-8">
      {/* Security Score */}
      {overview && (
        <div className="p-4 rounded-xl bg-white/3 border border-white/8">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-white">Security Score</span>
            <span className={cn('text-sm font-bold', securityScore >= 66 ? 'text-emerald-400' : securityScore >= 33 ? 'text-amber-400' : 'text-red-400')}>
              {securityScore}%
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-white/8 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${securityScore}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className={cn('h-full rounded-full', securityScore >= 66 ? 'bg-emerald-500' : securityScore >= 33 ? 'bg-amber-500' : 'bg-red-500')}
            />
          </div>
          <div className="grid grid-cols-3 gap-2 mt-3">
            {[
              { label: '2FA', ok: overview.mfa_enabled },
              { label: 'Wallet', ok: overview.wallet_linked },
              { label: 'Email', ok: overview.email_verified },
            ].map(item => (
              <div key={item.label} className={cn('flex items-center gap-1.5 text-xs', item.ok ? 'text-emerald-400' : 'text-white/30')}>
                {item.ok ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                {item.label}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-white/8">
            <div className="text-center">
              <p className="text-base font-bold text-white">{overview.active_sessions}</p>
              <p className="text-[10px] text-white/30">Active Sessions</p>
            </div>
            <div className="text-center">
              <p className="text-base font-bold text-white">{overview.trusted_devices}</p>
              <p className="text-[10px] text-white/30">Trusted Devices</p>
            </div>
            <div className="text-center">
              <p className="text-base font-bold text-white capitalize">{overview.role}</p>
              <p className="text-[10px] text-white/30">Role</p>
            </div>
          </div>
        </div>
      )}

      {/* Change password */}
      <section>
        <SectionHead title="Change Password" />
        <form onSubmit={e => { e.preventDefault(); pwMutation.mutate() }} className="space-y-4">
          {(['current', 'next', 'confirm'] as const).map(k => (
            <Field key={k} label={k === 'current' ? 'Current password' : k === 'next' ? 'New password' : 'Confirm new password'} icon={<Lock className="w-4 h-4" />}>
              <input type={showPw ? 'text' : 'password'} value={pw[k]} onChange={e => setPw(p => ({ ...p, [k]: e.target.value }))} placeholder="••••••••" className={INPUT} />
            </Field>
          ))}
          <div className="flex items-center gap-4">
            <button type="submit" disabled={pwMutation.isPending}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 transition-colors">
              <Lock className="w-4 h-4" />
              {pwMutation.isPending ? 'Saving…' : 'Update Password'}
            </button>
            <button type="button" onClick={() => setShowPw(v => !v)}
              className="flex items-center gap-1.5 text-sm text-white/40 hover:text-white/70 transition-colors">
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
          {profile?.totp_enabled
            ? <span className="px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 text-xs font-medium">Enabled</span>
            : <span className="px-2.5 py-1 rounded-full bg-white/8 text-white/40 text-xs">Disabled</span>}
        </div>
        {!profile?.totp_enabled && (
          !totpQR ? (
            <button onClick={getQR} disabled={loadingQR}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white hover:bg-white/10 disabled:opacity-50 transition-colors">
              <Smartphone className="w-4 h-4" />
              {loadingQR ? 'Loading…' : 'Set up 2FA'}
            </button>
          ) : (
            <div className="space-y-4 p-4 rounded-xl bg-white/5 border border-white/10">
              <p className="text-sm text-white/70">Scan this QR code with your authenticator app, then enter the 6-digit code below.</p>
              {totpQR.startsWith('data:image') ? (
                <img src={totpQR} alt="TOTP QR" className="w-40 h-40 rounded-lg border border-white/10" />
              ) : (
                <div className="text-xs text-white/40 font-mono break-all">{totpQR}</div>
              )}
              <div className="flex gap-3">
                <input value={totpCode} onChange={e => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000" maxLength={6}
                  className="w-36 text-center bg-surface-900/60 border border-white/10 rounded-lg px-3 py-2.5 text-white font-mono text-lg tracking-widest focus:outline-none focus:border-vit-500/60" />
                <button onClick={() => totpMutation.mutate()} disabled={totpCode.length !== 6 || totpMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 transition-colors">
                  {totpMutation.isPending ? 'Verifying…' : 'Enable 2FA'}
                </button>
              </div>
            </div>
          )
        )}
      </section>

      {/* Danger */}
      <section className="border-t border-white/6 pt-6">
        <h3 className="font-semibold text-red-400 mb-3">Danger Zone</h3>
        <button onClick={() => { clearAuth(); qc.clear(); navigate('/login') }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm hover:bg-red-500/15 transition-colors">
          <LogOut className="w-4 h-4" /> Sign out everywhere
        </button>
      </section>
    </div>
  )
}

// ── Sessions Tab ───────────────────────────────────────────────────────────────

function SessionsTab() {
  const qc = useQueryClient()
  const { data: sessions = [], isLoading, refetch } = useSessions()

  const revoke = useMutation({
    mutationFn: async (id: number) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/identity/me/sessions/${id}`, { method: 'DELETE', headers: authHeaders() })
      if (!r.ok && r.status !== 204) throw new Error('Revoke failed')
    },
    onSuccess: () => { toast.success('Session revoked'); qc.invalidateQueries({ queryKey: ['sessions'] }) },
    onError: (e: Error) => toast.error(e.message),
  })

  const revokeAll = useMutation({
    mutationFn: async () => {
      await fetch(`${ENDPOINTS.gateway}/api/identity/me/sessions`, { method: 'DELETE', headers: authHeaders() })
    },
    onSuccess: () => { toast.success('All sessions revoked'); qc.invalidateQueries({ queryKey: ['sessions'] }) },
  })

  if (isLoading) return <div className="flex justify-center py-10"><Spinner className="w-6 h-6" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionHead title="Active Sessions" subtitle="Devices currently signed in to your account." />
        <div className="flex gap-2">
          <button onClick={() => refetch()} className="p-2 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
          {sessions.length > 1 && (
            <button onClick={() => revokeAll.mutate()} disabled={revokeAll.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/15 transition-colors disabled:opacity-50">
              <LogOut className="w-3.5 h-3.5" /> Revoke All
            </button>
          )}
        </div>
      </div>

      {sessions.length === 0 ? (
        <div className="flex flex-col items-center py-12 gap-3 text-white/30">
          <Monitor className="w-10 h-10" />
          <p className="text-sm">No sessions found</p>
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((s: any) => (
            <div key={s.id} className={cn('flex items-start gap-3 p-4 rounded-xl border transition-colors', s.is_active ? 'bg-white/3 border-white/8' : 'bg-white/1 border-white/4 opacity-50')}>
              <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center shrink-0 mt-0.5">
                <Globe className="w-4 h-4 text-white/40" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-white truncate">{s.user_agent?.split(' ').slice(-1)[0] ?? 'Unknown browser'}</span>
                  {s.is_active && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-400">ACTIVE</span>}
                </div>
                <p className="text-xs text-white/35 mt-0.5">
                  {s.ip_address ?? 'Unknown IP'} · {s.device_id ? `Device ${s.device_id.slice(0, 8)}` : 'Unknown device'}
                </p>
                <p className="text-[10px] text-white/20 mt-1">
                  Last active {timeAgo(s.last_activity)} · Expires {new Date(s.expires_at).toLocaleDateString()}
                </p>
              </div>
              <button onClick={() => revoke.mutate(s.id)} disabled={revoke.isPending}
                className="shrink-0 px-2.5 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40">
                Revoke
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Devices Tab ────────────────────────────────────────────────────────────────

function DevicesTab() {
  const qc = useQueryClient()
  const { data: devices = [], isLoading, refetch } = useDevices()

  const trust = useMutation({
    mutationFn: async (deviceId: string) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/identity/me/devices/${encodeURIComponent(deviceId)}/trust`, { method: 'POST', headers: authHeaders() })
      if (!r.ok) throw new Error('Trust failed')
    },
    onSuccess: () => { toast.success('Device trusted'); qc.invalidateQueries({ queryKey: ['devices'] }) },
    onError: (e: Error) => toast.error(e.message),
  })

  const remove = useMutation({
    mutationFn: async (deviceId: string) => {
      await fetch(`${ENDPOINTS.gateway}/api/identity/me/devices/${encodeURIComponent(deviceId)}`, { method: 'DELETE', headers: authHeaders() })
    },
    onSuccess: () => { toast.success('Device removed'); qc.invalidateQueries({ queryKey: ['devices'] }) },
  })

  if (isLoading) return <div className="flex justify-center py-10"><Spinner className="w-6 h-6" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionHead title="Registered Devices" subtitle="Devices that have accessed your account." />
        <button onClick={() => refetch()} className="p-2 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {devices.length === 0 ? (
        <div className="flex flex-col items-center py-12 gap-3 text-white/30">
          <Laptop className="w-10 h-10" />
          <p className="text-sm">No devices registered</p>
          <p className="text-xs text-center">Devices appear here after you log in from them</p>
        </div>
      ) : (
        <div className="space-y-2">
          {devices.map((d: any) => (
            <div key={d.id} className="flex items-start gap-3 p-4 rounded-xl bg-white/3 border border-white/8">
              <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5', d.is_trusted ? 'bg-emerald-500/15' : 'bg-white/5')}>
                <Laptop className={cn('w-4 h-4', d.is_trusted ? 'text-emerald-400' : 'text-white/40')} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-white">{d.platform ?? d.device_id?.slice(0, 12) ?? 'Unknown device'}</span>
                  {d.is_trusted && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-400">TRUSTED</span>}
                  <span className={cn('px-1.5 py-0.5 rounded text-[9px] font-bold', d.risk_score < 30 ? 'bg-emerald-500/10 text-emerald-400' : d.risk_score < 70 ? 'bg-amber-500/10 text-amber-400' : 'bg-red-500/10 text-red-400')}>
                    Risk {d.risk_score}
                  </span>
                </div>
                <p className="text-xs text-white/35 mt-0.5">{d.browser ?? 'Unknown browser'} · {d.last_ip ?? 'Unknown IP'}</p>
                <p className="text-[10px] text-white/20 mt-1">Last seen {timeAgo(d.last_active)}</p>
              </div>
              <div className="flex gap-1 shrink-0">
                {!d.is_trusted && (
                  <button onClick={() => trust.mutate(d.device_id)} disabled={trust.isPending}
                    className="px-2.5 py-1.5 rounded-lg text-xs text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-40">
                    <ShieldCheck className="w-3.5 h-3.5" />
                  </button>
                )}
                <button onClick={() => remove.mutate(d.device_id)} disabled={remove.isPending}
                  className="px-2.5 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Login History Tab ──────────────────────────────────────────────────────────

const ACTION_LABEL: Record<string, { label: string; color: string }> = {
  login:          { label: 'Signed in',              color: 'text-emerald-400' },
  login_success:  { label: 'Signed in',              color: 'text-emerald-400' },
  login_failed:   { label: 'Failed login',           color: 'text-red-400'     },
  logout:         { label: 'Signed out',             color: 'text-white/40'    },
  password_reset: { label: 'Password reset',         color: 'text-amber-400'   },
  '2fa_enabled':  { label: '2FA enabled',            color: 'text-violet-400'  },
  '2fa_disabled': { label: '2FA disabled',           color: 'text-orange-400'  },
  email_verified: { label: 'Email verified',         color: 'text-emerald-400' },
}

function HistoryTab() {
  const { data: history = [], isLoading, refetch } = useLoginHistory()

  if (isLoading) return <div className="flex justify-center py-10"><Spinner className="w-6 h-6" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionHead title="Login History" subtitle="Recent authentication events on your account." />
        <button onClick={() => refetch()} className="p-2 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {history.length === 0 ? (
        <div className="flex flex-col items-center py-12 gap-3 text-white/30">
          <Clock className="w-10 h-10" />
          <p className="text-sm">No login history yet</p>
        </div>
      ) : (
        <div className="space-y-1">
          {history.map((h: any) => {
            const meta = ACTION_LABEL[h.action] ?? { label: h.action.replace(/_/g, ' '), color: 'text-white/50' }
            return (
              <div key={h.id} className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/3 transition-colors">
                <div className="w-2 h-2 rounded-full bg-white/15 shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className={cn('text-sm font-medium', meta.color)}>{meta.label}</span>
                  {h.details?.provider && <span className="text-xs text-white/30 ml-2">via {h.details.provider}</span>}
                  {h.ip_address && <span className="text-xs text-white/20 ml-2">· {h.ip_address}</span>}
                </div>
                <span className="text-[11px] text-white/25 shrink-0">{timeAgo(h.created_at)}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Permissions Tab ────────────────────────────────────────────────────────────

function PermissionsTab() {
  const { data: perms = [], isLoading } = usePermissions()

  if (isLoading) return <div className="flex justify-center py-10"><Spinner className="w-6 h-6" /></div>

  const byRole = (perms as any[]).reduce((acc: Record<string, any[]>, p) => {
    if (!acc[p.via_role]) acc[p.via_role] = []
    acc[p.via_role].push(p)
    return acc
  }, {})

  return (
    <div className="space-y-5">
      <SectionHead title="Your Permissions" subtitle="Permissions granted through your roles." />
      {Object.keys(byRole).length === 0 ? (
        <div className="flex flex-col items-center py-12 gap-3 text-white/30">
          <Key className="w-10 h-10" />
          <p className="text-sm">No permissions found</p>
        </div>
      ) : (
        Object.entries(byRole).map(([role, ps]) => (
          <div key={role} className="space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-4 h-4 text-vit-400" />
              <span className="text-sm font-semibold text-white capitalize">{role}</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-vit-500/10 text-vit-400">{(ps as any[]).length} permissions</span>
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              {(ps as any[]).map((p: any) => (
                <div key={p.slug} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/3 border border-white/6">
                  <CheckCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span className="text-sm font-mono text-white/70">{p.slug}</span>
                  {p.description && <span className="text-xs text-white/30 truncate ml-auto">{p.description}</span>}
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}

// ── Notifications Tab ──────────────────────────────────────────────────────────

function NotificationsTab() {
  const [prefs, setPrefs] = useState({
    predictions_resolved: true,
    governance_votes: true,
    wallet_transactions: true,
    leaderboard_updates: false,
    marketing_emails: false,
  })

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/users/me/notifications`, {
        method: 'PATCH', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs),
      })
      if (!r.ok) throw new Error('Failed to update preferences')
      return r.json()
    },
    onSuccess: () => toast.success('Notification preferences saved'),
    onError: (e: Error) => toast.error(e.message),
  })

  const ITEMS: { key: keyof typeof prefs; label: string; desc: string }[] = [
    { key: 'predictions_resolved', label: 'Prediction resolved',  desc: 'When a match you predicted on is settled'   },
    { key: 'governance_votes',     label: 'Governance activity',  desc: 'New proposals and vote results'              },
    { key: 'wallet_transactions',  label: 'Wallet transactions',  desc: 'Deposits, withdrawals and sends'             },
    { key: 'leaderboard_updates',  label: 'Leaderboard changes',  desc: 'When your rank changes'                      },
    { key: 'marketing_emails',     label: 'Product updates',      desc: 'Feature announcements and newsletters'       },
  ]

  return (
    <div className="space-y-6">
      <SectionHead title="Notification Preferences" subtitle="Choose what you want to be notified about." />
      <div className="space-y-3">
        {ITEMS.map(item => (
          <label key={item.key} className="flex items-center justify-between p-4 rounded-xl bg-white/3 border border-white/8 cursor-pointer hover:bg-white/5 transition-colors">
            <div>
              <p className="text-sm font-medium text-white">{item.label}</p>
              <p className="text-xs text-white/40 mt-0.5">{item.desc}</p>
            </div>
            <div onClick={() => setPrefs(p => ({ ...p, [item.key]: !p[item.key] }))}
              className={cn('relative rounded-full transition-colors cursor-pointer shrink-0', prefs[item.key] ? 'bg-vit-600' : 'bg-white/10')}
              style={{ height: '22px', width: '40px' }}>
              <span className={cn('absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform', prefs[item.key] ? 'translate-x-[18px]' : 'translate-x-0')} />
            </div>
          </label>
        ))}
      </div>
      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 transition-colors">
        <Save className="w-4 h-4" />
        {mutation.isPending ? 'Saving…' : 'Save Preferences'}
      </button>
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
        <Spinner className="w-8 h-8" />
      </div>
    )
  }

  return (
    <div className="pt-20 pb-20 min-h-screen relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      <div className="relative max-w-3xl mx-auto px-4 sm:px-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-2xl font-bold text-white">Account Settings</h1>
          <p className="text-white/45 text-sm mt-1">Manage your profile, security and preferences.</p>
        </motion.div>

        <div className="flex flex-col sm:flex-row gap-6">
          {/* Sidebar tabs */}
          <motion.nav initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.05 }} className="sm:w-48 shrink-0">
            <ul className="space-y-0.5">
              {TABS.map(t => (
                <li key={t.key}>
                  <button
                    onClick={() => setTab(t.key)}
                    className={cn(
                      'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left',
                      tab === t.key ? 'bg-vit-500/15 text-vit-400' : 'text-white/50 hover:text-white hover:bg-white/5',
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
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="flex-1 bg-surface-800/60 border border-white/8 rounded-2xl p-6"
            >
              {tab === 'profile'       && <ProfileTab profile={profile} />}
              {tab === 'security'      && <SecurityTab profile={profile} />}
              {tab === 'sessions'      && <SessionsTab />}
              {tab === 'devices'       && <DevicesTab />}
              {tab === 'history'       && <HistoryTab />}
              {tab === 'permissions'   && <PermissionsTab />}
              {tab === 'notifications' && <NotificationsTab />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
