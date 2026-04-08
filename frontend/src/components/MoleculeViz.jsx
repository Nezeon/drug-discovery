/**
 * MoleculeViz — Animated SVG molecular structure for the landing hero.
 * Renders a stylized drug-like molecule (quinazoline derivative) with
 * glowing heteroatoms, animated bonds, and floating effect.
 */

const ATOMS = [
  // Ring 1 (left hexagon)
  { x: 100, y: 95,  type: 'C' },   // 0
  { x: 130, y: 75,  type: 'C' },   // 1
  { x: 160, y: 95,  type: 'N' },   // 2
  { x: 160, y: 135, type: 'C' },   // 3
  { x: 130, y: 155, type: 'C' },   // 4
  { x: 100, y: 135, type: 'C' },   // 5
  // Ring 2 (right hexagon, fused)
  { x: 190, y: 75,  type: 'C' },   // 6
  { x: 220, y: 95,  type: 'C' },   // 7
  { x: 220, y: 135, type: 'C' },   // 8
  { x: 190, y: 155, type: 'C' },   // 9
  // Branches
  { x: 70,  y: 75,  type: 'O' },   // 10 — oxygen branch
  { x: 130, y: 40,  type: 'N' },   // 11 — amine branch
  { x: 250, y: 75,  type: 'O' },   // 12 — carbonyl
  { x: 130, y: 190, type: 'F' },   // 13 — fluorine
  // Extended chain
  { x: 100, y: 25,  type: 'C' },   // 14
  { x: 160, y: 25,  type: 'C' },   // 15
  { x: 280, y: 95,  type: 'C' },   // 16
  { x: 280, y: 135, type: 'N' },   // 17
]

const BONDS = [
  // Ring 1
  [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0],
  // Ring 2
  [2, 6], [6, 7], [7, 8], [8, 9], [9, 3],
  // Branches
  [0, 10], [1, 11], [7, 12], [4, 13],
  // Extended
  [11, 14], [11, 15], [12, 16], [16, 17],
]

const DOUBLE_BONDS = new Set(['1-2', '3-4', '6-7', '8-9', '7-12'])

const ATOM_COLORS = {
  C: '#00D8A4',
  N: '#5B9CF6',
  O: '#F5B731',
  F: '#A78BFA',
}

const ATOM_GLOW = {
  C: 'rgba(0, 216, 164, 0.3)',
  N: 'rgba(91, 156, 246, 0.4)',
  O: 'rgba(245, 183, 49, 0.4)',
  F: 'rgba(167, 139, 250, 0.4)',
}

export default function MoleculeViz({ className = '' }) {
  return (
    <div className={`animate-float-slow ${className}`}>
      <svg
        viewBox="0 0 350 230"
        className="w-full h-full max-w-md"
        style={{ filter: 'drop-shadow(0 0 40px rgba(0, 216, 164, 0.06))' }}
      >
        <defs>
          {/* Glow filters for each atom type */}
          {Object.entries(ATOM_GLOW).map(([type, color]) => (
            <filter key={type} id={`glow-${type}`} x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
              <feFlood floodColor={color} result="color" />
              <feComposite in="color" in2="blur" operator="in" result="glow" />
              <feMerge>
                <feMergeNode in="glow" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          ))}
        </defs>

        {/* Bonds */}
        {BONDS.map(([a, b], i) => {
          const from = ATOMS[a]
          const to = ATOMS[b]
          const key = `${Math.min(a,b)}-${Math.max(a,b)}`
          const isDouble = DOUBLE_BONDS.has(key)

          if (isDouble) {
            const dx = to.x - from.x
            const dy = to.y - from.y
            const len = Math.sqrt(dx*dx + dy*dy)
            const ox = (-dy / len) * 2.5
            const oy = (dx / len) * 2.5
            return (
              <g key={i}>
                <line
                  x1={from.x + ox} y1={from.y + oy}
                  x2={to.x + ox} y2={to.y + oy}
                  stroke="#00D8A4" strokeWidth="1.2" opacity="0.25"
                  className="mol-bond"
                />
                <line
                  x1={from.x - ox} y1={from.y - oy}
                  x2={to.x - ox} y2={to.y - oy}
                  stroke="#00D8A4" strokeWidth="1.2" opacity="0.25"
                  className="mol-bond"
                />
              </g>
            )
          }

          return (
            <line
              key={i}
              x1={from.x} y1={from.y}
              x2={to.x} y2={to.y}
              stroke="#00D8A4" strokeWidth="1.2" opacity="0.2"
              className="mol-bond"
            />
          )
        })}

        {/* Atom glow halos */}
        {ATOMS.map((atom, i) => {
          if (atom.type === 'C') return null
          return (
            <circle
              key={`glow-${i}`}
              cx={atom.x} cy={atom.y}
              r="8"
              fill={ATOM_GLOW[atom.type]}
              opacity="0.3"
              className="mol-atom-glow"
            >
              <animate
                attributeName="r"
                values="6;10;6"
                dur={`${2.5 + i * 0.3}s`}
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="0.2;0.4;0.2"
                dur={`${2.5 + i * 0.3}s`}
                repeatCount="indefinite"
              />
            </circle>
          )
        })}

        {/* Atoms */}
        {ATOMS.map((atom, i) => {
          const color = ATOM_COLORS[atom.type]
          const r = atom.type === 'C' ? 3 : 4.5
          return (
            <circle
              key={`atom-${i}`}
              cx={atom.x} cy={atom.y}
              r={r}
              fill={color}
              opacity={atom.type === 'C' ? 0.5 : 0.85}
              filter={atom.type !== 'C' ? `url(#glow-${atom.type})` : undefined}
              className="mol-atom"
            >
              <animate
                attributeName="opacity"
                values={atom.type === 'C' ? '0.4;0.6;0.4' : '0.7;1;0.7'}
                dur={`${3 + i * 0.2}s`}
                repeatCount="indefinite"
              />
            </circle>
          )
        })}

        {/* Heteroatom labels */}
        {ATOMS.map((atom, i) => {
          if (atom.type === 'C') return null
          return (
            <text
              key={`label-${i}`}
              x={atom.x}
              y={atom.y + 1}
              textAnchor="middle"
              dominantBaseline="central"
              fill={ATOM_COLORS[atom.type]}
              fontSize="7"
              fontFamily="var(--font-mono)"
              fontWeight="600"
              opacity="0.7"
            >
              {atom.type}
            </text>
          )
        })}
      </svg>
    </div>
  )
}
