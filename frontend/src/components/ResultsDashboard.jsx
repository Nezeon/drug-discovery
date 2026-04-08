import { useState } from 'react'
import { motion } from 'framer-motion'
import { Filter, FlaskConical, Dna, Target } from 'lucide-react'
import MoleculeCard from './MoleculeCard.jsx'
import MarketBrief from './MarketBrief.jsx'
import ReportDownload from './ReportDownload.jsx'
import ScoreRing from './ScoreRing.jsx'

const FILTER_TABS = ['All', 'GO', 'INVESTIGATE', 'NO-GO']

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
}
const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45 } },
}

export default function ResultsDashboard({ results, jobId, onViewDetail }) {
  const [activeFilter, setActiveFilter] = useState('All')
  if (!results) return null

  const { final_candidates = [], validated_target, market_brief } = results
  const filtered = activeFilter === 'All'
    ? final_candidates
    : final_candidates.filter(c => c.verdict === activeFilter)
  const sorted = [...filtered].sort((a, b) => (b.composite_score || 0) - (a.composite_score || 0))

  const goCt = final_candidates.filter(c => c.verdict === 'GO').length
  const invCt = final_candidates.filter(c => c.verdict === 'INVESTIGATE').length
  const nogoCt = final_candidates.filter(c => c.verdict === 'NO-GO').length
  const topScore = final_candidates.length > 0
    ? Math.max(...final_candidates.map(c => c.composite_score || 0))
    : 0

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="visible">

      {/* ═══ HERO STATS ═══ */}
      <motion.div className="card p-6 sm:p-8 mb-6" variants={itemVariants}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold font-display text-slate-100 mb-1">Discovery Complete</h2>
            <p className="text-sm text-slate-400">
              {final_candidates.length} candidate molecules analyzed for{' '}
              <span className="text-slate-200 font-medium">{results.disease}</span>
            </p>
          </div>
          <ReportDownload jobId={jobId} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatTile icon={FlaskConical} value={final_candidates.length} label="Total" color="text-slate-200" iconColor="text-slate-400" />
          <StatTile icon={Target} value={goCt} label="GO" color="text-teal-400" iconColor="text-teal-400" />
          <StatTile icon={Dna} value={invCt} label="Investigate" color="text-amber-400" iconColor="text-amber-400" />
          <div className="bg-slate-800/20 border border-slate-700/15 rounded-xl p-4 flex items-center gap-4">
            <ScoreRing score={topScore} size={48} strokeWidth={3} label="" colorMode="emerald" />
            <div>
              <p className="text-lg font-bold font-mono text-teal-400">{(topScore * 100).toFixed(0)}%</p>
              <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Top Score</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* ═══ MAIN GRID ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left — candidates */}
        <div className="lg:col-span-2 space-y-4">
          {/* Filters */}
          <motion.div className="flex items-center gap-3" variants={itemVariants}>
            <Filter className="w-4 h-4 text-slate-500" />
            <div className="flex items-center gap-1 bg-slate-900 border border-slate-800/60 rounded-xl p-1">
              {FILTER_TABS.map(tab => {
                const isActive = activeFilter === tab
                const count = tab === 'All' ? final_candidates.length
                  : tab === 'GO' ? goCt : tab === 'INVESTIGATE' ? invCt : nogoCt
                return (
                  <button
                    key={tab}
                    onClick={() => setActiveFilter(tab)}
                    className={`px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 flex items-center gap-1.5 cursor-pointer ${
                      isActive ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                    }`}
                  >
                    {tab}
                    <span className={`text-[10px] font-mono ${isActive ? 'text-slate-300' : 'text-slate-500'}`}>{count}</span>
                  </button>
                )
              })}
            </div>
          </motion.div>

          {/* Cards */}
          {sorted.length > 0 ? (
            <div className="space-y-3">
              {sorted.map((candidate, i) => (
                <MoleculeCard key={candidate.smiles || i} candidate={candidate} rank={i + 1} jobId={jobId} onViewDetail={onViewDetail} />
              ))}
            </div>
          ) : (
            <motion.div className="card p-12 text-center" variants={itemVariants}>
              <FlaskConical className="w-8 h-8 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">No candidates match this filter.</p>
            </motion.div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-4">
          {validated_target && (
            <motion.div className="card p-6" variants={itemVariants}>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="w-8 h-8 rounded-lg bg-violet-500/8 flex items-center justify-center">
                  <Dna className="w-4 h-4 text-violet-400" />
                </div>
                <h3 className="text-base font-semibold font-display text-slate-100">Validated Target</h3>
              </div>

              <div className="mb-4">
                <p className="text-2xl font-mono font-bold text-gradient-emerald mb-1">{validated_target.name}</p>
                {validated_target.protein_name && (
                  <p className="text-sm text-slate-400">{validated_target.protein_name}</p>
                )}
              </div>

              {validated_target.druggability_score != null && (
                <div className="mb-4">
                  <div className="flex items-center justify-between text-xs mb-2">
                    <span className="text-slate-500 font-medium">Druggability</span>
                    <span className="text-teal-400 font-mono font-semibold">{(validated_target.druggability_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-slate-800/50 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-linear-to-r from-teal-600 to-teal-400 rounded-full"
                      initial={{ width: '0%' }}
                      animate={{ width: `${validated_target.druggability_score * 100}%` }}
                      transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
                    />
                  </div>
                </div>
              )}

              {validated_target.uniprot_id && (
                <div className="bg-slate-800/20 border border-slate-700/15 rounded-lg px-3 py-2 inline-block">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-0.5">UniProt ID</p>
                  <p className="text-xs font-mono text-slate-300">{validated_target.uniprot_id}</p>
                </div>
              )}
            </motion.div>
          )}

          <MarketBrief marketData={market_brief} />
        </div>
      </div>
    </motion.div>
  )
}

function StatTile({ icon: Icon, value, label, color, iconColor }) {
  return (
    <motion.div className="bg-slate-800/20 border border-slate-700/15 rounded-xl p-4 flex items-center gap-3" variants={itemVariants}>
      <div className={`w-9 h-9 rounded-lg bg-slate-800/40 flex items-center justify-center shrink-0`}>
        <Icon className={`w-4 h-4 ${iconColor}`} />
      </div>
      <div>
        <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
        <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">{label}</p>
      </div>
    </motion.div>
  )
}
