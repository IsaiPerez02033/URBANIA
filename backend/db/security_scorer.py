"""
URBANIA SEGURIDAD — Motor de Scores + Watsonx AI
=================================================
Calcula el SSU y usa IBM Granite 3-8B para generar
narrativas ejecutivas reales — no textos hardcodeados.

Fallback: si Watsonx no está disponible, usa textos algorítmicos.
"""
# Importamos logging para registrar eventos del motor de scores y fallos de Watsonx
import logging
# Importamos la función de conexión a la base de datos de campo
from db.schema import get_connection

# Creamos el logger específico para el motor de cálculo de scores de seguridad
logger = logging.getLogger("urbania.security_scorer")

# Declaramos los pesos de cada componente del SSU — deben sumar 1.0
PESOS = {
    "iluminacion":    0.35,  # La iluminación tiene el mayor peso por su impacto directo en percepción
    "cobertura_cam":  0.30,  # La cobertura de cámara es el segundo factor más importante
    "infraestructura":0.20,  # El estado físico del entorno construido pesa un 20%
    "entorno":        0.15,  # El contexto socioeconómico completa el 15% restante
}

# Declaramos los umbrales de clasificación del SSU con sus etiquetas, colores y acciones
CLASIFICACIONES = {
    "optima":    {"min": 75, "label": "Seguridad Óptima",    "color": "#1D9E75", "accion": "Zona prioritaria para despliegue"},
    "aceptable": {"min": 50, "label": "Seguridad Aceptable", "color": "#EF9F27", "accion": "Refuerzo puntual recomendado"},
    "deficiente":{"min": 30, "label": "Seguridad Deficiente","color": "#E24B4A", "accion": "Intervención integral necesaria"},
    "critica":   {"min": 0,  "label": "Zona Crítica",        "color": "#7B1C1C", "accion": "No desplegar sin plan de mitigación"},
}


# Retornamos la clave de clasificación correspondiente al score recibido
def _clasificar(score: float) -> str:
    # Iteramos desde la clasificación más alta para retornar la primera que supere el mínimo
    for k, v in CLASIFICACIONES.items():
        if score >= v["min"]:
            return k
    # Retornamos critica como clasificación de último recurso si ninguna condición se cumple
    return "critica"


# Calculamos el score de iluminación de una zona a partir de sus luminarias de campo
def calcular_score_iluminacion(zona_id: str, conn) -> dict:
    # Consultamos el estado y radio de cobertura de todas las luminarias de la zona
    rows = conn.execute(
        "SELECT estado, radio_cobertura_m FROM luminarias WHERE zona_id = ?",
        (zona_id,)
    ).fetchall()

    # Devolvemos score cero con detalle explicativo si no hay luminarias registradas en campo
    if not rows:
        return {"score": 0.0, "total": 0, "ok": 0, "mal": 0,
                "vandalizadas": 0, "cobertura_pct": 0,
                "detalle": "Sin datos de campo registrados"}

    # Asignamos un peso numérico a cada estado de luminaria para calcular el score ponderado
    pesos = {"funciona": 1.0, "tenue": 0.5, "no_funciona": 0.0,
             "vandalizada": -0.2, "inexistente": 0.0}  # Las vandalizadas penalizan negativamente
    total = len(rows)
    # Calculamos el score promedio ponderado y lo escalamos a 100, garantizando mínimo de 0
    score_raw = max(0, sum(pesos.get(r["estado"], 0) for r in rows) / total)
    score = round(score_raw * 100, 1)
    # Contamos las luminarias en cada categoría de estado para el breakdown del reporte
    ok          = sum(1 for r in rows if r["estado"] == "funciona")
    mal         = sum(1 for r in rows if r["estado"] in ("no_funciona", "vandalizada", "inexistente"))
    vandalizadas= sum(1 for r in rows if r["estado"] == "vandalizada")

    # Devolvemos el score con todos los conteos para el breakdown de iluminación
    return {
        "score": score, "total": total, "ok": ok, "mal": mal,
        "vandalizadas": vandalizadas,
        "cobertura_pct": round(ok / total * 100, 1),
        "detalle": f"{ok}/{total} luminarias operativas verificadas en campo",
    }


