import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1', timeout: 30000 })

// ── Sistema ──────────────────────────────────────────────────────────────────
export const getHealth = () => api.get('/health').then(r => r.data)

// ── Seguridad: Consulta ───────────────────────────────────────────────────────
export const getZonas       = () => api.get('/seguridad/zonas').then(r => r.data)
export const getZona        = (id) => api.get(`/seguridad/zonas/${id}`).then(r => r.data)
export const getZonaGeojson = (id) => api.get(`/seguridad/zonas/${id}/geojson`).then(r => r.data)
export const getMapaCompleto= () => api.get('/seguridad/mapa/geojson-completo').then(r => r.data)
export const getStats       = () => api.get('/seguridad/stats/resumen').then(r => r.data)
export const getReporte     = (zona_id, cliente) =>
  api.get(`/seguridad/reporte/${zona_id}/${cliente}`).then(r => r.data)

// ── Seguridad: Exportar PDF ───────────────────────────────────────────────────
export const getReportePDF = async (zona_id, cliente) => {
  const response = await api.get(`/seguridad/reporte/${zona_id}/${cliente}/pdf`, {
    responseType: 'blob',
    timeout: 60000,
  })
  // Crear un enlace de descarga temporal
  const blob = new Blob([response.data], { type: 'application/pdf' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const disposition = response.headers['content-disposition']
  const filename = disposition
    ? disposition.split('filename=')[1]?.replace(/"/g, '')
    : `URBANIA_${cliente}_reporte.pdf`
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// ── Seguridad: Campo (app móvil) ──────────────────────────────────────────────
export const registrarLuminaria   = (data) => api.post('/seguridad/campo/luminaria', data).then(r => r.data)
export const registrarTerreno     = (data) => api.post('/seguridad/campo/terreno-abandonado', data).then(r => r.data)
export const registrarPuntoCiego  = (data) => api.post('/seguridad/campo/punto-ciego', data).then(r => r.data)
export const registrarObservacion = (data) => api.post('/seguridad/campo/observacion-calle', data).then(r => r.data)

