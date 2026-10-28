import React, { useState, useEffect } from 'react'
import {
  Sparkles,
  Calendar,
  Lightbulb,
  BarChart3,
  Brain,
  Twitter,
  Plus,
  Trash2,
  Send,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sliders,
  FileText,
  UserCheck,
  ChevronRight,
  TrendingUp,
  Layers,
  Zap,
} from 'lucide-react'
import { fetchWithAuth } from '@/hooks/useAuth'

interface Brand {
  id: string
  handle: string
  display_name: string
  niche: string
  bio?: string
  target_audience?: string
  tone_and_voice: string
  writing_style?: string
  preferred_topics: string[]
  topics_to_avoid: string[]
  goals: string[]
  is_active: boolean
}

interface Memory {
  id: string
  category: string
  key: string
  value: string
  weight: number
  source: string
}

interface Idea {
  id: string
  title: string
  angle?: string
  hook_templates: string[]
  suggested_format: string
  pillars: string[]
  status: string
}

interface ContentItem {
  id: string
  content_type: string
  title?: string
  posts: string[]
  content_pillar?: string
  status: string
  scheduled_for?: string
  published_at?: string
  impressions: number
  likes: number
  reposts: number
  replies: number
  clicks: number
  engagement_rate: number
  created_at: string
}

interface Analytics {
  total_posts_published: number
  total_impressions: number
  total_likes: number
  total_reposts: number
  total_replies: number
  avg_engagement_rate: number
  top_pillars: { pillar: string; impressions: number }[]
  performance_growth: { date: string; impressions: number; engagements: number }[]
}

const api = {
  get: async <T,>(url: string): Promise<T | null> => {
    const res = await fetchWithAuth(url)
    if (!res.ok) return null
    return res.json()
  },
  post: async <T,>(url: string, body?: any): Promise<T | null> => {
    const res = await fetchWithAuth(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    })
    if (!res.ok) return null
    return res.json()
  },
  delete: async <T,>(url: string): Promise<T | null> => {
    const res = await fetchWithAuth(url, { method: 'DELETE' })
    if (!res.ok) return null
    return res.json()
  },
}

