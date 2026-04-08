import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowLeft, FlaskConical, Target, Shield, Crosshair, Route, Dna,
  TrendingUp, Check, X, AlertTriangle, Copy, ExternalLink,
  BookOpen, Box, Atom,
} from 'lucide-react'
import ScoreBadge from './ScoreBadge.jsx'
import ScoreRing from './ScoreRing.jsx'
import AdmetRadar from './AdmetRadar.jsx'
import { getCandidateDetail, getMoleculeSvg } from '../api/discover.js'
import ProteinViewer from './ProteinViewer.jsx'

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
}

export default function CandidateDetail({ jobId, candidateIndex, onBack }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    setLoading(true)
    getCandidateDetail(jobId, candidateIndex)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [jobId, candidateIndex])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-8 h-8 border-2 border-teal-400 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-24 text-slate-500">
        <p>Could not load candidate details.</p>
        <button onClick={onBack} className="mt-4 text-teal-400 hover:underline cursor-pointer">Go back</button>
      </div>
    )
  }

  const { candidate, validated_target, protein_structure, docking, synthesis, admet_full, biologics, market_data, opportunity_score, disease } = data
  const svgUrl = getMoleculeSvg(jobId, candidateIndex)
  const pct = candidate.composite_score || 0

  function handleCopy() {
    navigator.clipboard.writeText(candidate.smiles)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-2 card px-4 py-2.5 text-sm font-medium text-slate-300 hover:text-slate-100 hover:border-slate-600 transition-all cursor-pointer font-display">
          <ArrowLeft className="w-4 h-4" />
          Back to Results
        </button>
        <ScoreBadge verdict={candidate.verdict} />
      </div>

      {/* ═══ HERO: Molecule + Score ═══ */}
      <div className="card p-6 sm:p-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
          {/* Structure image */}
          <div className="flex justify-center">
            <div className="rounded-xl overflow-hidden border border-slate-700/20" style={{ background: '#f8f8f8' }}>
              <img src={svgUrl} alt="Molecule structure" className="max-w-[300px] max-h-[220px] block" />
            </div>
          </div>

          {/* Info */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-4 mb-4">
              <ScoreRing score={pct} size={72} strokeWidth={4} label="Score" />
              <div>
                <h2 className="text-2xl font-bold font-display text-slate-100">Candidate {candidateIndex + 1}</h2>
                <p className="text-sm text-slate-400">{disease}</p>
              </div>
            </div>

            {/* SMILES */}
            {candidate.smiles && (
              <div className="flex items-center gap-2 mb-4">
                <code className="flex-1 text-xs font-mono text-slate-400 bg-slate-800/30 border border-slate-700/20 rounded-lg px-3 py-2 break-all">
                  {candidate.smiles}
                </code>
                <button onClick={handleCopy} className="p-2 rounded-lg bg-slate-800/30 hover:bg-slate-700/40 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer">
                  {copied ? <Check className="w-4 h-4 text-teal-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            )}

            {/* Quick stats */}
            <div className="flex flex-wrap gap-2">
              {candidate.novelty_score != null && <Pill label="Novelty" value={`${(candidate.novelty_score * 100).toFixed(0)}%`} color="violet" />}
              {admet_full?.mw != null && <Pill label="MW" value={Math.round(admet_full.mw)} />}
              {admet_full?.logp != null && <Pill label="LogP" value={admet_full.logp.toFixed(1)} />}
              {admet_full?.tpsa != null && <Pill label="TPSA" value={Math.round(admet_full.tpsa)} />}
              {admet_full?.hbd != null && <Pill label="HBD" value={admet_full.hbd} />}
              {admet_full?.hba != null && <Pill label="HBA" value={admet_full.hba} />}
            </div>
          </div>
        </div>
      </div>

      {/* ═══ 3D PROTEIN STRUCTURE ═══ */}
      <ProteinViewer jobId={jobId} ligandSmiles={candidate.smiles} />

      {/* ═══ PIPELINE RESEARCH STEPS ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* 1. Target Discovery */}
        <Section icon={Target} title="Target Discovery" color="#5B9CF6">
          {validated_target?.name && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-2xl font-mono font-bold text-gradient-emerald">{validated_target.name}</span>
                {validated_target.uniprot_id && (
                  <span className="text-xs font-mono text-slate-500 bg-slate-800/30 rounded px-2 py-0.5">{validated_target.uniprot_id}</span>
                )}
              </div>
              {validated_target.protein_name && <p className="text-sm text-slate-400">{validated_target.protein_name}</p>}
              {validated_target.druggability_score != null && (
                <BarStat label="Druggability" value={validated_target.druggability_score} />
              )}
              {validated_target.evidence && <p className="text-xs text-slate-400 italic leading-relaxed">{validated_target.evidence}</p>}
            </div>
          )}
        </Section>

        {/* 2. Protein Structure */}
        <Section icon={Box} title="Protein Structure" color="#A78BFA">
          {protein_structure?.source ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <StatusChip pass>{protein_structure.source === 'alphafold_db' ? 'AlphaFold DB' : 'RCSB PDB'}</StatusChip>
                {protein_structure.plddt_avg != null && (
                  <span className="text-xs text-slate-400">pLDDT: <span className="font-mono text-slate-200">{protein_structure.plddt_avg.toFixed(1)}</span></span>
                )}
              </div>
              {protein_structure.confidence_note && <p className="text-xs text-slate-400">{protein_structure.confidence_note}</p>}
              {protein_structure.pdb_file_path && <p className="text-xs font-mono text-slate-500 truncate">{protein_structure.pdb_file_path}</p>}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No structure data available</p>
          )}
        </Section>

        {/* 3. Score Breakdown */}
        <Section icon={FlaskConical} title="Score Breakdown" color="#00D8A4">
          <div className="space-y-3">
            <BarStat label="Binding" value={candidate.binding_score} />
            <BarStat label="ADMET" value={candidate.admet_score} />
            <BarStat label="Literature" value={candidate.literature_score} color="blue" />
            <BarStat label="Market" value={candidate.market_score} color="gold" />
            <div className="border-t border-slate-800/40 pt-3">
              <BarStat label="Composite" value={candidate.composite_score} />
            </div>
          </div>
        </Section>

        {/* 4. ADMET Safety */}
        <Section icon={Shield} title="ADMET Safety Profile" color="#00D8A4">
          <div className="grid grid-cols-2 gap-3 mb-4">
            {admet_full && (
              <>
                <AdmetItem label="hERG" value={admet_full.herg} />
                <AdmetItem label="Ames" value={admet_full.ames} />
                <AdmetItem label="DILI" value={admet_full.dili} />
                <AdmetItem label="BBB" value={admet_full.bbb} />
                <AdmetItem label="Caco-2" value={admet_full.caco2} />
                <AdmetItem label="Verdict" value={admet_full.verdict} />
              </>
            )}
          </div>
          {admet_full?.flags && admet_full.flags.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] text-slate-500 uppercase font-medium">Flags</p>
              {admet_full.flags.map((flag, i) => (
                <p key={i} className="text-xs text-amber-400/80 flex items-center gap-1.5">
                  <AlertTriangle className="w-3 h-3 shrink-0" />{flag}
                </p>
              ))}
            </div>
          )}
          <AdmetRadar admetDetail={candidate.admet_detail} />
        </Section>

        {/* 5. Docking */}
        <Section icon={Crosshair} title="Molecular Docking" color="#F5B731">
          {docking ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-3xl font-mono font-bold text-slate-100">{docking.binding_affinity_kcal}</span>
                <span className="text-sm text-slate-400">kcal/mol</span>
              </div>
              <div className="flex items-center gap-2">
                <StatusChip pass={docking.confidence === 'high'}>{docking.method === 'vina' ? 'AutoDock Vina' : 'RDKit Proxy'}</StatusChip>
                <span className="text-xs text-slate-400">Confidence: <span className="font-medium text-slate-200">{docking.confidence}</span></span>
              </div>
              {docking.details && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {docking.details.aromatic_rings != null && <Pill label="Arom. Rings" value={docking.details.aromatic_rings} />}
                  {docking.details.hbd != null && <Pill label="HBD" value={docking.details.hbd} />}
                  {docking.details.hba != null && <Pill label="HBA" value={docking.details.hba} />}
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No docking data available</p>
          )}
        </Section>

        {/* 6. Synthesis Route */}
        <Section icon={Route} title="Synthesis Planning" color="#00D8A4">
          {synthesis ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <StatusChip pass={synthesis.feasible}>{synthesis.feasible ? 'Feasible' : 'Challenging'}</StatusChip>
                <span className="text-xs text-slate-400">{synthesis.num_steps} steps</span>
                <span className="text-xs text-slate-400">Difficulty: <span className="font-medium text-slate-200">{synthesis.estimated_difficulty}</span></span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{synthesis.route_description}</p>
              {synthesis.fragments && synthesis.fragments.length > 0 && (
                <div>
                  <p className="text-[10px] text-slate-500 uppercase font-medium mb-2">Building Blocks</p>
                  <div className="space-y-1">
                    {synthesis.fragments.slice(0, 5).map((f, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        {f.available ? <Check className="w-3 h-3 text-teal-400" /> : <X className="w-3 h-3 text-red-400" />}
                        <span className="text-slate-300">{f.name}</span>
                        <code className="text-slate-500 font-mono text-[10px]">{f.smiles}</code>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {synthesis.sa_score != null && <BarStat label="SA Score" value={1 - synthesis.sa_score / 10} subtext={synthesis.sa_score.toFixed(1)} />}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No synthesis data available</p>
          )}
        </Section>

        {/* 7. Biologics Assessment */}
        <Section icon={Dna} title="Biologics Assessment" color="#A78BFA">
          {biologics && biologics.target ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-slate-400">Target class:</span>
                <span className="text-xs font-medium text-slate-200">{biologics.target_class}</span>
                <span className="text-xs text-slate-400">({biologics.localization})</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <ModalityCard label="Antibody" score={biologics.antibody?.score} rationale={biologics.antibody?.rationale} />
                <ModalityCard label="Peptide" score={biologics.peptide?.score} rationale={biologics.peptide?.rationale} />
                <ModalityCard label="ADC" score={biologics.adc?.score} rationale={biologics.adc?.rationale} />
              </div>
              {biologics.recommended_modality && biologics.recommended_modality !== 'none' && (
                <p className="text-xs text-teal-400 font-medium">
                  Recommended: <span className="capitalize">{biologics.recommended_modality}</span>
                </p>
              )}
              {biologics.key_considerations && biologics.key_considerations.length > 0 && (
                <div className="space-y-1">
                  {biologics.key_considerations.map((c, i) => (
                    <p key={i} className="text-xs text-slate-400">• {c}</p>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No biologics data available</p>
          )}
        </Section>

        {/* 8. Market Opportunity */}
        <Section icon={TrendingUp} title="Market Opportunity" color="#F5B731">
          {market_data ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <SmallStat label="Patients" value={market_data.patient_population || '—'} />
                <SmallStat label="Market Size" value={market_data.market_size_usd_estimate || market_data.market_size_usd || '—'} color="teal" />
              </div>
              {opportunity_score?.rating && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Rating:</span>
                  <span className={`text-sm font-bold ${opportunity_score.rating === 'EXCEPTIONAL' || opportunity_score.rating === 'HIGH' ? 'text-teal-400' : opportunity_score.rating === 'MEDIUM' ? 'text-amber-400' : 'text-slate-400'}`}>
                    {opportunity_score.rating}
                  </span>
                </div>
              )}
              {opportunity_score?.commercial_brief && (
                <p className="text-xs text-slate-400 italic leading-relaxed">{opportunity_score.commercial_brief}</p>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No market data available</p>
          )}
        </Section>
      </div>
    </motion.div>
  )
}

/* ─── Sub-components ─── */

function Section({ icon: Icon, title, color, children }) {
  return (
    <motion.div className="card p-5" variants={itemVariants} initial="hidden" animate="visible">
      <div className="flex items-center gap-2.5 mb-4">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${color}10` }}>
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        <h3 className="text-sm font-semibold font-display text-slate-100">{title}</h3>
      </div>
      {children}
    </motion.div>
  )
}

function BarStat({ label, value, color = 'emerald', subtext }) {
  const pct = Math.min(Math.max((value || 0) * 100, 0), 100)
  const barColor = color === 'blue' ? 'from-blue-600 to-blue-400'
    : color === 'gold' ? 'from-amber-600 to-amber-400'
    : 'from-teal-600 to-teal-400'
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-slate-400 font-medium">{label}</span>
        <span className="text-xs text-slate-200 font-mono font-semibold">{subtext || `${pct.toFixed(0)}%`}</span>
      </div>
      <div className="h-1.5 bg-slate-800/50 rounded-full overflow-hidden">
        <motion.div
          className={`h-full bg-linear-to-r ${barColor} rounded-full`}
          initial={{ width: '0%' }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

function Pill({ label, value, color }) {
  const colorClass = color === 'violet' ? 'bg-violet-500/8 text-violet-400 border-violet-500/15' : 'bg-slate-800/30 text-slate-400 border-slate-700/15'
  return (
    <span className={`text-xs px-2.5 py-1 rounded-lg border font-mono ${colorClass}`}>
      {label} {value}
    </span>
  )
}

function StatusChip({ pass: isPassing, children }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full border ${
      isPassing ? 'bg-teal-500/8 border-teal-500/20 text-teal-400' : 'bg-amber-500/8 border-amber-500/20 text-amber-400'
    }`}>
      {isPassing ? <Check className="w-2.5 h-2.5" /> : <AlertTriangle className="w-2.5 h-2.5" />}
      {children}
    </span>
  )
}

function AdmetItem({ label, value }) {
  if (value == null) return null
  const isPass = value === 'PASS' || value === 'PERMEABLE'
  const isFail = value === 'FAIL' || value === 'POSITIVE'
  return (
    <div className="bg-slate-800/20 border border-slate-700/10 rounded-lg p-2.5">
      <p className="text-[10px] text-slate-500 uppercase mb-0.5">{label}</p>
      <p className={`text-xs font-semibold ${isPass ? 'text-teal-400' : isFail ? 'text-red-400' : 'text-amber-400'}`}>
        {typeof value === 'string' ? value : value ? 'POSITIVE' : 'NEGATIVE'}
      </p>
    </div>
  )
}

function ModalityCard({ label, score, rationale }) {
  const pct = ((score || 0) * 100).toFixed(0)
  return (
    <div className="bg-slate-800/20 border border-slate-700/10 rounded-lg p-3 text-center">
      <p className="text-[10px] text-slate-500 uppercase mb-1">{label}</p>
      <p className={`text-lg font-bold font-mono ${score >= 0.6 ? 'text-teal-400' : score >= 0.3 ? 'text-amber-400' : 'text-slate-500'}`}>
        {pct}%
      </p>
      {rationale && <p className="text-[10px] text-slate-500 mt-1 leading-tight">{rationale}</p>}
    </div>
  )
}

function SmallStat({ label, value, color }) {
  return (
    <div className="bg-slate-800/20 border border-slate-700/10 rounded-lg p-3">
      <p className="text-[10px] text-slate-500 uppercase mb-0.5">{label}</p>
      <p className={`text-sm font-bold font-mono ${color === 'teal' ? 'text-teal-400' : 'text-slate-200'}`}>{value}</p>
    </div>
  )
}
