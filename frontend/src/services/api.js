// Importamos axios para realizar peticiones HTTP al backend de FastAPI
import axios from 'axios'

// Creamos la instancia de axios con la URL base de la API y un timeout de 30 segundos
const api = axios.create({ baseURL: '/api/v1', timeout: 30000 })

// ── Sistema ──────────────────────────────────────────────────────────────────
// Consultamos el estado de salud del backend y la disponibilidad de Watsonx
export const getHealth = () => api.get('/health').then(r => r.data)

// ── Seguridad: Consulta ───────────────────────────────────────────────────────
// Obtenemos el listado rápido de todas las zonas con su SSU (sin Watsonx)
export const getZonas       = () => api.get('/seguridad/zonas').then(r => r.data)
// Obtenemos el detalle completo de una zona con narrativa de Granite 3-8B
export const getZona        = (id) => api.get(`/seguridad/zonas/${id}`).then(r => r.data)
// Obtenemos el GeoJSON de activos verificados en campo para una zona específica
export const getZonaGeojson = (id) => api.get(`/seguridad/zonas/${id}/geojson`).then(r => r.data)
// Obtenemos el GeoJSON completo de todas las zonas para renderizar el mapa principal
export const getMapaCompleto= () => api.get('/seguridad/mapa/geojson-completo').then(r => r.data)
// Obtenemos las estadísticas globales de la base de datos de campo XOLUM
export const getStats       = () => api.get('/seguridad/stats/resumen').then(r => r.data)
// Obtenemos el reporte ejecutivo personalizado para un tipo de cliente específico
export const getReporte     = (zona_id, cliente) =>
  api.get(`/seguridad/reporte/${zona_id}/${cliente}`).then(r => r.data)

// ── Seguridad: Exportar PDF ───────────────────────────────────────────────────
export const getReportePDF = async (zona_id, cliente) => {
  // Solicitamos el PDF como blob binario con un timeout mayor por el tiempo de generación
  const response = await api.get(`/seguridad/reporte/${zona_id}/${cliente}/pdf`, {
    responseType: 'blob',
    timeout: 60000, // Aumentamos el timeout a 60s porque la generación de PDF puede tardar
  })
  // Creamos un enlace de descarga temporal para disparar la descarga del archivo
  const blob = new Blob([response.data], { type: 'application/pdf' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  // Intentamos extraer el nombre del archivo del header Content-Disposition del backend
  const disposition = response.headers['content-disposition']
  const filename = disposition
    ? disposition.split('filename=')[1]?.replace(/"/g, '')
    : `SUSVI_${cliente}_reporte.pdf`
  link.download = filename
  // Agregamos el enlace al DOM, simulamos el clic para descargar y luego lo limpiamos
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  // Liberamos el objeto URL de memoria después de la descarga
  window.URL.revokeObjectURL(url)
}

// ── Seguridad: Campo (app móvil) ──────────────────────────────────────────────
// Registramos una luminaria verificada en campo desde la app móvil de XOLUM
export const registrarLuminaria   = (data) => api.post('/seguridad/campo/luminaria', data).then(r => r.data)
// Registramos un terreno abandonado identificado en campo
export const registrarTerreno     = (data) => api.post('/seguridad/campo/terreno-abandonado', data).then(r => r.data)
// Registramos un punto ciego de cámara detectado en campo
export const registrarPuntoCiego  = (data) => api.post('/seguridad/campo/punto-ciego', data).then(r => r.data)
// Registramos una observación de calle con datos cualitativos del entorno urbano
export const registrarObservacion = (data) => api.post('/seguridad/campo/observacion-calle', data).then(r => r.data)

