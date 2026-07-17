import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { Trophy, Medal, TrendingUp, Users, Star, ChevronRight, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { authHeaders } from '@/hooks/useAuth'

type Tab = 'predictors' | 'validators'
type Period = 'weekly' | 'monthly' | 'all-time'

function useLeaderboard(tab: Tab, period: Period) {
  return useQuery({
    queryKey: ['leaderboard', tab, period],
    queryFn: async ({ signal }) => {
      const endpoint = tab === 'validators'
        ? `${ENDPOINTS.gateway}/api/analytics/leaderboard/validators`
        : `${ENDPOINTS.gateway}/api/analytics/leaderboard/users`
      const r = await fetch(`${endpoint}?period=${period}`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.leaderboard ?? d.items ?? d.data ?? []
    },
    staleTime: 120_000,
  })
}

const RANK_COLORS = ['text-amber-400', 'text-white/70', 'text-amber-700/80']
const RANK_BG    = ['bg-amber-400/10', 'bg-white/5', 'bg-amber-700/10']
const RANK_ICONS = [Trophy, Medal, Star]

export default function Leaderboard() {
  const [tab, setTab]       = useState<Tab>('predictors')
  const [period, setPeriod] = useState<Period>('weekly')
  const { data, isLoading, refetch } = useLeaderboard(tab, period)

  return (
    <div className="pt-16 min-h-screen">
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <Trophy className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Leaderboard</h1>
              <p className="text-white/50 text-sm">Top predictors and validators on VIT Network</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Controls */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <div className="flex gap-1 bg-white/5 border border-white/10 rounded-xl p-1">
            {(['predictors', 'validators'] as Tab[]).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={cn('px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all',
                  tab === t ? 'bg-vit-500 text-white' : 'text-white/50 hover:text-white hover:bg-white/5')}>
                {t}
              </button>
            ))}
          </div>
          <div className="flex gap-1 bg-white/5 border border-white/10 rounded-xl p-1">
            {([['weekly', 'This Week'], ['monthly', 'Month'], ['all-time', 'All Time']] as [Period, string][]).map(([p, label]) => (
              <button key={p} onClick={() => setPeriod(p)}
                className={cn('px-4 py-2 rounded-lg text-sm font-medium transition-all',
                  period === p ? 'bg-white/15 text-white' : 'text-white/50 hover:text-white hover:bg-white/5')}>
                {label}
              </button>
            ))}
          </div>
          <button onClick={() => refetch()} className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-white/50 hover:text-white transition-colors">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {/* Podium for top 3 */}
        {!isLoading && data && data.length >= 3 && (
          <div className="flex items-end justify-center gap-4 mb-8">
            {[data[1], data[0], data[2]].map((u: any, podiumIdx: number) => {
              const rank = podiumIdx === 0 ? 2 : podiumIdx === 1 ? 1 : 3
              const heights = ['h-24', 'h-32', 'h-20']
              const RankIcon = RANK_ICONS[rank - 1]
              return (
                <motion.div key={rank} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: podiumIdx * 0.1 }}
                  className="flex flex-col items-center gap-2">
                  <div className="w-12 h-12 rounded-full bg-vit-500/20 flex items-center justify-center text-lg font-bold text-vit-400 border-2 border-vit-500/30">
                    {(u?.username || u?.email || 'U')[0].toUpperCase()}
                  </div>
                  <p className="text-sm font-medium text-white text-center max-w-[80px] truncate">{u?.username || u?.email || 'Unknown'}</p>
                  <div className={cn('w-20 rounded-t-lg flex flex-col items-center justify-start pt-3', heights[podiumIdx], RANK_BG[rank - 1])}>
                    <RankIcon className={`w-5 h-5 ${RANK_COLORS[rank - 1]}`} />
                    <span className={`text-lg font-bold ${RANK_COLORS[rank - 1]}`}>#{rank}</span>
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}

        {/* Full table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-24"><Spinner className="w-8 h-8 text-vit-400" /></div>
        ) : !data || data.length === 0 ? (
          <div className="text-center py-24">
            <Users className="w-14 h-14 text-white/10 mx-auto mb-4" />
            <p className="text-white/50">No rankings available yet</p>
            <p className="text-white/30 text-sm mt-1">Rankings populate as predictions are made and validated.</p>
          </div>
        ) : (
          <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/8">
                  <th className="text-left text-xs text-white/40 font-medium px-6 py-4 uppercase tracking-wide">Rank</th>
                  <th className="text-left text-xs text-white/40 font-medium px-6 py-4 uppercase tracking-wide">User</th>
                  <th className="text-right text-xs text-white/40 font-medium px-6 py-4 uppercase tracking-wide">Win Rate</th>
                  <th className="text-right text-xs text-white/40 font-medium px-6 py-4 uppercase tracking-wide hidden sm:table-cell">Predictions</th>
                  <th className="text-right text-xs text-white/40 font-medium px-6 py-4 uppercase tracking-wide hidden md:table-cell">Score</th>
                </tr>
              </thead>
              <tbody>
                {data.map((u: any, i: number) => {
                  const RankIcon = i < 3 ? RANK_ICONS[i] : null
                  return (
                    <motion.tr key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                      className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                      <td className="px-6 py-4">
                        <span className={cn('text-sm font-bold', i < 3 ? RANK_COLORS[i] : 'text-white/30')}>
                          {RankIcon ? <RankIcon className="w-4 h-4 inline mr-1" /> : null}#{i + 1}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-vit-500/20 flex items-center justify-center text-xs font-bold text-vit-400">
                            {(u.username || u.email || 'U')[0].toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{u.username || u.email || 'Unknown'}</p>
                            {u.clv_tier && <p className="text-xs text-white/30">{u.clv_tier}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-bold text-emerald-400">
                          {u.win_rate ? `${(u.win_rate * 100).toFixed(1)}%` : '—'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right hidden sm:table-cell">
                        <span className="text-sm text-white/50">{u.prediction_count ?? u.total_predictions ?? '—'}</span>
                      </td>
                      <td className="px-6 py-4 text-right hidden md:table-cell">
                        <span className="text-sm text-vit-400 font-medium">{u.score ?? u.reputation_score ?? '—'}</span>
                      </td>
                    </motion.tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
