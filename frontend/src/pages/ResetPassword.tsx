import { useState } from 'react'
import { motion } from 'framer-motion'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { Lock, Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'

export default function ResetPassword() {
  const [params]              = useSearchParams()
  const navigate              = useNavigate()
  const token                 = params.get('token') ?? ''

  const [password, setPassword]   = useState('')
  const [confirm, setConfirm]     = useState('')
  const [showPw, setShowPw]       = useState(false)
  const [loading, setLoading]     = useState(false)
  const [done, setDone]           = useState(false)
  const [error, setError]         = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match.'); return }
    if (password.length < 8)  { setError('Password must be at least 8 characters.'); return }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${ENDPOINTS.gateway}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || data?.message || `Error ${res.status}`)
      setDone(true)
      setTimeout(() => navigate('/login'), 3000)
    } catch (e: any) {
      setError(e.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="pt-24 min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Invalid reset link</h2>
          <p className="text-white/50 text-sm">This link is missing a token. Request a new one.</p>
          <Link to="/forgot-password" className="inline-block px-6 py-2.5 rounded-lg bg-vit-600 text-white text-sm hover:bg-vit-500 transition-colors">
            Request reset link
          </Link>
        </div>
      </div>
    )
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
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex flex-col items-center gap-3">
            <img src="/logo.png" alt="VIT Network" className="w-12 h-12 rounded-xl object-cover shadow-lg shadow-vit-500/30" />
            <h1 className="text-2xl font-bold text-white">VIT Network</h1>
          </Link>
        </div>

        <div className="bg-surface-800/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl shadow-black/40">
          {done ? (
            <div className="text-center space-y-4">
              <div className="inline-flex w-14 h-14 rounded-full bg-emerald-500/15 items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7 text-emerald-400" />
              </div>
              <h2 className="text-xl font-bold text-white">Password updated</h2>
              <p className="text-white/50 text-sm">Your password has been reset. Redirecting you to Sign In…</p>
              <Link to="/login" className="block text-sm text-vit-400 hover:text-vit-300 transition-colors">
                Go to Sign In now
              </Link>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h2 className="text-xl font-bold text-white mb-1">Set new password</h2>
                <p className="text-white/45 text-sm">Choose a strong password for your account.</p>
              </div>

              {error && (
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/20 mb-4">
                  <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                  <p className="text-red-400 text-sm">{error}</p>
                </div>
              )}

              <form onSubmit={submit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-white/60 mb-1.5">New password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none" />
                    <input
                      type={showPw ? 'text' : 'password'}
                      required
                      minLength={8}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="Min. 8 characters"
                      className="w-full pl-9 pr-10 py-2.5 bg-surface-900/60 border border-white/10 rounded-lg text-white placeholder-white/25 text-sm focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
                    >
                      {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-white/60 mb-1.5">Confirm password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none" />
                    <input
                      type={showPw ? 'text' : 'password'}
                      required
                      value={confirm}
                      onChange={e => setConfirm(e.target.value)}
                      placeholder="Re-enter password"
                      className="w-full pl-9 pr-4 py-2.5 bg-surface-900/60 border border-white/10 rounded-lg text-white placeholder-white/25 text-sm focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-colors"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading || !password || !confirm}
                  className="w-full py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Saving…' : 'Set New Password'}
                </button>
              </form>
            </>
          )}
        </div>
      </motion.div>
    </div>
  )
}
