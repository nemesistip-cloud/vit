import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users, Heart, Flame, HelpCircle, Rocket, MessageCircle,
  Plus, X, Send, TrendingUp, Globe, UserPlus, Trash2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Post {
  id: string
  author_id: number
  author_email: string
  content: string
  prediction_id?: number
  match_id?: number
  tags: string[]
  created_at: number
  reaction_counts: Record<string, number>
  total_reactions: number
  my_reaction?: string | null
  comment_count: number
}

interface Comment {
  id: string
  post_id: string
  author_id: number
  author_email: string
  content: string
  created_at: number
}

interface SocialStats {
  total_posts: number
  total_reactions: number
  total_comments: number
  total_follows: number
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

const BASE = () => `${ENDPOINTS.gateway}/api/social`

function useFeed(filter: string) {
  return useQuery({
    queryKey: ['social-feed', filter],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/feed?filter=${filter}&limit=30`, { signal, headers: authHeaders() })
      if (!r.ok) return { items: [] as Post[], total: 0 }
      return r.json()
    },
    refetchInterval: 20_000,
    retry: false,
  })
}

function useSocialStats() {
  return useQuery({
    queryKey: ['social-stats'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/stats`, { signal })
      return r.ok ? (r.json() as Promise<SocialStats>) : null
    },
    staleTime: 30_000,
    retry: false,
  })
}

function useComments(postId: string | null) {
  return useQuery({
    queryKey: ['social-comments', postId],
    queryFn: async ({ signal }) => {
      if (!postId) return { comments: [] as Comment[] }
      const r = await fetch(`${BASE()}/posts/${postId}/comments`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : { comments: [] }
    },
    enabled: !!postId,
    refetchInterval: 10_000,
  })
}

// ── Reaction bar ──────────────────────────────────────────────────────────────

const REACTIONS = [
  { id: 'like',   icon: Heart,       label: 'Like',   color: 'text-rose-400'   },
  { id: 'fire',   icon: Flame,       label: 'Fire',   color: 'text-amber-400'  },
  { id: 'doubt',  icon: HelpCircle,  label: 'Doubt',  color: 'text-sky-400'    },
  { id: 'rocket', icon: Rocket,      label: 'Rocket', color: 'text-vit-400'    },
]

function ReactionBar({ post }: { post: Post }) {
  const qc = useQueryClient()
  const react = useMutation({
    mutationFn: async (reaction: string) => {
      const r = await fetch(`${BASE()}/react`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_id: post.id, reaction }),
      })
      if (!r.ok) throw new Error('Failed to react')
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['social-feed'] }),
  })

  return (
    <div className="flex items-center gap-1">
      {REACTIONS.map(rx => {
        const Icon   = rx.icon
        const count  = post.reaction_counts?.[rx.id] ?? 0
        const active = post.my_reaction === rx.id
        return (
          <button
            key={rx.id}
            onClick={() => react.mutate(rx.id)}
            disabled={react.isPending}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-all',
              active
                ? `bg-white/10 ${rx.color}`
                : 'text-white/40 hover:text-white/70 hover:bg-white/5',
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            {count > 0 && <span>{count}</span>}
          </button>
        )
      })}
    </div>
  )
}

// ── Comment thread ────────────────────────────────────────────────────────────

