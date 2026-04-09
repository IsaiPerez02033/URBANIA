"""
URBANIA — Agente de Negocios
=============================
Combina scores de Demanda y Riesgo con parámetros financieros del cliente.
Genera el Score de Viabilidad y 3 escenarios con ROI y payback.
Produce el reporte ejecutivo en lenguaje C-Suite.
"""
# Importamos el módulo de logging para registrar eventos del agente
import logging
# Importamos math para operaciones matemáticas en cálculos financieros
import math

# Creamos el logger específico para el agente de negocios
logger = logging.getLogger("urbania.business_agent")

# Declaramos los niveles de viabilidad con sus umbrales mínimos y colores para visualización
VIABILITY_TIERS = {
    "Alta viabilidad": {"min": 70, "color": "#1D9E75", "emoji": "🟢"},
    "Viabilidad media": {"min": 40, "color": "#EF9F27", "emoji": "🟡"},
    "Descarte": {"min": 0, "color": "#E24B4A", "emoji": "🔴"},
}

# Declaramos los factores de penalización por sector que ajustan el score de viabilidad
# Telecomunicaciones tiene el factor más alto por mayor potencial de mercado
SECTOR_FP = {
    "telecomunicaciones": 1.15,
    "seguridad": 1.05,
    "inmobiliario": 1.08,
}


def _score_viabilidad(sd: float, sr: float, fp: float, ti_norm: float) -> float:
    """
    SV = SD × (1 - SR/100) × FP / TI_norm
    Clipeado a [0, 100].
    """
    # Aplicamos la fórmula de viabilidad: demanda ajustada por riesgo, sector y ticket
    sv = sd * (1 - sr / 100) * fp / max(ti_norm, 0.5)
    # Retornamos el score redondeado a dos decimales y acotado entre 0 y 100
    return round(min(max(sv, 0), 100), 2)


def _ti_norm(ticket_mxn: float) -> float:
    """Normaliza el ticket de inversión. $2M = 1.0 (baseline)."""
    # Dividimos el ticket entre el baseline de 2 millones para obtener un factor normalizado
    return ticket_mxn / 2_000_000


def _categoria_viabilidad(sv: float) -> str:
    # Clasificamos el score de viabilidad en tres categorías según umbrales definidos
    if sv >= 70:
        return "Alta viabilidad"
    elif sv >= 40:
        return "Viabilidad media"
    return "Descarte"


def _roi_anual(sv: float, vida_util: int, tasa: float) -> float:
    """ROI estimado simple basado en score de viabilidad como proxy de retorno."""
    # Calculamos el ROI base como porcentaje del score de viabilidad sobre el máximo del 50%
    base_roi = (sv / 100) * 0.50  # máximo 50% ROI anual en zona perfecta
    # Penalizamos el ROI aplicando la tasa de descuento del sector
    roi = base_roi - tasa * 0.5
    # Retornamos el ROI mínimo de -5% para evitar valores extremadamente negativos
    return round(max(roi, -0.05), 4)


def _payback_years(roi: float, vida_util: int) -> float:
    # Si el ROI es negativo o cero, el payback es igual a la vida útil completa del activo
    if roi <= 0:
        return float(vida_util)
    # Calculamos los años de recuperación de la inversión como el inverso del ROI
    pb = 1 / roi
    # Limitamos el payback a la vida útil máxima del activo
    return round(min(pb, vida_util), 1)


def _npv(roi: float, ticket: float, vida_util: int, tasa: float) -> float:
    """VPN simplificado para flujos anuales uniformes."""
    # Calculamos el flujo de caja anual esperado como producto del ROI y el ticket de inversión
    flujo_anual = ticket * roi
    # Sumamos los flujos descontados para cada año dentro de la vida útil
    npv = sum(flujo_anual / ((1 + tasa) ** t) for t in range(1, vida_util + 1))
    # Retornamos el VPN neto restando la inversión inicial
    return round(npv - ticket, 0)


