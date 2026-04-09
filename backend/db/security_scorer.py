"""
URBANIA SEGURIDAD — Motor de Scores + Watsonx AI
=================================================
Calcula el SSU y usa IBM Granite 3-8B para generar
narrativas ejecutivas reales — no textos hardcodeados.

Fallback: si Watsonx no está disponible, usa textos algorítmicos.
"""
import logging
from db.schema import get_connection

logger = logging.getLogger("urbania.security_scorer")

PESOS = {
    "iluminacion":    0.35,
    "cobertura_cam":  0.30,
    "infraestructura":0.20,
    "entorno":        0.15,
}

CLASIFICACIONES = {
    "optima":    {"min": 75, "label": "Seguridad Óptima",    "color": "#1D9E75", "accion": "Zona prioritaria para despliegue"},
    "aceptable": {"min": 50, "label": "Seguridad Aceptable", "color": "#EF9F27", "accion": "Refuerzo puntual recomendado"},
    "deficiente":{"min": 30, "label": "Seguridad Deficiente","color": "#E24B4A", "accion": "Intervención integral necesaria"},
    "critica":   {"min": 0,  "label": "Zona Crítica",        "color": "#7B1C1C", "accion": "No desplegar sin plan de mitigación"},
}


def _clasificar(score: float) -> str:
    for k, v in CLASIFICACIONES.items():
        if score >= v["min"]:
            return k
    return "critica"


def calcular_score_iluminacion(zona_id: str, conn) -> dict:
    rows = conn.execute(
        "SELECT estado, radio_cobertura_m FROM luminarias WHERE zona_id = ?",
        (zona_id,)
    ).fetchall()

    if not rows:
        return {"score": 0.0, "total": 0, "ok": 0, "mal": 0,
                "vandalizadas": 0, "cobertura_pct": 0,
                "detalle": "Sin datos de campo registrados"}

    pesos = {"funciona": 1.0, "tenue": 0.5, "no_funciona": 0.0,
             "vandalizada": -0.2, "inexistente": 0.0}
    total = len(rows)
    score_raw = max(0, sum(pesos.get(r["estado"], 0) for r in rows) / total)
    score = round(score_raw * 100, 1)
    ok          = sum(1 for r in rows if r["estado"] == "funciona")
    mal         = sum(1 for r in rows if r["estado"] in ("no_funciona", "vandalizada", "inexistente"))
    vandalizadas= sum(1 for r in rows if r["estado"] == "vandalizada")

    return {
        "score": score, "total": total, "ok": ok, "mal": mal,
        "vandalizadas": vandalizadas,
        "cobertura_pct": round(ok / total * 100, 1),
        "detalle": f"{ok}/{total} luminarias operativas verificadas en campo",
    }


def calcular_score_cobertura_camara(zona_id: str, conn) -> dict:
    puntos = conn.execute(
        "SELECT tipo_punto_ciego, severidad, flujo_peatonal, incidentes_reportados "
        "FROM puntos_ciegos WHERE zona_id = ?", (zona_id,)
    ).fetchall()

    if not puntos:
        return {"score": 60.0, "n_puntos_ciegos": 0, "criticos": 0,
                "detalle": "Sin auditoría de cobertura registrada"}

    pen = 0
    criticos = 0
    for p in puntos:
        base  = {"critica": 25, "alta": 15, "media": 8}.get(p["severidad"], 5)
        flujo = {"alto": 1.5, "medio": 1.0, "bajo": 0.6}.get(p["flujo_peatonal"], 1.0)
        pen  += base * flujo + min(p["incidentes_reportados"] * 3, 15)
        if p["severidad"] == "critica":
            criticos += 1

    score = round(max(0, 100 - pen), 1)
    return {
        "score": score, "n_puntos_ciegos": len(puntos), "criticos": criticos,
        "detalle": f"{len(puntos)} puntos ciegos — {criticos} críticos identificados",
    }


