import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer,
} from 'recharts'

const VERDICT_SCORE = { PASS: 85, WARN: 50, FAIL: 15 }

function toScore(val) {
  if (typeof val === 'number') return Math.round(val * 100)
  return VERDICT_SCORE[val] ?? 50
}

export default function AdmetRadar({ admetDetail }) {
  if (!admetDetail) return null

  const data = [
    { axis: 'Absorption', value: toScore(admetDetail.absorption), fullMark: 100 },
    { axis: 'Distribution', value: toScore(admetDetail.distribution ?? admetDetail.bbb), fullMark: 100 },
    { axis: 'Metabolism', value: toScore(admetDetail.metabolism), fullMark: 100 },
    { axis: 'Excretion', value: toScore(admetDetail.excretion), fullMark: 100 },
    { axis: 'Cardio', value: toScore(admetDetail.herg ?? admetDetail.cardio), fullMark: 100 },
    { axis: 'Liver', value: toScore(admetDetail.dili ?? admetDetail.hepatotoxicity ?? admetDetail.ames), fullMark: 100 },
  ]

  return (
    <div className="relative">
      <p className="text-xs text-slate-500 font-medium mb-2">ADMET Profile</p>
      <div className="card p-3">
        <ResponsiveContainer width="100%" height={200}>
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
            <PolarGrid stroke="rgba(35, 35, 39, 0.6)" strokeDasharray="3 3" />
            <PolarAngleAxis
              dataKey="axis"
              tick={{ fill: '#555559', fontSize: 10, fontWeight: 500 }}
            />
            <defs>
              <linearGradient id="radarFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00D8A4" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#00B88B" stopOpacity={0.08} />
              </linearGradient>
            </defs>
            <Radar
              name="ADMET"
              dataKey="value"
              stroke="#00D8A4"
              fill="url(#radarFill)"
              strokeWidth={1.5}
              dot={{ r: 3, fill: '#00D8A4', stroke: '#111113', strokeWidth: 1.5 }}
              activeDot={{ r: 5, fill: '#00D8A4', stroke: 'rgba(0, 216, 164, 0.3)', strokeWidth: 4 }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
