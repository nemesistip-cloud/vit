import { useState, type ReactNode, type MouseEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Vote, Plus, CheckCircle2, XCircle, Clock, ChevronRight,
  Users, BarChart3, Shield, AlertCircle, X, FileText,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Proposal {
  id: number
  title: string
  description: string
  category: string
  status: 'draft' | 'active' | 'passed' | 'rejected' | 'cancelled' | 'executed'
  votes_for: number
  votes_against: number
  votes_abstain: number
  total_votes: number
  approval_pct: number
  quorum_required: number
  voting_starts_at: string | null
  voting_ends_at: string | null
  created_at: string
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useProposals(status?: string) {
  return useQuery({
    queryKey: ['governance-proposals', status],
    queryFn: async ({ signal }) => {
      const url = `${ENDPOINTS.gateway}/api/governance/proposals${status ? `?status=${status}` : ''}`
      const r = await fetch(url, { signal, headers: authHeaders() })
      if (!r.ok) return { items: [], total: 0 }
      const d = await r.json()
      return d
    },
    retry: false,
    staleTime: 30_000,
  })
}

function useConfig() {
  return useQuery({
    queryKey: ['governance-config'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/governance/config`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : {}
    },
    retry: false,
    staleTime: 60_000,
  })
}

// ── Status styles ──────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, { pill: string; label: string }> = {
  draft:     { pill: 'bg-white/10 text-white/40 border border-white/10',                  label: 'Draft'    },
  active:    { pill: 'bg-vit-500/15 text-vit-400 border border-vit-500/30',               label: 'Active'   },
  passed:    { pill: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',   label: 'Passed'   },
  rejected:  { pill: 'bg-red-500/15 text-red-400 border border-red-500/30',               label: 'Rejected' },
  cancelled: { pill: 'bg-white/10 text-white/30 border border-white/10',                  label: 'Cancelled'},
  executed:  { pill: 'bg-sky-500/15 text-sky-400 border border-sky-500/30',               label: 'Executed' },
}

const CATEGORY_COLORS: Record<string, string> = {
  general:           'text-white/50',
  fee_change:        'text-amber-400',
  parameter_update:  'text-sky-400',
  feature_approval:  'text-vit-400',
}

// ── Create Proposal Modal ──────────────────────────────────────────────────────

function CreateProposalModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    title: '',
    description: '',
    category: 'general',
    voting_period_days: 7,
  })

  const mutation = useMutation({
    mutationFn: async (data: typeof form) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/governance/proposals`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Failed to create proposal') }
      return r.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['governance-proposals'] })
      onClose()
    },
  })

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e: MouseEvent) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="w-full max-w-lg bg-surface-900 border border-white/10 rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between p-5 border-b border-white/8">
          <div className="flex items-center gap-2.5">
            <FileText className="w-5 h-5 text-vit-400" />
            <h2 className="font-semibold text-white">New Proposal</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Title</label>
            <input
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="Short, descriptive title (min 5 chars)"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Description</label>
            <textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={4}
              placeholder="Detailed description of the proposed change (min 20 chars)"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50 resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5">Category</label>
              <select
                value={form.category}
                onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-vit-500/50"
              >
                <option value="general">General</option>
                <option value="fee_change">Fee Change</option>
                <option value="parameter_update">Parameter Update</option>
                <option value="feature_approval">Feature Approval</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5">Voting Period (days)</label>
              <input
                type="number" min={1} max={30}
                value={form.voting_period_days}
                onChange={e => setForm(f => ({ ...f, voting_period_days: parseInt(e.target.value) || 7 }))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-vit-500/50"
              />
            </div>
          </div>

          {mutation.isError && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {(mutation.error as Error).message}
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <button onClick={onClose} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white/60 border border-white/10 hover:bg-white/5 transition-colors">
              Cancel
            </button>
            <button
              onClick={() => mutation.mutate(form)}
              disabled={mutation.isPending || form.title.length < 5 || form.description.length < 20}
              className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-vit-500 hover:bg-vit-400 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {mutation.isPending ? <Spinner className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
              Submit Proposal
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Vote Modal ─────────────────────────────────────────────────────────────────

function VoteModal({ proposal, onClose }: { proposal: Proposal; onClose: () => void }) {
  const qc = useQueryClient()
  const [choice, setChoice] = useState<'for' | 'against' | 'abstain'>('for')
  const [reason, setReason] = useState('')

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/governance/proposals/${proposal.id}/vote`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ choice, reason: reason || undefined }),
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Vote failed') }
      return r.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['governance-proposals'] })
      onClose()
    },
  })

  const choices: Array<{ value: typeof choice; label: string; icon: ReactNode; color: string }> = [
    { value: 'for', label: 'Vote For',     icon: <CheckCircle2 className="w-4 h-4" />, color: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400' },
    { value: 'against', label: 'Vote Against', icon: <XCircle className="w-4 h-4" />,     color: 'border-red-500/40 bg-red-500/10 text-red-400' },
    { value: 'abstain', label: 'Abstain',       icon: <Clock className="w-4 h-4" />,       color: 'border-white/20 bg-white/5 text-white/40' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e: MouseEvent) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="w-full max-w-md bg-surface-900 border border-white/10 rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between p-5 border-b border-white/8">
          <div className="flex items-center gap-2.5">
            <Vote className="w-5 h-5 text-vit-400" />
            <h2 className="font-semibold text-white">Cast Vote</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-sm text-white/60 line-clamp-2">{proposal.title}</p>

          <div className="grid grid-cols-3 gap-2">
            {choices.map(c => (
              <button
                key={c.value}
                onClick={() => setChoice(c.value)}
                className={cn(
                  'flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all',
                  choice === c.value ? c.color : 'border-white/10 text-white/30 hover:border-white/20 hover:text-white/50',
                )}
              >
                {c.icon}
                {c.label}
              </button>
            ))}
          </div>

          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Reason (optional)</label>
            <textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              rows={2}
              maxLength={1000}
              placeholder="Brief explanation for your vote..."
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50 resize-none"
            />
          </div>

          {mutation.isError && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {(mutation.error as Error).message}
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <button onClick={onClose} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white/60 border border-white/10 hover:bg-white/5 transition-colors">
              Cancel
            </button>
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-vit-500 hover:bg-vit-400 text-white transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
            >
              {mutation.isPending ? <Spinner className="w-4 h-4" /> : <Vote className="w-4 h-4" />}
              Submit Vote
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Proposal Card ──────────────────────────────────────────────────────────────

function ProposalCard({ proposal, onVote }: { proposal: Proposal; onVote: () => void }) {
  const style = STATUS_STYLES[proposal.status] ?? STATUS_STYLES.draft
  const total = proposal.total_votes || 1
  const forPct = Math.round((proposal.votes_for / total) * 100)
  const againstPct = Math.round((proposal.votes_against / total) * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      className="bg-white/3 border border-white/8 rounded-xl p-5 hover:border-white/15 transition-colors"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', CATEGORY_COLORS[proposal.category] || 'text-white/40')}>
              {proposal.category.replace('_', ' ')}
            </span>
            <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full border', style.pill)}>
              {style.label}
            </span>
          </div>
          <h3 className="font-medium text-white text-sm leading-tight">{proposal.title}</h3>
          <p className="text-xs text-white/40 mt-1 line-clamp-2">{proposal.description}</p>
        </div>
        {proposal.status === 'active' && (
          <button
            onClick={onVote}
            className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-vit-500/15 border border-vit-500/30 text-vit-400 hover:bg-vit-500/25 transition-colors"
          >
            <Vote className="w-3.5 h-3.5" /> Vote
          </button>
        )}
      </div>

      {/* Vote bars */}
      <div className="space-y-1.5 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-emerald-400 w-12">For</span>
          <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${forPct}%` }} />
          </div>
          <span className="text-xs text-white/40 w-10 text-right">{forPct}%</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-red-400 w-12">Against</span>
          <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div className="h-full bg-red-500 rounded-full transition-all" style={{ width: `${againstPct}%` }} />
          </div>
          <span className="text-xs text-white/40 w-10 text-right">{againstPct}%</span>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-white/30">
        <div className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          {proposal.total_votes.toLocaleString()} votes · {proposal.approval_pct}% approval
        </div>
        {proposal.voting_ends_at && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            ends {new Date(proposal.voting_ends_at).toLocaleDateString()}
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function Governance() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [showCreate, setShowCreate] = useState(false)
  const [votingProposal, setVotingProposal] = useState<Proposal | null>(null)

  const isLoggedIn = !!getAuthToken()
  useEffect(() => { if (!isLoggedIn) navigate('/login') }, [isLoggedIn, navigate])

  const { data, isLoading } = useProposals(statusFilter || undefined)
  const { data: config } = useConfig()

  const proposals: Proposal[] = data?.items ?? []
  const total = data?.total ?? 0

  const activeCount = proposals.filter(p => p.status === 'active').length
  const passedCount = proposals.filter(p => p.status === 'passed' || p.status === 'executed').length

  const STATUS_FILTERS = ['', 'active', 'passed', 'rejected', 'executed']

  return (
    <div className="pt-16 min-h-screen">
      <AnimatePresence>
        {showCreate && <CreateProposalModal onClose={() => setShowCreate(false)} />}
        {votingProposal && <VoteModal proposal={votingProposal} onClose={() => setVotingProposal(null)} />}
      </AnimatePresence>

      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
                <Shield className="w-5 h-5 text-vit-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Governance DAO</h1>
                <p className="text-white/50 text-sm">Participate in on-chain protocol governance</p>
              </div>
            </div>
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium bg-vit-500 hover:bg-vit-400 text-white transition-colors shadow-lg shadow-vit-500/20"
            >
              <Plus className="w-4 h-4" /> New Proposal
            </button>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Total Proposals', value: total, icon: FileText, color: 'text-white' },
              { label: 'Active Votes',    value: activeCount,  icon: Vote, color: 'text-vit-400' },
              { label: 'Passed',          value: passedCount,  icon: CheckCircle2, color: 'text-emerald-400' },
              { label: 'Quorum Required', value: config?.quorum_required ?? '1,000', icon: Users, color: 'text-sky-400' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="bg-white/5 border border-white/8 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Icon className={cn('w-4 h-4', color)} />
                  <span className="text-xs text-white/40">{label}</span>
                </div>
                <p className={cn('text-2xl font-bold', color)}>{typeof value === 'number' ? value.toLocaleString() : value}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {/* Filters */}
        <div className="flex items-center gap-2 mb-6 flex-wrap">
          {STATUS_FILTERS.map(s => (
            <button
              key={s || 'all'}
              onClick={() => setStatusFilter(s)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize',
                statusFilter === s
                  ? 'bg-vit-500/20 text-vit-400 border border-vit-500/30'
                  : 'text-white/40 border border-white/10 hover:border-white/20 hover:text-white/60',
              )}
            >
              {s || 'All'}
            </button>
          ))}
          <span className="ml-auto text-xs text-white/30">{total} proposal{total !== 1 ? 's' : ''}</span>
        </div>

        {/* Proposal list */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spinner className="w-8 h-8" />
          </div>
        ) : proposals.length === 0 ? (
          <div className="text-center py-20">
            <Vote className="w-10 h-10 text-white/20 mx-auto mb-3" />
            <p className="text-white/40 text-sm">No proposals found</p>
            <button onClick={() => setShowCreate(true)} className="mt-4 text-vit-400 text-sm hover:text-vit-300 flex items-center gap-1.5 mx-auto">
              <Plus className="w-3.5 h-3.5" /> Create the first proposal
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {proposals.map(p => (
              <ProposalCard
                key={p.id}
                proposal={p}
                onVote={() => setVotingProposal(p)}
              />
            ))}
          </div>
        )}

        {/* Governance info */}
        <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { icon: Vote,   title: 'Voting Power', body: 'Your vote weight is determined by your VIT stake × merit score × trust tier. Stake more VIT to gain governance influence.' },
            { icon: Shield, title: 'Timelock',      body: 'Passed proposals execute after a 24-hour timelock, giving stakeholders time to react before on-chain changes take effect.' },
            { icon: BarChart3, title: 'Quorum',     body: 'Each proposal requires a quorum of voting power to pass. Check the quorum threshold displayed on each active proposal.' },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="bg-white/3 border border-white/8 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4 text-vit-400" />
                <span className="text-sm font-medium text-white">{title}</span>
              </div>
              <p className="text-xs text-white/40 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
