"""
SUSVI — Módulo de Ingesta de Datos (M1)
==========================================
Carga el fixture GeoJSON y normaliza features a formato estándar.
En modo producción activa pipelines reales (DENUE, SNSP, VIIRS, OSM).
"""
import json
import os
import logging

logger = logging.getLogger("susvi.ingest")

PROD_MODE_VAR = "SUSVI_PROD_MODE"


def flag_production_sources() -> bool:
    val = os.environ.get(PROD_MODE_VAR, "0").strip().lower()
    return val in ("1", "true", "yes")


def load_mock_fixture(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_feature(feat: dict) -> dict:
    """Normaliza un feature GeoJSON a dict plano para los agentes."""
    props = feat.get("properties", {})
    fid = feat.get("id") or props.get("id", "unknown")
    coords = feat.get("geometry", {}).get("coordinates", [[]])[0]
    lats = [c[1] for c in coords]
    lngs = [c[0] for c in coords]
    centroid_lat = sum(lats) / len(lats) if lats else props.get("lat", 19.43)
    centroid_lng = sum(lngs) / len(lngs) if lngs else props.get("lng", -99.17)

    return {
        "id": fid,
        "nombre": props.get("nombre", fid),
        "lat": centroid_lat,
        "lng": centroid_lng,
        "geometry": feat.get("geometry"),
        # Variables de demanda
        "densidad_poblacional": float(props.get("densidad_poblacional", 15000)),
        "actividad_economica_denue": float(props.get("actividad_economica_denue", 100)),
        "luminosidad_viirs": float(props.get("luminosidad_viirs", 150)),
        "acceso_gtfs": bool(props.get("acceso_gtfs", True)),
        # Variables de riesgo
        "incidencia_delictiva_snsp": float(props.get("incidencia_delictiva_snsp", 30)),
        "tipo_delito_predominante": props.get("tipo_delito_predominante", "robo_transeúnte"),
        "iluminacion_publica": float(props.get("iluminacion_publica", 70)),
        "accesibilidad_logistica": float(props.get("accesibilidad_logistica", 70)),
    }


def run_ingestion(zone_polygon: dict, sector: str) -> list:
    """
    Punto de entrada principal del módulo de ingesta.
    Retorna lista de features normalizados.
    """
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    fixture_path = os.path.join(data_dir, "mock_fixture.json")

    if not os.path.exists(fixture_path):
        raise FileNotFoundError(f"Fixture no encontrado: {fixture_path}")

    geojson = load_mock_fixture(fixture_path)
    features = geojson.get("features", [])

    if not features:
        raise ValueError("El fixture no contiene features.")

    normalized = [_normalize_feature(f) for f in features]
    logger.info("Ingesta completada: %d manzanas normalizadas para sector=%s", len(normalized), sector)
    return normalized
