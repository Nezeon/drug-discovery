import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search, CheckCircle, Box, Atom, Shield,
  TrendingUp, BarChart3, DollarSign,
  Check, AlertTriangle, Loader2,
  Timer, Zap, Activity, Crosshair, Route, Dna,
} from 'lucide-react'
import { getResults } from '../api/discover.js'

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

const AGENTS = [
  { key: 'disease_analyst',     name: 'Disease Analyst',     shortName: 'DA', icon: Search,      desc: 'Mining literature for targets' },
  { key: 'target_validator',    name: 'Target Validator',    shortName: 'TV', icon: CheckCircle, desc: 'Validating druggability' },
  { key: 'structure_resolver',  name: 'Structure Resolver',  shortName: 'SR', icon: Box,         desc: 'Resolving 3D structure' },
  { key: 'compound_discovery',  name: 'Compound Discovery',  shortName: 'CD', icon: Atom,        desc: 'Generating novel molecules' },
  { key: 'admet_predictor',     name: 'ADMET Predictor',     shortName: 'AP', icon: Shield,      desc: 'Predicting drug safety' },
  { key: 'docking_scorer',      name: 'Docking Scorer',      shortName: 'DK', icon: Crosshair,   desc: 'Estimating binding affinity' },
  { key: 'synthesis_planner',   name: 'Synthesis Planner',   shortName: 'SP', icon: Route,        desc: 'Planning synthesis routes' },
  { key: 'biologics_analyst',   name: 'Biologics Analyst',   shortName: 'BA', icon: Dna,          desc: 'Evaluating biologic modalities' },
  { key: 'market_analyst',      name: 'Market Analyst',      shortName: 'MA', icon: TrendingUp,  desc: 'Analyzing market size' },
  { key: 'competitive_scout',   name: 'Competitive Scout',   shortName: 'CS', icon: BarChart3,   desc: 'Scouting competition' },
  { key: 'opportunity_scorer',  name: 'Opportunity Scorer',  shortName: 'OS', icon: DollarSign,  desc: 'Scoring opportunity' },
]

