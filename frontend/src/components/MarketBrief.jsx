import { motion } from 'framer-motion'
import { TrendingUp, Users, DollarSign, Swords, Target } from 'lucide-react'

const RATING_CONFIG = {
  EXCEPTIONAL: { color: 'text-teal-400' },
  HIGH: { color: 'text-teal-400' },
  MEDIUM: { color: 'text-amber-400' },
  LOW: { color: 'text-slate-400' },
}

const DENSITY_CONFIG = {
  WHITE_SPACE: { color: 'text-teal-400', label: 'White Space' },
  MODERATE: { color: 'text-amber-400', label: 'Moderate' },
  CROWDED: { color: 'text-red-400', label: 'Crowded' },
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}
const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
}

export default function MarketBrief({ marketData }) {
  if (!marketData) return null

  const rating = marketData.opportunity_rating || ''
  const density = marketData.competitive_density || ''
  const ratingConfig = RATING_CONFIG[rating] || RATING_CONFIG.MEDIUM
  const densityConfig = DENSITY_CONFIG[density] || { color: 'text-slate-400', label: density.replace('_', ' ') }

  return (
    <motion.div
      className="card p-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.div className="flex items-center gap-2.5 mb-5" variants={itemVariants}>
        <div className="w-8 h-8 rounded-lg bg-teal-600/8 flex items-center justify-center">
          <TrendingUp className="w-4 h-4 text-teal-400" />
        </div>
        <h3 className="text-base font-semibold font-display text-slate-100">Market Opportunity</h3>
      </motion.div>

      <div className="grid grid-cols-2 gap-3">
        <motion.div className="bg-slate-800/20 border border-slate-700/15 rounded-xl p-4" variants={itemVariants}>
          <div className="flex items-center gap-1.5 mb-2">
            <Users className="w-3 h-3 text-slate-500" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Patients</p>
          </div>
          <p className="text-lg font-bold text-slate-100 font-mono">{marketData.patient_population || '—'}</p>
        </motion.div>

        <motion.div className="bg-slate-800/20 border border-slate-700/15 rounded-xl p-4" variants={itemVariants}>
          <div className="flex items-center gap-1.5 mb-2">
            <DollarSign className="w-3 h-3 text-slate-500" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Market Size</p>
          </div>
          <p className="text-lg font-bold text-teal-400 font-mono">{marketData.market_size || marketData.market_size_usd || '—'}</p>
        </motion.div>

        <motion.div className="bg-slate-800/20 border border-slate-700/15 rounded-xl p-4" variants={itemVariants}>
          <div className="flex items-center gap-1.5 mb-2">
            <Swords className="w-3 h-3 text-slate-500" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Competition</p>
          </div>
          <p className={`text-lg font-bold ${densityConfig.color}`}>{densityConfig.label || '—'}</p>
        </motion.div>

        <motion.div className="bg-slate-800/20 border border-slate-700/15 rounded-xl p-4" variants={itemVariants}>
          <div className="flex items-center gap-1.5 mb-2">
            <Target className="w-3 h-3 text-slate-500" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Rating</p>
          </div>
          <p className={`text-lg font-bold ${ratingConfig.color}`}>{rating || '—'}</p>
        </motion.div>
      </div>

      {marketData.commercial_brief && (
        <motion.div className="mt-4 bg-slate-800/15 rounded-xl p-3.5 border border-slate-700/10" variants={itemVariants}>
          <p className="text-xs text-slate-400 leading-relaxed italic">{marketData.commercial_brief}</p>
        </motion.div>
      )}
    </motion.div>
  )
}
