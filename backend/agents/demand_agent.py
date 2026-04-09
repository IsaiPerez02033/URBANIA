"""
URBANIA — Agente de Demanda
============================
Calcula el Score de Demanda (0–100) por manzana ponderando variables
demográficas, económicas, de movilidad y de luminosidad nocturna.
Pesos diferenciados por sector.
"""
# Importamos el módulo de logging para registrar eventos del agente
import logging
# Importamos os para acceder a variables de entorno si fuera necesario
import os
# Importamos json para posible serialización de datos
import json
# Importamos copy para hacer copias profundas de los GeoJSON sin modificar el original
import copy

# Creamos el logger específico para el agente de demanda
logger = logging.getLogger("urbania.demand_agent")

# Declaramos los pesos de cada variable por sector (cada fila debe sumar 1.0)
# Los pesos reflejan la importancia relativa de cada indicador según el tipo de negocio
SECTOR_WEIGHTS = {
    "telecomunicaciones": {
        "densidad_poblacional": 0.30,      # Mayor densidad = más usuarios potenciales
        "actividad_economica_denue": 0.25, # Comercios = demanda de conectividad
        "luminosidad_viirs": 0.20,         # Actividad nocturna = uso intensivo de datos
        "acceso_gtfs": 0.15,               # Transporte = zonas dinámicas
        "ingreso_proxy": 0.10,             # Capacidad de pago del mercado
    },
    "seguridad": {
        "densidad_poblacional": 0.20,
        "actividad_economica_denue": 0.25,
        "luminosidad_viirs": 0.25,         # Luminosidad es crítica para videovigilancia
        "acceso_gtfs": 0.10,
        "ingreso_proxy": 0.20,             # Mayor ingreso = mayor disposición a pagar servicios
    },
    "inmobiliario": {
        "densidad_poblacional": 0.20,
        "actividad_economica_denue": 0.20,
        "luminosidad_viirs": 0.15,
        "acceso_gtfs": 0.20,               # Accesibilidad es clave para plusvalía inmobiliaria
        "ingreso_proxy": 0.25,             # El nivel de ingresos es el mayor driver de valor
    },
}

# Declaramos los rangos mínimos y máximos para normalizar cada variable entre 0 y 1
NORM_RANGES = {
    "densidad_poblacional":    {"min": 5000,  "max": 45000},
    "actividad_economica_denue": {"min": 50,  "max": 320},
    "luminosidad_viirs":       {"min": 80,   "max": 240},
    "acceso_gtfs":             {"min": 0,    "max": 1},
    "ingreso_proxy":           {"min": 0,    "max": 100},
}

# Declaramos las etiquetas descriptivas para cada nivel de demanda
DEMAND_TIER_LABELS = {
    "alta": "Alta demanda",
    "media": "Demanda media",
    "baja": "Baja demanda",
}

# Declaramos el mapa de colores por nivel de demanda para visualización en el mapa
COLOR_MAP = {
    "alta": "#1D9E75",   # Verde para alta demanda
    "media": "#EF9F27",  # Ambar para demanda media
    "baja": "#E24B4A",   # Rojo para baja demanda
}


def _normalize(value: float, vmin: float, vmax: float) -> float:
    # Si el rango es cero retornamos 0.5 como valor neutral para evitar división por cero
    if vmax == vmin:
        return 0.5
    # Normalizamos el valor al rango [0, 1] usando min-max scaling y lo acotamos
    return max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))


def _ingreso_proxy(feature: dict) -> float:
    """
    Proxy de ingreso: combina luminosidad alta + baja incidencia.
    Rango 0–100.
    """
    # Normalizamos la luminosidad nocturna como indicador de actividad económica
    lum_norm = _normalize(feature.get("luminosidad_viirs", 150), 80, 240)
    # Invertimos la incidencia delictiva: menos crimen = mayor ingreso estimado
    crime_norm = 1.0 - _normalize(feature.get("incidencia_delictiva_snsp", 30), 0, 180)
    # Combinamos ambos indicadores con mayor peso en luminosidad (60%) que en seguridad (40%)
    return (lum_norm * 0.6 + crime_norm * 0.4) * 100