# Calculamos el score de cobertura de cámara penalizando por puntos ciegos identificados
def calcular_score_cobertura_camara(zona_id: str, conn) -> dict:
    # Consultamos todos los puntos ciegos de la zona con sus atributos de severidad y flujo
    puntos = conn.execute(
        "SELECT tipo_punto_ciego, severidad, flujo_peatonal, incidentes_reportados "
        "FROM puntos_ciegos WHERE zona_id = ?", (zona_id,)
    ).fetchall()

    # Asumimos cobertura base de 60 si no hay auditoría de puntos ciegos registrada
    if not puntos:
        return {"score": 60.0, "n_puntos_ciegos": 0, "criticos": 0,
                "detalle": "Sin auditoría de cobertura registrada"}

    # Acumulamos la penalización total y contamos los puntos ciegos de severidad crítica
    pen = 0
    criticos = 0
    for p in puntos:
        # Asignamos la penalización base según la severidad del punto ciego
        base  = {"critica": 25, "alta": 15, "media": 8}.get(p["severidad"], 5)
        # Multiplicamos la penalización por el factor de flujo peatonal para amplificar el riesgo real
        flujo = {"alto": 1.5, "medio": 1.0, "bajo": 0.6}.get(p["flujo_peatonal"], 1.0)
        # Sumamos la penalización base ajustada más la penalización por incidentes reportados (máx 15)
        pen  += base * flujo + min(p["incidentes_reportados"] * 3, 15)
        if p["severidad"] == "critica":
            criticos += 1

    # El score de cobertura es 100 menos la penalización acumulada, con mínimo de 0
    score = round(max(0, 100 - pen), 1)
    return {
        "score": score, "n_puntos_ciegos": len(puntos), "criticos": criticos,
        "detalle": f"{len(puntos)} puntos ciegos — {criticos} críticos identificados",
    }


# Calculamos el score de infraestructura combinando penalización de terrenos y calidad vial
def calcular_score_infraestructura(zona_id: str, conn) -> dict:
    # Consultamos los terrenos abandonados con su nivel de riesgo y signos de actividad ilegal
    terrenos = conn.execute(
        "SELECT nivel_riesgo, area_estimada_m2, signos_actividad_ilegal "
        "FROM terrenos_abandonados WHERE zona_id = ?", (zona_id,)
    ).fetchall()
    # Consultamos el estado del pavimento de las calles observadas en campo
    calles = conn.execute(
        "SELECT estado_pavimento FROM observaciones_calle WHERE zona_id = ?",
        (zona_id,)
    ).fetchall()

    # Calculamos la penalización por terrenos abandonados acumulando penalidades por riesgo
    pen_ter = 0
    for t in terrenos:
        # Asignamos la penalización base según el nivel de riesgo del terreno
        base = {"alto": 20, "medio": 12, "bajo": 5}.get(t["nivel_riesgo"], 10)
        # Amplificamos la penalización si el terreno tiene signos de actividad ilegal
        if t["signos_actividad_ilegal"]:
            base *= 1.5
        pen_ter += base
    # El score de terrenos es 100 menos la penalización total acumulada
    score_ter = max(0, 100 - pen_ter)

    # Mapeamos cada estado de pavimento a su score numérico correspondiente
    pav_pesos = {"bueno": 100, "regular": 65, "malo": 30, "critico": 10}
    # Calculamos el score promedio de pavimento; usamos 50 como neutro si no hay calles
    score_pav = (
        sum(pav_pesos.get(c["estado_pavimento"], 50) for c in calles) / len(calles)
        if calles else 50.0
    )
    # Combinamos el score de terrenos (65%) y el de pavimento (35%) en el score final
    score = round(score_ter * 0.65 + score_pav * 0.35, 1)
    return {
        "score": score,
        "n_terrenos_abandonados": len(terrenos),
        "score_terrenos": round(score_ter, 1),
        "score_pavimento": round(score_pav, 1),
        "detalle": f"{len(terrenos)} terrenos abandonados · {len(calles)} calles auditadas",
    }


