// Importamos el store global para leer y actualizar el estado de la aplicación
import { useStore } from '../../store/useStore'

// Declaramos la lista de tipos de cliente disponibles para cambiar la perspectiva del reporte
const CLIENTES = [
  { key: 'videovigilancia', label: 'Videovigilancia', icon: '📷', desc: 'Instaladoras de cámaras' },
  { key: 'constructora',    label: 'Constructora',    icon: '🏗️', desc: 'Licitación de obra pública' },
  { key: 'inmobiliaria',    label: 'Inmobiliaria',    icon: '🏢', desc: 'Desarrolladoras de proyectos' },
]

// Retornamos el color correspondiente al SSU usando los mismos umbrales del backend
const SSU_COLOR = (ssu) => {
  if (ssu >= 75) return '#1D9E75'  // Seguridad optima
  if (ssu >= 50) return '#EF9F27'  // Seguridad aceptable
  if (ssu >= 30) return '#E24B4A'  // Seguridad deficiente
  return '#7B1C1C'                 // Zona critica
}

// Declaramos el componente SidebarPanel que muestra estadísticas, selector de cliente y ranking
export default function SidebarPanel() {
  // Leemos las estadísticas globales para los contadores de activos de campo
  const stats = useStore(s => s.stats)
  // Leemos la lista de zonas para construir el ranking ordenado por SSU
  const zonas = useStore(s => s.zonas)
  // Leemos el cliente actualmente seleccionado para destacar su botón
  const clienteFoco = useStore(s => s.clienteFoco)
  // Obtenemos la acción para cambiar el tipo de cliente activo
  const setClienteFoco = useStore(s => s.setClienteFoco)
  // Obtenemos la acción para seleccionar una zona al hacer clic en el ranking
  const setZonaSeleccionada = useStore(s => s.setZonaSeleccionada)
  // Leemos la zona seleccionada para resaltarla visualmente en el ranking
  const zonaSeleccionada = useStore(s => s.zonaSeleccionada)

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 34, height: 34, borderRadius: 8, background: '#185FA5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>🔐</div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 800, color: '#e8eaf0', letterSpacing: '-0.01em' }}>URBANIA</div>
          <div style={{ fontSize: 10, color: '#8b91a8', letterSpacing: '0.07em' }}>SEGURIDAD URBANA</div>
        </div>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Stats globales */}
      {stats && (
        <div>
          <Label>Base de datos de campo</Label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 6 }}>
            <StatCard value={stats.luminarias?.total || 0}    label="Luminarias"       sub={`${stats.luminarias?.funcionando || 0} ok`} color="#EF9F27" />
            <StatCard value={stats.puntos_ciegos?.total || 0} label="P. Ciegos"         sub={`${stats.puntos_ciegos?.criticos || 0} críticos`} color="#E24B4A" />
            <StatCard value={stats.terrenos_abandonados || 0} label="Terrenos"          sub="verificados" color="#7B1C1C" />
            <StatCard value={stats.zonas_auditadas || 0}      label="Zonas auditadas"   sub="campo XOLUM" color="#185FA5" />
          </div>
          <div style={{
            marginTop: 8, padding: '5px 10px', borderRadius: 6,
            background: 'rgba(29,158,117,0.1)', border: '1px solid rgba(29,158,117,0.2)',
            fontSize: 10, color: '#1D9E75',
          }}>
            🔒 Datos propios — no gubernamentales
          </div>
        </div>
      )}

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Selector de cliente */}
      <div>
        <Label>Perspectiva de cliente</Label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
          {CLIENTES.map(c => (
            <button key={c.key} onClick={() => setClienteFoco(c.key)} style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px',
              borderRadius: 8, textAlign: 'left',
              border: clienteFoco === c.key ? '1px solid #185FA544' : '1px solid rgba(255,255,255,0.07)',
              background: clienteFoco === c.key ? 'rgba(24,95,165,0.18)' : 'rgba(255,255,255,0.02)',
              color: clienteFoco === c.key ? '#e8eaf0' : '#8b91a8',
              cursor: 'pointer', transition: 'all 0.15s',
            }}>
              <span style={{ fontSize: 16 }}>{c.icon}</span>
              <div>
                <div style={{ fontSize: 12, fontWeight: clienteFoco === c.key ? 700 : 400 }}>{c.label}</div>
                <div style={{ fontSize: 10, color: '#4a5068' }}>{c.desc}</div>
              </div>
              {clienteFoco === c.key && <span style={{ marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%', background: '#185FA5' }} />}
            </button>
          ))}
        </div>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Ranking de zonas */}
      <div style={{ flex: 1 }}>
        <Label>Ranking de zonas</Label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
          {zonas.map((z, i) => (
            <button key={z.zona_id} onClick={() => setZonaSeleccionada(z)} style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
              borderRadius: 7, textAlign: 'left', width: '100%',
              border: zonaSeleccionada?.id === z.zona_id ? '1px solid rgba(24,95,165,0.4)' : '1px solid rgba(255,255,255,0.05)',
              background: zonaSeleccionada?.id === z.zona_id ? 'rgba(24,95,165,0.12)' : 'rgba(255,255,255,0.02)',
              cursor: 'pointer', transition: 'all 0.12s',
            }}>
              <span style={{ fontSize: 10, color: '#4a5068', minWidth: 16, textAlign: 'center' }}>{i + 1}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: '#b0b6c8', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {z.nombre}
                </div>
                <div style={{ fontSize: 10, color: '#4a5068' }}>{z.alcaldia}</div>
              </div>
              <div style={{
                fontSize: 13, fontWeight: 800, color: SSU_COLOR(z.ssu),
                minWidth: 36, textAlign: 'right',
              }}>
                {z.ssu?.toFixed(0)}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* IBM badge */}
      <div style={{
        padding: '8px 10px', borderRadius: 8, marginTop: 4,
        background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 10, color: '#8b91a8' }}>Powered by</div>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#7ab3f0' }}>IBM Watsonx AI</div>
        <div style={{ fontSize: 10, color: '#4a5068' }}>Granite 3-8B · IBM Cloud</div>
      </div>
    </div>
  )
}

function Label({ children }) {
  return <div style={{ fontSize: 10, fontWeight: 600, color: '#8b91a8', letterSpacing: '0.07em', textTransform: 'uppercase' }}>{children}</div>
}

function StatCard({ value, label, sub, color }) {
  return (
    <div style={{
      background: `${color}12`, border: `1px solid ${color}28`,
      borderRadius: 8, padding: '8px 10px',
    }}>
      <div style={{ fontSize: 20, fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 11, color: '#b0b6c8', marginTop: 2 }}>{label}</div>
      <div style={{ fontSize: 10, color: '#4a5068' }}>{sub}</div>
    </div>
  )
}
