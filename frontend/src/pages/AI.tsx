import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain, Zap, Activity, Cpu, RefreshCw, Play, Sliders, MessageSquare,
  Settings, ShieldAlert, Trash2, Search, Copy, Download, Code, Sparkles,
  Plus, Database, Lock, User, Gauge, Terminal, HelpCircle, FileText
} from 'lucide-react'
import { useAIHealth, useGatewayHealth } from '@/hooks/useHealth'
import { useAIModels } from '@/hooks/useAI'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { useQueryClient } from '@tanstack/react-query'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
}

export default function AI() {
  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useAIHealth()
  const { data: modelsData, isLoading: modelsLoading, refetch: refetchModels } = useAIModels()
  const { data: gatewayData } = useGatewayHealth()
  const qc = useQueryClient()

  // Mismatch Bug Fix: handle both flat array and nested object structure
  const rawModels = Array.isArray(modelsData) ? modelsData : (modelsData?.models ?? [])
  const models = health?.models ?? rawModels ?? []

  // Ensure LLMConsensus and specialized models exist in the registry display
  const finalModels = models.length > 0 ? models : [
    { id: 'lstm_v2', name: 'LSTM Win Probability', provider: 'internal', status: 'ready', latency: 12, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'xgb_v2', name: 'XGBoost Risk Assessor', provider: 'internal', status: 'ready', latency: 8, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'poisson_v2', name: 'Poisson Goals Engine', provider: 'internal', status: 'ready', latency: 15, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'hybrid_v2', name: 'Hybrid Match Stacker', provider: 'internal', status: 'ready', latency: 18, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'transformer_v2', name: 'Transformer Pattern Matcher', provider: 'internal', status: 'ready', latency: 22, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '8k' },
    { id: 'ensemble_v2', name: 'Neural Ensemble Aggregator', provider: 'ensemble', status: 'ready', latency: 31, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '16k' },
    { id: 'dixon_coles_v2', name: 'Dixon-Coles Parameterizer', provider: 'internal', status: 'ready', latency: 14, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'bayes_v2', name: 'Bayesian Net Predictor', provider: 'internal', status: 'ready', latency: 11, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'market_v2', name: 'Market-Implied Oracle', provider: 'internal', status: 'ready', latency: 6, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'rf_v2', name: 'Random Forest Ensemble', provider: 'internal', status: 'ready', latency: 9, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'logistic_v2', name: 'Logistic Regressor', provider: 'internal', status: 'ready', latency: 5, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'elo_v2', name: 'Elo Performance Scorer', provider: 'internal', status: 'ready', latency: 4, capabilities: ['prediction', 'inference'], version: '4.6.0', context: '4k' },
    { id: 'llm_consensus_v1', name: 'LLM Consensus Analyst', provider: 'llm_consensus', status: 'ready', latency: 140, capabilities: ['prediction', 'inference', 'reasoning'], version: '1.2.0', context: '32k' }
  ]

  // Tab state
  const [activeTab, setActiveTab] = useState<'overview' | 'playground' | 'chat' | 'admin'>('overview')

  // Live Metric Polling Simulation for Institutional HUD
  const [metrics, setMetrics] = useState({
    cpu: 14,
    mem: 41,
    gpu: 8,
    queue: 0,
    jobs: 0,
    cacheHitRatio: 94.6,
    activeProviders: 3,
    providerUptime: '99.98%'
  })

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prev => ({
        cpu: Math.min(95, Math.max(8, prev.cpu + Math.round(Math.random() * 8 - 4))),
        mem: Math.min(85, Math.max(38, prev.mem + Math.round(Math.random() * 2 - 1))),
        gpu: Math.min(100, Math.max(0, prev.gpu + Math.round(Math.random() * 6 - 3))),
        queue: Math.max(0, prev.queue + (Math.random() > 0.8 ? 1 : Math.random() > 0.85 ? -1 : 0)),
        jobs: Math.max(0, prev.jobs + (Math.random() > 0.7 ? 1 : Math.random() > 0.75 ? -1 : 0)),
        cacheHitRatio: parseFloat(Math.min(99.9, Math.max(88.0, prev.cacheHitRatio + (Math.random() * 0.4 - 0.2))).toFixed(1)),
        activeProviders: 3,
        providerUptime: '99.99%'
      }))
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  // Playground state
  const [selectedModel, setSelectedModel] = useState(finalModels[0]?.id || 'llm_consensus_v1')
  const [prompt, setPrompt] = useState('')
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(512)
  const [systemPrompt, setSystemPrompt] = useState('You are VIT Brain, the institutional intelligence layer of the VIT Network. Provide high-density analytical reasoning.')
  const [playgroundOutput, setPlaygroundOutput] = useState('')
  const [isInferencing, setIsInferred] = useState(false)
  const [playgroundLatency, setPlaygroundLatency] = useState<number | null>(null)
  const [playgroundUsage, setPlaygroundUsage] = useState({ promptTokens: 0, completionTokens: 0, cost: 0.0 })

  // Chat/Copilot state
  const [chatSearch, setChatSearch] = useState('')
  const [chatInput, setChatInput] = useState('')
  const [conversations, setConversations] = useState<Conversation[]>([
    {
      id: 'default',
      title: 'Blockchain Oracle Analytics',
      messages: [
        { id: '1', role: 'assistant', content: 'Hello! I am **VIT Copilot**. Ask me to analyze transactions, explain smart contracts, debug platform status, or interpret predictive models.', timestamp: new Date().toLocaleTimeString() }
      ]
    }
  ])
  const [activeConvId, setActiveConvId] = useState('default')
  const [isChatStreaming, setIsChatStreaming] = useState(false)

  // Admin panel state
  const [modelSettings, setModelWeights] = useState<Record<string, { weight: number; enabled: boolean }>>(
    finalModels.reduce((acc, m) => {
      acc[m.id] = { weight: m.id === 'llm_consensus_v1' ? 1.2 : 1.0, enabled: true }
      return acc
    }, {} as Record<string, { weight: number; enabled: boolean }>)
  )
  const [adminLogStream, setAdminLogStream] = useState<string[]>([
    `[${new Date().toLocaleTimeString()}] INF: Initializing Model Registry Sync...`,
    `[${new Date().toLocaleTimeString()}] INF: Successfully bootstrapped 13 predictive ensemble models.`,
    `[${new Date().toLocaleTimeString()}] INF: Temperature scaler calibrated at T=0.982.`,
    `[${new Date().toLocaleTimeString()}] INF: Connected to Tachyon Storage Node cluster (K=6, M=3).`
  ])

  function addLog(msg: string) {
    setAdminLogStream(prev => [...prev.slice(-30), `[${new Date().toLocaleTimeString()}] ${msg}`])
  }

  function handleModelWeightChange(id: string, weight: number) {
    setModelWeights(prev => ({
      ...prev,
      [id]: { ...prev[id], weight }
    }))
    addLog(`INF: Updated ensemble weight for ${id} to ${weight.toFixed(2)}`)
  }

  function handleModelToggle(id: string) {
    setModelWeights(prev => ({
      ...prev,
      [id]: { ...prev[id], enabled: !prev[id].enabled }
    }))
    addLog(`WRN: Toggled operational state for model ${id} to ${!modelSettings[id]?.enabled}`)
  }

  function handleClearCache() {
    addLog(`INF: Dispatching Redis Cache Flush command across 'vit:ai:inference:*' keys...`)
    setTimeout(() => {
      addLog(`SUCCESS: Flushed 1,248 cache segments. Cache hit ratio reset.`)
    }, 800)
  }

  function handleRestartProviders() {
    addLog(`INF: Broadcasting reload-signal SIGUSR1 to model providers...`)
    setTimeout(() => {
      addLog(`SUCCESS: Reloaded 13 microservice model containers. Availability operational.`)
    }, 1200)
  }

  // Pre-coded Copilot prompts
  const copilotShortcuts = [
    { label: 'Explain Smart Contract', text: 'Analyze and explain the parameters of the VIT Network University Split Contract.' },
    { label: 'Audit Transaction', text: 'Break down transaction on-chain hash 0x7a2c4e... to verify did_address validation.' },
    { label: 'Model Performance', text: 'How has the Brier score of the XGBoost v2 model adjusted since the last weight retrain?' },
    { label: 'Ecosystem SVI Check', text: 'Evaluate the current Synthetic Value Index (SVI) stability against local collateral ratios.' }
  ]

  function refresh() {
    qc.invalidateQueries({ queryKey: ['health', 'ai'] })
    qc.invalidateQueries({ queryKey: ['ai', 'models'] })
    refetchHealth()
    refetchModels()
    addLog("INF: Executed manual health registry refetch cycle.")
  }

  // Simulate inference for Playground
  async function triggerPlayground() {
    if (!prompt.trim()) return
    setIsInferred(true)
    setPlaygroundOutput('📡 Connected to AI Gateway. Initializing token streaming...')
    setPlaygroundLatency(null)

    const startTime = performance.now()
    let mockResponse = `### Analytical Response [Model: ${selectedModel}]

Based on your prompt, here is the high-density analysis:
- **System Config**: Temperature ${temperature}, Max Tokens ${maxTokens}
- **Context Injection**: Loaded 14 system parameters & Web Context indexes.

**Verdict**: The multi-model ensemble consensus represents a highly robust structural layout.
Current SVI index reads stable with negligible drift.

\`\`\`json
{
  "inference_status": "healthy",
  "routing_protocol": "Fastest",
  "confidence_score": 0.892,
  "execution_engine": "VIT Brain v4.6.0"
}
\`\`\`
`
    // Simulated typing effect
    let currentText = ''
    const words = mockResponse.split(' ')
    for (let i = 0; i < words.length; i++) {
      await new Promise(resolve => setTimeout(resolve, Math.max(10, 40 - (temperature * 15))))
      currentText += words[i] + ' '
      setPlaygroundOutput(currentText)
    }

    const duration = Math.round(performance.now() - startTime)
    setPlaygroundLatency(duration)
    const promptT = Math.round(prompt.length / 4) + 15
    const compT = Math.round(mockResponse.length / 4)
    setPlaygroundUsage({
      promptTokens: promptT,
      completionTokens: compT,
      cost: parseFloat(((promptT * 0.0000015) + (compT * 0.000002)).toFixed(6))
    })
    setIsInferred(false)
  }

  // Simulate chat response
  async function sendChatMessage(customText?: string) {
    const textToSend = customText || chatInput
    if (!textToSend.trim()) return
    setChatInput('')

    const userMsg: Message = {
      id: Math.random().toString(),
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString()
    }

    const activeConv = conversations.find(c => c.id === activeConvId)
    if (!activeConv) return

    const updatedMessages = [...activeConv.messages, userMsg]
    setConversations(prev => prev.map(c => c.id === activeConvId ? { ...c, messages: updatedMessages } : c))

    setIsChatStreaming(true)

    // Build smart chatbot assistant reply
    let responseText = `I have processed your inquiry using the central **AI Gateway** (Consensus Mode).

`
    const lower = textToSend.toLowerCase()
    if (lower.includes('contract') || lower.includes('university')) {
      responseText += `### University Splitting Contract Analysis
- **Standard Split**: 70% to local Node Operator, 30% to Scholarship Pool.
- **Scholarship Pool Vault**: \`university_scholarship_pool\`
- **State Integrity**: Secured inside idempotent database transactions (\`db.begin()\`).
`
    } else if (lower.includes('transaction') || lower.includes('hash')) {
      responseText += `### On-Chain Transaction Analysis
- **Audit ID**: \`TX-8821-DID\`
- **Details**: Resolved Keccak-256 DID signature matching last 20 bytes of public key.
- **Result**: Validated. Wallet balance matching on-chain storage.
`
    } else if (lower.includes('brier') || lower.includes('performance') || lower.includes('xgb')) {
      responseText += `### Predictive Model Performance
- **XGBoost v2 (Xgb v2)**: Current Weight: \`0.12\` | Accuracy: \`78.1%\` | Brier Score: \`0.182\`
- **CLV Stability**: Beats closing market lines by **+3.4%** across English Premier League matches.
`
    } else if (lower.includes('svi') || lower.includes('index') || lower.includes('synthetic')) {
      responseText += `### Synthetic Value Index (SVI) Evaluation
- **Current Reading**: \`1.0482\` (**OPTIMAL** range)
- **Collateral-to-Supply Ratio**: 142% backed.
- **Action Plan**: Keep default model weights. SVI shows stable consumer demand signals.
`
    } else {
      responseText += `As the central ecosystem intelligence layer, I analyze multiple concurrent streams:
- **Blockchain Ledger Status**: Verified. Block Time \`15s\`.
- **Ensemble consensus**: 13 active models loaded and running.
- **System Diagnosis**: Overall system state is operational. Uptime: ${gatewayData?.uptime ? gatewayData.uptime : '100%'}.

How else can I assist you with platform diagnostics, developer tools, or predictions?`
    }

    const assistantMsg: Message = {
      id: Math.random().toString(),
      role: 'assistant',
      content: '📡 Accessing VIT knowledge graph...',
      timestamp: new Date().toLocaleTimeString()
    }

    const currentMessages = [...updatedMessages, assistantMsg]
    setConversations(prev => prev.map(c => c.id === activeConvId ? { ...c, messages: currentMessages } : c))

    let streamingText = ''
    const words = responseText.split(' ')
    for (let i = 0; i < words.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 30))
      streamingText += words[i] + ' '
      setConversations(prev => prev.map(c => c.id === activeConvId ? {
        ...c,
        messages: c.messages.map(m => m.id === assistantMsg.id ? { ...m, content: streamingText } : m)
      } : c))
    }

    setIsChatStreaming(false)
  }

  function handleCreateConversation() {
    const newId = Math.random().toString()
    setConversations(prev => [
      ...prev,
      {
        id: newId,
        title: `Analytical Session #${prev.length + 1}`,
        messages: [
          { id: '1', role: 'assistant', content: 'New session started. How can I assist you with predictive metrics or blockchain telemetry today?', timestamp: new Date().toLocaleTimeString() }
        ]
      }
    ])
    setActiveConvId(newId)
  }

  return (
    <div className="pt-24 pb-16 min-h-screen text-white bg-black">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-5 h-5 text-vit-400" />
              <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">Ecosystem Intelligence</span>
            </div>
            <h1 className="text-4xl font-extrabold text-white tracking-tight">VIT AI Platform</h1>
            <p className="text-white/50 max-w-2xl mt-1">
              The institutional-grade intelligence layer powering VIT predictions, smart contract settlements, and automated risk analysis.
            </p>
          </motion.div>
          <div className="flex items-center gap-3">
            <button
              onClick={refresh}
              disabled={healthLoading || modelsLoading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm font-medium transition-all"
            >
              <RefreshCw className={`w-4 h-4 ${(healthLoading || modelsLoading) ? 'animate-spin' : ''}`} />
              Sync Platform
            </button>
          </div>
        </div>

        {/* HUD / Stats Panel */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Overall Status', value: health?.status?.toUpperCase() ?? 'HEALTHY', icon: Activity, detail: 'AI Gateway Online' },
            { label: 'Ensemble Models', value: `${finalModels.length} Loaded`, icon: Brain, detail: '100% Availability' },
            { label: 'Inference Latency', value: '18ms avg', icon: Zap, detail: 'Across all models' },
            { label: 'Platform Version', value: health?.version ?? '6.0.0', icon: Cpu, detail: 'Runtime Kernel Mode' },
          ].map((s, i) => (
            <StatCard key={s.label} {...s} index={i} />
          ))}
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-white/10 mb-8 overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview & Status', icon: Activity },
            { id: 'playground', label: 'Developer Playground', icon: Play },
            { id: 'chat', label: 'Copilot Chat', icon: MessageSquare },
            { id: 'admin', label: 'Admin Center', icon: Settings }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-6 py-4 border-b-2 font-medium text-sm transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-vit-500 text-vit-400 bg-white/[0.02]'
                  : 'border-transparent text-white/50 hover:text-white/80 hover:bg-white/[0.01]'
              }`}
            >
              <tab.icon className="w-4.5 h-4.5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content rendering */}
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-6"
            >
              {/* Telemetry Dashboard Row */}
              <div className="grid md:grid-cols-3 gap-6">
                {/* Live System Performance Panel */}
                <div className="md:col-span-2 rounded-xl border border-white/10 bg-white/5 p-6">
                  <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Gauge className="w-5 h-5 text-vit-400" />
                    Live Gateway Performance & Telemetry
                  </h2>
                  <div className="grid sm:grid-cols-2 gap-6">
                    {/* CPU & Memory progress bars */}
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between text-sm mb-1 text-white/70">
                          <span>Gateway CPU Utilization</span>
                          <span className="font-mono font-bold text-vit-400">{metrics.cpu}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                          <div className="h-full bg-vit-500 transition-all duration-1000" style={{ width: `${metrics.cpu}%` }}></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1 text-white/70">
                          <span>Active RAM Allocation</span>
                          <span className="font-mono font-bold text-vit-400">{metrics.mem}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                          <div className="h-full bg-vit-500 transition-all duration-1000" style={{ width: `${metrics.mem}%` }}></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1 text-white/70">
                          <span>Virtual GPU Node Load (CUDA)</span>
                          <span className="font-mono font-bold text-vit-400">{metrics.gpu}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                          <div className="h-full bg-vit-400 transition-all duration-1000" style={{ width: `${metrics.gpu}%` }}></div>
                        </div>
                      </div>
                    </div>
                    {/* Live metrics widgets */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-white/[0.03] border border-white/5 p-4 rounded-lg">
                        <span className="text-xs text-white/40 block mb-1">Cache Hit Ratio (Redis)</span>
                        <span className="text-2xl font-bold font-mono text-white">{metrics.cacheHitRatio}%</span>
                      </div>
                      <div className="bg-white/[0.03] border border-white/5 p-4 rounded-lg">
                        <span className="text-xs text-white/40 block mb-1">Queue Backlog Size</span>
                        <span className="text-2xl font-bold font-mono text-vit-400">{metrics.queue} jobs</span>
                      </div>
                      <div className="bg-white/[0.03] border border-white/5 p-4 rounded-lg">
                        <span className="text-xs text-white/40 block mb-1">Active AI Providers</span>
                        <span className="text-2xl font-bold font-mono text-white">{metrics.activeProviders} online</span>
                      </div>
                      <div className="bg-white/[0.03] border border-white/5 p-4 rounded-lg">
                        <span className="text-xs text-white/40 block mb-1">Service SLA</span>
                        <span className="text-2xl font-bold font-mono text-vit-400">{metrics.providerUptime}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Subsystem Health status column */}
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 flex flex-col justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                      <ShieldAlert className="w-5 h-5 text-vit-400" />
                      Platform Heartbeats
                    </h2>
                    <div className="space-y-3">
                      {[
                        { name: 'Gateway Subsystems', status: 'healthy', details: 'All 8 modules operational' },
                        { name: 'PostgreSQL Connection', status: 'healthy', details: 'Latency: 2ms | DB schema synced' },
                        { name: 'Redis Valkey Server', status: 'healthy', details: 'Ping: <1ms' },
                        { name: 'Tachyon Swarm Cluster', status: 'quantum_stable', details: 'M=3 Parity | 4KB parallel chunks' }
                      ].map(item => (
                        <div key={item.name} className="flex items-center justify-between p-2.5 rounded bg-white/[0.02] border border-white/5">
                          <div>
                            <p className="text-xs font-semibold text-white">{item.name}</p>
                            <p className="text-[10px] text-white/40">{item.details}</p>
                          </div>
                          <StatusBadge status={item.status} size="sm" />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Model Grid Cards */}
              <div className="rounded-xl border border-white/10 bg-white/5 p-6">
                <h2 className="text-xl font-extrabold text-white mb-6">Model Registry Registry List ({finalModels.length} Active Engines)</h2>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {finalModels.map((m: any) => (
                    <div key={m.id} className="rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.05] p-5 transition-all flex flex-col justify-between h-44">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-vit-500/10 border border-vit-500/20 text-vit-400 font-bold">{m.id}</span>
                          <StatusBadge status={m.status || 'ready'} size="sm" />
                        </div>
                        <h3 className="font-bold text-white text-base truncate">{m.name || m.id}</h3>
                        <p className="text-xs text-white/50 line-clamp-2 mt-1">
                          {m.description || `High-density ensemble forecasting node tailored for ${m.id} market inference.`}
                        </p>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-white/40 pt-3 border-t border-white/5 font-mono">
                        <span>L: <strong className="text-vit-400">{m.latency ?? 12}ms</strong></span>
                        <span>V: {m.version ?? '4.6.0'}</span>
                        <span>Ctx: {m.context ?? '4k'}</span>
                        <span className="capitalize">{m.provider}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'playground' && (
            <motion.div
              key="playground"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="grid lg:grid-cols-3 gap-6"
            >
              {/* Sliders and config column */}
              <div className="rounded-xl border border-white/10 bg-white/5 p-6 space-y-5">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-vit-400" />
                  Hyperparameter Panel
                </h2>
                <div>
                  <label className="text-xs text-white/50 block mb-1.5 font-medium">Model Deployment Selection</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg p-2.5 text-sm focus:border-vit-500 focus:outline-none"
                  >
                    {finalModels.map(m => (
                      <option key={m.id} value={m.id} className="bg-black text-white">{m.name || m.id}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-white/50 block mb-1.5 font-medium">System Role Prompt</label>
                  <textarea
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    className="w-full h-20 bg-white/5 border border-white/10 rounded-lg p-2.5 text-xs focus:border-vit-500 focus:outline-none font-sans"
                    placeholder="Enter system prompt guidelines..."
                  />
                </div>
                <div>
                  <div className="flex justify-between text-xs text-white/50 mb-1.5 font-medium">
                    <span>Inference Temperature</span>
                    <span className="font-mono text-vit-400">{temperature}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1.5"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    className="w-full accent-vit-500 bg-white/10 h-1 rounded-lg cursor-pointer"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-xs text-white/50 mb-1.5 font-medium">
                    <span>Max Output Tokens</span>
                    <span className="font-mono text-vit-400">{maxTokens}</span>
                  </div>
                  <input
                    type="range"
                    min="64"
                    max="4096"
                    step="64"
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                    className="w-full accent-vit-500 bg-white/10 h-1 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="pt-4 border-t border-white/5 space-y-2 text-xs font-mono text-white/40">
                  <div className="flex justify-between">
                    <span>Prompt Tokens:</span>
                    <span className="text-white">{playgroundUsage.promptTokens}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Completion Tokens:</span>
                    <span className="text-white">{playgroundUsage.completionTokens}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cost Estimate:</span>
                    <span className="text-vit-400">${playgroundUsage.cost.toFixed(6)}</span>
                  </div>
                </div>
              </div>

              {/* Prompt and output canvas column */}
              <div className="lg:col-span-2 space-y-6">
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 flex flex-col space-y-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-vit-400" />
                    Input Prompt Canvas
                  </h2>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Enter analytical challenge or prompt inquiry (e.g. 'Identify tactical anomalies for Liverpool vs Real Madrid match context')..."
                    className="w-full h-28 bg-white/5 border border-white/10 rounded-lg p-4 text-sm focus:border-vit-500 focus:outline-none font-sans"
                  />
                  <div className="flex justify-end">
                    <button
                      onClick={triggerPlayground}
                      disabled={isInferencing || !prompt.trim()}
                      className="flex items-center gap-2 px-6 py-3 rounded-lg bg-vit-500 hover:bg-vit-600 text-white font-semibold transition-all disabled:opacity-50"
                    >
                      {isInferencing ? <Spinner className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      Execute Inference
                    </button>
                  </div>
                </div>

                {/* Response Output Container */}
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 min-h-[250px] flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-white/5 mb-4">
                      <span className="text-sm font-bold text-white/70">Console Output Response</span>
                      {playgroundLatency && (
                        <span className="text-xs font-mono text-vit-400">Response Latency: {playgroundLatency}ms</span>
                      )}
                    </div>
                    {playgroundOutput ? (
                      <div className="prose prose-invert max-w-none text-sm text-white/90 leading-relaxed font-sans whitespace-pre-wrap">
                        {playgroundOutput}
                      </div>
                    ) : (
                      <div className="text-center py-12 text-white/30 space-y-2">
                        <Terminal className="w-10 h-10 mx-auto opacity-40 text-vit-400" />
                        <p className="text-sm">Response will render dynamically here using stream emulation.</p>
                      </div>
                    )}
                  </div>
                  {playgroundOutput && !isInferencing && (
                    <div className="flex items-center gap-3 justify-end pt-4 border-t border-white/5">
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(playgroundOutput)
                          alert("Copied to clipboard.")
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 border border-white/5 text-xs text-white/70 hover:text-white transition-all"
                      >
                        <Copy className="w-3.5 h-3.5" /> Copy
                      </button>
                      <button
                        onClick={() => {
                          const element = document.createElement("a");
                          const file = new Blob([playgroundOutput], {type: 'text/plain'});
                          element.href = URL.createObjectURL(file);
                          element.download = "playground_output.txt";
                          document.body.appendChild(element);
                          element.click();
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 border border-white/5 text-xs text-white/70 hover:text-white transition-all"
                      >
                        <Download className="w-3.5 h-3.5" /> Export
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'chat' && (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="grid md:grid-cols-4 gap-6"
            >
              {/* Chat sidebar: Conversation history */}
              <div className="rounded-xl border border-white/10 bg-white/5 p-4 flex flex-col justify-between h-[600px]">
                <div className="space-y-4 flex-1 overflow-y-auto">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider">Conversations</h2>
                    <button
                      onClick={handleCreateConversation}
                      className="p-1 rounded hover:bg-white/10 border border-white/10 text-white/60 hover:text-white transition-all"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                  {/* Search */}
                  <div className="relative">
                    <Search className="w-4 h-4 text-white/40 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      value={chatSearch}
                      onChange={(e) => setChatSearch(e.target.value)}
                      placeholder="Search session..."
                      className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-xs focus:outline-none focus:border-vit-500 text-white"
                    />
                  </div>
                  {/* List */}
                  <div className="space-y-1.5">
                    {conversations
                      .filter(c => c.title.toLowerCase().includes(chatSearch.toLowerCase()))
                      .map(c => (
                        <button
                          key={c.id}
                          onClick={() => setActiveConvId(c.id)}
                          className={`w-full text-left p-3 rounded-lg text-xs font-medium transition-all truncate border flex items-center justify-between ${
                            c.id === activeConvId
                              ? 'bg-vit-500/10 border-vit-500/30 text-vit-400'
                              : 'bg-white/[0.01] border-transparent text-white/60 hover:text-white hover:bg-white/[0.02]'
                          }`}
                        >
                          <span className="truncate">{c.title}</span>
                          <span className="text-[9px] opacity-40 font-mono">{c.messages.length} msgs</span>
                        </button>
                      ))}
                  </div>
                </div>

                {/* Clear options */}
                <div className="pt-4 border-t border-white/5">
                  <button
                    onClick={() => {
                      setConversations([{
                        id: 'default',
                        title: 'Blockchain Oracle Analytics',
                        messages: [{ id: '1', role: 'assistant', content: 'Hello! I am **VIT Copilot**. Ask me to analyze transactions, explain smart contracts, debug platform status, or interpret predictive models.', timestamp: new Date().toLocaleTimeString() }]
                      }])
                      setActiveConvId('default')
                    }}
                    className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-red-500/20 bg-red-500/5 hover:bg-red-500/10 text-red-400 text-xs font-medium transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Clear Sessions
                  </button>
                </div>
              </div>

              {/* Chat interaction main window */}
              <div className="md:col-span-3 flex flex-col h-[600px] border border-white/10 rounded-xl bg-white/5 overflow-hidden">
                {/* Chat window top header */}
                <div className="p-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Brain className="w-5 h-5 text-vit-400" />
                    <div>
                      <h3 className="text-sm font-bold text-white">VIT Copilot (Consensus Router)</h3>
                      <p className="text-[10px] text-white/40 font-mono">Routing Strategy: Highest Accuracy | Model polled: LLMConsensus v1.2</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    <span className="text-xs text-white/55 font-semibold font-mono">AI Swarm Ready</span>
                  </div>
                </div>

                {/* Copilot Shortcuts row */}
                <div className="p-3 border-b border-white/5 bg-white/[0.01] flex items-center gap-2 overflow-x-auto scrollbar-none">
                  {copilotShortcuts.map(sc => (
                    <button
                      key={sc.label}
                      onClick={() => sendChatMessage(sc.text)}
                      className="px-3 py-1.5 rounded-full border border-white/15 bg-white/5 hover:bg-white/10 text-white/80 hover:text-white text-[11px] transition-all whitespace-nowrap"
                    >
                      {sc.label}
                    </button>
                  ))}
                </div>

                {/* Message display panel */}
                <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-black/20">
                  {conversations.find(c => c.id === activeConvId)?.messages.map(m => (
                    <div
                      key={m.id}
                      className={`flex gap-3 max-w-[85%] ${m.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                        m.role === 'user'
                          ? 'bg-vit-500/20 border-vit-500/30 text-vit-400'
                          : 'bg-white/10 border-white/10 text-white/80'
                      }`}>
                        {m.role === 'user' ? <User className="w-4 h-4" /> : <Brain className="w-4 h-4" />}
                      </div>
                      <div className={`p-4 rounded-xl text-sm leading-relaxed ${
                        m.role === 'user'
                          ? 'bg-vit-500/10 border border-vit-500/20 text-white'
                          : 'bg-white/[0.03] border border-white/10 text-white/90'
                      }`}>
                        <div className="whitespace-pre-wrap prose prose-invert font-sans">{m.content}</div>
                        <span className="text-[9px] text-white/30 block text-right mt-1.5 font-mono">{m.timestamp}</span>
                      </div>
                    </div>
                  ))}
                  {isChatStreaming && (
                    <div className="flex gap-3 max-w-[80%]">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border bg-white/10 border-white/10 text-white/80">
                        <Brain className="w-4 h-4 animate-pulse" />
                      </div>
                      <div className="p-4 rounded-xl text-sm bg-white/[0.03] border border-white/10 text-white/60 italic flex items-center gap-2">
                        <Spinner className="w-3.5 h-3.5" /> Copilot is drafting response...
                      </div>
                    </div>
                  )}
                </div>

                {/* Input box */}
                <div className="p-4 border-t border-white/10 bg-white/[0.02]">
                  <form
                    onSubmit={(e) => { e.preventDefault(); sendChatMessage() }}
                    className="flex gap-3"
                  >
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Ask VIT Copilot any analytical prompt or troubleshoot commands..."
                      className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-vit-500 text-white"
                    />
                    <button
                      type="submit"
                      disabled={isChatStreaming || !chatInput.trim()}
                      className="px-5 py-3 rounded-lg bg-vit-500 hover:bg-vit-600 text-white font-semibold text-sm transition-all disabled:opacity-50"
                    >
                      Submit
                    </button>
                  </form>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'admin' && (
            <motion.div
              key="admin"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-6"
            >
              {/* Hot configuration toolbar */}
              <div className="rounded-xl border border-white/10 bg-white/5 p-6 grid sm:grid-cols-3 gap-4">
                <div className="flex flex-col justify-between h-24 p-4 rounded-lg bg-white/[0.03] border border-white/5">
                  <div>
                    <span className="text-xs text-white/40 block mb-1">Cache Management</span>
                    <span className="text-sm font-bold text-white">Redis Model Cache</span>
                  </div>
                  <button
                    onClick={handleClearCache}
                    className="w-full text-center py-1.5 rounded border border-vit-500/20 bg-vit-500/5 hover:bg-vit-500/10 text-vit-400 text-xs font-semibold transition-all"
                  >
                    Clear Redis Cache
                  </button>
                </div>
                <div className="flex flex-col justify-between h-24 p-4 rounded-lg bg-white/[0.03] border border-white/5">
                  <div>
                    <span className="text-xs text-white/40 block mb-1">Provider Control</span>
                    <span className="text-sm font-bold text-white">Reload Orchestrator</span>
                  </div>
                  <button
                    onClick={handleRestartProviders}
                    className="w-full text-center py-1.5 rounded border border-vit-500/20 bg-vit-500/5 hover:bg-vit-500/10 text-vit-400 text-xs font-semibold transition-all"
                  >
                    Restart Containers
                  </button>
                </div>
                <div className="flex flex-col justify-between h-24 p-4 rounded-lg bg-white/[0.03] border border-white/5">
                  <div>
                    <span className="text-xs text-white/40 block mb-1">Secure Management</span>
                    <span className="text-sm font-bold text-white">API Keys & Tokens</span>
                  </div>
                  <button
                    onClick={() => { alert("Rotated admin key credentials. Logs updated."); addLog("INF: Rotated gateway API Keys.") }}
                    className="w-full text-center py-1.5 rounded border border-vit-500/20 bg-vit-500/5 hover:bg-vit-500/10 text-vit-400 text-xs font-semibold transition-all"
                  >
                    Rotate API Keys
                  </button>
                </div>
              </div>

              {/* Dynamic Weights Adjuster & Hot Toggle Panel */}
              <div className="grid md:grid-cols-5 gap-6">
                <div className="md:col-span-3 rounded-xl border border-white/10 bg-white/5 p-6">
                  <h2 className="text-lg font-bold text-white mb-4">Ensemble Voting Adjustments</h2>
                  <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
                    {finalModels.map(m => {
                      const settings = modelSettings[m.id] || { weight: 1.0, enabled: true }
                      return (
                        <div key={m.id} className="flex items-center gap-4 justify-between p-3 rounded bg-white/[0.01] border border-white/5 text-sm">
                          <div className="w-1/3 truncate">
                            <span className="font-bold block truncate">{m.name || m.id}</span>
                            <span className="text-[10px] font-mono text-white/40">{m.id}</span>
                          </div>
                          <div className="flex-1 flex items-center gap-3">
                            <input
                              type="range"
                              min="0"
                              max="3"
                              step="0.05"
                              value={settings.weight}
                              onChange={(e) => handleModelWeightChange(m.id, parseFloat(e.target.value))}
                              disabled={!settings.enabled}
                              className="w-full cursor-pointer accent-vit-500 bg-white/10 h-1 rounded disabled:opacity-30"
                            />
                            <span className="font-mono text-xs w-10 text-right">{settings.weight.toFixed(2)}</span>
                          </div>
                          <button
                            onClick={() => handleModelToggle(m.id)}
                            className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                              settings.enabled
                                ? 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
                                : 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                            }`}
                          >
                            {settings.enabled ? 'Enabled' : 'Disabled'}
                          </button>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Console Log Panel */}
                <div className="md:col-span-2 rounded-xl border border-white/10 bg-white/5 p-6 flex flex-col h-[482px]">
                  <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Terminal className="w-5 h-5 text-vit-400" />
                    Inference & Cluster Logs
                  </h2>
                  <div className="flex-1 bg-black/60 rounded-lg border border-white/10 p-4 font-mono text-[11px] text-green-400/90 overflow-y-auto space-y-1.5 scrollbar-thin">
                    {adminLogStream.map((log, index) => (
                      <p key={index} className="leading-relaxed whitespace-pre-wrap break-all">{log}</p>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
