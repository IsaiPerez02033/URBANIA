"""
URBANIA — Agente de Riesgo Operativo
======================================
Calcula el Score de Riesgo (0–100) por manzana.
Integra: incidencia SNSP, déficit de iluminación y accesibilidad logística.
Clasifica zonas en: verde (<30), cautela (30-60), descarte (>60).
"""
# Importamos el módulo de logging para registrar eventos del agente
import logging
# Importamos copy para realizar copias profundas del GeoJSON sin modificar el original
import copy

# Creamos el logger específico para el agente de riesgo
logger = logging.getLogger("urbania.risk_agent")

# Declaramos los pesos del índice de riesgo (deben sumar 1.0)
# La incidencia delictiva tiene mayor peso por su impacto directo en seguridad patrimonial
RISK_WEIGHTS = {
    "incidencia_delictiva": 0.50,      # Mayor factor por impacto en activos físicos
    "deficit_iluminacion": 0.25,       # Iluminación deficiente aumenta riesgo nocturno
    "inaccesibilidad_logistica": 0.25, # Difícil acceso complica mantenimiento y respuesta
}

# Declaramos los rangos de normalización para cada componente del índice de riesgo
RISK_NORM = {
    "incidencia_delictiva": {"min": 0, "max": 180},      # Eventos SNSP en 12 meses
    "deficit_iluminacion": {"min": 0, "max": 100},        # Porcentaje de cobertura faltante
    "inaccesibilidad_logistica": {"min": 0, "max": 100},  # Índice de dificultad de acceso
}

# Declaramos el mapa de clasificaciones de riesgo con etiquetas y colores para el mapa
RISK_TIER_MAP = {
    "verde":   {"label": "Zona Verde — Invertir",      "color": "#1D9E75"},
    "cautela": {"label": "Zona Cautela — Mitigar",     "color": "#EF9F27"},
    "descarte":{"label": "Zona Descarte — No invertir","color": "#E24B4A"},
}

# Declaramos los factores de severidad por tipo de delito para ajustar el índice de incidencia
# Un factor de 1.0 indica el mayor riesgo y 0.4 el menor dentro de nuestra escala
DELITO_SEVERIDAD = {
    "fraude": 0.4,               # Menor impacto en infraestructura física
    "robo_vehículo": 0.7,        # Impacto moderado en activos móviles
    "robo_transeúnte": 0.8,      # Alto riesgo para técnicos en campo
    "robo_con_violencia": 1.0,   # Mayor multiplicador: riesgo crítico para operaciones
}

# Declaramos las plantillas de recomendaciones de mitigación por tipo de delito predominante
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
    # Si el rango es cero retornamos 0.5 para evitar división por cero
    if vmax == vmin:
        return 0.5
    # Normalizamos el valor al rango [0, 1] acotando los extremos
    return max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))


def _compute_risk_score(feature: dict) -> float:
    # Obtenemos la incidencia delictiva base del SNSP (últimos 12 meses)
    delito_base = feature.get("incidencia_delictiva_snsp", 30)
    # Obtenemos el tipo de delito predominante para aplicar el multiplicador de severidad
    tipo = feature.get("tipo_delito_predominante", "robo_transeúnte")
    # Aplicamos el factor de severidad del tipo de delito para ajustar la incidencia
    severidad = DELITO_SEVERIDAD.get(tipo, 0.8)
    # Ajustamos la incidencia con el factor de severidad, sin superar el máximo del rango
    delito_ajustado = min(delito_base * severidad, 180)

    # Calculamos el déficit de iluminación como el complemento de la cobertura disponible
    iluminacion = feature.get("iluminacion_publica", 70)
    deficit_iluminacion = 100 - iluminacion

    # Calculamos la inaccesibilidad logística como el complemento de la accesibilidad
    accesibilidad = feature.get("accesibilidad_logistica", 70)
    inaccesibilidad = 100 - accesibilidad

    # Normalizamos cada componente de riesgo a escala [0, 1]
    r_incidencia = _normalize(delito_ajustado, 0, 180)
    r_ilum = _normalize(deficit_iluminacion, 0, 100)
    r_inacc = _normalize(inaccesibilidad, 0, 100)

    # Calculamos el score de riesgo como suma ponderada de los tres componentes
    score = (
        r_incidencia * RISK_WEIGHTS["incidencia_delictiva"] +
        r_ilum * RISK_WEIGHTS["deficit_iluminacion"] +
        r_inacc * RISK_WEIGHTS["inaccesibilidad_logistica"]
    )
    # Retornamos el score en escala 0-100 redondeado a dos decimales
    return round(score * 100, 2)


def _risk_tier(score: float) -> str:
    # Clasificamos la zona en verde si el riesgo es bajo (menos de 30)
    if score < 30:
        return "verde"
    # Clasificamos en cautela si el riesgo es moderado (entre 30 y 60)
    elif score <= 60:
        return "cautela"
    # Clasificamos en descarte si el riesgo supera el umbral crítico (más de 60)
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
        # Indicamos si el agente opera en modo local sin llamadas a Watsonx
        self.use_fallback_only = use_fallback_only
        logger.info("RiskAgent init | fallback=%s", use_fallback_only)

    def score(self, features: list) -> list:
        results = []
        # Procesamos cada zona para calcular su score de riesgo operativo
        for feat in features:
            # Calculamos el score numérico de riesgo para esta zona
            sr = _compute_risk_score(feat)
            # Clasificamos el score en verde, cautela o descarte
            tier = _risk_tier(sr)
            # Generamos la lista de factores de riesgo identificados en la zona
            factors = _risk_factors(feat)
            # Solo generamos recomendaciones de mitigación para zonas de cautela o descarte
            mitigacion = MITIGACION_TEMPLATES.get(
                feat.get("tipo_delito_predominante", "robo_transeúnte"),
                MITIGACION_TEMPLATES["robo_transeúnte"]
            ) if tier in ("cautela", "descarte") else []
            # Generamos la razón de descarte en lenguaje ejecutivo si aplica
            razon = _razon_descarte(feat, sr, tier)

            # Construimos el objeto de resultado con todos los atributos de riesgo
            results.append({
                "id": feat["id"],
                "nombre": feat["nombre"],
                "score_riesgo": sr,
                "clasificacion": tier,
                "clasificacion_label": RISK_TIER_MAP[tier]["label"],
                "color_leaflet": RISK_TIER_MAP[tier]["color"],  # Color para el mapa
                "factores_riesgo": factors,
                "recomendaciones_mitigacion": mitigacion,
                "razon_descarte": razon,
                # Preservamos los datos originales de campo para trazabilidad
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
        # Indexamos los scores de riesgo por ID para enriquecer el GeoJSON eficientemente
        score_map = {r["id"]: r for r in risk_scores}
        # Hacemos una copia profunda para no modificar el GeoJSON original
        result = copy.deepcopy(original_geojson)

        # Actualizamos cada feature del GeoJSON con sus datos de riesgo calculados
        for feat in result.get("features", []):
            # Buscamos el ID ya sea en el feature directamente o en sus propiedades
            fid = feat.get("id") or feat.get("properties", {}).get("id")
            if fid in score_map:
                rs = score_map[fid]
                # Actualizamos las propiedades del feature con todos los datos de riesgo
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
        # Retornamos el GeoJSON enriquecido con datos de riesgo para Leaflet
        return result
