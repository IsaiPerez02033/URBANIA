// Importamos los hooks de React necesarios para el ciclo de vida, referencias y callbacks memorizados
import { useEffect, useRef, useCallback } from 'react'
// Importamos Leaflet como librería de mapas interactivos
import L from 'leaflet'
// Importamos el store global para leer el GeoJSON del mapa, la capa activa y actualizar la zona seleccionada
import { useStore } from '../../store/useStore'
// Importamos la función de la API para cargar los activos de campo al seleccionar una zona
import { getZonaGeojson } from '../../services/api'

// Eliminamos la propiedad privada que causa un error al intentar cargar los íconos por defecto de Leaflet
delete L.Icon.Default.prototype._getIconUrl
// Configuramos los URLs de los íconos de marcadores de Leaflet desde la CDN de Cloudflare
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Declaramos las coordenadas del centro de la Ciudad de Mexico como punto inicial del mapa
const CDMX = [19.4200, -99.1600]

// Retornamos el color del SSU correspondiente a los umbrales definidos en el sistema
const SSU_COLOR = (ssu) => {
  if (ssu >= 75) return '#1D9E75'  // Seguridad optima
  if (ssu >= 50) return '#EF9F27'  // Seguridad aceptable
  if (ssu >= 30) return '#E24B4A'  // Seguridad deficiente
  return '#7B1C1C'                 // Zona critica
}

// Declaramos los selectores de score para cada capa del mapa, extrayendo el campo correcto de las propiedades
const CAPA_SCORE = {
  ssu:            (p) => p.ssu,                    // Score de Seguridad Urbana total
  iluminacion:    (p) => p.score_iluminacion,       // Score de iluminación publica
  cobertura:      (p) => p.score_cobertura,         // Score de cobertura de camara
  infraestructura:(p) => p.score_infraestructura,   // Score de infraestructura vial y terrenos
}

const popupZona = (p) => `
  <div style="min-width:220px;font-family:system-ui">
    <div style="font-size:15px;font-weight:700;color:#e8eaf0;margin-bottom:2px">${p.nombre}</div>
    <div style="font-size:11px;color:#8b91a8;margin-bottom:8px">${p.alcaldia}</div>
    <div style="font-size:22px;font-weight:800;color:${SSU_COLOR(p.ssu)};margin-bottom:2px">
      ${(p.ssu||0).toFixed(0)}<span style="font-size:12px;color:#8b91a8">/100</span>
    </div>
    <div style="font-size:11px;font-weight:600;color:${SSU_COLOR(p.ssu)};margin-bottom:10px">${p.clasificacion_label}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:8px">
      <div style="background:rgba(255,255,255,0.05);border-radius:4px;padding:4px 6px">
        <div style="font-size:9px;color:#8b91a8">Iluminacion</div>
        <div style="font-size:13px;font-weight:700;color:#e8eaf0">${(p.score_iluminacion||0).toFixed(0)}</div>
      </div>
      <div style="background:rgba(255,255,255,0.05);border-radius:4px;padding:4px 6px">
        <div style="font-size:9px;color:#8b91a8">Cobertura Cam</div>
        <div style="font-size:13px;font-weight:700;color:#e8eaf0">${(p.score_cobertura||0).toFixed(0)}</div>
      </div>
      <div style="background:rgba(255,255,255,0.05);border-radius:4px;padding:4px 6px">
        <div style="font-size:9px;color:#8b91a8">Infraestructura</div>
        <div style="font-size:13px;font-weight:700;color:#e8eaf0">${(p.score_infraestructura||0).toFixed(0)}</div>
      </div>
      <div style="background:rgba(255,255,255,0.05);border-radius:4px;padding:4px 6px">
        <div style="font-size:9px;color:#8b91a8">Entorno</div>
        <div style="font-size:13px;font-weight:700;color:#e8eaf0">${(p.score_entorno||0).toFixed(0)}</div>
      </div>
    </div>
    <div style="font-size:10px;color:#4a5068;border-top:1px solid rgba(255,255,255,0.06);padding-top:6px">
      Luminarias ok: ${p.n_luminarias_ok} | P.Ciegos: ${p.n_puntos_ciegos} | Terrenos: ${p.n_terrenos}
    </div>
    <div style="font-size:10px;color:#1D9E75;margin-top:4px">Datos campo XOLUM verificados</div>
  </div>
`