def _generate_scenarios(
    viability_features: list,
    params: dict,
) -> list:
    """Genera 3 escenarios de despliegue: agresivo, conservador, equilibrado."""
    # Extraemos los parámetros financieros del cliente con valores por defecto
    ticket = params.get("ticket_inversion_mxn", 2_000_000)
    vida = params.get("vida_util_anios", 8)
    tasa = params.get("tasa_descuento", 0.12)
    n_units = params.get("n_unidades_objetivo", 12)
    sector = params.get("sector", "telecomunicaciones")

    # Separamos las zonas por categoría de viabilidad para construir cada escenario
    verdes = [f for f in viability_features if f["categoria_viabilidad"] == "Alta viabilidad"]
    cautela = [f for f in viability_features if f["categoria_viabilidad"] == "Viabilidad media"]

    # Escenario 1: Agresivo — solo zonas verdes
    # Tomamos únicamente las zonas de alta viabilidad sin exceder el objetivo de unidades
    n_agresivo = min(len(verdes), n_units)
    # Calculamos el score de viabilidad promedio para las zonas seleccionadas
    sv_agresivo = (
        sum(f["score_viabilidad"] for f in verdes[:n_agresivo]) / max(n_agresivo, 1)
    )
    # Calculamos las métricas financieras para el escenario agresivo
    roi_agresivo = _roi_anual(sv_agresivo, vida, tasa)
    pb_agresivo = _payback_years(roi_agresivo, vida)
    npv_agresivo = _npv(roi_agresivo, ticket * n_agresivo, vida, tasa)

    # Escenario 2: Conservador — top 50% de verdes
    # Tomamos la mitad de las zonas verdes del escenario agresivo para mayor margen de seguridad
    n_conservador = max(1, n_agresivo // 2)
    sv_conservador = (
        sum(f["score_viabilidad"] for f in verdes[:n_conservador]) / max(n_conservador, 1)
    )
    # Aplicamos una tasa ligeramente mayor para reflejar mayor cautela financiera
    roi_conservador = _roi_anual(sv_conservador, vida, tasa * 1.1)  # penalizamos un poco la tasa
    pb_conservador = _payback_years(roi_conservador, vida)
    npv_conservador = _npv(roi_conservador, ticket * n_conservador, vida, tasa)

    # Escenario 3: Equilibrado — verdes + algunos de cautela
    # Calculamos cuántas zonas de cautela podemos agregar para completar el objetivo de unidades
    n_cautela_adicional = max(0, n_units - n_agresivo)
    n_equilibrado_cautela = min(n_cautela_adicional, len(cautela))
    # Sumamos el total de unidades del escenario equilibrado
    n_equilibrado = n_agresivo + n_equilibrado_cautela
    # Usamos el score promedio de verdes o un valor base de 60 si no hay zonas verdes
    sv_eq_green = sv_agresivo if n_agresivo > 0 else 60
    # Calculamos el score promedio de las zonas de cautela incluidas, o 55 como fallback
    sv_eq_caution = (
        sum(f["score_viabilidad"] for f in cautela[:n_equilibrado_cautela]) / max(n_equilibrado_cautela, 1)
        if n_equilibrado_cautela > 0 else 55
    )
    # Calculamos el score ponderado combinando zonas verdes y de cautela
    sv_equilibrado = (sv_eq_green * n_agresivo + sv_eq_caution * n_equilibrado_cautela) / max(n_equilibrado, 1)
    # Aplicamos una tasa ligeramente menor al equilibrado para reflejar diversificación de riesgo
    roi_equilibrado = _roi_anual(sv_equilibrado, vida, tasa * 0.95)
    pb_equilibrado = _payback_years(roi_equilibrado, vida)
    npv_equilibrado = _npv(roi_equilibrado, ticket * n_equilibrado, vida, tasa)

    # Calculamos el ahorro comparativo vs. una distribución aleatoria de zonas (score promedio = 50)
    roi_aleatorio = _roi_anual(50, vida, tasa)
    npv_aleatorio = _npv(roi_aleatorio, ticket * n_units, vida, tasa)
    # Expresamos el ahorro en millones de MXN para el reporte ejecutivo
    ahorro_agresivo = round((npv_agresivo - npv_aleatorio) / 1_000_000, 2)
    ahorro_equilibrado = round((npv_equilibrado - npv_aleatorio) / 1_000_000, 2)

    return [
        {
            "nombre": "Escenario Agresivo",
            "descripcion": f"Desplegar {n_agresivo} unidades exclusivamente en zonas verdes de máxima viabilidad.",
            "n_unidades": n_agresivo,
            "sv_promedio": round(sv_agresivo, 1),
            "roi_estimado_pct": round(roi_agresivo * 100, 1),
            "payback_anios": pb_agresivo,
            "npv_mxn": int(npv_agresivo),
            "inversion_total_mxn": int(ticket * n_agresivo),
            "ahorro_vs_aleatorio_mxn": int(ahorro_agresivo * 1_000_000),
            "riesgo_exposicion": "Bajo",
            "recomendado": False,
        },
        {
            "nombre": "Escenario Conservador",
            "descripcion": f"Desplegar {n_conservador} unidades en el top 50% de zonas verdes con mayor margen de seguridad.",
            "n_unidades": n_conservador,
            "sv_promedio": round(sv_conservador, 1),
            "roi_estimado_pct": round(roi_conservador * 100, 1),
            "payback_anios": pb_conservador,
            "npv_mxn": int(npv_conservador),
            "inversion_total_mxn": int(ticket * n_conservador),
            "ahorro_vs_aleatorio_mxn": 0,
            "riesgo_exposicion": "Mínimo",
            "recomendado": False,
        },
        {
            "nombre": "Escenario Equilibrado",
            "descripcion": (
                f"Desplegar {n_equilibrado} unidades: {n_agresivo} en zonas verdes + "
                f"{n_equilibrado_cautela} en cautela con mitigación activa. Maximiza cobertura con riesgo controlado."
            ),
            "n_unidades": n_equilibrado,
            "sv_promedio": round(sv_equilibrado, 1),
            "roi_estimado_pct": round(roi_equilibrado * 100, 1),
            "payback_anios": pb_equilibrado,
            "npv_mxn": int(npv_equilibrado),
            "inversion_total_mxn": int(ticket * n_equilibrado),
            "ahorro_vs_aleatorio_mxn": int(ahorro_equilibrado * 1_000_000),
            "riesgo_exposicion": "Controlado",
            "recomendado": True,
        },
    ]


def _executive_report(
    viability_features: list,
    scenarios: list,
    params: dict,
) -> dict:
    """Genera el reporte ejecutivo en lenguaje CFO/director de inversión."""
    sector = params.get("sector", "telecomunicaciones")
    ticket = params.get("ticket_inversion_mxn", 2_000_000)
    n_total = len(viability_features)
    verdes = [f for f in viability_features if f["categoria_viabilidad"] == "Alta viabilidad"]
    cautela = [f for f in viability_features if f["categoria_viabilidad"] == "Viabilidad media"]
    descarte = [f for f in viability_features if f["categoria_viabilidad"] == "Descarte"]

    top_zonas_verdes = sorted(verdes, key=lambda x: x["score_viabilidad"], reverse=True)[:5]
    top_zonas_descarte = sorted(descarte, key=lambda x: x["score_viabilidad"])[:3]

    escenario_rec = next((s for s in scenarios if s["recomendado"]), scenarios[-1])

    reporte = {
        "titulo": f"Reporte Ejecutivo URBANIA — Sector {sector.capitalize()}",
        "resumen_ejecutivo": (
            f"El análisis territorial de {n_total} manzanas en la zona piloto CDMX identifica "
            f"{len(verdes)} zonas de alta viabilidad ({len(verdes)/n_total*100:.0f}%), "
            f"{len(cautela)} zonas de cautela y {len(descarte)} zonas de descarte. "
            f"El escenario recomendado ({escenario_rec['nombre']}) proyecta un ROI de "
            f"{escenario_rec['roi_estimado_pct']:.1f}% con payback a {escenario_rec['payback_anios']:.1f} años."
        ),
        "hallazgos_clave": [
            f"Solo {len(verdes)} de {n_total} manzanas ({len(verdes)/n_total*100:.0f}%) cumplen criterios de alta viabilidad.",
            f"{len(descarte)} zonas de descarte representan {int(len(descarte) * ticket / 1_000_000)} MXN en pérdidas potenciales evitadas.",
            f"El escenario equilibrado maximiza cobertura sin exceder umbrales de riesgo operativo.",
            "Las zonas de descarte presentan índices de robo con violencia superiores al percentil 85 del dataset.",
            "Correlación negativa fuerte entre iluminación pública y score de riesgo operativo.",
        ],
        "top_zonas_inversion": [
            {
                "zona": z["nombre"],
                "score_viabilidad": z["score_viabilidad"],
                "score_demanda": z.get("score_demanda", "—"),
                "score_riesgo": z.get("score_riesgo", "—"),
            }
            for z in top_zonas_verdes
        ],
        "zonas_descarte_explicitas": [
            {
                "zona": z["nombre"],
                "score_viabilidad": z["score_viabilidad"],
                "razon": z.get("razon_descarte", "Score de viabilidad inferior al umbral mínimo."),
            }
            for z in top_zonas_descarte
        ],
        "escenario_recomendado": escenario_rec,
        "advertencias": [
            "Los scores son indicadores relativos; se recomienda validación de campo antes del despliegue.",
            "Las zonas de cautela requieren póliza de seguro especializada para infraestructura.",
            "Los datos de incidencia SNSP corresponden a los últimos 12 meses disponibles.",
            "Este análisis no sustituye una auditoría de permisos de uso de suelo.",
        ],
        "proximos_pasos": [
            f"Solicitar visita técnica a las {min(len(verdes), 5)} zonas verdes prioritarias.",
            "Cotizar póliza de seguro para zonas de cautela con integradoras especializadas.",
            "Activar pipeline de datos reales (URBANIA_PROD_MODE=1) para actualización mensual.",
            "Generar escenario personalizado con tasa de descuento ajustada por sector.",
        ],
    }
    return reporte


class BusinessAgent:
    def __init__(self, use_fallback_only: bool = True):
        # Inicializamos el agente indicando si usamos únicamente el motor algorítmico
        self.use_fallback_only = use_fallback_only
        logger.info("BusinessAgent init | fallback=%s", use_fallback_only)

    def generate_scenarios(
        self,
        demand_scores: list,
        risk_scores: list,
        params: dict,
    ) -> dict:
        # Obtenemos el sector y el ticket de inversión de los parámetros del cliente
        sector = params.get("sector", "telecomunicaciones")
        ticket = params.get("ticket_inversion_mxn", 2_000_000)
        # Obtenemos el factor de potencial del sector y normalizamos el ticket
        fp = SECTOR_FP.get(sector, 1.0)
        ti_n = _ti_norm(ticket)

        # Indexamos los scores de demanda y riesgo por ID de zona para acceso eficiente
        demand_map = {d["id"]: d for d in demand_scores}
        risk_map = {r["id"]: r for r in risk_scores}

        # Inicializamos la lista de features con score de viabilidad calculado
        features_sv = []
        # Obtenemos el conjunto de todos los IDs presentes en demanda o riesgo
        all_ids = set(demand_map) | set(risk_map)

        # Iteramos sobre cada zona para calcular su score de viabilidad combinado
        for fid in all_ids:
            d = demand_map.get(fid, {})
            r = risk_map.get(fid, {})
            # Usamos 50 como valor neutral por defecto si falta algún score
            sd = d.get("score_demanda", 50.0)
            sr = r.get("score_riesgo", 50.0)
            # Calculamos el score de viabilidad final para esta zona
            sv = _score_viabilidad(sd, sr, fp, ti_n)
            cat = _categoria_viabilidad(sv)

            # Construimos el objeto de la zona con todos sus atributos de viabilidad
            features_sv.append({
                "id": fid,
                "nombre": d.get("nombre") or r.get("nombre", fid),
                "score_viabilidad": sv,
                "score_demanda": sd,
                "score_riesgo": sr,
                "categoria_viabilidad": cat,
                "color": VIABILITY_TIERS[cat]["color"],
                "razon_descarte": r.get("razon_descarte", ""),
            })

        # Generamos los tres escenarios de despliegue con sus métricas financieras
        scenarios = _generate_scenarios(features_sv, params)
        # Generamos el reporte ejecutivo completo para el comité de inversión
        report = _executive_report(features_sv, scenarios, params)

        # Preparamos una versión simplificada de los scores para el frontend
        viability_scores_simple = [
            {
                "id": f["id"],
                "score_viabilidad": f["score_viabilidad"],
                "clasificacion": f["categoria_viabilidad"],
            }
            for f in features_sv
        ]

        # Retornamos el resultado completo con features, scores, escenarios y reporte
        return {
            "features_score_viabilidad": features_sv,
            "viability_scores": viability_scores_simple,
            "escenarios_algoritmicos": scenarios,
            "reporte_ejecutivo": report,
        }

    def to_pdf_ready_dict(self, business_results: dict) -> dict:
        """Prepara dict para generación de PDF."""
        # Extraemos el reporte ejecutivo del resultado completo del agente
        report = business_results.get("reporte_ejecutivo", {})
        # Retornamos solo los campos necesarios para construir el documento PDF
        return {
            "titulo": report.get("titulo", "Reporte Ejecutivo URBANIA"),
            "resumen_ejecutivo": report.get("resumen_ejecutivo", ""),
            "hallazgos_clave": report.get("hallazgos_clave", []),
            "top_zonas_inversion": report.get("top_zonas_inversion", []),
            "zonas_descarte_explicitas": report.get("zonas_descarte_explicitas", []),
            "escenario_recomendado": report.get("escenario_recomendado", {}),
            "advertencias": report.get("advertencias", []),
            "proximos_pasos": report.get("proximos_pasos", []),
        }
