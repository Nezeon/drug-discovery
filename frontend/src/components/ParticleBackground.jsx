export default function ParticleBackground({ variant = 'default' }) {
  const orbs = variant === 'dense' ? DENSE_ORBS : DEFAULT_ORBS

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{ zIndex: 0 }}>
      {/* Base */}
      <div className="absolute inset-0" style={{ background: '#08080A' }} />

      {/* Orbs */}
      {orbs.map((orb, i) => (
        <div
          key={i}
          className={`absolute rounded-full ${orb.animation}`}
          style={{
            width: orb.size,
            height: orb.size,
            left: orb.x,
            top: orb.y,
            background: orb.color,
            opacity: orb.opacity,
            filter: `blur(${orb.blur || '0px'})`,
          }}
        />
      ))}

      {/* Grid pattern */}
      <div className="absolute inset-0 grid-pattern opacity-[0.03]" />

      {/* Vignette */}
      <div
        className="absolute inset-0"
        style={{ background: 'radial-gradient(ellipse at center, transparent 0%, #08080A 75%)' }}
      />
    </div>
  )
}

const DEFAULT_ORBS = [
  {
    size: '500px', x: '-5%', y: '-10%', blur: '80px',
    color: 'radial-gradient(circle, rgba(0, 216, 164, 0.07) 0%, transparent 70%)',
    opacity: 1, animation: 'animate-mesh',
  },
  {
    size: '400px', x: '60%', y: '15%', blur: '60px',
    color: 'radial-gradient(circle, rgba(245, 183, 49, 0.04) 0%, transparent 70%)',
    opacity: 1, animation: 'animate-mesh-reverse',
  },
  {
    size: '350px', x: '30%', y: '55%', blur: '70px',
    color: 'radial-gradient(circle, rgba(0, 184, 139, 0.05) 0%, transparent 70%)',
    opacity: 1, animation: 'animate-mesh-drift',
  },
]

const DENSE_ORBS = [
  {
    size: '600px', x: '-8%', y: '-12%', blur: '100px',
    color: 'radial-gradient(circle, rgba(0, 216, 164, 0.09) 0%, transparent 70%)',
    opacity: 1, animation: 'animate-mesh',
  },
  {
    size: '500px', x: '55%', y: '5%', blur: '80px',
    color: 'radial-gradient(circle, rgba(245, 183, 49, 0.05) 0%, transparent 70%)',
    opacity: 1, animation: 'animate-mesh-reverse',
  },
  {
    size: '450px', x: '15%', y: '50%', blur: '90px',
    color: 'radial-gradient(circle, rgba(0, 184, 139, 0.06) 0%, transparent 70%)',
    opacity: 1, animation: 'animate-mesh-drift',
  },
  {
    size: '300px', x: '75%', y: '60%', blur: '70px',
    color: 'radial-gradient(circle, rgba(139, 92, 246, 0.04) 0%, transparent 70%)',
    opacity: 1, animation: 'animate-mesh',
  },
]
