import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'

type State = 'verifying' | 'success' | 'error'

export default function VerifyEmail() {
  const [params]       = useSearchParams()
  const token          = params.get('token') ?? ''
  const [state, setState]   = useState<State>('verifying')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) { setState('error'); setMessage('No verification token found. Check your email link.'); return }

    const ctrl = new AbortController()
    fetch(`${ENDPOINTS.gateway}/api/auth/verify-email?token=${encodeURIComponent(token)}`, {
      signal: ctrl.signal,
    })
      .then(async r => {
        const d = await r.json().catch(() => ({}))
        if (r.ok) {
          setState('success')
          setMessage(d.message || 'Your email address has been verified.')
        } else {
          setState('error')
          setMessage(d.detail || d.message || 'Verification failed. The link may have expired.')
        }
      })
      .catch(e => {
        if (e.name !== 'AbortError') {
          setState('error')
          setMessage('Could not reach the server. Please try again.')
        }
      })

    return () => ctrl.abort()
  }, [token])

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

        <div className="bg-surface-800/80 backdrop-blur-xl border border-white/10 rounded-2xl p-10 shadow-2xl shadow-black/40 text-center space-y-5">
          {state === 'verifying' && (
            <>
              <Loader2 className="w-12 h-12 text-vit-400 mx-auto animate-spin" />
              <h2 className="text-xl font-bold text-white">Verifying your email…</h2>
              <p className="text-white/45 text-sm">This will only take a moment.</p>
            </>
          )}

          {state === 'success' && (
            <>
              <div className="inline-flex w-14 h-14 rounded-full bg-emerald-500/15 items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7 text-emerald-400" />
              </div>
              <h2 className="text-xl font-bold text-white">Email verified!</h2>
              <p className="text-white/50 text-sm">{message}</p>
              <Link
                to="/login"
                className="inline-block px-6 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 transition-colors"
              >
                Sign In
              </Link>
            </>
          )}

          {state === 'error' && (
            <>
              <div className="inline-flex w-14 h-14 rounded-full bg-red-500/15 items-center justify-center mx-auto">
                <XCircle className="w-7 h-7 text-red-400" />
              </div>
              <h2 className="text-xl font-bold text-white">Verification failed</h2>
              <p className="text-white/50 text-sm">{message}</p>
              <div className="flex flex-col gap-3 items-center">
                <Link
                  to="/login"
                  className="inline-block px-6 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 transition-colors"
                >
                  Back to Sign In
                </Link>
                <p className="text-white/30 text-xs">
                  Need a new link?{' '}
                  <Link to="/forgot-password" className="text-vit-400 hover:text-vit-300 transition-colors">
                    Reset your password
                  </Link>
                </p>
              </div>
            </>
          )}
        </div>
      </motion.div>
    </div>
  )
}
