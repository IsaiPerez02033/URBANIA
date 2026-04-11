// Importamos useEffect y useState para manejar el ciclo de vida y estado local del componente
import { useEffect, useState } from 'react'
// Importamos el store global para leer el estado de error y estadísticas
import { useStore } from '../../store/useStore'
// Importamos la función de la API para verificar el estado del backend
import { getHealth } from '../../services/api'

// Declaramos el componente TopBar que muestra el encabezado principal del dashboard
export default function TopBar() {
  // Leemos el mensaje de error global del store para mostrarlo en la barra si existe
  const error = useStore(s => s.error)
  // Leemos las estadísticas globales de campo para mostrar conteos en el encabezado
  const stats = useStore(s => s.stats)
  // Declaramos el estado local para almacenar el resultado del health check del backend
  const [health, setHealth] = useState(null)

  // Ejecutamos el health check al montar el componente para mostrar el estado de la API
  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ status: 'error' }))
  }, [])

  return (
    // Renderizamos la barra superior fija con fondo oscuro semitransparente y blur de fondo
    <div style={{
      height: 44, flexShrink: 0,
      background: 'rgba(15,17,23,0.97)', backdropFilter: 'blur(8px)',
      borderBottom: '1px solid rgba(255,255,255,0.07)',
      display: 'flex', alignItems: 'center',
      padding: '0 16px', gap: 12, zIndex: 100,
    }}>
      {/* Logotipo de SUSVI con ícono de seguridad y badge de módulo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 26, height: 26, borderRadius: 6, background: '#185FA5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>🔐</div>
        <span style={{ fontSize: 15, fontWeight: 800, color: '#e8eaf0', letterSpacing: '-0.01em' }}>SUSVI</span>
        {/* Badge identificador del módulo de seguridad */}
        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'rgba(24,95,165,0.3)', color: '#7ab3f0', fontWeight: 600 }}>SEGURIDAD</span>
      </div>

      {/* Separador vertical entre el logo y el tagline */}
      <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.1)' }} />

      {/* Tagline de la plataforma con el contexto del piloto CDMX */}
      <div style={{ fontSize: 12, color: '#8b91a8' }}>
        Inteligencia de Seguridad Urbana · CDMX Piloto · Datos propios verificados en campo
      </div>

      {/* Resumen de estadísticas globales de campo, visible solo cuando las estadísticas están cargadas */}
      {stats && (
        <>
          <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.07)' }} />
          <div style={{ fontSize: 11, color: '#4a5068' }}>
            {stats.zonas_auditadas} zonas · {stats.luminarias?.total} luminarias · {stats.puntos_ciegos?.total} puntos ciegos
          </div>
        </>
      )}

      {/* Notificación de error global, visible solo cuando hay un error activo en el store */}
      {error && (
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, padding: '3px 10px', borderRadius: 6, background: 'rgba(226,75,74,0.15)', border: '1px solid rgba(226,75,74,0.3)', fontSize: 11, color: '#E24B4A' }}>
          {/* Truncamos el mensaje de error a 70 caracteres para que no desborde la barra */}
          ⚠ {error.slice(0, 70)}
        </div>
      )}

      {/* Sección derecha con el indicador de estado de la API y el crédito de XOLUM */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
        {/* Indicador de estado del backend con punto verde si OK o rojo si hay error */}
        {health && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: health.status === 'ok' ? '#1D9E75' : '#E24B4A' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: health.status === 'ok' ? '#1D9E75' : '#E24B4A' }} />
            API {health.status === 'ok' ? 'OK' : 'Error'}
          </div>
        )}
        {/* Crédito de XOLUM como propietario de los datos de campo */}
        <div style={{ fontSize: 11, color: '#4a5068' }}>XOLUM © 2026</div>
      </div>
    </div>
  )
}
