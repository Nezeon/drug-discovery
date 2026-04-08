import { motion } from 'framer-motion'
import { Download, FileText } from 'lucide-react'
import { getReportUrl } from '../api/discover.js'

export default function ReportDownload({ jobId }) {
  return (
    <motion.button
      onClick={() => window.open(getReportUrl(jobId), '_blank')}
      className="btn-shimmer flex items-center gap-2.5 bg-teal-600 hover:bg-teal-500 text-white rounded-xl px-5 py-2.5 text-sm font-semibold font-display transition-all duration-300 cursor-pointer"
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      style={{ boxShadow: '0 0 24px rgba(0, 216, 164, 0.1), 0 4px 12px rgba(0, 0, 0, 0.4)' }}
    >
      <FileText className="w-4 h-4" />
      Export PDF
      <Download className="w-3.5 h-3.5 opacity-60" />
    </motion.button>
  )
}
