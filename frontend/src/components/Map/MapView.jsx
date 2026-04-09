import { useEffect, useRef, useCallback } from 'react'
import L from 'leaflet'
import { useStore } from '../../store/useStore'
import { getZonaGeojson } from '../../services/api'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const CDMX = [19.4200, -99.1600]

const SSU_COLOR = (ssu) => {
  if (ssu >= 75) return '#1D9E75'
  if (ssu >= 50) return '#EF9F27'
  if (ssu >= 30) return '#E24B4A'
  return '#7B1C1C'
}

const CAPA_SCORE = {
  ssu:            (p) => p.ssu,
  iluminacion:    (p) => p.score_iluminacion,
  cobertura:      (p) => p.score_cobertura,
  infraestructura:(p) => p.score_infraestructura,
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

export default function MapView() {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const zonaLayerRef = useRef(null)
  const activosLayerRef = useRef(null)

  const mapaGeojson = useStore(s => s.mapaGeojson)
  const capaActiva = useStore(s => s.capaActiva)
  const setZonaSeleccionada = useStore(s => s.setZonaSeleccionada)

  useEffect(() => {
    if (mapInstanceRef.current) return
    const map = L.map(mapRef.current, {
      center: CDMX, zoom: 12,
      zoomControl: true, attributionControl: false,
    })
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      { maxZoom: 19, subdomains: 'abcd' }
    ).addTo(map)
    mapInstanceRef.current = map
    return () => { map.remove(); mapInstanceRef.current = null }
  }, [])

  const loadActivosZona = useCallback(async (zona_id) => {
    const map = mapInstanceRef.current
    if (!map) return
    if (activosLayerRef.current) { activosLayerRef.current.remove(); activosLayerRef.current = null }
    try {
      const geojson = await getZonaGeojson(zona_id)
      const layer = L.geoJSON(geojson, {
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
        onEachFeature: (feature, layer) => {
          layer.bindPopup(feature.properties.popup || feature.properties.id, { maxWidth: 260 })
        },
      }).addTo(map)
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

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || !mapaGeojson) return
    if (zonaLayerRef.current) { zonaLayerRef.current.remove(); zonaLayerRef.current = null }
    const getScore = CAPA_SCORE[capaActiva] || CAPA_SCORE.ssu
    const layer = L.geoJSON(mapaGeojson, {
      style: (feature) => ({
        fillColor: SSU_COLOR(getScore(feature.properties) ?? 0),
        fillOpacity: 0.55, color: 'rgba(0,0,0,0.4)', weight: 1.5,
      }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties
        layer.bindPopup(popupZona(p), { maxWidth: 280 })
        layer.on('click', () => { setZonaSeleccionada(p); loadActivosZona(p.id); layer.openPopup() })
        layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.85, weight: 2.5 }))
        layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.55, weight: 1.5 }))
      },
    }).addTo(map)
    zonaLayerRef.current = layer
  }, [mapaGeojson, capaActiva, setZonaSeleccionada, loadActivosZona])

  return <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
}
