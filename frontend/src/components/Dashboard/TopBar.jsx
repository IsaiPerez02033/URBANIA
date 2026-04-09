import { useEffect, useState } from 'react'
import { useStore } from '../../store/useStore'
import { getHealth } from '../../services/api'

export default function TopBar() {
  const error = useStore(s => s.error)
  const stats = useStore(s => s.stats)
  const [health, setHealth] = useState(null)

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ status: 'error' }))
  }, [])

  return (
    <div style={{
      height: 44, flexShrink: 0,
      background: 'rgba(15,17,23,0.97)', backdropFilter: 'blur(8px)',
      borderBottom: '1px solid rgba(255,255,255,0.07)',
      display: 'flex', alignItems: 'center',
      padding: '0 16px', gap: 12, zIndex: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 26, height: 26, borderRadius: 6, background: '#185FA5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>🔐</div>
        <span style={{ fontSize: 15, fontWeight: 800, color: '#e8eaf0', letterSpacing: '-0.01em' }}>URBANIA</span>
        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'rgba(24,95,165,0.3)', color: '#7ab3f0', fontWeight: 600 }}>SEGURIDAD</span>
      </div>

      <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.1)' }} />

      <div style={{ fontSize: 12, color: '#8b91a8' }}>
        Inteligencia de Seguridad Urbana · CDMX Piloto · Datos propios verificados en campo
      </div>

      {stats && (
        <>
          <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.07)' }} />
          <div style={{ fontSize: 11, color: '#4a5068' }}>
            {stats.zonas_auditadas} zonas · {stats.luminarias?.total} luminarias · {stats.puntos_ciegos?.total} puntos ciegos
          </div>
        </>
      )}

      {error && (
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, padding: '3px 10px', borderRadius: 6, background: 'rgba(226,75,74,0.15)', border: '1px solid rgba(226,75,74,0.3)', fontSize: 11, color: '#E24B4A' }}>
          ⚠ {error.slice(0, 70)}
        </div>
      )}

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
        {health && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: health.status === 'ok' ? '#1D9E75' : '#E24B4A' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: health.status === 'ok' ? '#1D9E75' : '#E24B4A' }} />
            API {health.status === 'ok' ? 'OK' : 'Error'}
          </div>
        )}
        <div style={{ fontSize: 11, color: '#4a5068' }}>XOLUM © 2026</div>
      </div>
    </div>
  )
}
