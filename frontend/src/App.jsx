import { useEffect } from 'react'
import { useStore } from './store/useStore'
import { getMapaCompleto, getZonas, getStats } from './services/api'
import TopBar from './components/Dashboard/TopBar'
import SidebarPanel from './components/Dashboard/SidebarPanel'
import ResultsPanel from './components/Dashboard/ResultsPanel'
import MapView from './components/Map/MapView'
import LayerControl from './components/Map/LayerControl'

export default function App() {
  const setMapaGeojson = useStore(s => s.setMapaGeojson)
  const setZonas = useStore(s => s.setZonas)
  const setStats = useStore(s => s.setStats)
  const setError = useStore(s => s.setError)
  const isLoading = useStore(s => s.isLoading)

  useEffect(() => {
    Promise.all([getMapaCompleto(), getZonas(), getStats()])
      .then(([mapa, zonas, stats]) => {
        setMapaGeojson(mapa)
        setZonas(zonas.zonas || [])
        setStats(stats)
      })
      .catch(e => setError('No se pudo conectar al backend. Verifica que el servidor esté corriendo.'))
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', overflow: 'hidden', background: '#0f1117' }}>
      <TopBar />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Sidebar izquierdo */}
        <div style={{ width: 248, flexShrink: 0, background: '#1a1d27', borderRight: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden' }}>
          <SidebarPanel />
        </div>

        {/* Mapa */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <MapView />
          <LayerControl />
          {isLoading && (
            <div style={{
              position: 'absolute', inset: 0, zIndex: 500,
              background: 'rgba(15,17,23,0.75)', backdropFilter: 'blur(4px)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <div style={{
                padding: '24px 32px', borderRadius: 16, background: '#1a1d27',
                border: '1px solid rgba(255,255,255,0.08)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
              }}>
                <div style={{ width: 36, height: 36, borderRadius: '50%', border: '3px solid rgba(239,159,39,0.2)', borderTopColor: '#EF9F27', animation: 'spin 0.7s linear infinite' }} />
                <div style={{ fontSize: 14, fontWeight: 700, color: '#e8eaf0' }}>Cargando inteligencia territorial...</div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar derecho */}
        <div style={{ width: 292, flexShrink: 0, background: '#1a1d27', borderLeft: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden' }}>
          <ResultsPanel />
        </div>
      </div>
    </div>
  )
}