def calcular_score_infraestructura(zona_id: str, conn) -> dict:
    terrenos = conn.execute(
        "SELECT nivel_riesgo, area_estimada_m2, signos_actividad_ilegal "
        "FROM terrenos_abandonados WHERE zona_id = ?", (zona_id,)
    ).fetchall()
    calles = conn.execute(
        "SELECT estado_pavimento FROM observaciones_calle WHERE zona_id = ?",
        (zona_id,)
    ).fetchall()

    pen_ter = 0
    for t in terrenos:
        base = {"alto": 20, "medio": 12, "bajo": 5}.get(t["nivel_riesgo"], 10)
        if t["signos_actividad_ilegal"]:
            base *= 1.5
        pen_ter += base
    score_ter = max(0, 100 - pen_ter)

    pav_pesos = {"bueno": 100, "regular": 65, "malo": 30, "critico": 10}
    score_pav = (
        sum(pav_pesos.get(c["estado_pavimento"], 50) for c in calles) / len(calles)
        if calles else 50.0
    )
    score = round(score_ter * 0.65 + score_pav * 0.35, 1)
    return {
        "score": score,
        "n_terrenos_abandonados": len(terrenos),
        "score_terrenos": round(score_ter, 1),
        "score_pavimento": round(score_pav, 1),
        "detalle": f"{len(terrenos)} terrenos abandonados · {len(calles)} calles auditadas",
    }


def calcular_score_entorno(zona_id: str, conn) -> dict:
    obs = conn.execute(
        "SELECT nivel_gentrificacion, presencia_comercio_formal, "
        "iluminacion_general, transito_vehicular "
        "FROM observaciones_calle WHERE zona_id = ?", (zona_id,)
    ).fetchall()

    if not obs:
        return {"score": 50.0, "nivel_gentrificacion_predominante": "desconocido",
                "n_calles_observadas": 0, "detalle": "Sin observaciones registradas"}

    gent_p = {"alto": 85, "en_proceso": 65, "bajo": 45, "deterioro": 15}
    ilum_p = {"buena": 90, "regular": 60, "mala": 30, "nula": 5}
    scores = []
    for o in obs:
        scores.append((
            gent_p.get(o["nivel_gentrificacion"], 45) +
            ilum_p.get(o["iluminacion_general"], 50) +
            (70 if o["presencia_comercio_formal"] else 30)
        ) / 3)

    return {
        "score": round(sum(scores) / len(scores), 1),
        "nivel_gentrificacion_predominante": obs[0]["nivel_gentrificacion"],
        "n_calles_observadas": len(obs),
        "detalle": f"Entorno {obs[0]['nivel_gentrificacion']} · {len(obs)} calles observadas",
    }


