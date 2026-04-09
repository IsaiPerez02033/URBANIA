"""
URBANIA SEGURIDAD — Endpoints REST
====================================
GET  /api/v1/seguridad/zonas                     → listado rápido (sin Watsonx)
GET  /api/v1/seguridad/zonas/{id}                → zona completa CON Granite
GET  /api/v1/seguridad/zonas/{id}/geojson        → activos de campo GeoJSON
GET  /api/v1/seguridad/mapa/geojson-completo     → mapa principal
GET  /api/v1/seguridad/reporte/{id}/{cliente}    → reporte cliente CON Granite
GET  /api/v1/seguridad/reporte/{id}/{cliente}/pdf → PDF ejecutivo por cliente
GET  /api/v1/seguridad/stats/resumen             → estadísticas globales
POST /api/v1/seguridad/campo/luminaria           → captura de campo (app móvil)
POST /api/v1/seguridad/campo/terreno-abandonado
POST /api/v1/seguridad/campo/punto-ciego
POST /api/v1/seguridad/campo/observacion-calle
"""
# Importamos las herramientas necesarias para generación de IDs, logging, matemáticas y archivos temporales
import uuid, logging, math, os, tempfile
# Importamos Optional para tipar parámetros opcionales de los modelos Pydantic
from typing import Optional
# Importamos APIRouter y HTTPException para definir las rutas y manejar errores HTTP
from fastapi import APIRouter, HTTPException
# Importamos FileResponse para servir el PDF generado como descarga directa
from fastapi.responses import FileResponse
# Importamos BaseModel y Field de Pydantic para definir y validar los modelos de entrada
from pydantic import BaseModel, Field

# Importamos la función de conexión a la base de datos
from db.schema import get_connection
# Importamos las funciones del motor de scores para calcular el SSU por zona
from db.security_scorer import (
    calcular_ssu_zona,
    calcular_todas_las_zonas,
)

# Creamos el logger específico para el módulo de rutas de seguridad
logger = logging.getLogger("urbania.routes.security")
# Creamos el router con el prefijo y la etiqueta de la sección en la documentación
router = APIRouter(prefix="/api/v1/seguridad", tags=["Seguridad Urbana"])


# ── Modelos ───────────────────────────────────────────────────────────────────

# Declaramos el modelo de entrada para registrar una luminaria desde la app móvil
class LuminariaIn(BaseModel):
    zona_id: str
    lat: float
    lng: float
    calle: Optional[str] = None
    numero_poste: Optional[str] = None
    # Validamos el estado con un patrón regex para aceptar solo valores conocidos
    estado: str = Field(..., pattern="^(funciona|no_funciona|vandalizada|inexistente|tenue)$")
    tipo: str = "desconocido"
    altura_m: Optional[float] = None
    radio_cobertura_m: float = 15.0  # Radio de cobertura por defecto de 15 metros
    notas: Optional[str] = None

# Declaramos el modelo de entrada para registrar un terreno abandonado desde campo
class TerrenoIn(BaseModel):
    zona_id: str
    lat: float
    lng: float
    calle_referencia: Optional[str] = None
    area_estimada_m2: Optional[float] = None
    # Validamos el nivel de riesgo para aceptar solo los tres niveles definidos
    nivel_riesgo: str = Field(default="medio", pattern="^(alto|medio|bajo)$")
    tiene_acceso_publico: bool = True
    tiempo_abandono: str = "desconocido"
    signos_actividad_ilegal: bool = False
    notas: Optional[str] = None

# Declaramos el modelo de entrada para registrar un punto ciego de cámara en campo
class PuntoCiegoIn(BaseModel):
    zona_id: str
    lat: float
    lng: float
    calle: Optional[str] = None
    tipo_punto_ciego: str = "sin_camara"
    # Validamos la severidad para aceptar solo los niveles definidos en el sistema
    severidad: str = Field(default="alta", pattern="^(critica|alta|media)$")
    flujo_peatonal: str = Field(default="medio", pattern="^(alto|medio|bajo)$")
    incidentes_reportados: int = 0
    notas: Optional[str] = None

