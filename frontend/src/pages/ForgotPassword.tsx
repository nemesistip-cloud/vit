import { useState } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Mail, ArrowLeft, CheckCircle2, AlertCircle } from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'

export default function ForgotPassword() {
  const [email, setEmail]     = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent]       = useState(false)
  const [error, setError]     = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${ENDPOINTS.gateway}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || data?.message || `Error ${res.status}`)
      setSent(true)
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
            <img src="/logo.png" alt="VIT Network" className="w-12 h-12 rounded-xl object-cover shadow-lg shadow-vit-500/30" />
            <h1 className="text-2xl font-bold text-white">VIT Network</h1>
          </Link>
        </div>

        <div className="bg-surface-800/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl shadow-black/40">
          {sent ? (
            <div className="text-center space-y-4">
              <div className="inline-flex w-14 h-14 rounded-full bg-emerald-500/15 items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7 text-emerald-400" />
              </div>
              <h2 className="text-xl font-bold text-white">Check your inbox</h2>
              <p className="text-white/50 text-sm">
                If an account exists for <strong className="text-white/70">{email}</strong>, you'll receive a password reset link within a few minutes.
              </p>
              <p className="text-white/30 text-xs">Didn't receive it? Check your spam folder or try again.</p>
              <div className="flex flex-col gap-3 pt-2">
                <button
                  onClick={() => { setSent(false); setEmail('') }}
                  className="w-full py-2.5 rounded-lg bg-white/5 text-white/70 text-sm hover:bg-white/10 transition-colors"
                >
                  Try a different email
                </button>
                <Link to="/login" className="block text-center text-sm text-vit-400 hover:text-vit-300 transition-colors">
                  Back to Sign In
                </Link>
              </div>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h2 className="text-xl font-bold text-white mb-1">Reset your password</h2>
                <p className="text-white/45 text-sm">Enter your email and we'll send you a reset link.</p>
              </div>

              {error && (
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/20 mb-4">
                  <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                  <p className="text-red-400 text-sm">{error}</p>
                </div>
              )}

              <form onSubmit={submit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-white/60 mb-1.5">Email address</label>
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

                <button
                  type="submit"
                  disabled={loading || !email}
                  className="w-full py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Sending…' : 'Send Reset Link'}
                </button>
              </form>

              <Link
                to="/login"
                className="flex items-center justify-center gap-1.5 mt-5 text-sm text-white/40 hover:text-white/70 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Sign In
              </Link>
            </>
          )}
        </div>
      </motion.div>
    </div>
  )
}
