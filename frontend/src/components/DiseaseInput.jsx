import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Loader2, Search, Sparkles, ArrowRight, Clock, Trash2, ChevronRight,
  BookOpen, Target, FlaskConical, Shield,
} from 'lucide-react'
import MoleculeViz from './MoleculeViz.jsx'
import { getHistory, removeFromHistory, formatTimeAgo } from '../api/history.js'

const DEMO_DISEASES = ["Parkinson's Disease", "Type 2 Diabetes", "Alzheimer's Disease"]

const PIPELINE_STEPS = [
  { icon: BookOpen, title: 'Literature Mining', desc: 'Scans PubMed & Europe PMC for emerging protein targets associated with your disease.', color: '#5B9CF6' },
  { icon: Target, title: 'Target Validation', desc: 'Cross-references OpenTargets, UniProt, and AlphaFold to confirm druggability.', color: '#A78BFA' },
  { icon: FlaskConical, title: 'Molecule Generation', desc: 'Seeds from ChEMBL actives, extracts scaffolds, generates novel analogues with RDKit & DeepChem.', color: '#00D8A4' },
  { icon: Shield, title: 'Safety & Scoring', desc: 'Predicts ADMET properties, scores candidates on 4 dimensions, and delivers GO/NO-GO verdicts.', color: '#F5B731' },
]

const API_BADGES = [
  'PubMed', 'Europe PMC', 'OpenTargets', 'UniProt', 'AlphaFold',
  'ChEMBL', 'PubChem', 'WHO GHO', 'ClinicalTrials.gov', 'OpenFDA', 'RCSB PDB',
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.07, delayChildren: 0.15 } },
}
const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.25, 0.46, 0.45, 0.94] } },
}

