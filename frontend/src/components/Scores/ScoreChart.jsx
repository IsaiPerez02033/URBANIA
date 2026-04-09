import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, ReferenceLine, Legend,
} from 'recharts'
import { useStore } from '../../store/useStore'

const COLORS = {
  demand: '#185FA5',
  risk: '#E24B4A',
  viability: '#1D9E75',
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1a1d27', border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8, padding: '8px 12px', fontSize: 12,
    }}>
      <div style={{ fontWeight: 700, color: '#e8eaf0', marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: <b>{Number(p.value).toFixed(0)}</b>
        </div>
      ))}
    </div>
  )
}

export default function ScoreChart() {
  const analysisResult = useStore(s => s.analysisResult)

  const data = useMemo(() => {
    if (!analysisResult) return []

    const demandMap = {}
    ;(analysisResult.demand_geojson?.features ?? []).forEach(f => {
      const p = f.properties ?? {}
      demandMap[p.id || f.id] = { nombre: p.nombre, demand: p.score_demanda }
    })

    const riskMap = {}
    ;(analysisResult.risk_geojson?.features ?? []).forEach(f => {
      const p = f.properties ?? {}
      riskMap[p.id || f.id] = p.score_riesgo
    })

    const viabilityMap = {}
    ;(analysisResult.viability_scores ?? []).forEach(v => {
      viabilityMap[v.id] = v.score_viabilidad
    })

    return Object.entries(demandMap)
      .map(([id, { nombre, demand }]) => ({
        id,
        nombre: nombre?.length > 14 ? nombre.slice(0, 13) + '…' : nombre,
        demand: demand != null ? Math.round(demand) : null,
        risk: riskMap[id] != null ? Math.round(riskMap[id]) : null,
        viability: viabilityMap[id] != null ? Math.round(viabilityMap[id]) : null,
      }))
      .filter(d => d.demand != null)
      .sort((a, b) => (b.viability ?? 0) - (a.viability ?? 0))
      .slice(0, 20) // top 20 para que el chart no sea ilegible
  }, [analysisResult])

  if (!analysisResult || data.length === 0) return null

  return (
    <div style={{
      background: '#1a1d27', borderTop: '1px solid rgba(255,255,255,0.07)',
      padding: '12px 16px',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 10,
      }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#8b91a8', letterSpacing: '0.06em' }}>
          RANKING DE ZONAS (TOP 20)
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          {[
            { key: 'viability', label: 'Viabilidad', color: COLORS.viability },
            { key: 'demand', label: 'Demanda', color: COLORS.demand },
            { key: 'risk', label: 'Riesgo', color: COLORS.risk },
          ].map(l => (
            <div key={l.key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: l.color }} />
              <span style={{ fontSize: 10, color: '#8b91a8' }}>{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }} barCategoryGap="20%">
          <XAxis
            dataKey="nombre"
            tick={{ fill: '#6b7280', fontSize: 9 }}
            axisLine={false}
            tickLine={false}
            interval={0}
            angle={-35}
            textAnchor="end"
            height={45}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#6b7280', fontSize: 9 }}
            axisLine={false}
            tickLine={false}
            ticks={[0, 30, 60, 100]}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
          <ReferenceLine y={70} stroke="rgba(29,158,117,0.3)" strokeDasharray="3 3" />
          <ReferenceLine y={40} stroke="rgba(239,159,39,0.3)" strokeDasharray="3 3" />
          <Bar dataKey="viability" name="Viabilidad" radius={[2, 2, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={
                  (entry.viability ?? 0) >= 70 ? COLORS.viability
                  : (entry.viability ?? 0) >= 40 ? '#EF9F27'
                  : COLORS.risk
                }
                fillOpacity={0.85}
              />
            ))}
          </Bar>
          <Bar dataKey="demand" name="Demanda" fill={COLORS.demand} fillOpacity={0.5} radius={[2, 2, 0, 0]} />
          <Bar dataKey="risk" name="Riesgo" fill={COLORS.risk} fillOpacity={0.4} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
