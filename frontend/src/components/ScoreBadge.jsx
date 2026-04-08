import { motion } from 'framer-motion'
import { Check, AlertTriangle, X } from 'lucide-react'

const VERDICT_CONFIG = {
  GO: {
    bg: 'bg-teal-500/8',
    border: 'border-teal-500/20',
    text: 'text-teal-400',
    glow: '0 0 12px rgba(0, 216, 164, 0.1)',
    icon: Check,
  },
  INVESTIGATE: {
    bg: 'bg-amber-500/8',
    border: 'border-amber-500/20',
    text: 'text-amber-400',
    glow: '0 0 12px rgba(245, 183, 49, 0.08)',
    icon: AlertTriangle,
  },
  'NO-GO': {
    bg: 'bg-red-500/8',
    border: 'border-red-500/20',
    text: 'text-red-400',
    glow: '0 0 12px rgba(240, 104, 104, 0.08)',
    icon: X,
  },
}

export default function ScoreBadge({ verdict, size = 'default' }) {
  const config = VERDICT_CONFIG[verdict] || VERDICT_CONFIG['INVESTIGATE']
  const Icon = config.icon
  const isSmall = size === 'sm'

  return (
    <motion.span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold border ${config.bg} ${config.border} ${config.text} ${
        isSmall ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs'
      }`}
      style={{ boxShadow: config.glow }}
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
    >
      <Icon className={isSmall ? 'w-2.5 h-2.5' : 'w-3 h-3'} />
      {verdict}
    </motion.span>
  )
}
