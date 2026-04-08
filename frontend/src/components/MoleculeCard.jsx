import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Copy, Check, Fingerprint, ExternalLink } from 'lucide-react'
import ScoreBadge from './ScoreBadge.jsx'
import ScoreRing from './ScoreRing.jsx'
import AdmetRadar from './AdmetRadar.jsx'
import { getMoleculeSvg } from '../api/discover.js'

const SCORE_ROWS = [
  { key: 'binding_score', label: 'Binding', color: 'from-teal-600 to-teal-400' },
  { key: 'admet_score', label: 'ADMET', color: 'from-emerald-600 to-emerald-400' },
  { key: 'literature_score', label: 'Literature', color: 'from-blue-600 to-blue-400' },
  { key: 'market_score', label: 'Market', color: 'from-amber-600 to-amber-400' },
]

export default function MoleculeCard({ candidate, rank, jobId, onViewDetail }) {
  const [expanded, setExpanded] = useState(false)
  const [imgError, setImgError] = useState(false)
  const [copied, setCopied] = useState(false)

  const svgUrl = getMoleculeSvg(jobId, rank - 1)
  const pct = candidate.composite_score || 0

  function handleCopySmiles() {
    if (!candidate.smiles) return
    navigator.clipboard.writeText(candidate.smiles)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <motion.div
      className="card overflow-hidden"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.05, duration: 0.4 }}
      layout
    >
      {/* Header */}
      <button
        className="w-full flex items-center justify-between px-5 sm:px-6 py-4 cursor-pointer hover:bg-slate-800/30 transition-colors duration-200"
        onClick={() => setExpanded(v => !v)}
      >
        <div className="flex items-center gap-4">
          <ScoreRing
            score={pct}
            size={48}
            strokeWidth={3}
            label=""
            animate={true}
            delay={rank * 80}
            className="shrink-0"
          />
          <div className="text-left">
            <div className="flex items-center gap-2.5 mb-0.5">
              <span className="text-slate-200 font-semibold text-sm font-display">Candidate {rank}</span>
              <ScoreBadge verdict={candidate.verdict} size="sm" />
            </div>
            {candidate.smiles && (
              <p className="text-xs font-mono text-slate-500 max-w-xs truncate">{candidate.smiles}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {candidate.novelty_score != null && (
            <div className="hidden sm:flex items-center gap-1.5 bg-violet-500/8 border border-violet-500/15 rounded-lg px-2.5 py-1">
              <Fingerprint className="w-3 h-3 text-violet-400" />
              <span className="text-xs font-mono text-violet-400 font-medium">{(candidate.novelty_score * 100).toFixed(0)}%</span>
            </div>
          )}
          <motion.div animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.3 }}>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </motion.div>
        </div>
      </button>

      {/* Expanded */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="overflow-hidden"
          >
            <div className="border-t border-slate-800/40 px-5 sm:px-6 pb-6 pt-5 space-y-6">
              {/* Structure + SMILES */}
              <div className="flex flex-col sm:flex-row gap-5">
                <div className="shrink-0 flex justify-center">
                  {imgError ? (
                    <div className="w-56 h-44 flex items-center justify-center card">
                      <span className="text-slate-500 text-xs">Structure unavailable</span>
                    </div>
                  ) : (
                    <div className="rounded-xl overflow-hidden inline-block border border-slate-700/20" style={{ background: '#f8f8f8' }}>
                      <img
                        src={svgUrl}
                        alt={`Structure of Candidate ${rank}`}
                        className="max-w-[220px] max-h-[170px] block"
                        onError={() => setImgError(true)}
                      />
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  {candidate.smiles && (
                    <div className="flex items-start gap-2 mb-4">
                      <div className="flex-1 min-w-0 bg-slate-800/30 border border-slate-700/20 rounded-xl px-3 py-2.5">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-1">SMILES</p>
                        <p className="font-mono text-xs text-slate-400 break-all leading-relaxed">{candidate.smiles}</p>
                      </div>
                      <button
                        onClick={handleCopySmiles}
                        className="shrink-0 mt-5 p-1.5 rounded-lg bg-slate-800/30 hover:bg-slate-700/40 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
                        title="Copy SMILES"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-teal-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  )}

                  {/* Property pills */}
                  <div className="flex flex-wrap gap-2">
                    {candidate.mw != null && (
                      <Pill label="MW" value={Math.round(candidate.mw)} />
                    )}
                    {candidate.logp != null && (
                      <Pill label="LogP" value={candidate.logp.toFixed(1)} />
                    )}
                    {candidate.tpsa != null && (
                      <Pill label="TPSA" value={Math.round(candidate.tpsa)} />
                    )}
                    {candidate.sa_score != null && (
                      <Pill label="SA" value={candidate.sa_score.toFixed(1)} />
                    )}
                    {candidate.novelty_score != null && (
                      <span className="bg-violet-500/8 text-violet-400 border border-violet-500/15 text-xs px-2.5 py-1 rounded-lg font-mono font-medium">
                        Novelty {(candidate.novelty_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Score breakdown + ADMET radar */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <p className="text-xs text-slate-500 font-medium mb-3">Score Breakdown</p>
                  <div className="space-y-3">
                    {SCORE_ROWS.map(({ key, label, color }) => {
                      const val = candidate[key] || 0
                      return (
                        <div key={key}>
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs text-slate-400 font-medium">{label}</span>
                            <span className="text-xs text-slate-200 font-mono font-semibold">{(val * 100).toFixed(0)}%</span>
                          </div>
                          <div className="h-1.5 bg-slate-800/50 rounded-full overflow-hidden">
                            <motion.div
                              className={`h-full bg-linear-to-r ${color} rounded-full`}
                              initial={{ width: '0%' }}
                              animate={{ width: `${val * 100}%` }}
                              transition={{ duration: 1, delay: 0.2, ease: 'easeOut' }}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
                <AdmetRadar admetDetail={candidate.admet_detail} />
              </div>

              {/* View Detail button */}
              {onViewDetail && (
                <motion.button
                  onClick={() => onViewDetail(rank - 1)}
                  className="w-full flex items-center justify-center gap-2 card px-4 py-3 text-sm font-medium font-display text-teal-400 hover:text-teal-300 hover:border-teal-600/30 transition-all cursor-pointer"
                  whileHover={{ scale: 1.005 }}
                  whileTap={{ scale: 0.995 }}
                >
                  <ExternalLink className="w-4 h-4" />
                  View Full Research Detail
                </motion.button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function Pill({ label, value }) {
  return (
    <span className="bg-slate-800/30 text-slate-400 text-xs px-2.5 py-1 rounded-lg border border-slate-700/15 font-mono">
      {label} {value}
    </span>
  )
}
