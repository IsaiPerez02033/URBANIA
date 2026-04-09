"""
URBANIA SEGURIDAD — Endpoints REST
====================================
GET  /api/v1/seguridad/zonas                     → listado rápido (sin Watsonx)
GET  /api/v1/seguridad/zonas/{id}                → zona completa CON Granite
GET  /api/v1/seguridad/zonas/{id}/geojson        → activos de campo GeoJSON
GET  /api/v1/seguridad/mapa/geojson-completo     → mapa principal
GET  /api/v1/seguridad/reporte/{id}/{cliente}    → reporte cliente CON Granite
GET  /api/v1/seguridad/stats/resumen             → estadísticas globales
POST /api/v1/seguridad/campo/luminaria           → captura de campo (app móvil)
POST /api/v1/seguridad/campo/terreno-abandonado
POST /api/v1/seguridad/campo/punto-ciego
POST /api/v1/seguridad/campo/observacion-calle
"""
import uuid, logging, math
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.schema import get_connection
from db.security_scorer import (
    calcular_ssu_zona,
    calcular_todas_las_zonas,
)

logger = logging.getLogger("urbania.routes.security")
router = APIRouter(prefix="/api/v1/seguridad", tags=["Seguridad Urbana"])


# ── Modelos ───────────────────────────────────────────────────────────────────

class LuminariaIn(BaseModel):
    zona_id: str
    lat: float
    lng: float
    calle: Optional[str] = None
    numero_poste: Optional[str] = None
    estado: str = Field(..., pattern="^(funciona|no_funciona|vandalizada|inexistente|tenue)$")
    tipo: str = "desconocido"
    altura_m: Optional[float] = None
    radio_cobertura_m: float = 15.0
    notas: Optional[str] = None

class TerrenoIn(BaseModel):
    zona_id: str
    lat: float
    lng: float
    calle_referencia: Optional[str] = None
    area_estimada_m2: Optional[float] = None
    nivel_riesgo: str = Field(default="medio", pattern="^(alto|medio|bajo)$")
    tiene_acceso_publico: bool = True
    tiempo_abandono: str = "desconocido"
    signos_actividad_ilegal: bool = False
    notas: Optional[str] = None

class PuntoCiegoIn(BaseModel):
    zona_id: str
    lat: float
    lng: float
    calle: Optional[str] = None
    tipo_punto_ciego: str = "sin_camara"
    severidad: str = Field(default="alta", pattern="^(critica|alta|media)$")
    flujo_peatonal: str = Field(default="medio", pattern="^(alto|medio|bajo)$")
    incidentes_reportados: int = 0
    notas: Optional[str] = None

class ObservacionCalleIn(BaseModel):
    zona_id: str
    nombre_calle: str
    estado_pavimento: str = "regular"
    iluminacion_general: str = "regular"
    nivel_gentrificacion: str = "bajo"
    presencia_comercio_formal: bool = True
    presencia_comercio_informal: bool = False
    transito_vehicular: str = "medio"
    notas: Optional[str] = None


# ── Consulta ──────────────────────────────────────────────────────────────────

@router.get("/zonas", summary="Listado de zonas con SSU (sin Watsonx para velocidad)")
def listar_zonas():
    """
    Listado rápido de todas las zonas — NO llama a Watsonx para evitar latencia.
    Las narrativas IA se cargan al seleccionar una zona específica.
    """
    results = calcular_todas_las_zonas(usar_watsonx=False)
    return {
        "total": len(results),
        "zonas": results,
        "resumen": {
            "optima":     len([z for z in results if z["clasificacion"] == "optima"]),
            "aceptable":  len([z for z in results if z["clasificacion"] == "aceptable"]),
            "deficiente": len([z for z in results if z["clasificacion"] == "deficiente"]),
            "critica":    len([z for z in results if z["clasificacion"] == "critica"]),
        }
    }


