import { useEffect, useState } from 'react'

export default function ScoreRing({
  score = 0,
  size = 80,
  strokeWidth = 4,
  label,
  showPercent = true,
  colorMode = 'auto',
  animate = true,
  delay = 0,
  className = '',
}) {
  const [mounted, setMounted] = useState(false)

  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const pct = Math.min(Math.max(score, 0), 1)
  const offset = circumference - pct * circumference

  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), delay)
    return () => clearTimeout(timer)
  }, [delay])

  const color = colorMode === 'auto'
    ? pct >= 0.7 ? '#00D8A4' : pct >= 0.4 ? '#F5B731' : '#F06868'
    : colorMode === 'emerald' ? '#00D8A4'
    : colorMode === 'gold' ? '#F5B731'
    : colorMode === 'violet' ? '#8B5CF6'
    : '#00D8A4'

  const glowColor = colorMode === 'auto'
    ? pct >= 0.7 ? 'rgba(0, 216, 164, 0.25)' : pct >= 0.4 ? 'rgba(245, 183, 49, 0.25)' : 'rgba(240, 104, 104, 0.25)'
    : colorMode === 'emerald' ? 'rgba(0, 216, 164, 0.25)'
    : colorMode === 'gold' ? 'rgba(245, 183, 49, 0.25)'
    : colorMode === 'violet' ? 'rgba(139, 92, 246, 0.25)'
    : 'rgba(0, 216, 164, 0.25)'

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke="#19191C"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={mounted && animate ? offset : circumference}
          style={{
            transition: 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)',
            filter: `drop-shadow(0 0 6px ${glowColor})`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {showPercent && (
          <span
            className="font-mono font-semibold text-slate-50"
            style={{ fontSize: size * 0.22 }}
          >
            {Math.round(pct * 100)}
          </span>
        )}
        {label && (
          <span
            className="text-slate-500 font-medium"
            style={{ fontSize: Math.max(size * 0.11, 9) }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  )
}
