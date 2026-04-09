import { useStore } from '../../store/useStore'
import { getReporte } from '../../services/api'
import { useState } from 'react'

const SSU_COLOR = (ssu) => {
  if (ssu >= 75) return '#1D9E75'
  if (ssu >= 50) return '#EF9F27'
  if (ssu >= 30) return '#E24B4A'
  return '#7B1C1C'
}

const CLIENTE_KEY = {
  videovigilancia: 'empresa_videovigilancia',
  constructora: 'constructora_gobierno',
  inmobiliaria: 'desarrolladora_inmobiliaria',
}

export default function ResultsPanel() {
  const zonaSeleccionada = useStore(s => s.zonaSeleccionada)
  const zonas = useStore(s => s.zonas)
  const clienteFoco = useStore(s => s.clienteFoco)
  const [reporte, setReporte] = useState(null)
  const [loadingReporte, setLoadingReporte] = useState(false)

  const zona = zonaSeleccionada
    ? zonas.find(z => z.zona_id === zonaSeleccionada.id) || null
    : null

  const handleReporte = async () => {
    if (!zona) return
    setLoadingReporte(true)
    try {
      const data = await getReporte(zona.zona_id, clienteFoco)
      setReporte(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingReporte(false)
    }
  }

  if (!zonaSeleccionada && !zona) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, gap: 12 }}>
        <div style={{ fontSize: 40 }}>🔐</div>
        <div style={{ fontSize: 13, color: '#8b91a8', textAlign: 'center', lineHeight: 1.6 }}>
          Haz clic en una zona del mapa para ver el análisis de seguridad
        </div>
        <div style={{ fontSize: 11, color: '#4a5068', textAlign: 'center' }}>
          Datos verificados en campo por equipo XOLUM
        </div>
      </div>
    )
  }

  const data = zona || zonaSeleccionada
  const ssu = data.ssu ?? data.score_seguridad ?? 0
  const bd = data.breakdown || {}

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Zona header */}
      <div>
        <div style={{ fontSize: 16, fontWeight: 800, color: '#e8eaf0' }}>{data.nombre}</div>
        <div style={{ fontSize: 11, color: '#8b91a8' }}>{data.alcaldia} · {data.colonia || data.fecha_auditoria || ''}</div>
      </div>

      {/* SSU grande */}
      <div style={{
        background: `${SSU_COLOR(ssu)}14`, border: `1px solid ${SSU_COLOR(ssu)}30`,
        borderRadius: 12, padding: '14px 16px', textAlign: 'center',
      }}>
        <div style={{ fontSize: 48, fontWeight: 900, color: SSU_COLOR(ssu), lineHeight: 1 }}>
          {ssu.toFixed(0)}
        </div>
        <div style={{ fontSize: 11, color: '#8b91a8', marginTop: 2 }}>Score de Seguridad Urbana / 100</div>
        <div style={{ fontSize: 13, fontWeight: 700, color: SSU_COLOR(ssu), marginTop: 6 }}>
          {data.clasificacion_label || data.clasificacion || '—'}
        </div>
        {data.accion_recomendada && (
          <div style={{ fontSize: 11, color: '#8b91a8', marginTop: 4 }}>{data.accion_recomendada}</div>
        )}
      </div>

      {/* Breakdown de scores */}
      {bd.iluminacion && (
        <div>
          <SectionTitle>Breakdown por componente</SectionTitle>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
            <ScoreBar label="💡 Iluminación (35%)"    score={bd.iluminacion?.score}    detalle={bd.iluminacion?.detalle} />
            <ScoreBar label="📷 Cobertura Cámara (30%)" score={bd.cobertura_camara?.score} detalle={bd.cobertura_camara?.detalle} />
            <ScoreBar label="🏗️ Infraestructura (20%)" score={bd.infraestructura?.score}  detalle={bd.infraestructura?.detalle} />
            <ScoreBar label="🏘️ Entorno (15%)"        score={bd.entorno?.score}         detalle={bd.entorno?.detalle} />
          </div>
        </div>
      )}

      {/* Datos de campo */}
      <div>
        <SectionTitle>Activos verificados en campo</SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginTop: 6 }}>
          <MiniStat icon="💡" value={bd.iluminacion?.ok ?? data.n_luminarias_ok ?? '—'} label="Luminarias ok" color="#EF9F27" />
          <MiniStat icon="📷" value={bd.cobertura_camara?.n_puntos_ciegos ?? data.n_puntos_ciegos ?? '—'} label="P. ciegos" color="#E24B4A" />
          <MiniStat icon="🏚️" value={bd.infraestructura?.n_terrenos_abandonados ?? data.n_terrenos ?? '—'} label="Terrenos" color="#7B1C1C" />
        </div>
        <div style={{ marginTop: 6, fontSize: 10, color: '#1D9E75' }}>
          🔒 Datos campo XOLUM — verificados in situ, no gubernamentales
        </div>
      </div>

      {/* Botón reporte por cliente */}
      <div>
        <SectionTitle>Reporte por cliente</SectionTitle>
        <button onClick={handleReporte} disabled={loadingReporte || !zona} style={{
          width: '100%', marginTop: 6, padding: '9px 14px', borderRadius: 8,
          border: 'none', background: loadingReporte ? '#2a2d3a' : '#185FA5',
          color: loadingReporte ? '#8b91a8' : '#fff',
          cursor: loadingReporte ? 'not-allowed' : 'pointer',
          fontSize: 12, fontWeight: 700,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
        }}>
          {loadingReporte ? '⏳ Generando...' : `📋 Reporte para ${clienteFoco}`}
        </button>
      </div>

      {/* Reporte generado */}
      {reporte && (
        <div style={{
          background: 'rgba(24,95,165,0.08)', border: '1px solid rgba(24,95,165,0.2)',
          borderRadius: 10, padding: '12px 14px',
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#7ab3f0', marginBottom: 8 }}>
            {reporte.reporte?.titulo}
          </div>
          <div style={{ fontSize: 11, color: '#b0b6c8', lineHeight: 1.6, marginBottom: 10 }}>
            {reporte.reporte?.oportunidad}
          </div>
          {reporte.reporte?.puntos_clave?.map((p, i) => (
            <div key={i} style={{ display: 'flex', gap: 7, marginBottom: 5 }}>
              <span style={{ color: '#185FA5', flexShrink: 0, fontSize: 10 }}>•</span>
              <span style={{ fontSize: 11, color: '#8b91a8', lineHeight: 1.5 }}>{p}</span>
            </div>
          ))}
          {reporte.reporte?.alerta && (
            <div style={{
              marginTop: 8, padding: '6px 10px', borderRadius: 6,
              background: 'rgba(226,75,74,0.1)', border: '1px solid rgba(226,75,74,0.3)',
              fontSize: 11, color: '#E24B4A',
            }}>
              ⚠ {reporte.reporte.alerta}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SectionTitle({ children }) {
  return <div style={{ fontSize: 10, fontWeight: 600, color: '#8b91a8', letterSpacing: '0.07em', textTransform: 'uppercase' }}>{children}</div>
}

function ScoreBar({ label, score, detalle }) {
  const s = score ?? 0
  const color = s >= 75 ? '#1D9E75' : s >= 50 ? '#EF9F27' : s >= 30 ? '#E24B4A' : '#7B1C1C'
  return (
    <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 7, padding: '8px 10px', border: '1px solid rgba(255,255,255,0.05)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
        <span style={{ fontSize: 11, color: '#b0b6c8' }}>{label}</span>
        <span style={{ fontSize: 14, fontWeight: 800, color }}>{s.toFixed(0)}</span>
      </div>
      <div style={{ height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2 }}>
        <div style={{ height: 4, borderRadius: 2, background: color, width: `${s}%`, transition: 'width 0.5s ease' }} />
      </div>
      {detalle && <div style={{ fontSize: 10, color: '#4a5068', marginTop: 4 }}>{detalle}</div>}
    </div>
  )
}

function MiniStat({ icon, value, label, color }) {
  return (
    <div style={{ background: `${color}12`, border: `1px solid ${color}28`, borderRadius: 7, padding: '7px 8px', textAlign: 'center' }}>
      <div style={{ fontSize: 16 }}>{icon}</div>
      <div style={{ fontSize: 16, fontWeight: 800, color, lineHeight: 1.2 }}>{value}</div>
      <div style={{ fontSize: 9, color: '#4a5068' }}>{label}</div>
    </div>
  )
}