# Calculamos el score de entorno socioeconómico a partir de las observaciones de calle
def calcular_score_entorno(zona_id: str, conn) -> dict:
    # Consultamos las observaciones de calle con variables de contexto urbano y social
    obs = conn.execute(
        "SELECT nivel_gentrificacion, presencia_comercio_formal, "
        "iluminacion_general, transito_vehicular "
        "FROM observaciones_calle WHERE zona_id = ?", (zona_id,)
    ).fetchall()

    # Devolvemos score neutro de 50 si no hay observaciones de calle registradas en campo
    if not obs:
        return {"score": 50.0, "nivel_gentrificacion_predominante": "desconocido",
                "n_calles_observadas": 0, "detalle": "Sin observaciones registradas"}

    # Mapeamos el nivel de gentrificación a su score de entorno correspondiente
    gent_p = {"alto": 85, "en_proceso": 65, "bajo": 45, "deterioro": 15}
    # Mapeamos la iluminación general observada a su score numérico
    ilum_p = {"buena": 90, "regular": 60, "mala": 30, "nula": 5}
    # Calculamos el score de entorno por calle como promedio de los tres indicadores
    scores = []
    for o in obs:
        scores.append((
            gent_p.get(o["nivel_gentrificacion"], 45) +
            ilum_p.get(o["iluminacion_general"], 50) +
            # Asignamos 70 si hay comercio formal, 30 si no, como proxy de vitalidad urbana
            (70 if o["presencia_comercio_formal"] else 30)
        ) / 3)

    # Retornamos el promedio de todos los scores de calle con el nivel predominante de la zona
    return {
        "score": round(sum(scores) / len(scores), 1),
        # Usamos el nivel de gentrificación de la primera observación como indicador de zona
        "nivel_gentrificacion_predominante": obs[0]["nivel_gentrificacion"],
        "n_calles_observadas": len(obs),
        "detalle": f"Entorno {obs[0]['nivel_gentrificacion']} · {len(obs)} calles observadas",
    }


# Calculamos el SSU completo de una zona incluyendo narrativa IA opcional con Granite 3-8B
def calcular_ssu_zona(zona_id: str, usar_watsonx: bool = True) -> dict:
    """
    Calcula SSU completo para una zona.
    Si usar_watsonx=True y hay credenciales, usa Granite 3-8B para narrativas.
    """
    # Abrimos la conexión para leer todos los datos de campo de la zona
    conn = get_connection()
    try:
        # Buscamos la zona en la tabla de zonas auditadas por su ID
        zona = conn.execute(
            "SELECT * FROM zonas_auditadas WHERE id = ?", (zona_id,)
        ).fetchone()
        if not zona:
            raise ValueError(f"Zona {zona_id} no encontrada")

        # Convertimos la fila SQLite a diccionario para facilitar el acceso por clave
        zona_dict = dict(zona)

        # Calculamos los cuatro scores de componente usando los datos de campo
        ilum    = calcular_score_iluminacion(zona_id, conn)
        cam     = calcular_score_cobertura_camara(zona_id, conn)
        infra   = calcular_score_infraestructura(zona_id, conn)
        entorno = calcular_score_entorno(zona_id, conn)

        # Calculamos el SSU final como suma ponderada de los cuatro scores de componente
        ssu = round(
            ilum["score"]    * PESOS["iluminacion"] +
            cam["score"]     * PESOS["cobertura_cam"] +
            infra["score"]   * PESOS["infraestructura"] +
            entorno["score"] * PESOS["entorno"],
            1
        )
        # Clasificamos el SSU y obtenemos la metadata de color, etiqueta y acción
        clasificacion = _clasificar(ssu)
        meta = CLASIFICACIONES[clasificacion]

        # Persistimos el score calculado en la tabla de historial para consultas rápidas futuras
        conn.execute("""
            INSERT OR REPLACE INTO score_seguridad_zona
            (zona_id, score_iluminacion, score_cobertura_camara,
             score_infraestructura, score_entorno, score_total,
             clasificacion, n_luminarias_ok, n_puntos_ciegos,
             n_terrenos_abandonados, calculado_en)
            VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))
        """, (
            zona_id, ilum["score"], cam["score"], infra["score"],
            entorno["score"], ssu, clasificacion,
            ilum.get("ok", 0), cam.get("n_puntos_ciegos", 0),
            infra.get("n_terrenos_abandonados", 0),
        ))
        conn.commit()

        # Construimos el diccionario de breakdown enriqueciendo cada componente con su peso y aportación
        breakdown = {
            "iluminacion":      {**ilum,    "peso": PESOS["iluminacion"],    "ponderado": round(ilum["score"]    * PESOS["iluminacion"], 1)},
            "cobertura_camara": {**cam,     "peso": PESOS["cobertura_cam"],  "ponderado": round(cam["score"]     * PESOS["cobertura_cam"], 1)},
            "infraestructura":  {**infra,   "peso": PESOS["infraestructura"],"ponderado": round(infra["score"]   * PESOS["infraestructura"], 1)},
            "entorno":          {**entorno, "peso": PESOS["entorno"],        "ponderado": round(entorno["score"] * PESOS["entorno"], 1)},
        }

        # ── Narrativas con Granite 3-8B ──────────────────────────────────────
        # Inicializamos la narrativa vacía y el indicador de uso de Watsonx
        narrativa_ia = ""
        watsonx_usado = False

        if usar_watsonx:
            # Importamos el cliente de Watsonx de forma diferida para evitar carga innecesaria
            from utils.watsonx_client import get_watsonx_client
            wx = get_watsonx_client()
            if wx.is_available():
                try:
                    # Solicitamos la narrativa ejecutiva al modelo Granite 3-8B
                    narrativa_ia = wx.narrativa_zona(zona_dict, ssu, breakdown)
                    watsonx_usado = True
                    logger.info("Granite generó narrativa para %s (%d chars)",
                                zona_dict["nombre"], len(narrativa_ia))
                except Exception as e:
                    # Registramos el fallo pero continuamos con el fallback algorítmico
                    logger.warning("Watsonx falló para %s: %s", zona_dict["nombre"], e)

        # Usamos la narrativa de fallback algorítmico si Watsonx no generó texto
        if not narrativa_ia:
            narrativa_ia = _narrativa_fallback(zona_dict, ssu, clasificacion, ilum, cam)

        # ── Recomendaciones por cliente ──────────────────────────────────────
        # Generamos las recomendaciones especializadas para los tres perfiles de cliente
        recomendaciones = _generar_recomendaciones_con_ia(
            zona_dict, ssu, clasificacion, breakdown, usar_watsonx
        )

        # Devolvemos el resultado completo con SSU, narrativa, breakdown y recomendaciones
        return {
            "zona_id": zona_id,
            "nombre": zona_dict["nombre"],
            "alcaldia": zona_dict["alcaldia"],
            "colonia": zona_dict["colonia"],
            "lat": zona_dict["lat_centro"],
            "lng": zona_dict["lng_centro"],
            "ssu": ssu,
            "clasificacion": clasificacion,
            "clasificacion_label": meta["label"],
            "color": meta["color"],
            "accion_recomendada": meta["accion"],
            "narrativa_ia": narrativa_ia,
            "watsonx_usado": watsonx_usado,
            "breakdown": breakdown,
            "recomendaciones": recomendaciones,
            "fuente_datos": "XOLUM Campo Propio — verificado en sitio",
            "fecha_auditoria": zona_dict["fecha_auditoria"],
        }
    finally:
        # Cerramos la conexión siempre, incluso si ocurre una excepción en el cálculo
        conn.close()


