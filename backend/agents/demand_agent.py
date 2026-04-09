"""
URBANIA — Agente de Demanda
============================
Calcula el Score de Demanda (0–100) por manzana ponderando variables
demográficas, económicas, de movilidad y de luminosidad nocturna.
Pesos diferenciados por sector.
"""
import logging
import os
import json
import copy

logger = logging.getLogger("urbania.demand_agent")

# Pesos por sector (deben sumar 1.0)
SECTOR_WEIGHTS = {
    "telecomunicaciones": {
        "densidad_poblacional": 0.30,
        "actividad_economica_denue": 0.25,
        "luminosidad_viirs": 0.20,
        "acceso_gtfs": 0.15,
        "ingreso_proxy": 0.10,
    },
    "seguridad": {
        "densidad_poblacional": 0.20,
        "actividad_economica_denue": 0.25,
        "luminosidad_viirs": 0.25,
        "acceso_gtfs": 0.10,
        "ingreso_proxy": 0.20,
    },
    "inmobiliario": {
        "densidad_poblacional": 0.20,
        "actividad_economica_denue": 0.20,
        "luminosidad_viirs": 0.15,
        "acceso_gtfs": 0.20,
        "ingreso_proxy": 0.25,
    },
}

# Rangos de normalización por variable
NORM_RANGES = {
    "densidad_poblacional":    {"min": 5000,  "max": 45000},
    "actividad_economica_denue": {"min": 50,  "max": 320},
    "luminosidad_viirs":       {"min": 80,   "max": 240},
    "acceso_gtfs":             {"min": 0,    "max": 1},
    "ingreso_proxy":           {"min": 0,    "max": 100},
}

DEMAND_TIER_LABELS = {
    "alta": "Alta demanda",
    "media": "Demanda media",
    "baja": "Baja demanda",
}

COLOR_MAP = {
    "alta": "#1D9E75",
    "media": "#EF9F27",
    "baja": "#E24B4A",
}


def _normalize(value: float, vmin: float, vmax: float) -> float:
    if vmax == vmin:
        return 0.5
    return max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))


def _ingreso_proxy(feature: dict) -> float:
    """
    Proxy de ingreso: combina luminosidad alta + baja incidencia.
    Rango 0–100.
    """
    lum_norm = _normalize(feature.get("luminosidad_viirs", 150), 80, 240)
    crime_norm = 1.0 - _normalize(feature.get("incidencia_delictiva_snsp", 30), 0, 180)
    return (lum_norm * 0.6 + crime_norm * 0.4) * 100


def _compute_demand_score(feature: dict, weights: dict) -> float:
    """Calcula score de demanda 0–100 para un feature."""
    ingreso = _ingreso_proxy(feature)
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
        "acceso_gtfs": 1.0 if feature.get("acceso_gtfs") else 0.0,
        "ingreso_proxy": _normalize(ingreso, 0, 100),
    }

    score = sum(vars_norm[k] * weights[k] for k in weights)
    return round(score * 100, 2)


def _demand_tier(score: float) -> str:
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
        self.sector = sector
        self.use_fallback_only = use_fallback_only
        self.weights = SECTOR_WEIGHTS.get(sector, SECTOR_WEIGHTS["telecomunicaciones"])
        logger.info("DemandAgent init | sector=%s | fallback=%s", sector, use_fallback_only)

    def score(self, features: list, sector: str = None) -> list:
        """
        Calcula scores de demanda para todos los features.
        Retorna lista de dicts con id, score_demanda, tier, justificacion.
        """
        if sector:
            self.sector = sector
            self.weights = SECTOR_WEIGHTS.get(sector, SECTOR_WEIGHTS["telecomunicaciones"])

        results = []
        for feat in features:
            sd = _compute_demand_score(feat, self.weights)
            tier = _demand_tier(sd)
            top3 = _top3_justification(feat, self.weights, self.sector)

            # Narrativa ejecutiva (fallback hardcoded, estilo Watsonx)
            narrativa = self._generate_narrative(feat, sd, tier)

            results.append({
                "id": feat["id"],
                "nombre": feat["nombre"],
                "score_demanda": sd,
                "demand_tier": tier,
                "demand_tier_label": DEMAND_TIER_LABELS[tier],
                "color_leaflet": COLOR_MAP[tier],
                "justificacion_top3": top3,
                "narrativa_ejecutiva": narrativa,
                "score_source": "algorithmic_fallback",
                "lat": feat.get("lat"),
                "lng": feat.get("lng"),
                # Datos originales para raw export
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
        score_map = {d["id"]: d for d in demand_scores}
        result = copy.deepcopy(original_geojson)

        for feat in result.get("features", []):
            fid = feat.get("id") or feat.get("properties", {}).get("id")
            if fid in score_map:
                ds = score_map[fid]
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
        return result