def _compute_demand_score(feature: dict, weights: dict) -> float:
    """Calcula score de demanda 0–100 para un feature."""
    # Calculamos el proxy de ingreso para incluirlo en la ponderación
    ingreso = _ingreso_proxy(feature)
    # Normalizamos cada variable según sus rangos de referencia definidos en NORM_RANGES
    vars_norm = {
        "densidad_poblacional": _normalize(
            feature["densidad_poblacional"],
            NORM_RANGES["densidad_poblacional"]["min"],
            NORM_RANGES["densidad_poblacional"]["max"]
        ),
        "actividad_economica_denue": _normalize(
            feature["actividad_economica_denue"],
            NORM_RANGES["actividad_economica_denue"]["min"],
            NORM_RANGES["actividad_economica_denue"]["max"]
        ),
        "luminosidad_viirs": _normalize(
            feature["luminosidad_viirs"],
            NORM_RANGES["luminosidad_viirs"]["min"],
            NORM_RANGES["luminosidad_viirs"]["max"]
        ),
        # El acceso a GTFS es binario: 1.0 si tiene cobertura de transporte, 0.0 si no
        "acceso_gtfs": 1.0 if feature.get("acceso_gtfs") else 0.0,
        "ingreso_proxy": _normalize(ingreso, 0, 100),
    }

    # Calculamos el score como suma ponderada de todas las variables normalizadas
    score = sum(vars_norm[k] * weights[k] for k in weights)
    # Retornamos el score multiplicado por 100 para expresarlo en escala 0-100
    return round(score * 100, 2)


def _demand_tier(score: float) -> str:
    # Clasificamos el score en tres niveles según los umbrales definidos para demanda
    if score >= 65:
        return "alta"
    elif score >= 40:
        return "media"
    return "baja"


def _top3_justification(feature: dict, weights: dict, sector: str) -> list:
    """Genera las top 3 variables que más aportan al score."""
    ingreso = _ingreso_proxy(feature)
    contributions = {
        "densidad_poblacional": weights["densidad_poblacional"] * _normalize(
            feature["densidad_poblacional"],
            NORM_RANGES["densidad_poblacional"]["min"],
            NORM_RANGES["densidad_poblacional"]["max"]
        ),
        "actividad_economica_denue": weights["actividad_economica_denue"] * _normalize(
            feature["actividad_economica_denue"],
            NORM_RANGES["actividad_economica_denue"]["min"],
            NORM_RANGES["actividad_economica_denue"]["max"]
        ),
        "luminosidad_viirs": weights["luminosidad_viirs"] * _normalize(
            feature["luminosidad_viirs"],
            NORM_RANGES["luminosidad_viirs"]["min"],
            NORM_RANGES["luminosidad_viirs"]["max"]
        ),
        "acceso_gtfs": weights["acceso_gtfs"] * (1.0 if feature.get("acceso_gtfs") else 0.0),
        "ingreso_proxy": weights["ingreso_proxy"] * _normalize(ingreso, 0, 100),
    }

    labels = {
        "densidad_poblacional": f"Densidad: {int(feature['densidad_poblacional'])} hab/km²",
        "actividad_economica_denue": f"DENUE: {int(feature['actividad_economica_denue'])} establecimientos",
        "luminosidad_viirs": f"VIIRS: {int(feature['luminosidad_viirs'])} (actividad nocturna)",
        "acceso_gtfs": "Cobertura GTFS: {}".format("Sí" if feature.get("acceso_gtfs") else "No"),
        "ingreso_proxy": f"Proxy ingreso: {ingreso:.0f}/100",
    }

    top3 = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:3]
    return [labels[k] for k, _ in top3]