# Generamos una narrativa textual algorítmica cuando Watsonx no está disponible
def _narrativa_fallback(zona, ssu, clasificacion, ilum, cam) -> str:
    """Narrativa algorítmica cuando Watsonx no está disponible."""
    nombre = zona["nombre"]
    # Retornamos el texto según la clasificación de seguridad de la zona
    if clasificacion == "optima":
        # Destacamos las condiciones favorables para justificar el despliegue sin restricciones
        return (
            f"{nombre} presenta un SSU de {ssu:.0f}/100, clasificada como Seguridad Óptima. "
            f"Con {ilum.get('ok', 0)}/{ilum.get('total', 0)} luminarias operativas y cobertura "
            f"de cámara de {cam.get('score', 0):.0f}/100, la zona ofrece condiciones favorables "
            f"para despliegue de infraestructura sin mitigación adicional."
        )
    elif clasificacion == "aceptable":
        # Indicamos las brechas específicas que deben atenderse para viabilizar la inversión
        return (
            f"{nombre} tiene un SSU de {ssu:.0f}/100. "
            f"La zona es viable para inversión con refuerzo puntual en iluminación "
            f"({ilum.get('mal', 0)} luminarias fuera de servicio) y atención a "
            f"{cam.get('n_puntos_ciegos', 0)} puntos ciegos identificados."
        )
    elif clasificacion == "deficiente":
        # Enfatizamos la necesidad de intervención previa antes de cualquier despliegue
        return (
            f"{nombre} muestra deficiencias de seguridad (SSU {ssu:.0f}/100). "
            f"Se requiere intervención en iluminación y cobertura de cámara antes de "
            f"cualquier despliegue. Evaluar plan de mitigación con autoridades locales."
        )
    else:
        # Emitimos alerta crítica para zonas que no deben ser consideradas sin rehabilitación previa
        return (
            f"ALERTA: {nombre} registra SSU crítico de {ssu:.0f}/100. "
            f"Alta incidencia de infraestructura vandalizadas "
            f"({ilum.get('vandalizadas', 0)} luminarias) y múltiples puntos ciegos críticos. "
            f"NO se recomienda inversión sin plan de rehabilitación previo."
        )