export default function DiseaseInput({ onSubmit, onLoadHistory }) {
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const [history, setHistory] = useState(() => getHistory())

  async function handleSubmit(e) {
    e.preventDefault()
    const name = inputValue.trim()
    if (!name || isLoading) return
    setIsLoading(true)
    try { await onSubmit(name) } finally { setIsLoading(false) }
  }

  function handleDemo(disease) {
    if (isLoading) return
    setInputValue(disease)
    setIsLoading(true)
    Promise.resolve(onSubmit(disease)).finally(() => setIsLoading(false))
  }

  function handleRemoveHistory(e, jobId) {
    e.stopPropagation()
    removeFromHistory(jobId)
    setHistory(getHistory())
  }

  return (
    <div className="min-h-screen flex flex-col">

      {/* ═══ HERO ═══ */}
      <section className="flex-1 flex items-center relative overflow-hidden min-h-[80vh]">
        {/* Glow behind molecule */}
        <div
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-[0.04] pointer-events-none hidden lg:block"
          style={{ background: 'radial-gradient(circle, #00D8A4 0%, transparent 70%)', left: '5%' }}
        />
        {/* Glow behind heading */}
        <div
          className="absolute right-[10%] top-[20%] w-[400px] h-[400px] rounded-full opacity-[0.03] pointer-events-none hidden lg:block"
          style={{ background: 'radial-gradient(circle, #F5B731 0%, transparent 70%)' }}
        />

        <motion.div
          className="max-w-7xl mx-auto w-full px-6 sm:px-10 grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center py-16 lg:py-0"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Left — Molecule */}
          <motion.div className="hidden lg:flex items-center justify-center" variants={itemVariants}>
            <div className="relative">
              <MoleculeViz className="w-[420px] h-[280px] opacity-80" />
              <div className="absolute -top-8 -left-8 w-[460px] h-[320px] rounded-full border border-slate-800/20 pointer-events-none" />
            </div>
          </motion.div>

          {/* Right — Content */}
          <div>
            <motion.div variants={itemVariants}>
              <span className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-teal-400/80 mb-6 font-display">
                <span className="w-8 h-px bg-teal-400/40" />
                Autonomous Drug Discovery
              </span>
            </motion.div>

            {/* ── Dramatic Heading ── */}
            <motion.div className="relative mb-6" variants={itemVariants}>
              {/* Glow layer behind text (pure decoration) */}
              <div className="absolute -inset-4 hero-glow pointer-events-none select-none" aria-hidden="true">
                <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold font-display opacity-0">
                  MolForge AI
                </h1>
              </div>
              <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold font-display leading-[1.05] relative">
                <span className="text-gradient-hero">MolForge</span>
                <br />
                <span className="text-slate-50">AI</span>
                <span className="inline-block w-3 h-3 rounded-full bg-teal-400 ml-3 mb-2 animate-pulse-dot" />
              </h1>
            </motion.div>

            <motion.p className="text-lg text-slate-400 leading-relaxed mb-9 max-w-lg" variants={itemVariants}>
              Nine AI agents. Eleven biomedical APIs. One autonomous pipeline that takes you from disease to drug candidate.
            </motion.p>

            {/* Search */}
            <motion.form onSubmit={handleSubmit} variants={itemVariants}>
              <div className="relative mb-4">
                <Search className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors duration-300 ${isFocused ? 'text-teal-400' : 'text-slate-500'}`} />
                <input
                  type="text"
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setIsFocused(false)}
                  placeholder="Enter a disease name..."
                  disabled={isLoading}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl py-4 pl-12 pr-5 text-slate-50 placeholder-slate-500 text-base focus:outline-none focus:border-teal-600/40 focus:ring-1 focus:ring-teal-600/20 disabled:opacity-50 transition-all duration-300"
                  style={{ boxShadow: isFocused ? '0 0 40px rgba(0, 216, 164, 0.04)' : 'none' }}
                />
              </div>

              <motion.button
                type="submit"
                disabled={isLoading || !inputValue.trim()}
                className="btn-shimmer w-full bg-teal-600 hover:bg-teal-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl py-4 text-base font-semibold transition-all duration-300 flex items-center justify-center gap-2.5 cursor-pointer font-display"
                whileHover={{ scale: isLoading || !inputValue.trim() ? 1 : 1.01 }}
                whileTap={{ scale: isLoading || !inputValue.trim() ? 1 : 0.99 }}
                style={{
                  boxShadow: !isLoading && inputValue.trim()
                    ? '0 0 40px rgba(0, 216, 164, 0.12), 0 8px 24px rgba(0, 0, 0, 0.4)' : 'none',
                }}
              >
                {isLoading ? (
                  <><Loader2 className="w-5 h-5 animate-spin" /> Initializing Pipeline...</>
                ) : (
                  <><Sparkles className="w-5 h-5" /> Begin Discovery <ArrowRight className="w-4 h-4 opacity-60" /></>
                )}
              </motion.button>
            </motion.form>

            {/* Quick start */}
            <motion.div className="flex flex-wrap items-center gap-2.5 mt-5" variants={itemVariants}>
              <span className="text-[11px] text-slate-500 font-medium uppercase tracking-wider">Try</span>
              {DEMO_DISEASES.map((d, i) => (
                <motion.button
                  key={d}
                  onClick={() => handleDemo(d)}
                  disabled={isLoading}
                  className="text-xs bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-700/50 rounded-lg px-3.5 py-2 transition-all duration-200 disabled:opacity-40 cursor-pointer"
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + i * 0.08 }}
                >
                  {d}
                </motion.button>
              ))}
            </motion.div>
          </div>
        </motion.div>
      </section>

      {/* ═══ RECENT SEARCHES ═══ */}
      {history.length > 0 && (
        <section className="border-t border-slate-800/60 py-16 relative">
          <div className="max-w-7xl mx-auto px-6 sm:px-10">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <div className="flex items-center gap-2.5 mb-8">
                <Clock className="w-4 h-4 text-slate-500" />
                <h2 className="text-lg font-semibold font-display text-slate-200">Recent Searches</h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {history.slice(0, 6).map((entry, i) => (
                  <motion.div
                    key={entry.jobId}
                    onClick={() => onLoadHistory?.(entry)}
                    role="button"
                    tabIndex={0}
                    className="card p-4 text-left cursor-pointer hover:border-slate-600 transition-all duration-200 group flex items-center justify-between"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.05, duration: 0.3 }}
                    whileHover={{ scale: 1.01 }}
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate mb-1">{entry.disease}</p>
                      <div className="flex items-center gap-3 text-[11px]">
                        <span className="text-slate-500">{formatTimeAgo(entry.timestamp)}</span>
                        {entry.candidateCount != null && (
                          <span className="text-slate-500">{entry.candidateCount} candidates</span>
                        )}
                        {entry.goCount != null && entry.goCount > 0 && (
                          <span className="text-teal-400 font-medium">{entry.goCount} GO</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0 ml-3">
                      <button
                        onClick={(e) => handleRemoveHistory(e, entry.jobId)}
                        className="p-1 rounded-md hover:bg-slate-800 text-slate-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                        title="Remove"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400 transition-colors" />
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </section>
      )}

      {/* ═══ HOW IT WORKS ═══ */}
      <section className="border-t border-slate-800/60 py-20 relative">
        <div className="max-w-7xl mx-auto px-6 sm:px-10">
          <motion.div
            className="text-center mb-14"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-2xl sm:text-3xl font-bold font-display mb-3">How MolForge Works</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">Four stages, fully autonomous. From literature to lead compounds in minutes.</p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {PIPELINE_STEPS.map((step, i) => (
              <motion.div
                key={step.title}
                className="card p-6 group hover:border-slate-600 transition-all duration-300"
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-xs font-mono font-bold text-slate-600">0{i + 1}</span>
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${step.color}10` }}>
                    <step.icon className="w-4.5 h-4.5" style={{ color: step.color }} />
                  </div>
                </div>
                <h3 className="text-sm font-semibold text-slate-100 font-display mb-2">{step.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ POWERED BY ═══ */}
      <section className="border-t border-slate-800/60 py-14">
        <div className="max-w-7xl mx-auto px-6 sm:px-10">
          <motion.div
            className="text-center"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500 font-medium mb-5">Powered by 11 biomedical APIs</p>
            <div className="flex flex-wrap justify-center gap-2.5">
              {API_BADGES.map((api, i) => (
                <motion.span
                  key={api}
                  className="text-xs text-slate-400 bg-slate-900 border border-slate-800 rounded-lg px-3.5 py-1.5 font-medium"
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.03, duration: 0.3 }}
                >
                  {api}
                </motion.span>
              ))}
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  )
}