def calcular_ssu_zona(zona_id: str, usar_watsonx: bool = True) -> dict:
    """
    Calcula SSU completo para una zona.
    Si usar_watsonx=True y hay credenciales, usa Granite 3-8B para narrativas.
    """
    conn = get_connection()
    try:
        zona = conn.execute(
            "SELECT * FROM zonas_auditadas WHERE id = ?", (zona_id,)
        ).fetchone()
        if not zona:
            raise ValueError(f"Zona {zona_id} no encontrada")

        zona_dict = dict(zona)

        ilum    = calcular_score_iluminacion(zona_id, conn)
        cam     = calcular_score_cobertura_camara(zona_id, conn)
        infra   = calcular_score_infraestructura(zona_id, conn)
        entorno = calcular_score_entorno(zona_id, conn)

        ssu = round(
            ilum["score"]    * PESOS["iluminacion"] +
            cam["score"]     * PESOS["cobertura_cam"] +
            infra["score"]   * PESOS["infraestructura"] +
            entorno["score"] * PESOS["entorno"],
            1
        )
        clasificacion = _clasificar(ssu)
        meta = CLASIFICACIONES[clasificacion]

        # Persistir en BD
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

        breakdown = {
            "iluminacion":      {**ilum,    "peso": PESOS["iluminacion"],    "ponderado": round(ilum["score"]    * PESOS["iluminacion"], 1)},
            "cobertura_camara": {**cam,     "peso": PESOS["cobertura_cam"],  "ponderado": round(cam["score"]     * PESOS["cobertura_cam"], 1)},
            "infraestructura":  {**infra,   "peso": PESOS["infraestructura"],"ponderado": round(infra["score"]   * PESOS["infraestructura"], 1)},
            "entorno":          {**entorno, "peso": PESOS["entorno"],        "ponderado": round(entorno["score"] * PESOS["entorno"], 1)},
        }

        # ── Narrativas con Granite 3-8B ──────────────────────────────────────
        narrativa_ia = ""
        watsonx_usado = False

        if usar_watsonx:
            from utils.watsonx_client import get_watsonx_client
            wx = get_watsonx_client()
            if wx.is_available():
                try:
                    narrativa_ia = wx.narrativa_zona(zona_dict, ssu, breakdown)
                    watsonx_usado = True
                    logger.info("Granite generó narrativa para %s (%d chars)",
                                zona_dict["nombre"], len(narrativa_ia))
                except Exception as e:
                    logger.warning("Watsonx falló para %s: %s", zona_dict["nombre"], e)

        if not narrativa_ia:
            narrativa_ia = _narrativa_fallback(zona_dict, ssu, clasificacion, ilum, cam)

        # ── Recomendaciones por cliente ──────────────────────────────────────
        recomendaciones = _generar_recomendaciones_con_ia(
            zona_dict, ssu, clasificacion, breakdown, usar_watsonx
        )

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
        conn.close()


def _narrativa_fallback(zona, ssu, clasificacion, ilum, cam) -> str:
    """Narrativa algorítmica cuando Watsonx no está disponible."""
    nombre = zona["nombre"]
    if clasificacion == "optima":
        return (
            f"{nombre} presenta un SSU de {ssu:.0f}/100, clasificada como Seguridad Óptima. "
            f"Con {ilum.get('ok', 0)}/{ilum.get('total', 0)} luminarias operativas y cobertura "
            f"de cámara de {cam.get('score', 0):.0f}/100, la zona ofrece condiciones favorables "
            f"para despliegue de infraestructura sin mitigación adicional."
        )
    elif clasificacion == "aceptable":
        return (
            f"{nombre} tiene un SSU de {ssu:.0f}/100. "
            f"La zona es viable para inversión con refuerzo puntual en iluminación "
            f"({ilum.get('mal', 0)} luminarias fuera de servicio) y atención a "
            f"{cam.get('n_puntos_ciegos', 0)} puntos ciegos identificados."
        )
    elif clasificacion == "deficiente":
        return (
            f"{nombre} muestra deficiencias de seguridad (SSU {ssu:.0f}/100). "
            f"Se requiere intervención en iluminación y cobertura de cámara antes de "
            f"cualquier despliegue. Evaluar plan de mitigación con autoridades locales."
        )
    else:
        return (
            f"ALERTA: {nombre} registra SSU crítico de {ssu:.0f}/100. "
            f"Alta incidencia de infraestructura vandalizadas "
            f"({ilum.get('vandalizadas', 0)} luminarias) y múltiples puntos ciegos críticos. "
            f"NO se recomienda inversión sin plan de rehabilitación previo."
        )


