// Importamos el store global para leer y actualizar la capa activa del mapa
import { useStore } from '../../store/useStore'

// Declaramos la lista de capas disponibles con sus colores y descripciones para el control
const CAPAS = [
  { key: 'ssu',             label: 'SSU Total',       color: '#185FA5', desc: 'Score Seguridad Urbana' },
  { key: 'iluminacion',     label: 'Iluminación',     color: '#EF9F27', desc: 'Luminarias de campo' },
  { key: 'cobertura',       label: 'Cámaras',         color: '#E24B4A', desc: 'Puntos ciegos' },
  { key: 'infraestructura', label: 'Infraestructura', color: '#1D9E75', desc: 'Terrenos y vialidad' },
]

// Declaramos el componente LayerControl que flota sobre el mapa para cambiar la capa visible
export default function LayerControl() {
  // Leemos la capa actualmente seleccionada para resaltar su botón correspondiente
  const capaActiva = useStore(s => s.capaActiva)
  // Obtenemos la acción para cambiar la capa activa en el store global
  const setCapaActiva = useStore(s => s.setCapaActiva)

  return (
    <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 1000, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{
        background: 'rgba(26,29,39,0.94)', backdropFilter: 'blur(8px)',
        borderRadius: 12, padding: '8px 10px', border: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ fontSize: 10, color: '#8b91a8', fontWeight: 600, marginBottom: 6, letterSpacing: '0.06em' }}>CAPA</div>
        {CAPAS.map(c => (
          <button key={c.key} onClick={() => setCapaActiva(c.key)} style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '5px 10px', borderRadius: 8, width: '100%',
            border: capaActiva === c.key ? `1px solid ${c.color}55` : '1px solid transparent',
            background: capaActiva === c.key ? `${c.color}20` : 'transparent',
            color: capaActiva === c.key ? '#e8eaf0' : '#8b91a8',
            cursor: 'pointer', fontSize: 12, fontWeight: 500, marginBottom: 2,
            transition: 'all 0.15s',
          }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: capaActiva === c.key ? c.color : 'rgba(255,255,255,0.2)', flexShrink: 0 }} />
            {c.label}
          </button>
        ))}
      </div>

      <div style={{
        background: 'rgba(26,29,39,0.94)', backdropFilter: 'blur(8px)',
        borderRadius: 12, padding: '8px 10px', border: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ fontSize: 10, color: '#8b91a8', fontWeight: 600, marginBottom: 6, letterSpacing: '0.06em' }}>LEYENDA SSU</div>
        {[
          { color: '#1D9E75', label: 'Óptima (75+)' },
          { color: '#EF9F27', label: 'Aceptable (50-75)' },
          { color: '#E24B4A', label: 'Deficiente (30-50)' },
          { color: '#7B1C1C', label: 'Crítica (<30)' },
        ].map(item => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 3 }}>
            <span style={{ width: 12, height: 12, borderRadius: 3, background: item.color, flexShrink: 0 }} />
            <span style={{ fontSize: 10, color: '#b0b6c8' }}>{item.label}</span>
          </div>
        ))}
        <div style={{ marginTop: 6, fontSize: 9, color: '#4a5068', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 5 }}>
          Haz clic en una zona para ver activos de campo
        </div>
      </div>
    </div>
  )
}