@router.get("/zonas/{zona_id}", summary="Zona completa con narrativa IBM Granite 3-8B")
def get_zona(zona_id: str):
    """
    Detalle completo del SSU con narrativa ejecutiva generada por Granite 3-8B.
    Si Watsonx no está disponible usa fallback algorítmico.
    """
    try:
        return calcular_ssu_zona(zona_id, usar_watsonx=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/zonas/{zona_id}/geojson", summary="GeoJSON de activos de campo")
def get_zona_geojson(zona_id: str):
    conn = get_connection()
    features = []

    lums = conn.execute("SELECT * FROM luminarias WHERE zona_id = ?", (zona_id,)).fetchall()
    for l in lums:
        color_map = {
            "funciona": "#1D9E75", "tenue": "#EF9F27",
            "no_funciona": "#E24B4A", "vandalizada": "#7B1C1C", "inexistente": "#888780",
        }
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [l["lng"], l["lat"]]},
            "properties": {
                "tipo_activo": "luminaria",
                "id": l["id"], "estado": l["estado"],
                "calle": l["calle"],
                "color": color_map.get(l["estado"], "#888780"),
                "radio": l["radio_cobertura_m"],
                "popup": f"<b>Luminaria {l['id']}</b><br>{l['calle'] or '—'}<br>Estado: <b>{l['estado']}</b>",
            }
        })

    pcs = conn.execute("SELECT * FROM puntos_ciegos WHERE zona_id = ?", (zona_id,)).fetchall()
    for pc in pcs:
        sev_color = {"critica": "#7B1C1C", "alta": "#E24B4A", "media": "#EF9F27"}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [pc["lng"], pc["lat"]]},
            "properties": {
                "tipo_activo": "punto_ciego",
                "id": pc["id"], "tipo": pc["tipo_punto_ciego"], "severidad": pc["severidad"],
                "color": sev_color.get(pc["severidad"], "#E24B4A"),
                "popup": f"<b>Punto Ciego {pc['id']}</b><br>{pc['calle'] or '—'}<br>Tipo: {pc['tipo_punto_ciego']}<br>Severidad: <b>{pc['severidad']}</b>",
            }
        })

    ters = conn.execute("SELECT * FROM terrenos_abandonados WHERE zona_id = ?", (zona_id,)).fetchall()
    for t in ters:
        riesgo_color = {"alto": "#7B1C1C", "medio": "#E24B4A", "bajo": "#EF9F27"}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [t["lng"], t["lat"]]},
            "properties": {
                "tipo_activo": "terreno_abandonado",
                "id": t["id"], "nivel_riesgo": t["nivel_riesgo"],
                "color": riesgo_color.get(t["nivel_riesgo"], "#E24B4A"),
                "area_m2": t["area_estimada_m2"],
                "popup": f"<b>Terreno Abandonado {t['id']}</b><br>{t['calle_referencia'] or '—'}<br>Riesgo: <b>{t['nivel_riesgo']}</b><br>Área: {t['area_estimada_m2']} m²",
            }
        })

    conn.close()
    return {
        "type": "FeatureCollection", "zona_id": zona_id, "features": features,
        "totales": {"luminarias": len(lums), "puntos_ciegos": len(pcs), "terrenos_abandonados": len(ters)},
    }


