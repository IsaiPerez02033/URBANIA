// Importamos useMemo para calcular los datos del chart solo cuando cambian los resultados
import { useMemo } from 'react'
// Importamos los componentes de Recharts para construir la gráfica de barras
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, ReferenceLine, Legend,
} from 'recharts'
// Importamos el store global para leer los resultados del análisis territorial
import { useStore } from '../../store/useStore'

// Declaramos los colores de cada tipo de score en la gráfica de comparación
const COLORS = {
  demand: '#185FA5',    // Azul corporativo para el score de demanda
  risk: '#E24B4A',      // Rojo para el score de riesgo
  viability: '#1D9E75', // Verde para el score de viabilidad (resultado combinado)
}

// Declaramos el componente de tooltip personalizado que muestra los valores al hacer hover
const CustomTooltip = ({ active, payload, label }) => {
  // Solo renderizamos el tooltip si está activo y tiene datos para mostrar
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1a1d27', border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8, padding: '8px 12px', fontSize: 12,
    }}>
      {/* Mostramos el nombre de la zona como título del tooltip */}
      <div style={{ fontWeight: 700, color: '#e8eaf0', marginBottom: 4 }}>{label}</div>
      {/* Iteramos sobre cada serie de datos para mostrar su valor con el color correspondiente */}
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: <b>{Number(p.value).toFixed(0)}</b>
        </div>
      ))}
    </div>
  )
}

// Declaramos el componente ScoreChart que muestra el ranking comparativo de zonas
export default function ScoreChart() {
  // Leemos los resultados del análisis territorial del store
  const analysisResult = useStore(s => s.analysisResult)

  // Calculamos los datos del chart combinando demanda, riesgo y viabilidad por zona
  const data = useMemo(() => {
    if (!analysisResult) return []

    // Indexamos los scores de demanda por ID de zona para acceso eficiente
    const demandMap = {}
    ;(analysisResult.demand_geojson?.features ?? []).forEach(f => {
      const p = f.properties ?? {}
      demandMap[p.id || f.id] = { nombre: p.nombre, demand: p.score_demanda }
    })

    // Indexamos los scores de riesgo por ID de zona
    const riskMap = {}
    ;(analysisResult.risk_geojson?.features ?? []).forEach(f => {
      const p = f.properties ?? {}
      riskMap[p.id || f.id] = p.score_riesgo
    })

    // Indexamos los scores de viabilidad por ID de zona
    const viabilityMap = {}
    ;(analysisResult.viability_scores ?? []).forEach(v => {
      viabilityMap[v.id] = v.score_viabilidad
    })

    // Construimos el array de datos del chart combinando los tres scores por zona
    return Object.entries(demandMap)
      .map(([id, { nombre, demand }]) => ({
        id,
        // Truncamos el nombre si es muy largo para que no desborde en el eje X
        nombre: nombre?.length > 14 ? nombre.slice(0, 13) + '…' : nombre,
        demand: demand != null ? Math.round(demand) : null,
        risk: riskMap[id] != null ? Math.round(riskMap[id]) : null,
        viability: viabilityMap[id] != null ? Math.round(viabilityMap[id]) : null,
      }))
      // Filtramos zonas que no tienen score de demanda para evitar barras vacías
      .filter(d => d.demand != null)
      // Ordenamos de mayor a menor viabilidad para el ranking visual
      .sort((a, b) => (b.viability ?? 0) - (a.viability ?? 0))
      // Limitamos a las 20 mejores zonas para mantener la legibilidad de la gráfica
      .slice(0, 20)
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