# Declaramos el modelo de entrada para registrar una observación cualitativa de calle
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
    # Calculamos el SSU de todas las zonas sin invocar Watsonx para mantener la respuesta rápida
    results = calcular_todas_las_zonas(usar_watsonx=False)
    # Devolvemos el total, el listado completo y un resumen de conteo por clasificación
    return {
        "total": len(results),
        "zonas": results,
        "resumen": {
            # Contamos cuántas zonas caen en cada nivel de clasificación de seguridad
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
        # Calculamos el SSU completo de la zona activando la generación de narrativa con Watsonx
        return calcular_ssu_zona(zona_id, usar_watsonx=True)
    except ValueError as e:
        # Devolvemos 404 si la zona no existe en la base de datos de campo
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/zonas/{zona_id}/geojson", summary="GeoJSON de activos de campo")
def get_zona_geojson(zona_id: str):
    # Abrimos conexión a la base de datos para consultar los activos de campo de la zona
    conn = get_connection()
    # Inicializamos la lista de features GeoJSON que acumulará todos los activos de la zona
    features = []

    # Consultamos todas las luminarias registradas para esta zona específica
    lums = conn.execute("SELECT * FROM luminarias WHERE zona_id = ?", (zona_id,)).fetchall()
    for l in lums:
        # Mapeamos cada estado de luminaria a su color de visualización en el mapa
        color_map = {
            "funciona": "#1D9E75", "tenue": "#EF9F27",
            "no_funciona": "#E24B4A", "vandalizada": "#7B1C1C", "inexistente": "#888780",
        }
        # Construimos el feature GeoJSON de cada luminaria con sus propiedades de visualización
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [l["lng"], l["lat"]]},
            "properties": {
                "tipo_activo": "luminaria",
                "id": l["id"], "estado": l["estado"],
                "calle": l["calle"],
                # Asignamos el color según el estado de la luminaria, usando gris como fallback
                "color": color_map.get(l["estado"], "#888780"),
                "radio": l["radio_cobertura_m"],
                "popup": f"<b>Luminaria {l['id']}</b><br>{l['calle'] or '—'}<br>Estado: <b>{l['estado']}</b>",
            }
        })

    # Consultamos todos los puntos ciegos de cámara registrados para esta zona
    pcs = conn.execute("SELECT * FROM puntos_ciegos WHERE zona_id = ?", (zona_id,)).fetchall()
    for pc in pcs:
        # Mapeamos la severidad del punto ciego a su color de peligrosidad correspondiente
        sev_color = {"critica": "#7B1C1C", "alta": "#E24B4A", "media": "#EF9F27"}
        # Construimos el feature GeoJSON del punto ciego con severidad y tipo de punto
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

    # Consultamos todos los terrenos abandonados registrados para esta zona
    ters = conn.execute("SELECT * FROM terrenos_abandonados WHERE zona_id = ?", (zona_id,)).fetchall()
    for t in ters:
        # Mapeamos el nivel de riesgo del terreno a su color de alerta visual
        riesgo_color = {"alto": "#7B1C1C", "medio": "#E24B4A", "bajo": "#EF9F27"}
        # Construimos el feature GeoJSON del terreno con nivel de riesgo y área estimada
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

    # Cerramos la conexión y devolvemos la colección GeoJSON con el conteo de activos por tipo
    conn.close()
    return {
        "type": "FeatureCollection", "zona_id": zona_id, "features": features,
        "totales": {"luminarias": len(lums), "puntos_ciegos": len(pcs), "terrenos_abandonados": len(ters)},
    }