function CommentThread({ post, onClose }: { post: Post; onClose: () => void }) {
  const qc = useQueryClient()
  const { data, isLoading } = useComments(post.id)
  const [text, setText] = useState('')

  const addComment = useMutation({
    mutationFn: async (content: string) => {
      const r = await fetch(`${BASE()}/posts/${post.id}/comments`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_id: post.id, content }),
      })
      if (!r.ok) throw new Error('Failed to comment')
      return r.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['social-comments', post.id] })
      qc.invalidateQueries({ queryKey: ['social-feed'] })
      setText('')
    },
  })

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="w-full max-w-lg bg-surface-900 border border-white/10 rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between p-4 border-b border-white/8">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-4 h-4 text-vit-400" />
            <span className="font-semibold text-sm text-white">Comments ({data?.comments?.length ?? 0})</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 max-h-80 overflow-y-auto space-y-3">
          {isLoading && <Spinner className="w-5 h-5 mx-auto" />}
          {!isLoading && (!data?.comments?.length) && (
            <p className="text-center text-white/30 text-sm py-4">No comments yet. Be first!</p>
          )}
          {data?.comments?.map((c: Comment) => (
            <div key={c.id} className="flex gap-2.5">
              <div className="w-7 h-7 rounded-full bg-vit-500/20 border border-vit-500/30 flex items-center justify-center shrink-0">
                <span className="text-xs font-bold text-vit-400">{c.author_email?.[0]?.toUpperCase()}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-0.5">
                  <span className="text-xs font-medium text-white/70">{c.author_email?.split('@')[0]}</span>
                  <span className="text-xs text-white/30">{new Date(c.created_at * 1000).toLocaleTimeString()}</span>
                </div>
                <p className="text-sm text-white/80">{c.content}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-white/8 flex gap-2">
          <input
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && text.trim() && addComment.mutate(text.trim())}
            placeholder="Add a comment…"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50"
          />
          <button
            onClick={() => text.trim() && addComment.mutate(text.trim())}
            disabled={!text.trim() || addComment.isPending}
            className="px-3 py-2 bg-vit-500 hover:bg-vit-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Post card ─────────────────────────────────────────────────────────────────

function PostCard({ post }: { post: Post }) {
  const qc = useQueryClient()
  const [showComments, setShowComments] = useState(false)

  const deletePost = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${BASE()}/posts/${post.id}`, { method: 'DELETE', headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to delete')
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['social-feed'] }),
  })

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-3 hover:border-white/15 transition-colors"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-vit-500/20 border border-vit-500/30 flex items-center justify-center shrink-0">
            <span className="text-xs font-bold text-vit-400">{post.author_email?.[0]?.toUpperCase()}</span>
          </div>
          <div>
            <p className="text-sm font-medium text-white">{post.author_email?.split('@')[0]}</p>
            <p className="text-xs text-white/30">{new Date(post.created_at * 1000).toLocaleString()}</p>
          </div>
        </div>
        <button
          onClick={() => deletePost.mutate()}
          className="p-1.5 text-white/20 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
          title="Delete post"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Content */}
      <p className="text-sm text-white/85 leading-relaxed">{post.content}</p>

      {/* Tags */}
      {post.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {post.tags.map(tag => (
            <span key={tag} className="px-2 py-0.5 bg-vit-500/10 text-vit-400 border border-vit-500/20 rounded text-xs">
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-center justify-between pt-1 border-t border-white/5">
        <ReactionBar post={post} />
        <button
          onClick={() => setShowComments(true)}
          className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors px-2 py-1 rounded-lg hover:bg-white/5"
        >
          <MessageCircle className="w-3.5 h-3.5" />
          {post.comment_count > 0 ? post.comment_count : 'Comment'}
        </button>
      </div>

      <AnimatePresence>
        {showComments && <CommentThread post={post} onClose={() => setShowComments(false)} />}
      </AnimatePresence>
    </motion.div>
  )
}

// ── Create post modal ─────────────────────────────────────────────────────────

function CreatePostModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [content, setContent] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [tags, setTags] = useState<string[]>([])

  const createPost = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${BASE()}/posts`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, tags }),
      })
      if (!r.ok) throw new Error('Failed to create post')
      return r.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['social-feed'] })
      onClose()
    },
  })

  function addTag() {
    const t = tagInput.trim().toLowerCase().replace(/\s+/g, '-')
    if (t && !tags.includes(t) && tags.length < 5) {
      setTags(prev => [...prev, t])
      setTagInput('')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="w-full max-w-lg bg-surface-900 border border-white/10 rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between p-5 border-b border-white/8">
          <div className="flex items-center gap-2">
            <Plus className="w-4 h-4 text-vit-400" />
            <span className="font-semibold text-white">New Post</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            rows={5}
            placeholder="Share your prediction insight, analysis, or tip…"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50 resize-none"
          />

          <div>
            <label className="block text-xs font-medium text-white/50 mb-2">Tags (max 5)</label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {tags.map(t => (
                <span key={t} className="flex items-center gap-1 px-2 py-0.5 bg-vit-500/10 text-vit-400 border border-vit-500/20 rounded text-xs">
                  #{t}
                  <button onClick={() => setTags(prev => prev.filter(x => x !== t))}>
                    <X className="w-2.5 h-2.5" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addTag()}
                placeholder="e.g. premier-league"
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50"
              />
              <button onClick={addTag} className="px-3 py-2 bg-white/5 hover:bg-white/10 text-white/60 rounded-lg text-sm transition-colors">
                Add
              </button>
            </div>
          </div>

          <button
            onClick={() => createPost.mutate()}
            disabled={!content.trim() || createPost.isPending}
            className="w-full py-2.5 bg-vit-500 hover:bg-vit-600 text-white rounded-xl font-medium text-sm transition-colors disabled:opacity-40"
          >
            {createPost.isPending ? <Spinner className="w-4 h-4 mx-auto" /> : 'Post to Feed'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Social() {
  const navigate  = useNavigate()
  const [filter, setFilter]     = useState<'all' | 'following' | 'trending'>('all')
  const [showCreate, setShowCreate] = useState(false)

  useEffect(() => {
    if (!getAuthToken()) navigate('/login')
  }, [navigate])

  const { data: feedData, isLoading } = useFeed(filter)
  const { data: stats }               = useSocialStats()

  const posts: Post[] = feedData?.items ?? []

  const FILTERS: { id: 'all' | 'following' | 'trending'; label: string; icon: typeof Globe }[] = [
    { id: 'all',       label: 'All',       icon: Globe      },
    { id: 'following', label: 'Following', icon: Users      },
    { id: 'trending',  label: 'Trending',  icon: TrendingUp },
  ]

  return (
    <div className="min-h-screen bg-surface-950 pt-24 pb-16">
      <div className="max-w-2xl mx-auto px-4">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-vit-500/15 border border-vit-500/25 rounded-xl">
                <Users className="w-5 h-5 text-vit-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Social Feed</h1>
                <p className="text-white/50 text-sm">Predictions, analysis & community insights</p>
              </div>
            </div>
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 px-4 py-2 bg-vit-500 hover:bg-vit-600 text-white rounded-xl text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" /> Post
            </button>
          </div>

          {/* Stats */}
          {stats && (
            <div className="grid grid-cols-4 gap-2 mt-4">
              {[
                { label: 'Posts',     value: stats.total_posts },
                { label: 'Reactions', value: stats.total_reactions },
                { label: 'Comments',  value: stats.total_comments },
                { label: 'Follows',   value: stats.total_follows },
              ].map(s => (
                <div key={s.label} className="bg-white/3 border border-white/8 rounded-xl p-3 text-center">
                  <p className="text-lg font-bold text-white">{s.value.toLocaleString()}</p>
                  <p className="text-xs text-white/40">{s.label}</p>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Filter tabs */}
        <div className="flex gap-1 mb-6 bg-white/3 border border-white/8 rounded-xl p-1">
          {FILTERS.map(f => {
            const Icon = f.icon
            return (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={cn(
                  'flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all',
                  filter === f.id
                    ? 'bg-vit-500/20 text-vit-300 border border-vit-500/30'
                    : 'text-white/50 hover:text-white/80',
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {f.label}
              </button>
            )
          })}
        </div>

        {/* Feed */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <Spinner className="w-6 h-6 text-vit-400" />
          </div>
        )}

        {!isLoading && posts.length === 0 && (
          <div className="text-center py-16">
            <Users className="w-10 h-10 text-white/20 mx-auto mb-3" />
            <p className="text-white/40 text-sm">No posts yet. Be the first to share a prediction!</p>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-4 px-4 py-2 bg-vit-500/20 text-vit-400 border border-vit-500/30 rounded-xl text-sm hover:bg-vit-500/30 transition-colors"
            >
              Create first post
            </button>
          </div>
        )}

        <div className="space-y-4">
          <AnimatePresence mode="popLayout">
            {posts.map(post => <PostCard key={post.id} post={post} />)}
          </AnimatePresence>
        </div>
      </div>

      <AnimatePresence>
        {showCreate && <CreatePostModal onClose={() => setShowCreate(false)} />}
      </AnimatePresence>
    </div>
  )
}