function formatTime(s) { return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}` }

export default function AgentActivityPanel({ jobId, onComplete }) {
  const [agentStates, setAgentStates] = useState(() =>
    Object.fromEntries(AGENTS.map(a => [a.key, { status: 'pending', message: '' }]))
  )
  const [logs, setLogs] = useState([])
  const [pipelineStatus, setPipelineStatus] = useState('running')
  const [progress, setProgress] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const logRef = useRef(null)
  const wsRef = useRef(null)
  const timerRef = useRef(null)

  const doneCount = Object.values(agentStates).filter(a => a.status === 'done').length
  const totalAgents = AGENTS.length
  const runningAgent = AGENTS.find(a => agentStates[a.key]?.status === 'running')
  const completedAgents = AGENTS.filter(a => agentStates[a.key]?.status === 'done')

  // Elapsed timer — use ref-based counting to avoid stale closure issues
  useEffect(() => {
    const startTime = Date.now()
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000))
    }, 500)
    return () => clearInterval(timerRef.current)
  }, [])

  useEffect(() => {
    if (pipelineStatus !== 'running') clearInterval(timerRef.current)
  }, [pipelineStatus])

  useEffect(() => {
    if (!jobId) return
    const ws = new WebSocket(`${WS_BASE}/ws/${jobId}`)
    wsRef.current = ws
    ws.onopen = () => setPipelineStatus('running')
    ws.onmessage = async (event) => {
      const msg = JSON.parse(event.data)
      const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
      setLogs(prev => [...prev, { text: msg.message || JSON.stringify(msg), time, type: msg.type }])

      if (msg.type === 'agent_start' && msg.agent) {
        setAgentStates(prev => ({ ...prev, [msg.agent]: { status: 'running', message: msg.message || '' } }))
      }
      if (msg.type === 'agent_done' && msg.agent) {
        setAgentStates(prev => ({ ...prev, [msg.agent]: { status: 'done', message: msg.message || '' } }))
      }
      if (msg.type === 'error' && msg.agent) {
        setAgentStates(prev => ({ ...prev, [msg.agent]: { status: 'error', message: msg.message || '' } }))
      }
      if (msg.type === 'progress' && msg.pct != null) setProgress(msg.pct)
      if (msg.type === 'complete') {
        setPipelineStatus('complete')
        setProgress(100)
        try { onComplete?.(await getResults(jobId)) } catch (err) { console.error(err) }
      }
      setTimeout(() => logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' }), 50)
    }
    ws.onerror = () => setPipelineStatus('error')
    ws.onclose = () => { if (pipelineStatus === 'running') setPipelineStatus('disconnected') }
    return () => ws.close()
  }, [jobId]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="w-full max-w-7xl mx-auto space-y-5">

      {/* ═══ PROGRESS HEADER ═══ */}
      <motion.div
        className="card p-6"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* Stats row */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${
              pipelineStatus === 'running' ? 'bg-teal-400 animate-pulse-dot'
              : pipelineStatus === 'complete' ? 'bg-teal-400'
              : 'bg-red-400'
            }`} />
            <span className="text-sm font-semibold font-display text-slate-200">
              {pipelineStatus === 'running' ? 'Pipeline Active' : pipelineStatus === 'complete' ? 'Complete' : 'Error'}
            </span>
          </div>
          <div className="flex items-center gap-5 sm:gap-8">
            <Stat icon={Zap} value={`${doneCount}/${totalAgents}`} label="Agents" color="text-teal-400" />
            <Stat icon={Timer} value={formatTime(elapsed)} label="Elapsed" color="text-amber-400" />
            <Stat icon={Activity} value={`${progress}%`} label="Progress" color="text-blue-400" />
          </div>
        </div>

        {/* Progress bar */}
        <div className="relative h-2 bg-slate-800 rounded-full overflow-hidden">
          <motion.div
            className="absolute inset-y-0 left-0 progress-bar rounded-full"
            initial={{ width: '0%' }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </div>

        {/* Current step */}
        {runningAgent && (
          <motion.p className="text-xs text-slate-500 mt-3" key={runningAgent.key} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            Active: <span className="text-violet-400 font-medium">{runningAgent.name}</span>
            {agentStates[runningAgent.key]?.message && (
              <span className="text-slate-500 ml-1">— {agentStates[runningAgent.key].message}</span>
            )}
          </motion.p>
        )}
      </motion.div>

      {/* ═══ HORIZONTAL TIMELINE ═══ */}
      <motion.div
        className="card p-6"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4 }}
      >
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-5">Agent Pipeline</p>
        <div className="flex items-center justify-between relative">
          {/* Connecting line */}
          <div className="absolute top-4 left-6 right-6 h-px bg-slate-800" />
          <div
            className="absolute top-4 left-6 h-px bg-teal-600/50 transition-all duration-700"
            style={{ width: `${Math.max(0, (doneCount / AGENTS.length) * 100 - 4)}%` }}
          />

          {AGENTS.map((agent, i) => {
            const state = agentStates[agent.key]
            const isDone = state.status === 'done'
            const isRunning = state.status === 'running'
            const isError = state.status === 'error'

            return (
              <div key={agent.key} className="relative flex flex-col items-center z-10" style={{ width: `${100 / AGENTS.length}%` }}>
                {/* Node */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold font-mono transition-all duration-300 ${
                  isDone ? 'bg-teal-600/15 text-teal-400 border border-teal-600/30'
                  : isRunning ? 'bg-violet-600/15 text-violet-400 border border-violet-500/40 animate-pulse-glow-violet'
                  : isError ? 'bg-red-600/15 text-red-400 border border-red-500/30'
                  : 'bg-slate-800 text-slate-600 border border-slate-700'
                }`}>
                  {isDone ? (
                    <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 500, damping: 25 }}>
                      <Check className="w-3.5 h-3.5" />
                    </motion.div>
                  ) : isRunning ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : isError ? (
                    <AlertTriangle className="w-3 h-3" />
                  ) : (
                    <span className="text-[10px]">{i + 1}</span>
                  )}
                </div>

                {/* Label */}
                <span className={`mt-2.5 text-[10px] font-medium text-center leading-tight hidden sm:block ${
                  isDone ? 'text-teal-400/70'
                  : isRunning ? 'text-violet-400'
                  : 'text-slate-600'
                }`}>
                  {agent.shortName}
                </span>
              </div>
            )
          })}
        </div>
      </motion.div>

      {/* ═══ MAIN CONTENT: 2 columns ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* LEFT (2/3) — Active agent + completed list */}
        <div className="lg:col-span-2 space-y-5">

          {/* Active agent spotlight */}
          <AnimatePresence mode="wait">
            {runningAgent && (
              <motion.div
                key={runningAgent.key}
                className="card p-6 relative overflow-hidden agent-running"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35 }}
              >
                {/* Shimmer overlay */}
                <div
                  className="absolute inset-0 opacity-[0.02] pointer-events-none"
                  style={{
                    background: 'linear-gradient(110deg, transparent 30%, rgba(139, 92, 246, 0.5) 50%, transparent 70%)',
                    backgroundSize: '200% 100%',
                    animation: 'shimmer 2.5s ease-in-out infinite',
                  }}
                />

                <div className="relative z-10">
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center">
                      <runningAgent.icon className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                      <p className="text-[10px] text-violet-400/60 uppercase tracking-wider font-semibold mb-0.5">Currently Active</p>
                      <h3 className="text-lg font-bold font-display text-slate-100">{runningAgent.name}</h3>
                    </div>
                  </div>
                  <p className="text-sm text-slate-400">
                    {agentStates[runningAgent.key]?.message || runningAgent.desc}
                  </p>
                  <div className="mt-4 flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 text-violet-400 animate-spin" />
                    <span className="text-xs text-violet-400/70">Processing...</span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Completed agents */}
          {completedAgents.length > 0 && (
            <motion.div
              className="card p-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-4">Completed Steps</p>
              <div className="space-y-2">
                {completedAgents.map((agent) => {
                  const state = agentStates[agent.key]
                  return (
                    <motion.div
                      key={agent.key}
                      className="flex items-center gap-3 px-3 py-2.5 bg-slate-800/30 rounded-xl"
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <div className="w-7 h-7 rounded-lg bg-teal-600/10 flex items-center justify-center shrink-0">
                        <Check className="w-3.5 h-3.5 text-teal-400" />
                      </div>
                      <div className="min-w-0">
                        <span className="text-sm font-medium text-slate-200">{agent.name}</span>
                        {state.message && (
                          <p className="text-xs text-slate-500 truncate">{state.message}</p>
                        )}
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>
          )}
        </div>

        {/* RIGHT (1/3) — Live feed terminal */}
        <div className="lg:col-span-1">
          <motion.div
            className="terminal overflow-hidden sticky top-6"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25, duration: 0.4 }}
          >
            {/* Terminal header */}
            <div className="flex items-center gap-2 px-5 py-3 border-b border-slate-800/60 bg-[#0D0D0F]">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
                <div className="w-2.5 h-2.5 rounded-full bg-amber-500/50" />
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/50" />
              </div>
              <span className="text-[10px] text-slate-600 ml-2 font-mono">live-feed</span>
            </div>

            {/* Log content */}
            <div
              ref={logRef}
              className="h-80 sm:h-96 p-4 overflow-y-auto text-xs leading-relaxed"
            >
              {logs.length === 0 ? (
                <span className="text-slate-600 terminal-cursor">Awaiting pipeline output</span>
              ) : (
                logs.map((log, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.15 }}
                    className="flex gap-3 mb-1.5 terminal-line"
                  >
                    <span className="text-slate-700 shrink-0 w-14 text-[10px]">{log.time}</span>
                    <span className={
                      log.type === 'error' ? 'text-red-400'
                      : log.type === 'agent_done' ? 'text-teal-400'
                      : log.type === 'agent_start' ? 'text-violet-400'
                      : 'text-slate-400'
                    }>
                      {log.text}
                    </span>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

function Stat({ icon: Icon, value, label, color }) {
  return (
    <div className="flex items-center gap-2">
      <Icon className={`w-3.5 h-3.5 ${color} opacity-70`} />
      <span className={`text-sm font-mono font-semibold ${color}`}>{value}</span>
      <span className="text-[10px] text-slate-500 hidden sm:inline">{label}</span>
    </div>
  )
}