@router.get("/mapa/geojson-completo", summary="GeoJSON de todas las zonas para mapa")
def get_mapa_completo():
    # Calculamos el SSU de todas las zonas sin Watsonx para construir el mapa con agilidad
    zonas = calcular_todas_las_zonas(usar_watsonx=False)
    # Inicializamos la lista de features que conformará la colección GeoJSON del mapa principal
    features = []

    # Generamos un polígono circular aproximado a partir de coordenadas centrales y radio en km
    def circle_polygon(lat, lng, radius_km=0.35, points=8):
        coords = []
        for i in range(points + 1):
            # Calculamos el ángulo en radianes para distribuir los puntos uniformemente
            angle = math.radians(i * 360 / points)
            # Convertimos el radio de km a grados de latitud y longitud ajustando por el coseno
            dlat = radius_km / 111.32
            dlng = radius_km / (111.32 * math.cos(math.radians(lat)))
            coords.append([lng + dlng * math.cos(angle), lat + dlat * math.sin(angle)])
        return coords

    # Construimos un feature GeoJSON por cada zona con todos sus scores y metadatos de campo
    for z in zonas:
        features.append({
            "type": "Feature",
            "id": z["zona_id"],
            # Representamos cada zona como un polígono circular centrado en sus coordenadas
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
                # Extraemos los scores de cada componente del breakdown para las capas del mapa
                "score_iluminacion":     z["breakdown"]["iluminacion"]["score"],
                "score_cobertura":       z["breakdown"]["cobertura_camara"]["score"],
                "score_infraestructura": z["breakdown"]["infraestructura"]["score"],
                "score_entorno":         z["breakdown"]["entorno"]["score"],
                # Extraemos los conteos de activos de campo verificados por XOLUM
                "n_luminarias_ok":       z["breakdown"]["iluminacion"].get("ok", 0),
                "n_puntos_ciegos":       z["breakdown"]["cobertura_camara"].get("n_puntos_ciegos", 0),
                "n_terrenos":            z["breakdown"]["infraestructura"].get("n_terrenos_abandonados", 0),
                "fuente": "XOLUM Campo Propio",
                "fecha_auditoria": z["fecha_auditoria"],
            }
        })

    # Devolvemos la colección GeoJSON completa con todos los polígonos de zonas
    return {"type": "FeatureCollection", "features": features}


@router.get("/reporte/{zona_id}/{cliente}", summary="Reporte por cliente con Granite")
def reporte_por_cliente(zona_id: str, cliente: str):
    # Validamos que el tipo de cliente solicitado sea uno de los tres perfiles del sistema
    clientes_validos = {"constructora", "videovigilancia", "inmobiliaria"}
    if cliente not in clientes_validos:
        raise HTTPException(status_code=400, detail=f"Cliente debe ser: {clientes_validos}")
    try:
        # Calculamos el SSU completo con narrativa Watsonx para enriquecer el reporte
        zona_data = calcular_ssu_zona(zona_id, usar_watsonx=True)
    except ValueError as e:
        # Devolvemos 404 si la zona no existe en la base de datos
        raise HTTPException(status_code=404, detail=str(e))

    # Mapeamos la clave de cliente del request a la clave interna del diccionario de recomendaciones
    key_map = {
        "constructora":    "constructora_gobierno",
        "videovigilancia": "empresa_videovigilancia",
        "inmobiliaria":    "desarrolladora_inmobiliaria",
    }
    # Extraemos el bloque de recomendaciones específico para el tipo de cliente solicitado
    rec = zona_data["recomendaciones"][key_map[cliente]]
    # Devolvemos el reporte con SSU, narrativa IA, recomendaciones y metadatos de campo
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


