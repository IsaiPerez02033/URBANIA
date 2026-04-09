import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // Datos
  zonas: [],
  zonaSeleccionada: null,
  mapaGeojson: null,
  stats: null,
  isLoading: false,
  error: null,

  // Capa activa en el mapa
  capaActiva: 'ssu',        // 'ssu' | 'iluminacion' | 'cobertura' | 'infraestructura'
  clienteFoco: 'videovigilancia', // 'constructora' | 'videovigilancia' | 'inmobiliaria'

  // Acciones
  setZonas: (zonas) => set({ zonas }),
  setZonaSeleccionada: (z) => set({ zonaSeleccionada: z }),
  setMapaGeojson: (g) => set({ mapaGeojson: g }),
  setStats: (s) => set({ stats: s }),
  setLoading: (v) => set({ isLoading: v }),
  setError: (e) => set({ error: e }),
  setCapaActiva: (c) => set({ capaActiva: c }),
  setClienteFoco: (c) => set({ clienteFoco: c }),

  // Helpers
  getResumen: () => {
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
