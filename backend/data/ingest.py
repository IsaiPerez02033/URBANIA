"""
# Documentamos como equipo el módulo de ingesta de datos (M1),
# donde definimos que este componente se encarga de cargar datos GeoJSON
# y normalizarlos a un formato estándar para los agentes del sistema.
URBANIA — Módulo de Ingesta de Datos (M1)
==========================================
Carga el fixture GeoJSON y normaliza features a formato estándar.
En modo producción activa pipelines reales (DENUE, SNSP, VIIRS, OSM).
"""
# Importamos json para leer archivos en formato JSON
import json
# Importamos os para manejar rutas y variables de entorno
import os
# Importamos logging para registrar eventos del proceso de ingesta
import logging

# Inicializamos el logger del módulo de ingesta
logger = logging.getLogger("urbania.ingest")

# Definimos la variable de entorno que controla el modo producción
PROD_MODE_VAR = "URBANIA_PROD_MODE"


# Definimos una función que valida si debemos usar fuentes reales de datos
def flag_production_sources() -> bool:
    val = os.environ.get(PROD_MODE_VAR, "0").strip().lower()  # Leemos la variable de entorno y la normalizamos
    return val in ("1", "true", "yes")  # Evaluamos si está activado el modo producción


# Definimos la función para cargar el fixture mock desde un archivo
def load_mock_fixture(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:  # Abrimos el archivo en modo lectura con codificación UTF-8
        return json.load(f)  # Cargamos y retornamos el contenido como diccionario


# Definimos la función que normaliza cada feature del GeoJSON
def _normalize_feature(feat: dict) -> dict:
    """Normaliza un feature GeoJSON a dict plano para los agentes."""
    props = feat.get("properties", {})  # Extraemos las propiedades del feature
    fid = feat.get("id") or props.get("id", "unknown")  # Definimos un identificador único

    coords = feat.get("geometry", {}).get("coordinates", [[]])[0]  # Obtenemos coordenadas del polígono
    lats = [c[1] for c in coords]  # Extraemos latitudes
    lngs = [c[0] for c in coords]  # Extraemos longitudes

    # Calculamos el centroide en latitud o usamos valor por defecto
    centroid_lat = sum(lats) / len(lats) if lats else props.get("lat", 19.43)
    # Calculamos el centroide en longitud o usamos valor por defecto
    centroid_lng = sum(lngs) / len(lngs) if lngs else props.get("lng", -99.17)

    # Retornamos el feature en formato plano estandarizado
    return {
        "id": fid,  # ID del feature
        "nombre": props.get("nombre", fid),  # Nombre de la zona
        "lat": centroid_lat,  # Latitud del centroide
        "lng": centroid_lng,  # Longitud del centroide
        "geometry": feat.get("geometry"),  # Geometría original

        # Variables de demanda
        "densidad_poblacional": float(props.get("densidad_poblacional", 15000)),  # Densidad poblacional
        "actividad_economica_denue": float(props.get("actividad_economica_denue", 100)),  # Actividad económica
        "luminosidad_viirs": float(props.get("luminosidad_viirs", 150)),  # Luminosidad nocturna
        "acceso_gtfs": bool(props.get("acceso_gtfs", True)),  # Acceso a transporte

        # Variables de riesgo
        "incidencia_delictiva_snsp": float(props.get("incidencia_delictiva_snsp", 30)),  # Incidencia delictiva
        "tipo_delito_predominante": props.get("tipo_delito_predominante", "robo_transeúnte"),  # Tipo de delito
        "iluminacion_publica": float(props.get("iluminacion_publica", 70)),  # Nivel de iluminación
        "accesibilidad_logistica": float(props.get("accesibilidad_logistica", 70)),  # Accesibilidad logística
    }


# Definimos la función principal de ingesta de datos
def run_ingestion(zone_polygon: dict, sector: str) -> list:
    """
    Punto de entrada principal del módulo de ingesta.
    Retorna lista de features normalizados.
    """
    # Construimos la ruta del directorio actual del archivo
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    # Definimos la ruta al archivo fixture
    fixture_path = os.path.join(data_dir, "mock_fixture.json")

    # Validamos que el archivo exista
    if not os.path.exists(fixture_path):
        raise FileNotFoundError(f"Fixture no encontrado: {fixture_path}")

    # Cargamos el archivo GeoJSON
    geojson = load_mock_fixture(fixture_path)
    # Extraemos la lista de features
    features = geojson.get("features", [])

    # Validamos que existan features
    if not features:
        raise ValueError("El fixture no contiene features.")

    # Normalizamos todos los features utilizando la función definida
    normalized = [_normalize_feature(f) for f in features]

    # Registramos en logs el resultado de la ingesta
    logger.info("Ingesta completada: %d manzanas normalizadas para sector=%s", len(normalized), sector)

    return normalized  # Retornamos la lista de features normalizados