def _generar_recomendaciones_con_ia(zona, ssu, clasificacion, breakdown, usar_watsonx) -> dict:
    """Genera recomendaciones por cliente — con Granite si está disponible."""
    ilum    = breakdown["iluminacion"]
    cam     = breakdown["cobertura_camara"]
    infra   = breakdown["infraestructura"]
    entorno = breakdown["entorno"]

    wx_rec = {"videovig": "", "constructora": "", "inmobiliaria": ""}

    if usar_watsonx:
        from utils.watsonx_client import get_watsonx_client
        wx = get_watsonx_client()
        if wx.is_available():
            try:
                wx_rec["videovig"]    = wx.recomendacion_videovigilancia(zona, cam, ilum)
            except Exception as e:
                logger.warning("Watsonx videovig falló: %s", e)
            try:
                wx_rec["constructora"] = wx.recomendacion_constructora(zona, ssu, infra, entorno)
            except Exception as e:
                logger.warning("Watsonx constructora falló: %s", e)
            try:
                wx_rec["inmobiliaria"] = wx.recomendacion_inmobiliaria(zona, ssu, entorno, infra)
            except Exception as e:
                logger.warning("Watsonx inmobiliaria falló: %s", e)

    nombre = zona["nombre"]

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

    def _fallback_constructora():
        viable = ssu >= 50
        return (
            f"{nombre} {'es viable' if viable else 'requiere rehabilitación previa'} para obra pública (SSU {ssu:.0f}/100). "
            f"{'La propuesta técnica debe incluir reposición de ' + str(ilum.get('mal',0)) + ' luminarias.' if ilum.get('mal',0) > 0 else 'Infraestructura vial en condiciones aceptables.'} "
            f"El nivel de gentrificación '{entorno.get('nivel_gentrificacion_predominante','')}' favorece la valorización post-obra."
        )

    def _fallback_inmobiliaria():
        gent = entorno.get("nivel_gentrificacion_predominante", "bajo")
        potencial = {"alto": "alta plusvalía consolidada", "en_proceso": "tendencia de valorización activa", "bajo": "zona estable sin dinamismo evidente", "deterioro": "riesgo de pérdida de valor"}.get(gent, "")
        return (
            f"{nombre} presenta {potencial} con SSU {ssu:.0f}/100. "
            f"{'Los ' + str(infra.get('n_terrenos_abandonados',0)) + ' terrenos abandonados representan oportunidad de adquisición a precio bajo.' if infra.get('n_terrenos_abandonados',0) > 0 else 'Sin terrenos abandonados de riesgo identificados.'} "
            f"El score de seguridad auditado por XOLUM es argumento válido para due diligence ante fondos de inversión."
        )

    return {
        "constructora_gobierno": {
            "titulo": "Para Constructoras / Licitación de Obra Pública",
            "oportunidad": wx_rec["constructora"] or _fallback_constructora(),
            "generado_con": "IBM Granite 3-8B" if wx_rec["constructora"] else "Fallback algorítmico",
            "puntos_clave": [
                f"SSU: {ssu:.0f}/100 — {CLASIFICACIONES[clasificacion]['label']}",
                f"Luminarias a reponer: {ilum.get('mal',0)} verificadas en campo",
                f"Terrenos con potencial de intervención: {infra.get('n_terrenos_abandonados',0)}",
                f"Gentrificación: {entorno.get('nivel_gentrificacion_predominante','')} (define plusvalía post-obra)",
                "Datos campo XOLUM — no dependen de registros gubernamentales desactualizados",
            ],
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
            "alerta": "Zona en deterioro activo" if entorno.get("nivel_gentrificacion_predominante") == "deterioro" else None,
        },
    }


def calcular_todas_las_zonas(usar_watsonx: bool = False) -> list:
    """
    Calcula SSU para todas las zonas.
    usar_watsonx=False por defecto para el listado rápido (evita latencia en masa).
    La narrativa IA se carga on-demand al seleccionar una zona específica.
    """
    conn = get_connection()
    zonas = conn.execute("SELECT id FROM zonas_auditadas").fetchall()
    conn.close()

    results = []
    for z in zonas:
        try:
            r = calcular_ssu_zona(z["id"], usar_watsonx=usar_watsonx)
            results.append(r)
        except Exception as e:
            logger.error("Error SSU %s: %s", z["id"], e)

    results.sort(key=lambda x: x["ssu"], reverse=True)
    return results