class DemandAgent:
    def __init__(self, sector: str = "telecomunicaciones", use_fallback_only: bool = True):
        # Guardamos el sector actual para usar los pesos correctos en el cálculo
        self.sector = sector
        # Indicamos si usamos únicamente el motor algorítmico o si podemos llamar a Watsonx
        self.use_fallback_only = use_fallback_only
        # Cargamos los pesos del sector seleccionado, usando telecomunicaciones como fallback
        self.weights = SECTOR_WEIGHTS.get(sector, SECTOR_WEIGHTS["telecomunicaciones"])
        logger.info("DemandAgent init | sector=%s | fallback=%s", sector, use_fallback_only)

    def score(self, features: list, sector: str = None) -> list:
        """
        Calcula scores de demanda para todos los features.
        Retorna lista de dicts con id, score_demanda, tier, justificacion.
        """
        # Si se pasa un sector diferente al actual, actualizamos los pesos antes de procesar
        if sector:
            self.sector = sector
            self.weights = SECTOR_WEIGHTS.get(sector, SECTOR_WEIGHTS["telecomunicaciones"])

        results = []
        # Procesamos cada zona para calcular su score de demanda individual
        for feat in features:
            # Calculamos el score numérico de demanda para esta zona
            sd = _compute_demand_score(feat, self.weights)
            # Clasificamos el score en nivel alto, medio o bajo
            tier = _demand_tier(sd)
            # Obtenemos las tres variables que más aportan al score para la justificación
            top3 = _top3_justification(feat, self.weights, self.sector)

            # Generamos la narrativa ejecutiva en lenguaje de negocio (fallback algorítmico)
            narrativa = self._generate_narrative(feat, sd, tier)

            # Construimos el objeto de resultado con todos los campos necesarios para el frontend
            results.append({
                "id": feat["id"],
                "nombre": feat["nombre"],
                "score_demanda": sd,
                "demand_tier": tier,
                "demand_tier_label": DEMAND_TIER_LABELS[tier],
                "color_leaflet": COLOR_MAP[tier],      # Color para pintar la zona en el mapa
                "justificacion_top3": top3,
                "narrativa_ejecutiva": narrativa,
                "score_source": "algorithmic_fallback", # Indicamos que el origen es el motor local
                "lat": feat.get("lat"),
                "lng": feat.get("lng"),
                # Preservamos los datos originales para exportación y auditoría
                "densidad_poblacional": feat.get("densidad_poblacional"),
                "actividad_economica_denue": feat.get("actividad_economica_denue"),
                "luminosidad_viirs": feat.get("luminosidad_viirs"),
                "acceso_gtfs": feat.get("acceso_gtfs"),
                "geometry": feat.get("geometry"),
            })

        logger.info("DemandAgent scored %d features", len(results))
        return results

    def _generate_narrative(self, feat: dict, score: float, tier: str) -> str:
        nombre = feat.get("nombre", feat["id"])
        dens = int(feat.get("densidad_poblacional", 0))
        denue = int(feat.get("actividad_economica_denue", 0))

        if tier == "alta":
            return (
                f"{nombre} registra una demanda alta (score {score:.0f}/100). "
                f"Con {dens:,} hab/km² y {denue} establecimientos DENUE, esta zona presenta "
                f"condiciones óptimas para despliegue prioritario en {self.sector}. "
                f"Se recomienda acción inmediata."
            )
        elif tier == "media":
            return (
                f"{nombre} presenta demanda media (score {score:.0f}/100). "
                f"Densidad de {dens:,} hab/km² con actividad comercial moderada ({denue} DENUE). "
                f"Candidato viable sujeto a validación de riesgo operativo."
            )
        else:
            return (
                f"{nombre} muestra baja demanda (score {score:.0f}/100). "
                f"Indicadores de densidad y actividad económica insuficientes para justificar "
                f"inversión en {self.sector} sin estrategia de activación de mercado."
            )

    def to_geojson(self, demand_scores: list, original_geojson: dict) -> dict:
        """Combina los scores con el GeoJSON original para Leaflet."""
        # Indexamos los scores por ID para asociarlos eficientemente con los features del GeoJSON
        score_map = {d["id"]: d for d in demand_scores}
        # Hacemos una copia profunda para no modificar el GeoJSON original
        result = copy.deepcopy(original_geojson)

        # Enriquecemos cada feature del GeoJSON con sus scores de demanda calculados
        for feat in result.get("features", []):
            # Buscamos el ID ya sea en el feature directamente o en sus propiedades
            fid = feat.get("id") or feat.get("properties", {}).get("id")
            if fid in score_map:
                ds = score_map[fid]
                # Actualizamos las propiedades del feature con todos los datos de demanda
                feat.setdefault("properties", {}).update({
                    "id": fid,
                    "nombre": ds["nombre"],
                    "score_demanda": ds["score_demanda"],
                    "demand_tier": ds["demand_tier"],
                    "demand_tier_label": ds["demand_tier_label"],
                    "color_leaflet": ds["color_leaflet"],
                    "justificacion_top3": ds["justificacion_top3"],
                    "narrativa_ejecutiva": ds["narrativa_ejecutiva"],
                    "score_source": ds["score_source"],
                    "lat": ds["lat"],
                    "lng": ds["lng"],
                    "densidad_poblacional": ds.get("densidad_poblacional"),
                    "actividad_economica_denue": ds.get("actividad_economica_denue"),
                    "luminosidad_viirs": ds.get("luminosidad_viirs"),
                    "acceso_gtfs": ds.get("acceso_gtfs"),
                })
        # Retornamos el GeoJSON enriquecido listo para renderizar en Leaflet
        return result
