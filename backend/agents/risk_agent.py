"""
URBANIA — Agente de Riesgo Operativo
======================================
Calcula el Score de Riesgo (0–100) por manzana.
Integra: incidencia SNSP, déficit de iluminación y accesibilidad logística.
Clasifica zonas en: verde (<30), cautela (30-60), descarte (>60).
"""
import logging
import copy

logger = logging.getLogger("urbania.risk_agent")

# Pesos del índice de riesgo (suman 1.0)
RISK_WEIGHTS = {
    "incidencia_delictiva": 0.50,
    "deficit_iluminacion": 0.25,
    "inaccesibilidad_logistica": 0.25,
}

RISK_NORM = {
    "incidencia_delictiva": {"min": 0, "max": 180},
    "deficit_iluminacion": {"min": 0, "max": 100},
    "inaccesibilidad_logistica": {"min": 0, "max": 100},
}

RISK_TIER_MAP = {
    "verde": {"label": "Zona Verde — Invertir", "color": "#1D9E75"},
    "cautela": {"label": "Zona Cautela — Mitigar", "color": "#EF9F27"},
    "descarte": {"label": "Zona Descarte — No invertir", "color": "#E24B4A"},
}

DELITO_SEVERIDAD = {
    "fraude": 0.4,
    "robo_vehículo": 0.7,
    "robo_transeúnte": 0.8,
    "robo_con_violencia": 1.0,
}

MITIGACION_TEMPLATES = {
    "robo_con_violencia": [
        "Contratar póliza de seguro especializada (cobertura robo de infraestructura).",
        "Instalar sistemas de geolocalización en activos.",
        "Programar mantenimiento únicamente en horario diurno con escolta.",
    ],
    "robo_transeúnte": [
        "Evaluar custodia activa durante instalación.",
        "Coordinar con C4/C5 municipal para incremento de patrullaje.",
        "Usar gabinetes anti-vandálicos certificados.",
    ],
    "robo_vehículo": [
        "Instalar cámaras de vigilancia adicionales en el sitio.",
        "Considerar infraestructura soterrada donde sea viable.",
        "Póliza de seguro con cobertura de reposición rápida (<72h).",
    ],
    "fraude": [
        "Documentar auditoría de permisos antes del despliegue.",
        "Verificar estatus de uso de suelo con delegación.",
    ],
}


def _normalize(value: float, vmin: float, vmax: float) -> float:
    if vmax == vmin:
        return 0.5
    return max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))


def _compute_risk_score(feature: dict) -> float:
    delito_base = feature.get("incidencia_delictiva_snsp", 30)
    tipo = feature.get("tipo_delito_predominante", "robo_transeúnte")
    severidad = DELITO_SEVERIDAD.get(tipo, 0.8)
    delito_ajustado = min(delito_base * severidad, 180)

    iluminacion = feature.get("iluminacion_publica", 70)
    deficit_iluminacion = 100 - iluminacion

    accesibilidad = feature.get("accesibilidad_logistica", 70)
    inaccesibilidad = 100 - accesibilidad

    r_incidencia = _normalize(delito_ajustado, 0, 180)
    r_ilum = _normalize(deficit_iluminacion, 0, 100)
    r_inacc = _normalize(inaccesibilidad, 0, 100)

    score = (
        r_incidencia * RISK_WEIGHTS["incidencia_delictiva"] +
        r_ilum * RISK_WEIGHTS["deficit_iluminacion"] +
        r_inacc * RISK_WEIGHTS["inaccesibilidad_logistica"]
    )
    return round(score * 100, 2)


def _risk_tier(score: float) -> str:
    if score < 30:
        return "verde"
    elif score <= 60:
        return "cautela"
    return "descarte"