# Generamos las recomendaciones especializadas por tipo de cliente usando Granite o fallback
def _generar_recomendaciones_con_ia(zona, ssu, clasificacion, breakdown, usar_watsonx) -> dict:
    """Genera recomendaciones por cliente — con Granite si está disponible."""
    # Extraemos los cuatro breakdowns para usarlos en las recomendaciones de cada perfil
    ilum    = breakdown["iluminacion"]
    cam     = breakdown["cobertura_camara"]
    infra   = breakdown["infraestructura"]
    entorno = breakdown["entorno"]

    # Inicializamos los textos de recomendación vacíos para los tres perfiles de cliente
    wx_rec = {"videovig": "", "constructora": "", "inmobiliaria": ""}

    if usar_watsonx:
        # Importamos el cliente de Watsonx de forma diferida para evitar carga al importar el módulo
        from utils.watsonx_client import get_watsonx_client
        wx = get_watsonx_client()
        if wx.is_available():
            # Generamos la recomendación para empresa de videovigilancia con Granite
            try:
                wx_rec["videovig"]    = wx.recomendacion_videovigilancia(zona, cam, ilum)
            except Exception as e:
                logger.warning("Watsonx videovig falló: %s", e)
            # Generamos la recomendación para constructoras y obras públicas con Granite
            try:
                wx_rec["constructora"] = wx.recomendacion_constructora(zona, ssu, infra, entorno)
            except Exception as e:
                logger.warning("Watsonx constructora falló: %s", e)
            # Generamos la recomendación para desarrolladoras inmobiliarias con Granite
            try:
                wx_rec["inmobiliaria"] = wx.recomendacion_inmobiliaria(zona, ssu, entorno, infra)
            except Exception as e:
                logger.warning("Watsonx inmobiliaria falló: %s", e)

    nombre = zona["nombre"]

    # Generamos el texto de fallback para empresa de videovigilancia cuando Granite no responde
    def _fallback_videovig():
        n_pc = cam.get("n_puntos_ciegos", 0)
        crit = cam.get("criticos", 0)
        if n_pc == 0:
            return f"{nombre} tiene buena cobertura de cámara actual. Se recomienda mantenimiento preventivo y auditoría semestral para mantener el estándar."
        return (
            f"Se identificaron {n_pc} puntos ciegos en {nombre}, "
            f"de los cuales {crit} son críticos con flujo peatonal alto — "
            f"oportunidad directa de venta e instalación. "
            f"Priorizar cámaras con visión nocturna dada la deficiencia de iluminación ({ilum.get('mal',0)} postes fuera de servicio)."
        )

    # Generamos el texto de fallback para constructoras cuando Granite no responde
    def _fallback_constructora():
        viable = ssu >= 50
        return (
            f"{nombre} {'es viable' if viable else 'requiere rehabilitación previa'} para obra pública (SSU {ssu:.0f}/100). "
            f"{'La propuesta técnica debe incluir reposición de ' + str(ilum.get('mal',0)) + ' luminarias.' if ilum.get('mal',0) > 0 else 'Infraestructura vial en condiciones aceptables.'} "
            f"El nivel de gentrificación '{entorno.get('nivel_gentrificacion_predominante','')}' favorece la valorización post-obra."
        )

    # Generamos el texto de fallback para desarrolladoras inmobiliarias cuando Granite no responde
    def _fallback_inmobiliaria():
        gent = entorno.get("nivel_gentrificacion_predominante", "bajo")
        # Mapeamos el nivel de gentrificación a su descripción de potencial de inversión
        potencial = {"alto": "alta plusvalía consolidada", "en_proceso": "tendencia de valorización activa", "bajo": "zona estable sin dinamismo evidente", "deterioro": "riesgo de pérdida de valor"}.get(gent, "")
        return (
            f"{nombre} presenta {potencial} con SSU {ssu:.0f}/100. "
            f"{'Los ' + str(infra.get('n_terrenos_abandonados',0)) + ' terrenos abandonados representan oportunidad de adquisición a precio bajo.' if infra.get('n_terrenos_abandonados',0) > 0 else 'Sin terrenos abandonados de riesgo identificados.'} "
            f"El score de seguridad auditado por XOLUM es argumento válido para due diligence ante fondos de inversión."
        )

    # Construimos y retornamos el diccionario con las recomendaciones para los tres perfiles
    return {
        "constructora_gobierno": {
            "titulo": "Para Constructoras / Licitación de Obra Pública",
            # Usamos la narrativa de Granite si está disponible, sino el fallback algorítmico
            "oportunidad": wx_rec["constructora"] or _fallback_constructora(),
            "generado_con": "IBM Granite 3-8B" if wx_rec["constructora"] else "Fallback algorítmico",
            "puntos_clave": [
                f"SSU: {ssu:.0f}/100 — {CLASIFICACIONES[clasificacion]['label']}",
                f"Luminarias a reponer: {ilum.get('mal',0)} verificadas en campo",
                f"Terrenos con potencial de intervención: {infra.get('n_terrenos_abandonados',0)}",
                f"Gentrificación: {entorno.get('nivel_gentrificacion_predominante','')} (define plusvalía post-obra)",
                "Datos campo XOLUM — no dependen de registros gubernamentales desactualizados",
            ],
            # Incluimos alerta solo si la zona no alcanza el umbral mínimo de viabilidad
            "alerta": f"Zona requiere plan de rehabilitación previo" if ssu < 50 else None,
        },
        "empresa_videovigilancia": {
            "titulo": "Para Empresas de Videovigilancia / Instaladoras de Cámaras",
            "oportunidad": wx_rec["videovig"] or _fallback_videovig(),
            "generado_con": "IBM Granite 3-8B" if wx_rec["videovig"] else "Fallback algorítmico",
            "puntos_clave": [
                f"Puntos ciegos críticos: {cam.get('criticos',0)} — instalación justificada",
                f"Score cobertura actual: {cam.get('score',0):.0f}/100",
                f"Luminarias fuera de servicio: {ilum.get('mal',0)} — sinergia cámara+iluminación integrada",
                "Mapa georreferenciado de puntos ciegos disponible para propuesta técnica",
            ],
            # Incluimos alerta solo si hay puntos críticos con incidentes reportados
            "alerta": f"{cam.get('criticos',0)} puntos críticos con incidentes reportados" if cam.get("criticos", 0) > 0 else None,
        },
        "desarrolladora_inmobiliaria": {
            "titulo": "Para Desarrolladoras Inmobiliarias",
            "oportunidad": wx_rec["inmobiliaria"] or _fallback_inmobiliaria(),
            "generado_con": "IBM Granite 3-8B" if wx_rec["inmobiliaria"] else "Fallback algorítmico",
            "puntos_clave": [
                f"Gentrificación: {entorno.get('nivel_gentrificacion_predominante','')} — tendencia de valor",
                f"Estado vial: {infra.get('score_pavimento',0):.0f}/100",
                f"Terrenos abandonados identificados: {infra.get('n_terrenos_abandonados',0)}",
                "SSU auditado es argumento para due diligence ante fondos de inversión",
            ],
            # Alertamos si el entorno está en proceso activo de deterioro urbano
            "alerta": "Zona en deterioro activo" if entorno.get("nivel_gentrificacion_predominante") == "deterioro" else None,
        },
    }


# Calculamos el SSU de todas las zonas auditadas y las devolvemos ordenadas por score
def calcular_todas_las_zonas(usar_watsonx: bool = False) -> list:
    """
    Calcula SSU para todas las zonas.
    usar_watsonx=False por defecto para el listado rápido (evita latencia en masa).
    La narrativa IA se carga on-demand al seleccionar una zona específica.
    """
    # Obtenemos solo los IDs de zonas auditadas para iterar sin cargar datos innecesarios
    conn = get_connection()
    zonas = conn.execute("SELECT id FROM zonas_auditadas").fetchall()
    conn.close()

    # Calculamos el SSU de cada zona individualmente, capturando errores por zona sin detener el proceso
    results = []
    for z in zonas:
        try:
            r = calcular_ssu_zona(z["id"], usar_watsonx=usar_watsonx)
            results.append(r)
        except Exception as e:
            # Registramos el error de la zona problemática y continuamos con las siguientes
            logger.error("Error SSU %s: %s", z["id"], e)

    # Ordenamos de mayor a menor SSU para que el listado muestre primero las zonas más seguras
    results.sort(key=lambda x: x["ssu"], reverse=True)
    return results
