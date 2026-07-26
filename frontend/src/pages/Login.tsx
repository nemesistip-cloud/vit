import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { Mail, Lock, User, Eye, EyeOff, AlertCircle, Layers, Brain, Shield } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { setAuthToken, storeUser } from '@/hooks/useAuth'

const PERKS = [
  { icon: Brain,  label: 'AI Predictions',  desc: '13+ ML models across 50+ leagues' },
  { icon: Layers, label: 'VIT Chain',        desc: 'Chain ID 7764 — proof-of-storage PoS' },
  { icon: Shield, label: 'Non-custodial',    desc: 'Your keys, your wallet, always' },
]

export default function Login() {
  const [tab, setTab]           = useState<'login' | 'register'>('login')
  const [email, setEmail]       = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const navigate                = useNavigate()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      // Fix: /api/auth/login (not /api/auth/auth/login)
      const path = tab === 'login' ? '/api/auth/login' : '/api/auth/register'
      const body = tab === 'login'
        ? { email, password }
        : { email, username, password }

      const res = await fetch(`${ENDPOINTS.gateway}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      let data: any = {}
      try {
        data = await res.clone().json()
      } catch (_) {
        // ignore JSON parse errors; we'll fallback to text below
        data = {}
      }

      if (!res.ok) {
        const serverMsg = data?.detail || data?.error?.message || data?.message
        let fallback = serverMsg
        if (!fallback) {
          try {
            fallback = await res.text()
          } catch (_e) {
            fallback = res.statusText || `Request failed (${res.status})`
          }
        }
        throw new Error(fallback || `Request failed (${res.status})`)
      }
      setAuthToken(data.access_token)
      storeUser({ id: data.user_id, username: data.username, role: data.role })
      navigate('/workspace')
    } catch (e: any) {
      // Surface network errors separately for clarity
      if (e instanceof TypeError) {
        setError(`Network error: ${e.message}`)
      } else {
        setError(e.message || 'Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex relative overflow-hidden bg-surface-900">
      {/* Ambient glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-vit-600/20 blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full bg-vit-800/20 blur-[120px] pointer-events-none" />
      <div className="absolute inset-0 section-grid opacity-30 pointer-events-none" />

      {/* ── Left brand panel (desktop only) ─────────────────────────────────── */}
      <div className="hidden lg:flex flex-col justify-between w-[480px] shrink-0 relative z-10 p-12 border-r border-white/5">
        <Link to="/" className="flex items-center gap-3 group">
          <img src="/logo.png" alt="VIT Network" className="w-9 h-9 rounded-xl object-cover shadow-lg shadow-vit-500/30 group-hover:shadow-vit-500/50 transition-shadow" />
          <div>
            <span className="text-white font-bold text-lg leading-none">VIT Network</span>
            <p className="text-white/30 text-xs mt-0.5">Chain ID 7764</p>
          </div>
        </Link>

        <div className="space-y-10">
          <div>
            <h2 className="text-4xl font-bold text-white leading-tight mb-4">
              Africa's sovereign<br />
              <span className="gradient-text">intelligence layer</span>
            </h2>
            <p className="text-white/50 text-base leading-relaxed">
              AI-powered predictions, decentralized storage, and a native PoS blockchain — unified in one gateway.
            </p>
          </div>

          <div className="space-y-5">
            {PERKS.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-4">
                <div className="w-9 h-9 rounded-lg bg-vit-600/15 border border-vit-500/20 flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-vit-400" />
                </div>
                <div>
                  <p className="text-white font-medium text-sm">{label}</p>
                  <p className="text-white/40 text-xs mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-white/20 text-xs">
          © {new Date().getFullYear()} VIT Network · Built on VIT Chain
        </p>
      </div>

      {/* ── Right form panel ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-6 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm"
        >
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <Link to="/" className="inline-flex flex-col items-center gap-3">
              <img src="/logo.png" alt="VIT Network" className="w-12 h-12 rounded-2xl object-cover shadow-lg shadow-vit-500/30" />
              <div>
                <h1 className="text-xl font-bold text-white">VIT Network</h1>
                <p className="text-white/40 text-xs mt-0.5">The AI-powered decentralised gateway</p>
              </div>
            </Link>
          </div>

          {/* Heading */}
          <div className="mb-7 lg:mt-0 mt-0">
            <h2 className="text-2xl font-bold text-white">
              {tab === 'login' ? 'Welcome back' : 'Create account'}
            </h2>
            <p className="text-white/40 text-sm mt-1">
              {tab === 'login' ? 'Sign in to your VIT Network account' : 'Join the decentralized intelligence network'}
            </p>
          </div>

          {/* Card */}
          <div className="bg-surface-800/60 backdrop-blur-xl border border-white/8 rounded-2xl p-7 shadow-2xl shadow-black/50">
            {/* Tabs */}
            <div className="flex rounded-xl bg-surface-900/80 p-1 mb-6 gap-1">
              {(['login', 'register'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => { setTab(t); setError(null) }}
                  className={cn(
                    'flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200',
                    tab === t
                      ? 'bg-vit-600 text-white shadow-md shadow-vit-600/30'
                      : 'text-white/40 hover:text-white/70',
                  )}
                >
                  {t === 'login' ? 'Sign In' : 'Create Account'}
                </button>
              ))}
            </div>

            <form onSubmit={submit} className="space-y-4">
              {/* Email */}
              <div>
                <label className="block text-xs font-medium text-white/50 mb-1.5 uppercase tracking-wide">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/25" />
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    placeholder="you@example.com"
                    className="w-full bg-surface-900/60 border border-white/8 rounded-xl pl-9 pr-4 py-2.5 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-all"
                  />
                </div>
              </div>

              {/* Username (register only) */}
              <AnimatePresence>
                {tab === 'register' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <label className="block text-xs font-medium text-white/50 mb-1.5 uppercase tracking-wide">Username</label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/25" />
                      <input
                        type="text"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        required={tab === 'register'}
                        placeholder="your_username"
                        className="w-full bg-surface-900/60 border border-white/8 rounded-xl pl-9 pr-4 py-2.5 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-all"
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Password */}
              <div>
                <label className="block text-xs font-medium text-white/50 mb-1.5 uppercase tracking-wide">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/25" />
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    placeholder={tab === 'register' ? 'Min 10 chars, uppercase + lowercase' : '••••••••••'}
                    className="w-full bg-surface-900/60 border border-white/8 rounded-xl pl-9 pr-10 py-2.5 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 transition-colors"
                  >
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {tab === 'login' && (
                  <div className="text-right mt-1.5">
                    <Link to="/forgot-password" className="text-xs text-vit-400/70 hover:text-vit-400 transition-colors">
                      Forgot password?
                    </Link>
                  </div>
                )}
              </div>

              {/* Error */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-start gap-2.5 px-3.5 py-3 rounded-xl bg-red-500/8 border border-red-500/20 text-red-400 text-sm"
                  >
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-vit-600 hover:bg-vit-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all shadow-lg shadow-vit-600/25 hover:shadow-vit-500/35 mt-1 text-sm"
              >
                {loading
                  ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Please wait…</span>
                  : tab === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            </form>

            <p className="text-center text-white/30 text-xs mt-5">
              {tab === 'login' ? (
                <>Don't have an account?{' '}
                  <button onClick={() => { setTab('register'); setError(null) }} className="text-vit-400 hover:text-vit-300 transition-colors font-medium">Create one</button>
                </>
              ) : (
                <>Already have an account?{' '}
                  <button onClick={() => { setTab('login'); setError(null) }} className="text-vit-400 hover:text-vit-300 transition-colors font-medium">Sign in</button>
                </>
              )}
            </p>
          </div>

          <p className="text-center text-white/20 text-xs mt-5">
            <Link to="/" className="hover:text-white/40 transition-colors">← Back to VIT Network</Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
