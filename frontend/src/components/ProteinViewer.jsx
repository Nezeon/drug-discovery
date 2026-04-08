import { useEffect, useRef, useState, useCallback } from 'react'
import { Box, Maximize2, Minimize2, RotateCcw, Pause } from 'lucide-react'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const CDN = 'https://3Dmol.org/build/3Dmol-min.js'

let _p = null
function load3Dmol() {
  if (window.$3Dmol) return Promise.resolve(window.$3Dmol)
  if (_p) return _p
  _p = new Promise((res, rej) => {
    const s = document.createElement('script')
    s.src = CDN; s.async = true
    s.onload = () => window.$3Dmol ? res(window.$3Dmol) : rej(new Error('3Dmol init failed'))
    s.onerror = () => rej(new Error('CDN load failed'))
    document.head.appendChild(s)
  })
  return _p
}

function waitForLayout(el, ms = 4000) {
  return new Promise((res, rej) => {
    const t0 = Date.now()
    ;(function poll() {
      if (el.clientWidth > 10 && el.clientHeight > 10) return res()
      if (Date.now() - t0 > ms) return rej(new Error('Zero-size container'))
      requestAnimationFrame(poll)
    })()
  })
}

export default function ProteinViewer({ jobId, className = '' }) {
  const boxRef = useRef(null)
  const viewerRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(false)
  const [spinning, setSpinning] = useState(true)

  const build = useCallback(async () => {
    const el = boxRef.current
    if (!el || !jobId) return
    try {
      setLoading(true); setError(null)
      await waitForLayout(el)

      const $3Dmol = await load3Dmol()

      const r = await fetch(`${BASE_URL}/api/protein/pdb/${jobId}`)
      if (!r.ok) throw new Error('PDB not available')
      const pdb = await r.text()

      // Tear down old viewer
      if (viewerRef.current) { try { viewerRef.current.clear() } catch {} }
      el.innerHTML = ''

      const viewer = $3Dmol.createViewer(el, {
        backgroundColor: '#0e0e10',
        antialias: true,
      })
      viewerRef.current = viewer

      viewer.addModel(pdb, 'pdb')

      // Simple, reliable cartoon colored by chain spectrum
      viewer.setStyle({}, {
        cartoon: { color: 'spectrum', opacity: 0.95 },
      })

      // Highlight hetero atoms (ligands, waters, ions) as sticks
      viewer.setStyle({ hetflag: true }, {
        stick: { radius: 0.15, colorscheme: 'Jmol' },
        sphere: { radius: 0.4, colorscheme: 'Jmol' },
      })

      viewer.zoomTo()
      viewer.spin('y', 0.5)
      viewer.render()

      setSpinning(true)
      setLoading(false)
    } catch (e) {
      console.error('ProteinViewer:', e)
      setError(e.message)
      setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    build()
    return () => {
      if (viewerRef.current) {
        try { viewerRef.current.spin(false); viewerRef.current.clear() } catch {}
        viewerRef.current = null
      }
    }
  }, [build])

  // Resize on expand/collapse
  useEffect(() => {
    const t = setTimeout(() => {
      if (viewerRef.current) {
        try { viewerRef.current.resize(); viewerRef.current.render() } catch {}
      }
    }, 400)
    return () => clearTimeout(t)
  }, [expanded])

  function handleReset() {
    if (!viewerRef.current) return
    viewerRef.current.zoomTo()
    viewerRef.current.spin('y', 0.5)
    viewerRef.current.render()
    setSpinning(true)
  }

  function toggleSpin() {
    if (!viewerRef.current) return
    if (spinning) {
      viewerRef.current.spin(false)
    } else {
      viewerRef.current.spin('y', 0.5)
    }
    viewerRef.current.render()
    setSpinning(s => !s)
  }

  if (error) {
    return (
      <div className={`card p-5 ${className}`}>
        <div className="flex items-center gap-2.5 mb-3">
          <IconBadge />
          <h3 className="text-sm font-semibold font-display text-slate-100">3D Protein Structure</h3>
        </div>
        <p className="text-xs text-slate-500">Visualization unavailable — {error}</p>
      </div>
    )
  }

  return (
    <div className={`card overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/40">
        <div className="flex items-center gap-2.5">
          <IconBadge />
          <h3 className="text-sm font-semibold font-display text-slate-100">3D Protein Structure</h3>
          {!loading && <span className="text-[10px] text-slate-500 ml-1">Interactive</span>}
        </div>
        <div className="flex items-center gap-1">
          <Btn onClick={toggleSpin} title={spinning ? 'Stop spin' : 'Start spin'}>
            <Pause className={`w-3.5 h-3.5 ${spinning ? 'text-teal-400' : ''}`} />
          </Btn>
          <Btn onClick={handleReset} title="Reset view"><RotateCcw className="w-3.5 h-3.5" /></Btn>
          <Btn onClick={() => setExpanded(v => !v)} title={expanded ? 'Shrink' : 'Expand'}>
            {expanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </Btn>
        </div>
      </div>

      {/* Viewport */}
      <div style={{ height: expanded ? 520 : 340, position: 'relative', transition: 'height 0.3s ease' }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10" style={{ background: '#0e0e10' }}>
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-slate-500">Loading protein structure...</span>
            </div>
          </div>
        )}
        <div ref={boxRef} style={{ width: '100%', height: '100%', position: 'relative' }} />
      </div>

      {/* Footer */}
      <div className="flex items-center gap-4 px-5 py-2 border-t border-slate-800/40">
        <span className="text-[10px] text-slate-500">Rainbow: N-terminus → C-terminus</span>
        <span className="text-[10px] text-slate-600 ml-auto">Drag to rotate · Scroll to zoom · Right-drag to pan</span>
      </div>
    </div>
  )
}

function IconBadge() {
  return (
    <div className="w-7 h-7 rounded-lg bg-violet-500/10 flex items-center justify-center">
      <Box className="w-3.5 h-3.5 text-violet-400" />
    </div>
  )
}

function Btn({ onClick, title, children }) {
  return (
    <button onClick={onClick} title={title} className="p-1.5 rounded-lg hover:bg-slate-800/40 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer">
      {children}
    </button>
  )
}