@router.get("/mapa/geojson-completo", summary="GeoJSON de todas las zonas para mapa")
def get_mapa_completo():
    zonas = calcular_todas_las_zonas(usar_watsonx=False)
    features = []

    def circle_polygon(lat, lng, radius_km=0.35, points=8):
        coords = []
        for i in range(points + 1):
            angle = math.radians(i * 360 / points)
            dlat = radius_km / 111.32
            dlng = radius_km / (111.32 * math.cos(math.radians(lat)))
            coords.append([lng + dlng * math.cos(angle), lat + dlat * math.sin(angle)])
        return coords

    for z in zonas:
        features.append({
            "type": "Feature",
            "id": z["zona_id"],
            "geometry": {"type": "Polygon", "coordinates": [circle_polygon(z["lat"], z["lng"])]},
            "properties": {
                "id": z["zona_id"],
                "nombre": z["nombre"],
                "alcaldia": z["alcaldia"],
                "colonia": z["colonia"],
                "ssu": z["ssu"],
                "clasificacion": z["clasificacion"],
                "clasificacion_label": z["clasificacion_label"],
                "color": z["color"],
                "accion": z["accion_recomendada"],
                "score_iluminacion":     z["breakdown"]["iluminacion"]["score"],
                "score_cobertura":       z["breakdown"]["cobertura_camara"]["score"],
                "score_infraestructura": z["breakdown"]["infraestructura"]["score"],
                "score_entorno":         z["breakdown"]["entorno"]["score"],
                "n_luminarias_ok":       z["breakdown"]["iluminacion"].get("ok", 0),
                "n_puntos_ciegos":       z["breakdown"]["cobertura_camara"].get("n_puntos_ciegos", 0),
                "n_terrenos":            z["breakdown"]["infraestructura"].get("n_terrenos_abandonados", 0),
                "fuente": "XOLUM Campo Propio",
                "fecha_auditoria": z["fecha_auditoria"],
            }
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/reporte/{zona_id}/{cliente}", summary="Reporte por cliente con Granite")
def reporte_por_cliente(zona_id: str, cliente: str):
    clientes_validos = {"constructora", "videovigilancia", "inmobiliaria"}
    if cliente not in clientes_validos:
        raise HTTPException(status_code=400, detail=f"Cliente debe ser: {clientes_validos}")
    try:
        zona_data = calcular_ssu_zona(zona_id, usar_watsonx=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    key_map = {
        "constructora":    "constructora_gobierno",
        "videovigilancia": "empresa_videovigilancia",
        "inmobiliaria":    "desarrolladora_inmobiliaria",
    }
    rec = zona_data["recomendaciones"][key_map[cliente]]
    return {
        "zona": zona_data["nombre"],
        "ssu": zona_data["ssu"],
        "clasificacion": zona_data["clasificacion_label"],
        "narrativa_zona_ia": zona_data.get("narrativa_ia", ""),
        "watsonx_usado": zona_data.get("watsonx_usado", False),
        "cliente": cliente,
        "reporte": rec,
        "breakdown": zona_data["breakdown"],
        "fuente": zona_data["fuente_datos"],
        "fecha_auditoria": zona_data["fecha_auditoria"],
    }


@router.get("/stats/resumen", summary="Estadísticas globales de la BD de campo")
def stats_resumen():
    conn = get_connection()
    total_lum   = conn.execute("SELECT COUNT(*) FROM luminarias").fetchone()[0]
    lum_ok      = conn.execute("SELECT COUNT(*) FROM luminarias WHERE estado='funciona'").fetchone()[0]
    lum_mal     = conn.execute("SELECT COUNT(*) FROM luminarias WHERE estado IN ('no_funciona','vandalizada','inexistente')").fetchone()[0]
    total_ter   = conn.execute("SELECT COUNT(*) FROM terrenos_abandonados").fetchone()[0]
    total_pc    = conn.execute("SELECT COUNT(*) FROM puntos_ciegos").fetchone()[0]
    pc_criticos = conn.execute("SELECT COUNT(*) FROM puntos_ciegos WHERE severidad='critica'").fetchone()[0]
    total_obs   = conn.execute("SELECT COUNT(*) FROM observaciones_calle").fetchone()[0]
    total_zonas = conn.execute("SELECT COUNT(*) FROM zonas_auditadas").fetchone()[0]
    conn.close()

    from utils.watsonx_client import get_watsonx_client
    wx = get_watsonx_client()

    return {
        "zonas_auditadas": total_zonas,
        "luminarias": {
            "total": total_lum, "funcionando": lum_ok, "fuera_servicio": lum_mal,
            "cobertura_pct": round(lum_ok / total_lum * 100, 1) if total_lum else 0,
        },
        "terrenos_abandonados": total_ter,
        "puntos_ciegos": {"total": total_pc, "criticos": pc_criticos},
        "observaciones_calle": total_obs,
        "watsonx": {
            "activo": wx.is_available(),
            "modelo": wx.model_id if wx.is_available() else "fallback_algoritmico",
        },
        "nota": "Datos 100% verificados en campo por equipo XOLUM — no gubernamentales",
    }


# ── Captura de Campo ──────────────────────────────────────────────────────────

@router.post("/campo/luminaria", summary="Registrar luminaria (app móvil)")
def registrar_luminaria(data: LuminariaIn):
    conn = get_connection()
    if not conn.execute("SELECT id FROM zonas_auditadas WHERE id = ?", (data.zona_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Zona {data.zona_id} no existe")
    lum_id = f"LUM-{uuid.uuid4().hex[:8].upper()}"
    conn.execute("""
        INSERT INTO luminarias
        (id,zona_id,lat,lng,calle,numero_poste,estado,tipo,altura_m,radio_cobertura_m,verificada,notas)
        VALUES (?,?,?,?,?,?,?,?,?,?,1,?)
    """, (lum_id, data.zona_id, data.lat, data.lng, data.calle, data.numero_poste,
          data.estado, data.tipo, data.altura_m, data.radio_cobertura_m, data.notas))
    conn.commit(); conn.close()
    logger.info("Luminaria %s registrada en %s — %s", lum_id, data.zona_id, data.estado)
    return {"ok": True, "id": lum_id}


@router.post("/campo/terreno-abandonado", summary="Registrar terreno (app móvil)")
def registrar_terreno(data: TerrenoIn):
    conn = get_connection()
    if not conn.execute("SELECT id FROM zonas_auditadas WHERE id = ?", (data.zona_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Zona {data.zona_id} no existe")
    ter_id = f"TER-{uuid.uuid4().hex[:8].upper()}"
    conn.execute("""
        INSERT INTO terrenos_abandonados
        (id,zona_id,lat,lng,calle_referencia,area_estimada_m2,nivel_riesgo,
         tiene_acceso_publico,tiempo_abandono,signos_actividad_ilegal,notas)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (ter_id, data.zona_id, data.lat, data.lng, data.calle_referencia,
          data.area_estimada_m2, data.nivel_riesgo,
          1 if data.tiene_acceso_publico else 0,
          data.tiempo_abandono,
          1 if data.signos_actividad_ilegal else 0, data.notas))
    conn.commit(); conn.close()
    return {"ok": True, "id": ter_id}


@router.post("/campo/punto-ciego", summary="Registrar punto ciego (app móvil)")
def registrar_punto_ciego(data: PuntoCiegoIn):
    conn = get_connection()
    if not conn.execute("SELECT id FROM zonas_auditadas WHERE id = ?", (data.zona_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Zona {data.zona_id} no existe")
    pc_id = f"PC-{uuid.uuid4().hex[:8].upper()}"
    conn.execute("""
        INSERT INTO puntos_ciegos
        (id,zona_id,lat,lng,calle,tipo_punto_ciego,severidad,flujo_peatonal,incidentes_reportados,notas)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (pc_id, data.zona_id, data.lat, data.lng, data.calle,
          data.tipo_punto_ciego, data.severidad, data.flujo_peatonal,
          data.incidentes_reportados, data.notas))
    conn.commit(); conn.close()
    return {"ok": True, "id": pc_id}


@router.post("/campo/observacion-calle", summary="Registrar observación (app móvil)")
def registrar_observacion(data: ObservacionCalleIn):
    conn = get_connection()
    if not conn.execute("SELECT id FROM zonas_auditadas WHERE id = ?", (data.zona_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Zona {data.zona_id} no existe")
    obs_id = f"OBS-{uuid.uuid4().hex[:8].upper()}"
    conn.execute("""
        INSERT INTO observaciones_calle
        (id,zona_id,nombre_calle,estado_pavimento,iluminacion_general,
         nivel_gentrificacion,presencia_comercio_formal,presencia_comercio_informal,
         transito_vehicular,notas)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (obs_id, data.zona_id, data.nombre_calle, data.estado_pavimento,
          data.iluminacion_general, data.nivel_gentrificacion,
          1 if data.presencia_comercio_formal else 0,
          1 if data.presencia_comercio_informal else 0,
          data.transito_vehicular, data.notas))
    conn.commit(); conn.close()
    return {"ok": True, "id": obs_id}
