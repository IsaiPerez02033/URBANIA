// Importamos useEffect para ejecutar la carga inicial de datos al montar el componente
import { useEffect } from 'react'
// Importamos el store global para acceder y actualizar el estado de la aplicación
import { useStore } from './store/useStore'
// Importamos las funciones de la API para cargar los datos del mapa, zonas y estadísticas
import { getMapaCompleto, getZonas, getStats } from './services/api'
// Importamos los componentes del layout principal del dashboard
import TopBar from './components/Dashboard/TopBar'
import SidebarPanel from './components/Dashboard/SidebarPanel'
import ResultsPanel from './components/Dashboard/ResultsPanel'
// Importamos los componentes del mapa interactivo y el control de capas
import MapView from './components/Map/MapView'
import LayerControl from './components/Map/LayerControl'

export default function App() {
  // Obtenemos las acciones del store para actualizar el estado global al cargar datos
  const setMapaGeojson = useStore(s => s.setMapaGeojson)
  const setZonas = useStore(s => s.setZonas)
  const setStats = useStore(s => s.setStats)
  const setError = useStore(s => s.setError)
  // Observamos el estado de carga para mostrar el overlay de espera
  const isLoading = useStore(s => s.isLoading)

  // Cargamos todos los datos necesarios en paralelo al montar la aplicación
  useEffect(() => {
    Promise.all([getMapaCompleto(), getZonas(), getStats()])
      .then(([mapa, zonas, stats]) => {
        // Guardamos el GeoJSON del mapa completo en el store para renderizarlo en Leaflet
        setMapaGeojson(mapa)
        // Guardamos la lista de zonas con sus SSU para el ranking del sidebar
        setZonas(zonas.zonas || [])
        // Guardamos las estadísticas globales del campo para el encabezado
        setStats(stats)
      })
      // Si falla alguna llamada mostramos el mensaje de error al usuario
      .catch(e => setError('No se pudo conectar al backend. Verifica que el servidor esté corriendo.'))
  }, [])

  return (
    // Contenedor principal que ocupa toda la ventana con fondo oscuro corporativo
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', overflow: 'hidden', background: '#0f1117' }}>
      {/* Barra superior con nombre, estado de API y estadísticas globales */}
      <TopBar />
      {/* Contenedor del cuerpo principal: sidebar izquierdo + mapa + sidebar derecho */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Sidebar izquierdo: estadísticas de campo, selector de cliente y ranking de zonas */}
        <div style={{ width: 248, flexShrink: 0, background: '#1a1d27', borderRight: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden' }}>
          <SidebarPanel />
        </div>

        {/* Área central del mapa con Leaflet y control de capas superpuesto */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <MapView />
          {/* Control de capas flotante para cambiar el score visualizado en el mapa */}
          <LayerControl />
          {/* Overlay de carga que cubre el mapa mientras se obtienen datos del backend */}
          {isLoading && (
            <div style={{
              position: 'absolute', inset: 0, zIndex: 500,
              background: 'rgba(15,17,23,0.75)', backdropFilter: 'blur(4px)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {/* Tarjeta de carga con spinner animado y mensaje de estado */}
              <div style={{
                padding: '24px 32px', borderRadius: 16, background: '#1a1d27',
                border: '1px solid rgba(255,255,255,0.08)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
              }}>
                {/* Spinner CSS animado con los colores corporativos */}
                <div style={{ width: 36, height: 36, borderRadius: '50%', border: '3px solid rgba(239,159,39,0.2)', borderTopColor: '#EF9F27', animation: 'spin 0.7s linear infinite' }} />
                <div style={{ fontSize: 14, fontWeight: 700, color: '#e8eaf0' }}>Cargando inteligencia territorial...</div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar derecho: SSU, breakdown, activos de campo y reporte por cliente */}
        <div style={{ width: 292, flexShrink: 0, background: '#1a1d27', borderLeft: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden' }}>
          <ResultsPanel />
        </div>
      </div>
    </div>
  )
}