def _risk_factors(feature: dict) -> list:
    factors = []
    snsp = feature.get("incidencia_delictiva_snsp", 0)
    tipo = feature.get("tipo_delito_predominante", "")
    ilum = feature.get("iluminacion_publica", 100)
    acc = feature.get("accesibilidad_logistica", 100)

    if snsp > 80:
        factors.append(f"Alta incidencia delictiva: {int(snsp)} eventos SNSP (12 meses)")
    elif snsp > 30:
        factors.append(f"Incidencia delictiva moderada: {int(snsp)} eventos SNSP")

    if tipo == "robo_con_violencia":
        factors.append("Tipo predominante: robo con violencia — riesgo alto de infraestructura")
    elif tipo in ("robo_transeúnte", "robo_vehículo"):
        factors.append(f"Tipo predominante: {tipo.replace('_', ' ')} — requiere medidas de seguridad")

    if ilum < 50:
        factors.append(f"Iluminación pública deficiente: {ilum:.0f}% cobertura — riesgo nocturno alto")
    elif ilum < 70:
        factors.append(f"Iluminación pública moderada: {ilum:.0f}% cobertura")

    if acc < 50:
        factors.append(f"Accesibilidad logística crítica: {acc:.0f}/100 — mantenimiento complejo")
    elif acc < 70:
        factors.append(f"Accesibilidad logística limitada: {acc:.0f}/100")

    return factors if factors else ["Sin factores de riesgo críticos identificados."]


def _razon_descarte(feature: dict, score: float, tier: str) -> str:
    if tier != "descarte":
        return ""
    nombre = feature.get("nombre", feature.get("id", ""))
    snsp = int(feature.get("incidencia_delictiva_snsp", 0))
    tipo = feature.get("tipo_delito_predominante", "")
    return (
        f"{nombre}: Score de riesgo {score:.0f}/100 supera umbral de descarte (>60). "
        f"{snsp} eventos SNSP registrados (predominio: {tipo.replace('_', ' ')}). "
        f"Inversión en esta zona presenta probabilidad alta de pérdida patrimonial. "
        f"URBANIA recomienda explícitamente NO desplegar activos aquí."
    )


class RiskAgent:
    def __init__(self, use_fallback_only: bool = True):
        self.use_fallback_only = use_fallback_only
        logger.info("RiskAgent init | fallback=%s", use_fallback_only)

    def score(self, features: list) -> list:
        results = []
        for feat in features:
            sr = _compute_risk_score(feat)
            tier = _risk_tier(sr)
            factors = _risk_factors(feat)
            mitigacion = MITIGACION_TEMPLATES.get(
                feat.get("tipo_delito_predominante", "robo_transeúnte"),
                MITIGACION_TEMPLATES["robo_transeúnte"]
            ) if tier in ("cautela", "descarte") else []
            razon = _razon_descarte(feat, sr, tier)

            results.append({
                "id": feat["id"],
                "nombre": feat["nombre"],
                "score_riesgo": sr,
                "clasificacion": tier,
                "clasificacion_label": RISK_TIER_MAP[tier]["label"],
                "color_leaflet": RISK_TIER_MAP[tier]["color"],
                "factores_riesgo": factors,
                "recomendaciones_mitigacion": mitigacion,
                "razon_descarte": razon,
                "incidencia_delictiva_snsp": feat.get("incidencia_delictiva_snsp"),
                "tipo_delito_predominante": feat.get("tipo_delito_predominante"),
                "iluminacion_publica": feat.get("iluminacion_publica"),
                "accesibilidad_logistica": feat.get("accesibilidad_logistica"),
                "lat": feat.get("lat"),
                "lng": feat.get("lng"),
                "geometry": feat.get("geometry"),
            })

        logger.info("RiskAgent scored %d features", len(results))
        return results

    def generate_risk_geojson(self, risk_scores: list, original_geojson: dict) -> dict:
        score_map = {r["id"]: r for r in risk_scores}
        result = copy.deepcopy(original_geojson)

        for feat in result.get("features", []):
            fid = feat.get("id") or feat.get("properties", {}).get("id")
            if fid in score_map:
                rs = score_map[fid]
                feat.setdefault("properties", {}).update({
                    "id": fid,
                    "nombre": rs["nombre"],
                    "score_riesgo": rs["score_riesgo"],
                    "clasificacion": rs["clasificacion"],
                    "clasificacion_label": rs["clasificacion_label"],
                    "color_leaflet": rs["color_leaflet"],
                    "factores_riesgo": rs["factores_riesgo"],
                    "recomendaciones_mitigacion": rs["recomendaciones_mitigacion"],
                    "razon_descarte": rs["razon_descarte"],
                    "incidencia_delictiva_snsp": rs.get("incidencia_delictiva_snsp"),
                    "tipo_delito_predominante": rs.get("tipo_delito_predominante"),
                    "iluminacion_publica": rs.get("iluminacion_publica"),
                    "accesibilidad_logistica": rs.get("accesibilidad_logistica"),
                })
        return result
