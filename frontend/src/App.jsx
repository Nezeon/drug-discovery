import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { ArrowLeft, FlaskConical } from 'lucide-react'
import DiseaseInput from './components/DiseaseInput.jsx'
import AgentActivityPanel from './components/AgentActivityPanel.jsx'
import ResultsDashboard from './components/ResultsDashboard.jsx'
import CandidateDetail from './components/CandidateDetail.jsx'
import ParticleBackground from './components/ParticleBackground.jsx'
import { postDiscover, getResults } from './api/discover.js'
import { addToHistory } from './api/history.js'

const pageTransition = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] } },
  exit: { opacity: 0, y: -12, transition: { duration: 0.25 } },
}

export default function App() {
  const [phase, setPhase] = useState('input')  // input | running | results | detail
  const [jobId, setJobId] = useState(null)
  const [disease, setDisease] = useState('')
  const [results, setResults] = useState(null)
  const [detailIndex, setDetailIndex] = useState(null)

  async function handleSubmit(diseaseName) {
    try {
      setDisease(diseaseName)
      const data = await postDiscover(diseaseName)
      setJobId(data.job_id)
      setResults(null)
      setPhase('running')
    } catch (err) {
      toast.error(err.message || 'Failed to start pipeline')
      throw err
    }
  }

  function handleComplete(finalResults) {
    setResults(finalResults)
    setPhase('results')
    const candidates = finalResults?.final_candidates || []
    addToHistory({
      disease: finalResults?.disease || disease,
      jobId,
      timestamp: new Date().toISOString(),
      candidateCount: candidates.length,
      goCount: candidates.filter(c => c.verdict === 'GO').length,
      topScore: candidates.length > 0 ? Math.max(...candidates.map(c => c.composite_score || 0)) : 0,
    })
  }

  async function handleLoadHistory(entry) {
    setDisease(entry.disease)
    setJobId(entry.jobId)
    try {
      const data = await getResults(entry.jobId)
      setResults(data)
      setPhase('results')
    } catch {
      toast.error('Could not load previous results. The data may have expired.')
    }
  }

  function handleViewDetail(candidateIndex) {
    setDetailIndex(candidateIndex)
    setPhase('detail')
  }

  function handleBackToResults() {
    setDetailIndex(null)
    setPhase('results')
  }

  function handleNewSearch() {
    setPhase('input')
    setJobId(null)
    setResults(null)
    setDisease('')
    setDetailIndex(null)
  }

  return (
    <div className="min-h-screen text-slate-50 noise-overlay" style={{ background: '#08080A' }}>
      <AnimatePresence mode="wait">

        {/* ═══ INPUT ═══ */}
        {phase === 'input' && (
          <motion.div key="input" {...pageTransition} className="relative">
            <ParticleBackground variant="dense" />
            <div className="relative z-10">
              <DiseaseInput onSubmit={handleSubmit} onLoadHistory={handleLoadHistory} />
            </div>
          </motion.div>
        )}

        {/* ═══ RUNNING ═══ */}
        {phase === 'running' && (
          <motion.div key="running" {...pageTransition} className="relative min-h-screen">
            <ParticleBackground />
            <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
              <Header disease={disease} onNew={handleNewSearch} showNew={false} />
              <AgentActivityPanel jobId={jobId} onComplete={handleComplete} />
            </div>
          </motion.div>
        )}

        {/* ═══ RESULTS ═══ */}
        {phase === 'results' && (
          <motion.div key="results" {...pageTransition} className="relative min-h-screen">
            <ParticleBackground />
            <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
              <Header disease={disease} onNew={handleNewSearch} showNew />
              <ResultsDashboard results={results} jobId={jobId} onViewDetail={handleViewDetail} />
            </div>
          </motion.div>
        )}

        {/* ═══ CANDIDATE DETAIL ═══ */}
        {phase === 'detail' && (
          <motion.div key="detail" {...pageTransition} className="relative min-h-screen">
            <ParticleBackground />
            <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
              <Header disease={disease} onNew={handleNewSearch} showNew />
              <CandidateDetail jobId={jobId} candidateIndex={detailIndex} onBack={handleBackToResults} />
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}

function Header({ disease, onNew, showNew }) {
  return (
    <motion.div
      className="flex items-center justify-between mb-7"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1, duration: 0.4 }}
    >
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-teal-600 flex items-center justify-center" style={{ boxShadow: '0 0 20px rgba(0, 216, 164, 0.15)' }}>
          <FlaskConical className="w-4.5 h-4.5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold font-display">
            <span className="text-gradient-emerald">MolForge</span>
            <span className="text-gradient-gold ml-1.5">AI</span>
          </h1>
          {disease && <p className="text-xs text-slate-500">Analyzing <span className="text-slate-300">{disease}</span></p>}
        </div>
      </div>
      {showNew && (
        <motion.button
          onClick={onNew}
          className="flex items-center gap-2 card px-4 py-2.5 text-sm font-medium font-display text-slate-300 hover:text-slate-100 hover:border-slate-600 transition-all cursor-pointer"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <ArrowLeft className="w-4 h-4" />
          New Search
        </motion.button>
      )}
    </motion.div>
  )
}