// Declaramos el componente MapView que renderiza el mapa de Leaflet con las zonas de seguridad
export default function MapView() {
  // Declaramos la referencia al elemento DOM donde montamos el mapa
  const mapRef = useRef(null)
  // Declaramos la referencia a la instancia del mapa de Leaflet para evitar montajes duplicados
  const mapInstanceRef = useRef(null)
  // Declaramos la referencia a la capa de zonas para poder removerla al cambiar de capa activa
  const zonaLayerRef = useRef(null)
  // Declaramos la referencia a la capa de activos de campo para limpiarla al cambiar de zona
  const activosLayerRef = useRef(null)

  // Leemos el GeoJSON completo del mapa para renderizar los polígonos de zonas
  const mapaGeojson = useStore(s => s.mapaGeojson)
  // Leemos la capa activa para saber qué score usar para colorear las zonas
  const capaActiva = useStore(s => s.capaActiva)
  // Obtenemos la acción para actualizar la zona seleccionada al hacer clic en el mapa
  const setZonaSeleccionada = useStore(s => s.setZonaSeleccionada)

  // Inicializamos el mapa de Leaflet solo una vez al montar el componente
  useEffect(() => {
    if (mapInstanceRef.current) return  // Evitamos crear el mapa si ya existe una instancia
    const map = L.map(mapRef.current, {
      center: CDMX, zoom: 12,
      zoomControl: true, attributionControl: false,  // Ocultamos la atribución por diseño
    })
    // Agregamos el tile layer oscuro de CartoDB para mantener el estilo dark del dashboard
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      { maxZoom: 19, subdomains: 'abcd' }
    ).addTo(map)
    mapInstanceRef.current = map
    // Limpiamos el mapa al desmontar el componente para evitar fugas de memoria
    return () => { map.remove(); mapInstanceRef.current = null }
  }, [])

  // Cargamos y mostramos los activos de campo (luminarias, puntos ciegos, terrenos) de una zona
  const loadActivosZona = useCallback(async (zona_id) => {
    const map = mapInstanceRef.current
    if (!map) return
    // Removemos la capa de activos anterior si existe antes de cargar la nueva zona
    if (activosLayerRef.current) { activosLayerRef.current.remove(); activosLayerRef.current = null }
    try {
      // Obtenemos el GeoJSON de activos del backend para esta zona específica
      const geojson = await getZonaGeojson(zona_id)
      const layer = L.geoJSON(geojson, {
        // Creamos marcadores personalizados con íconos segun el tipo de activo
        pointToLayer: (feature, latlng) => {
          const tipo = feature.properties.tipo_activo
          const iconMap = { luminaria: '💡', punto_ciego: '📷', terreno_abandonado: '🏚️' }
          return L.marker(latlng, {
            icon: L.divIcon({
              html: `<div style="font-size:18px;filter:drop-shadow(0 1px 3px rgba(0,0,0,0.8))">${iconMap[tipo]||'📍'}</div>`,
              className: '', iconSize: [24, 24], iconAnchor: [12, 12],
            })
          })
        },
        // Asociamos el popup HTML de cada activo al hacer clic en el marcador
        onEachFeature: (feature, layer) => {
          layer.bindPopup(feature.properties.popup || feature.properties.id, { maxWidth: 260 })
        },
      }).addTo(map)
      // Dibujamos círculos de cobertura para cada luminaria que tenga radio definido
      geojson.features
        .filter(f => f.properties.tipo_activo === 'luminaria' && f.properties.radio > 0)
        .forEach(f => {
          const [lng, lat] = f.geometry.coordinates
          L.circle([lat, lng], {
            radius: f.properties.radio,
            fillColor: f.properties.color, fillOpacity: 0.12,
            color: f.properties.color, weight: 1, opacity: 0.4,
          }).addTo(map)
        })
      activosLayerRef.current = layer
    } catch (e) { console.warn('Error cargando activos:', e) }
  }, [])

  // Actualizamos la capa de zonas cada vez que cambia el GeoJSON del mapa o la capa activa
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || !mapaGeojson) return
    // Removemos la capa anterior antes de renderizar la nueva para evitar superposiciones
    if (zonaLayerRef.current) { zonaLayerRef.current.remove(); zonaLayerRef.current = null }
    // Seleccionamos la función extractora del score según la capa activa en el control
    const getScore = CAPA_SCORE[capaActiva] || CAPA_SCORE.ssu
    const layer = L.geoJSON(mapaGeojson, {
      // Coloreamos cada polígono según el score de la capa activa
      style: (feature) => ({
        fillColor: SSU_COLOR(getScore(feature.properties) ?? 0),
        fillOpacity: 0.55, color: 'rgba(0,0,0,0.4)', weight: 1.5,
      }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties
        // Asociamos el popup detallado HTML al hacer clic en cada zona
        layer.bindPopup(popupZona(p), { maxWidth: 280 })
        // Al hacer clic seleccionamos la zona y cargamos sus activos de campo
        layer.on('click', () => { setZonaSeleccionada(p); loadActivosZona(p.id); layer.openPopup() })
        // Aplicamos efecto hover para mejorar la interactividad visual del mapa
        layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.85, weight: 2.5 }))
        layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.55, weight: 1.5 }))
      },
    }).addTo(map)
    zonaLayerRef.current = layer
  }, [mapaGeojson, capaActiva, setZonaSeleccionada, loadActivosZona])

  // Retornamos el contenedor div donde Leaflet monta el mapa
  return <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
}
