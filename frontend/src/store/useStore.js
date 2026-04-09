// Importamos la función create de Zustand para crear el store global de estado
import { create } from 'zustand'

// Creamos y exportamos el store global que centraliza todo el estado de la aplicación
export const useStore = create((set, get) => ({
  // ── Estado de datos ────────────────────────────────────────────────────────
  zonas: [],               // Lista de zonas con sus SSU cargadas desde el backend
  zonaSeleccionada: null,  // Zona actualmente seleccionada en el mapa o sidebar
  mapaGeojson: null,       // GeoJSON completo con todas las zonas para Leaflet
  stats: null,             // Estadísticas globales de la base de datos de campo
  isLoading: false,        // Indicador de carga activa para mostrar el overlay
  error: null,             // Mensaje de error global para mostrar al usuario

  // ── Estado de configuración del mapa ──────────────────────────────────────
  capaActiva: 'ssu',              // Capa del mapa visible: 'ssu' | 'iluminacion' | 'cobertura' | 'infraestructura'
  clienteFoco: 'videovigilancia', // Tipo de cliente activo: 'constructora' | 'videovigilancia' | 'inmobiliaria'

  // ── Acciones de actualización del estado ──────────────────────────────────
  setZonas: (zonas) => set({ zonas }),                         // Actualizamos la lista de zonas
  setZonaSeleccionada: (z) => set({ zonaSeleccionada: z }),    // Actualizamos la zona seleccionada
  setMapaGeojson: (g) => set({ mapaGeojson: g }),              // Actualizamos el GeoJSON del mapa
  setStats: (s) => set({ stats: s }),                          // Actualizamos las estadísticas globales
  setLoading: (v) => set({ isLoading: v }),                    // Actualizamos el estado de carga
  setError: (e) => set({ error: e }),                          // Actualizamos el mensaje de error
  setCapaActiva: (c) => set({ capaActiva: c }),                // Cambiamos la capa visible en el mapa
  setClienteFoco: (c) => set({ clienteFoco: c }),              // Cambiamos el tipo de cliente activo

  // ── Helpers derivados del estado ──────────────────────────────────────────
  getResumen: () => {
    // Calculamos el conteo de zonas por clasificación SSU a partir del estado actual
    const { zonas } = get()
    return {
      optima:     zonas.filter(z => z.clasificacion === 'optima').length,
      aceptable:  zonas.filter(z => z.clasificacion === 'aceptable').length,
      deficiente: zonas.filter(z => z.clasificacion === 'deficiente').length,
      critica:    zonas.filter(z => z.clasificacion === 'critica').length,
      total:      zonas.length,
    }
  },
}))