export default function CreatorStudio() {
  const [activeTab, setActiveTab] = useState<'studio' | 'calendar' | 'ideas' | 'memory' | 'analytics' | 'brand'>('studio')
  const [brands, setBrands] = useState<Brand[]>([])
  const [selectedBrand, setSelectedBrand] = useState<Brand | null>(null)
  const [memories, setMemories] = useState<Memory[]>([])
  const [ideas, setIdeas] = useState<Idea[]>([])
  const [contentPipeline, setContentPipeline] = useState<ContentItem[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [xConnected, setXConnected] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(true)

  // Form states for creation
  const [genTopic, setGenTopic] = useState<string>('')
  const [genFormat, setGenFormat] = useState<string>('SINGLE_POST')
  const [isGenerating, setIsGenerating] = useState<boolean>(false)
  const [newMemoryKey, setNewMemoryKey] = useState<string>('')
  const [newMemoryVal, setNewMemoryVal] = useState<string>('')

  // Brand creation state
  const [showNewBrandModal, setShowNewBrandModal] = useState<boolean>(false)
  const [newHandle, setNewHandle] = useState<string>('')
  const [newDisplayName, setNewDisplayName] = useState<string>('')
  const [newNiche, setNewNiche] = useState<string>('Tech & Web3')
  const [newTone, setNewTone] = useState<string>('Authoritative & Direct')

  useEffect(() => {
    fetchBrands()
  }, [])

  useEffect(() => {
    if (selectedBrand) {
      fetchBrandDetails(selectedBrand.id)
    }
  }, [selectedBrand])

  const fetchBrands = async () => {
    setLoading(true)
    try {
      const res = await api.get<Brand[]>('/api/creator/brands')
      if (res && res.length > 0) {
        setBrands(res)
        setSelectedBrand(res[0])
      } else {
        // Create default initial brand persona for demo / fallback
        const initRes = await api.post<Brand>('/api/creator/brands', {
          handle: 'anselemcrizyx',
          display_name: 'Anselem Crizyx',
          niche: 'Web3 & AI Agents',
          bio: 'Building autonomous AI systems & prediction infrastructure.',
          target_audience: 'Developers, Web3 builders, AI researchers',
          tone_and_voice: 'Direct, Analytical, Visionary',
          preferred_topics: ['AI Infrastructure', 'VIT Chain', 'DeFi'],
          topics_to_avoid: ['Unverified hype', 'Spam'],
          goals: ['Grow brand reach', 'Establish AI authority'],
        })
        if (initRes) {
          setBrands([initRes])
          setSelectedBrand(initRes)
        }
      }
    } catch (e) {
      console.error('Failed to fetch brands', e)
    } finally {
      setLoading(false)
    }
  }

  const fetchBrandDetails = async (brandId: string) => {
    try {
      const [mRes, iRes, cRes, aRes] = await Promise.all([
        api.get<Memory[]>(`/api/creator/brands/${brandId}/memory`),
        api.get<Idea[]>(`/api/creator/brands/${brandId}/ideas`),
        api.get<ContentItem[]>(`/api/creator/brands/${brandId}/content`),
        api.get<Analytics>(`/api/creator/brands/${brandId}/analytics`),
      ])
      setMemories(mRes || [])
      setIdeas(iRes || [])
      setContentPipeline(cRes || [])
      setAnalytics(aRes || null)
    } catch (e) {
      console.error('Failed to fetch brand details', e)
    }
  }

  const handleCreateBrand = async () => {
    if (!newHandle || !newDisplayName) return
    try {
      const created = await api.post<Brand>('/api/creator/brands', {
        handle: newHandle,
        display_name: newDisplayName,
        niche: newNiche,
        tone_and_voice: newTone,
        preferred_topics: [newNiche],
        goals: ['Grow engagement'],
      })
      if (created) {
        setBrands([...brands, created])
        setSelectedBrand(created)
        setShowNewBrandModal(false)
        setNewHandle('')
        setNewDisplayName('')
      }
    } catch (e) {
      console.error('Failed to create brand', e)
    }
  }

  const handleGenerateIdeas = async () => {
    if (!selectedBrand) return
    setIsGenerating(true)
    try {
      const res = await api.post<Idea[]>('/api/creator/ideas/generate', {
        brand_id: selectedBrand.id,
        topic: genTopic || selectedBrand.niche,
        count: 5,
      })
      if (res) {
        setIdeas([...res, ...ideas])
      }
    } catch (e) {
      console.error('Failed to generate ideas', e)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateContent = async (ideaId?: string) => {
    if (!selectedBrand) return
    setIsGenerating(true)
    try {
      const res = await api.post<ContentItem>('/api/creator/content/generate', {
        brand_id: selectedBrand.id,
        idea_id: ideaId,
        topic: genTopic || selectedBrand.niche,
        content_type: genFormat,
      })
      if (res) {
        setContentPipeline([res, ...contentPipeline])
        setActiveTab('studio')
      }
    } catch (e) {
      console.error('Failed to generate content', e)
    } finally {
      setIsGenerating(false)
    }
  }

  const handlePublishNow = async (itemId: string) => {
    if (!selectedBrand) return
    try {
      const res = await api.post<ContentItem>(`/api/creator/brands/${selectedBrand.id}/content/${itemId}/publish`)
      if (res) {
        setContentPipeline(contentPipeline.map((item) => (item.id === itemId ? res : item)))
        fetchBrandDetails(selectedBrand.id)
      }
    } catch (e) {
      console.error('Failed to publish content', e)
    }
  }

  const handleAddMemory = async () => {
    if (!selectedBrand || !newMemoryKey || !newMemoryVal) return
    try {
      const res = await api.post<Memory>(`/api/creator/brands/${selectedBrand.id}/memory`, {
        category: 'THEME',
        key: newMemoryKey,
        value: newMemoryVal,
        weight: 1.0,
      })
      if (res) {
        setMemories([...memories, res])
        setNewMemoryKey('')
        setNewMemoryVal('')
      }
    } catch (e) {
      console.error('Failed to add memory', e)
    }
  }

  const handleDeleteMemory = async (memId: string) => {
    if (!selectedBrand) return
    try {
      await api.delete(`/api/creator/brands/${selectedBrand.id}/memory/${memId}`)
      setMemories(memories.filter((m) => m.id !== memId))
    } catch (e) {
      console.error('Failed to delete memory', e)
    }
  }

  const handleConnectX = async () => {
    if (!selectedBrand) return
    try {
      await api.post(`/api/creator/brands/${selectedBrand.id}/x-account`, {
        x_user_id: `x_usr_${Math.floor(Math.random() * 100000)}`,
        x_handle: selectedBrand.handle,
        access_token: 'mock_oauth_access_token_v2',
      })
      setXConnected(true)
    } catch (e) {
      console.error('Failed to connect X account', e)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      {/* Header & Brand Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/20">
              <Twitter className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                VIT Creator Studio
              </h1>
              <p className="text-sm text-slate-400">Autonomous X Content Strategy & Publishing Engine</p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="relative">
            <select
              value={selectedBrand?.id || ''}
              onChange={(e) => {
                const b = brands.find((x) => x.id === e.target.value)
                if (b) setSelectedBrand(b)
              }}
              className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg focus:ring-cyan-500 focus:border-cyan-500 px-3.5 py-2 pr-8 appearance-none"
            >
              {brands.map((b) => (
                <option key={b.id} value={b.id}>
                  @{b.handle} ({b.display_name})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setShowNewBrandModal(true)}
            className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded-lg text-slate-200 transition"
          >
            <Plus className="w-4 h-4" />
            <span>New Brand</span>
          </button>

          <button
            onClick={handleConnectX}
            className={`flex items-center space-x-2 px-4 py-2 text-xs font-semibold rounded-lg transition shadow-md ${
              xConnected
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950'
            }`}
          >
            <Twitter className="w-4 h-4" />
            <span>{xConnected ? 'X Connected' : 'Connect X Account'}</span>
          </button>
        </div>
      </div>

      {/* Main Workspace Navigation */}
      <div className="flex space-x-1 border-b border-slate-800 mb-8 overflow-x-auto pb-1">
        {[
          { id: 'studio', label: 'AI Studio', icon: Sparkles },
          { id: 'ideas', label: 'Ideas Engine', icon: Lightbulb },
          { id: 'calendar', label: 'Publishing Calendar', icon: Calendar },
          { id: 'memory', label: 'Brand Memory', icon: Brain },
          { id: 'analytics', label: 'Growth Intelligence', icon: BarChart3 },
          { id: 'brand', label: 'Brand Persona', icon: Sliders },
        ].map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition border-b-2 ${
                isActive
                  ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Tab Contents */}
      {selectedBrand && (
        <div className="space-y-6">
          {/* TAB 1: AI STUDIO */}
          {activeTab === 'studio' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Controls & Generation Panel */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <h2 className="text-lg font-semibold text-slate-200 flex items-center space-x-2">
                  <Sparkles className="w-5 h-5 text-cyan-400" />
                  <span>Generate Content</span>
                </h2>

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Topic or Keyword</label>
                    <input
                      type="text"
                      placeholder={`e.g. ${selectedBrand.niche}`}
                      value={genTopic}
                      onChange={(e) => setGenTopic(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Format</label>
                    <select
                      value={genFormat}
                      onChange={(e) => setGenFormat(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      <option value="SINGLE_POST">Single Post (280 chars)</option>
                      <option value="THREAD">X Thread (5 Posts)</option>
                      <option value="HOT_TAKE">Hot Take / Contrarian</option>
                      <option value="STORY">Storytelling Narrative</option>
                      <option value="LONG_FORM">Long-form Post</option>
                    </select>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-lg text-xs space-y-1.5 text-slate-400">
                    <div className="font-semibold text-slate-300">Active Brand Persona</div>
                    <div>Tone: <span className="text-cyan-400">{selectedBrand.tone_and_voice}</span></div>
                    <div>Target: <span className="text-slate-300">{selectedBrand.target_audience || 'General'}</span></div>
                  </div>

                  <button
                    onClick={() => handleGenerateContent()}
                    disabled={isGenerating}
                    className="w-full flex items-center justify-center space-x-2 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-semibold rounded-lg transition shadow-md disabled:opacity-50"
                  >
                    {isGenerating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                    <span>{isGenerating ? 'Generating...' : 'Generate Post Draft'}</span>
                  </button>
                </div>
              </div>

              {/* Content Pipeline / Drafts View */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-200">Content Pipeline & Drafts</h2>
                  <span className="text-xs text-slate-400">{contentPipeline.length} Total Drafts</span>
                </div>

                {contentPipeline.length === 0 ? (
                  <div className="bg-slate-900/50 border border-dashed border-slate-800 rounded-xl p-8 text-center space-y-2">
                    <FileText className="w-8 h-8 text-slate-600 mx-auto" />
                    <p className="text-sm text-slate-400">No content items generated yet.</p>
                    <p className="text-xs text-slate-500">Use the generator on the left or select an idea from the Ideas Engine.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {contentPipeline.map((item) => (
                      <div key={item.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 bg-cyan-950 text-cyan-400 border border-cyan-800/50 rounded font-medium">
                              {item.content_type}
                            </span>
                            <span className="text-slate-500">{new Date(item.created_at).toLocaleDateString()}</span>
                          </div>

                          <span
                            className={`px-2 py-0.5 rounded font-medium ${
                              item.status === 'PUBLISHED'
                                ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                                : 'bg-amber-950 text-amber-400 border border-amber-800/50'
                            }`}
                          >
                            {item.status}
                          </span>
                        </div>

                        <div className="space-y-2">
                          {item.posts.map((p, idx) => (
                            <div key={idx} className="p-3 bg-slate-950 border border-slate-800/80 rounded-lg text-sm text-slate-200 whitespace-pre-wrap">
                              {p}
                            </div>
                          ))}
                        </div>

                        <div className="flex items-center justify-between pt-2 border-t border-slate-800/60">
                          {item.status === 'PUBLISHED' ? (
                            <div className="flex items-center space-x-4 text-xs text-slate-400">
                              <span>👁️ {item.impressions}</span>
                              <span>❤️ {item.likes}</span>
                              <span>🔄 {item.reposts}</span>
                              <span className="text-cyan-400 font-medium">ER: {item.engagement_rate}%</span>
                            </div>
                          ) : (
                            <div className="text-xs text-slate-500">Ready for review & publishing</div>
                          )}

                          {item.status !== 'PUBLISHED' && (
                            <button
                              onClick={() => handlePublishNow(item.id)}
                              className="flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold rounded-lg transition"
                            >
                              <Send className="w-3.5 h-3.5" />
                              <span>Publish to X</span>
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: IDEAS ENGINE */}
          {activeTab === 'ideas' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-200">Personalized Ideas Bank</h2>
                  <p className="text-xs text-slate-400">AI-suggested hooks and post angles generated from brand memory.</p>
                </div>

                <button
                  onClick={handleGenerateIdeas}
                  disabled={isGenerating}
                  className="flex items-center space-x-2 px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold rounded-lg transition disabled:opacity-50"
                >
                  <Lightbulb className="w-4 h-4" />
                  <span>Generate New Ideas</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {ideas.map((idea) => (
                  <div key={idea.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 bg-blue-950 text-blue-400 border border-blue-800/50 rounded text-xs font-medium">
                          {idea.suggested_format}
                        </span>
                        <span className="text-xs text-slate-500">{idea.status}</span>
                      </div>

                      <h3 className="font-semibold text-slate-200 text-sm leading-snug">{idea.title}</h3>
                      <p className="text-xs text-slate-400">{idea.angle}</p>

                      {idea.hook_templates && idea.hook_templates.length > 0 && (
                        <div className="p-2.5 bg-slate-950 rounded-lg text-xs text-slate-300 space-y-1">
                          <span className="text-slate-500 font-medium block">Suggested Hook:</span>
                          <p className="italic">"{idea.hook_templates[0]}"</p>
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => handleGenerateContent(idea.id)}
                      className="w-full flex items-center justify-center space-x-1.5 py-2 bg-slate-800 hover:bg-slate-700 text-xs text-cyan-400 font-medium rounded-lg transition"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Turn into Content</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: PUBLISHING CALENDAR */}
          {activeTab === 'calendar' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-200 flex items-center space-x-2">
                  <Calendar className="w-5 h-5 text-cyan-400" />
                  <span>Weekly Content Pipeline</span>
                </h2>
                <div className="text-xs text-slate-400">Timezone: UTC</div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, idx) => (
                  <div key={day} className="bg-slate-950 border border-slate-800/80 rounded-lg p-3 space-y-3 min-h-[160px]">
                    <div className="font-semibold text-xs text-slate-400 border-b border-slate-800 pb-1.5 flex justify-between">
                      <span>{day}</span>
                      <span className="text-slate-600">Day {idx + 1}</span>
                    </div>

                    <div className="space-y-2">
                      {contentPipeline.slice(idx * 1, idx * 1 + 1).map((item) => (
                        <div key={item.id} className="p-2 bg-slate-900 border border-slate-800 rounded text-xs space-y-1">
                          <div className="font-medium text-slate-200 line-clamp-1">{item.title || item.posts[0]}</div>
                          <div className="text-[10px] text-cyan-400 font-medium">{item.status}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: BRAND MEMORY */}
          {activeTab === 'memory' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <h2 className="text-lg font-semibold text-slate-200 flex items-center space-x-2">
                  <Brain className="w-5 h-5 text-cyan-400" />
                  <span>Add Brand Memory</span>
                </h2>

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Key / Core Principle</label>
                    <input
                      type="text"
                      placeholder="e.g. Core Belief on AI"
                      value={newMemoryKey}
                      onChange={(e) => setNewMemoryKey(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Details / Context</label>
                    <textarea
                      placeholder="e.g. Autonomous AI agents will replace centralized software orchestration within 3 years."
                      value={newMemoryVal}
                      onChange={(e) => setNewMemoryVal(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 h-24"
                    />
                  </div>

                  <button
                    onClick={handleAddMemory}
                    className="w-full py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs rounded-lg transition"
                  >
                    Save Memory
                  </button>
                </div>
              </div>

              <div className="lg:col-span-2 space-y-4">
                <h2 className="text-lg font-semibold text-slate-200">Stored Brand Knowledge & Tone Memory</h2>

                <div className="space-y-3">
                  {memories.map((m) => (
                    <div key={m.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-slate-200 text-sm">{m.key}</span>
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded text-[10px]">{m.category}</span>
                        </div>
                        <p className="text-xs text-slate-300">{m.value}</p>
                      </div>

                      <button onClick={() => handleDeleteMemory(m.id)} className="text-slate-500 hover:text-rose-400 p-1">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: GROWTH INTELLIGENCE */}
          {activeTab === 'analytics' && analytics && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-1">
                  <span className="text-xs text-slate-400 font-medium">Published Posts</span>
                  <div className="text-2xl font-bold text-white">{analytics.total_posts_published}</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-1">
                  <span className="text-xs text-slate-400 font-medium">Total Impressions</span>
                  <div className="text-2xl font-bold text-cyan-400">{analytics.total_impressions.toLocaleString()}</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-1">
                  <span className="text-xs text-slate-400 font-medium">Avg Engagement Rate</span>
                  <div className="text-2xl font-bold text-emerald-400">{analytics.avg_engagement_rate}%</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-1">
                  <span className="text-xs text-slate-400 font-medium">Total Likes & Reposts</span>
                  <div className="text-2xl font-bold text-blue-400">{analytics.total_likes + analytics.total_reposts}</div>
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
                <h3 className="font-semibold text-slate-200 text-sm">Top Content Pillars</h3>
                <div className="space-y-3">
                  {analytics.top_pillars.map((p) => (
                    <div key={p.pillar} className="space-y-1">
                      <div className="flex justify-between text-xs text-slate-300">
                        <span>{p.pillar}</span>
                        <span>{p.impressions.toLocaleString()} impressions</span>
                      </div>
                      <div className="w-full bg-slate-950 rounded-full h-2">
                        <div
                          className="bg-cyan-500 h-2 rounded-full"
                          style={{
                            width: `${Math.min(100, (p.impressions / Math.max(1, analytics.total_impressions)) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: BRAND PERSONA */}
          {activeTab === 'brand' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 max-w-2xl">
              <h2 className="text-lg font-semibold text-slate-200">Brand Persona Configuration</h2>

              <div className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Handle</label>
                  <input
                    type="text"
                    value={selectedBrand.handle}
                    disabled
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-300"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Display Name</label>
                  <input
                    type="text"
                    value={selectedBrand.display_name}
                    disabled
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-300"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Tone and Voice</label>
                  <input
                    type="text"
                    value={selectedBrand.tone_and_voice}
                    disabled
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-300"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Bio / Overview</label>
                  <textarea
                    value={selectedBrand.bio || ''}
                    disabled
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-300 h-20"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal: New Brand */}
      {showNewBrandModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 w-full max-w-md">
            <h3 className="text-lg font-semibold text-slate-200">Create New Brand Persona</h3>

            <div className="space-y-3">
              <input
                type="text"
                placeholder="X Handle (e.g. anselemcrizyx)"
                value={newHandle}
                onChange={(e) => setNewHandle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200"
              />

              <input
                type="text"
                placeholder="Display Name"
                value={newDisplayName}
                onChange={(e) => setNewDisplayName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200"
              />

              <input
                type="text"
                placeholder="Niche (e.g. Web3 & AI)"
                value={newNiche}
                onChange={(e) => setNewNiche(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200"
              />
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowNewBrandModal(false)}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateBrand}
                className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs rounded-lg"
              >
                Create Brand
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
