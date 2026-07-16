import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { Mail, Lock, User, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { setAuthToken, storeUser } from '@/hooks/useAuth'

export default function Login() {
  const [tab, setTab]         = useState<'login' | 'register'>('login')
  const [email, setEmail]     = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]   = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const navigate               = useNavigate()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const path = tab === 'login'
        ? '/api/auth/auth/login'
        : '/api/auth/auth/register'
      const body = tab === 'login'
        ? { email, password }
        : { email, username, password }

      const res = await fetch(`${ENDPOINTS.gateway}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          data?.detail ||
          data?.error?.message ||
          data?.message ||
          `Request failed (${res.status})`
        )
      }
      setAuthToken(data.access_token)
      storeUser({ id: data.user_id, username: data.username, role: data.role })
      navigate('/dashboard')
    } catch (e: any) {
      setError(e.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pt-16 min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="absolute inset-0 section-grid opacity-40" />
      <div className="absolute inset-0 bg-radial-vit" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative w-full max-w-md mx-4"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex flex-col items-center gap-3">
            <img
              src="/logo.png"
              alt="VIT Network"
              className="w-12 h-12 rounded-xl object-cover shadow-lg shadow-vit-500/30"
            />
            <div>
              <h1 className="text-2xl font-bold text-white">VIT Network</h1>
              <p className="text-white/40 text-sm mt-0.5">The AI-powered decentralised gateway</p>
            </div>
          </Link>
        </div>

        {/* Card */}
        <div className="bg-surface-800/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl shadow-black/40">
          {/* Tabs */}
          <div className="flex rounded-lg bg-surface-900/60 p-1 mb-7">
            {(['login', 'register'] as const).map(t => (
              <button
                key={t}
                onClick={() => { setTab(t); setError(null) }}
                className={cn(
                  'flex-1 py-2 text-sm font-medium rounded-md transition-all duration-200',
                  tab === t
                    ? 'bg-vit-600 text-white shadow-sm'
                    : 'text-white/50 hover:text-white',
                )}
              >
                {t === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-white/60 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full pl-9 pr-4 py-2.5 bg-surface-900/60 border border-white/10 rounded-lg text-white placeholder-white/25 text-sm focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-colors"
                />
              </div>
            </div>

            {/* Username — register only */}
            <AnimatePresence>
              {tab === 'register' && (
                <motion.div
                  initial={{ opacity: 0, height: 0, marginTop: 0 }}
                  animate={{ opacity: 1, height: 'auto', marginTop: 16 }}
                  exit={{ opacity: 0, height: 0, marginTop: 0 }}
                  style={{ overflow: 'hidden' }}
                >
                  <label className="block text-sm font-medium text-white/60 mb-1.5">Username</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none" />
                    <input
                      type="text"
                      required={tab === 'register'}
                      value={username}
                      onChange={e => setUsername(e.target.value)}
                      placeholder="your_username"
                      className="w-full pl-9 pr-4 py-2.5 bg-surface-900/60 border border-white/10 rounded-lg text-white placeholder-white/25 text-sm focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-colors"
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-white/60 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none" />
                <input
                  type={showPw ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  minLength={tab === 'register' ? 8 : undefined}
                  className="w-full pl-9 pr-10 py-2.5 bg-surface-900/60 border border-white/10 rounded-lg text-white placeholder-white/25 text-sm focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {tab === 'register' && (
                <p className="text-white/30 text-xs mt-1">Minimum 8 characters</p>
              )}
            </div>

            {/* Error message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
                >
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-vit-600 hover:bg-vit-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors shadow-lg shadow-vit-600/25 mt-2"
            >
              {loading
                ? 'Please wait…'
                : tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-white/35 text-xs mt-5">
            {tab === 'login' ? (
              <>Don't have an account?{' '}
                <button onClick={() => setTab('register')} className="text-vit-400 hover:text-vit-300 transition-colors">
                  Create one
                </button>
              </>
            ) : (
              <>Already have an account?{' '}
                <button onClick={() => setTab('login')} className="text-vit-400 hover:text-vit-300 transition-colors">
                  Sign in
                </button>
              </>
            )}
          </p>
        </div>

        <p className="text-center text-white/25 text-xs mt-5">
          <Link to="/" className="hover:text-white/50 transition-colors">← Back to VIT Network</Link>
        </p>
      </motion.div>
    </div>
  )
}