@router.get("/reporte/{zona_id}/{cliente}/pdf", summary="PDF ejecutivo por cliente")
def reporte_pdf(zona_id: str, cliente: str):
    """
    Genera y descarga un PDF ejecutivo con todos los datos del reporte.
    Incluye: zona, SSU, breakdown, narrativa IA, recomendaciones por cliente,
    activos de campo verificados y alertas.
    """
    # Validamos que el cliente sea uno de los tres perfiles del sistema antes de generar el PDF
    clientes_validos = {"constructora", "videovigilancia", "inmobiliaria"}
    if cliente not in clientes_validos:
        raise HTTPException(status_code=400, detail=f"Cliente debe ser: {clientes_validos}")
    try:
        # Calculamos el SSU completo con narrativa IA para incluirla en el PDF ejecutivo
        zona_data = calcular_ssu_zona(zona_id, usar_watsonx=True)
    except ValueError as e:
        # Devolvemos 404 si la zona solicitada no existe en la base de datos de campo
        raise HTTPException(status_code=404, detail=str(e))

    # Mapeamos la clave de cliente del request a la clave interna de recomendaciones
    key_map = {
        "constructora":    "constructora_gobierno",
        "videovigilancia": "empresa_videovigilancia",
        "inmobiliaria":    "desarrolladora_inmobiliaria",
    }
    # Extraemos el bloque de recomendaciones del cliente para incluirlo en el PDF
    rec = zona_data["recomendaciones"][key_map[cliente]]

    # Construimos el diccionario de datos del reporte que pasaremos al generador de PDF
    reporte_data = {
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

    # Importamos el generador de PDF de forma diferida para evitar la carga al arrancar el módulo
    from utils.pdf_generator import URBANIAReportGenerator
    generator = URBANIAReportGenerator()

    # Creamos el directorio temporal donde guardamos los PDFs antes de servirlos
    tmp_dir = os.path.join(tempfile.gettempdir(), "urbania_pdfs")
    os.makedirs(tmp_dir, exist_ok=True)

    # Sanitizamos el nombre de la zona para usarlo como parte del nombre del archivo PDF
    safe_zona = zona_data["nombre"].replace(" ", "_").replace("/", "-")[:30]
    filename = f"URBANIA_{cliente}_{safe_zona}.pdf"
    output_path = os.path.join(tmp_dir, filename)

    try:
        # Generamos el PDF y lo servimos como descarga directa con los encabezados correctos
        result_path = generator.generate_reporte_cliente(reporte_data, output_path)
        return FileResponse(
            path=result_path,
            filename=filename,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as e:
        # Registramos el error y devolvemos 500 si la generación del PDF falla
        logger.error("Error generando PDF: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")

@router.get("/stats/resumen", summary="Estadísticas globales de la BD de campo")
def stats_resumen():
    # Abrimos la conexión para realizar todas las consultas de estadísticas globales
    conn = get_connection()
    # Contamos el total de luminarias registradas en la base de datos de campo
    total_lum   = conn.execute("SELECT COUNT(*) FROM luminarias").fetchone()[0]
    # Contamos las luminarias en estado funcional para calcular el porcentaje de cobertura
    lum_ok      = conn.execute("SELECT COUNT(*) FROM luminarias WHERE estado='funciona'").fetchone()[0]
    # Contamos las luminarias fuera de servicio para el indicador de déficit de iluminación
    lum_mal     = conn.execute("SELECT COUNT(*) FROM luminarias WHERE estado IN ('no_funciona','vandalizada','inexistente')").fetchone()[0]
    # Contamos el total de terrenos abandonados identificados en campo
    total_ter   = conn.execute("SELECT COUNT(*) FROM terrenos_abandonados").fetchone()[0]
    # Contamos el total de puntos ciegos de cámara registrados
    total_pc    = conn.execute("SELECT COUNT(*) FROM puntos_ciegos").fetchone()[0]
    # Contamos los puntos ciegos de severidad crítica para la alerta de seguridad
    pc_criticos = conn.execute("SELECT COUNT(*) FROM puntos_ciegos WHERE severidad='critica'").fetchone()[0]
    # Contamos el total de observaciones cualitativas de calle capturadas en campo
    total_obs   = conn.execute("SELECT COUNT(*) FROM observaciones_calle").fetchone()[0]
    # Contamos el número de zonas auditadas en el piloto CDMX
    total_zonas = conn.execute("SELECT COUNT(*) FROM zonas_auditadas").fetchone()[0]
    conn.close()

    # Importamos el cliente de Watsonx para incluir su estado en el resumen de sistema
    from utils.watsonx_client import get_watsonx_client
    wx = get_watsonx_client()

    # Devolvemos el resumen global con estadísticas de campo y estado del sistema IA
    return {
        "zonas_auditadas": total_zonas,
        "luminarias": {
            "total": total_lum, "funcionando": lum_ok, "fuera_servicio": lum_mal,
            # Calculamos el porcentaje de cobertura evitando división por cero si no hay luminarias
            "cobertura_pct": round(lum_ok / total_lum * 100, 1) if total_lum else 0,
        },
        "terrenos_abandonados": total_ter,
        "puntos_ciegos": {"total": total_pc, "criticos": pc_criticos},
        "observaciones_calle": total_obs,
        "watsonx": {
            "activo": wx.is_available(),
            # Mostramos el modelo activo o indicamos que se usa el fallback algorítmico
            "modelo": wx.model_id if wx.is_available() else "fallback_algoritmico",
        },
        "nota": "Datos 100% verificados en campo por equipo XOLUM — no gubernamentales",
    }


# ── Captura de Campo ──────────────────────────────────────────────────────────

@router.post("/campo/luminaria", summary="Registrar luminaria (app móvil)")
def registrar_luminaria(data: LuminariaIn):
    # Abrimos la conexión y verificamos que la zona existe antes de insertar la luminaria
    conn = get_connection()
    if not conn.execute("SELECT id FROM zonas_auditadas WHERE id = ?", (data.zona_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Zona {data.zona_id} no existe")
    # Generamos un ID único para la luminaria con prefijo LUM y 8 caracteres hexadecimales
    lum_id = f"LUM-{uuid.uuid4().hex[:8].upper()}"
    # Insertamos el registro de la luminaria con todos sus atributos de campo y verificada=1
    conn.execute("""
        INSERT INTO luminarias
        (id,zona_id,lat,lng,calle,numero_poste,estado,tipo,altura_m,radio_cobertura_m,verificada,notas)
        VALUES (?,?,?,?,?,?,?,?,?,?,1,?)
    """, (lum_id, data.zona_id, data.lat, data.lng, data.calle, data.numero_poste,
          data.estado, data.tipo, data.altura_m, data.radio_cobertura_m, data.notas))
    conn.commit(); conn.close()
    # Registramos la inserción en el log para trazabilidad de la captura de campo
    logger.info("Luminaria %s registrada en %s — %s", lum_id, data.zona_id, data.estado)
    return {"ok": True, "id": lum_id}


@router.post("/campo/terreno-abandonado", summary="Registrar terreno (app móvil)")
def registrar_terreno(data: TerrenoIn):
    # Abrimos la conexión y verificamos que la zona destino existe en la base de datos
    conn = get_connection()
    if not conn.execute("SELECT id FROM zonas_auditadas WHERE id = ?", (data.zona_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Zona {data.zona_id} no existe")
    # Generamos un ID único para el terreno con prefijo TER y 8 caracteres hexadecimales
    ter_id = f"TER-{uuid.uuid4().hex[:8].upper()}"
    # Insertamos el terreno abandonado convirtiendo los booleanos a enteros para SQLite
    conn.execute("""
        INSERT INTO terrenos_abandonados
        (id,zona_id,lat,lng,calle_referencia,area_estimada_m2,nivel_riesgo,
         tiene_acceso_publico,tiempo_abandono,signos_actividad_ilegal,notas)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (ter_id, data.zona_id, data.lat, data.lng, data.calle_referencia,
          data.area_estimada_m2, data.nivel_riesgo,
          # Convertimos los campos booleanos a 0/1 para compatibilidad con SQLite
          1 if data.tiene_acceso_publico else 0,
          data.tiempo_abandono,
          1 if data.signos_actividad_ilegal else 0, data.notas))
    conn.commit(); conn.close()
    return {"ok": True, "id": ter_id}


@router.post("/campo/punto-ciego", summary="Registrar punto ciego (app móvil)")
def registrar_punto_ciego(data: PuntoCiegoIn):
    # Abrimos la conexión y verificamos que la zona existe antes de registrar el punto ciego
    conn = get_connection()
    if not conn.execute("SELECT id FROM zonas_auditadas WHERE id = ?", (data.zona_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Zona {data.zona_id} no existe")
    # Generamos un ID único para el punto ciego con prefijo PC y 8 caracteres hexadecimales
    pc_id = f"PC-{uuid.uuid4().hex[:8].upper()}"
    # Insertamos el punto ciego con su severidad, flujo peatonal e incidentes reportados
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
    # Abrimos la conexión y verificamos que la zona existe antes de registrar la observación
    conn = get_connection()
    if not conn.execute("SELECT id FROM zonas_auditadas WHERE id = ?", (data.zona_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Zona {data.zona_id} no existe")
    # Generamos un ID único para la observación con prefijo OBS y 8 caracteres hexadecimales
    obs_id = f"OBS-{uuid.uuid4().hex[:8].upper()}"
    # Insertamos la observación de calle convirtiendo los booleanos de comercio a enteros
    conn.execute("""
        INSERT INTO observaciones_calle
        (id,zona_id,nombre_calle,estado_pavimento,iluminacion_general,
         nivel_gentrificacion,presencia_comercio_formal,presencia_comercio_informal,
         transito_vehicular,notas)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (obs_id, data.zona_id, data.nombre_calle, data.estado_pavimento,
          data.iluminacion_general, data.nivel_gentrificacion,
          # Convertimos los campos booleanos a 0/1 para compatibilidad con SQLite
          1 if data.presencia_comercio_formal else 0,
          1 if data.presencia_comercio_informal else 0,
          data.transito_vehicular, data.notas))
    conn.commit(); conn.close()
    return {"ok": True, "id": obs_id}
