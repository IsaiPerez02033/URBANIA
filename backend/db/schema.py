"""
URBANIA SEGURIDAD — Esquema de Base de Datos Propia
=====================================================
SQLite local para la fase piloto CDMX.
Diseñado para escalar a PostgreSQL en producción.

Entidades propias levantadas en campo por equipo XOLUM:
  - Luminarias (funciona / no funciona / vandalizada)
  - Terrenos abandonados
  - Puntos ciegos de cámara
  - Observaciones de calle (gentrificación, estado)
  - Zonas auditadas (polígono con fecha de revisión)

Esta base de datos es el activo diferenciador de URBANIA:
datos verificados en campo, no dependientes de fuentes gubernamentales.
"""
import sqlite3
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("urbania.db")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "urbania_campo.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    """Inicializa todas las tablas. Idempotente."""
    conn = get_connection()
    cur = conn.cursor()

    # ── Zonas auditadas ───────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS zonas_auditadas (
        id              TEXT PRIMARY KEY,
        nombre          TEXT NOT NULL,
        alcaldia        TEXT NOT NULL,
        colonia         TEXT NOT NULL,
        lat_centro      REAL NOT NULL,
        lng_centro      REAL NOT NULL,
        area_m2         REAL,
        fecha_auditoria TEXT NOT NULL,
        auditor         TEXT,
        notas           TEXT,
        creado_en       TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── Luminarias ────────────────────────────────────────────────────────────
    # Estado verificado en campo por equipo propio, no datos del gobierno
    cur.execute("""
    CREATE TABLE IF NOT EXISTS luminarias (
        id              TEXT PRIMARY KEY,
        zona_id         TEXT REFERENCES zonas_auditadas(id),
        lat             REAL NOT NULL,
        lng             REAL NOT NULL,
        calle           TEXT,
        numero_poste    TEXT,
        estado          TEXT NOT NULL CHECK(estado IN (
                            'funciona',
                            'no_funciona',
                            'vandalizada',
                            'inexistente',
                            'tenue'
                        )),
        tipo            TEXT CHECK(tipo IN (
                            'led', 'sodio', 'mercurio', 'fluorescente', 'desconocido'
                        )) DEFAULT 'desconocido',
        altura_m        REAL,
        radio_cobertura_m REAL DEFAULT 15.0,
        foto_url        TEXT,
        reportada_en    TEXT DEFAULT (datetime('now')),
        verificada      INTEGER DEFAULT 1,
        notas           TEXT
    )
    """)

    # ── Terrenos abandonados ──────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS terrenos_abandonados (
        id              TEXT PRIMARY KEY,
        zona_id         TEXT REFERENCES zonas_auditadas(id),
        lat             REAL NOT NULL,
        lng             REAL NOT NULL,
        calle_referencia TEXT,
        area_estimada_m2 REAL,
        nivel_riesgo    TEXT CHECK(nivel_riesgo IN ('alto', 'medio', 'bajo')) DEFAULT 'medio',
        tiene_acceso_publico INTEGER DEFAULT 1,
        tiempo_abandono TEXT CHECK(tiempo_abandono IN (
                            'menos_6m', '6m_a_2a', 'mas_2a', 'desconocido'
                        )) DEFAULT 'desconocido',
        signos_actividad_ilegal INTEGER DEFAULT 0,
        foto_url        TEXT,
        reportado_en    TEXT DEFAULT (datetime('now')),
        notas           TEXT
    )
    """)

    # ── Puntos ciegos de cámara ───────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS puntos_ciegos (
        id              TEXT PRIMARY KEY,
        zona_id         TEXT REFERENCES zonas_auditadas(id),
        lat             REAL NOT NULL,
        lng             REAL NOT NULL,
        calle           TEXT,
        tipo_punto_ciego TEXT CHECK(tipo_punto_ciego IN (
                            'sin_camara',
                            'camara_danada',
                            'angulo_muerto',
                            'sin_iluminacion_nocturna'
                        )) DEFAULT 'sin_camara',
        severidad       TEXT CHECK(severidad IN ('critica', 'alta', 'media')) DEFAULT 'alta',
        flujo_peatonal  TEXT CHECK(flujo_peatonal IN ('alto', 'medio', 'bajo')) DEFAULT 'medio',
        incidentes_reportados INTEGER DEFAULT 0,
        foto_url        TEXT,
        reportado_en    TEXT DEFAULT (datetime('now')),
        notas           TEXT
    )
    """)

    # ── Observaciones de calle ────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS observaciones_calle (
        id              TEXT PRIMARY KEY,
        zona_id         TEXT REFERENCES zonas_auditadas(id),
        nombre_calle    TEXT NOT NULL,
        lat_inicio      REAL,
        lng_inicio      REAL,
        lat_fin         REAL,
        lng_fin         REAL,
        estado_pavimento TEXT CHECK(estado_pavimento IN (
                            'bueno', 'regular', 'malo', 'critico'
                        )) DEFAULT 'regular',
        iluminacion_general TEXT CHECK(iluminacion_general IN (
                            'buena', 'regular', 'mala', 'nula'
                        )) DEFAULT 'regular',
        nivel_gentrificacion TEXT CHECK(nivel_gentrificacion IN (
                            'alto',    -- zona ya gentrificada (comercios premium, lofts)
                            'en_proceso', -- mezcla, precios subiendo
                            'bajo',    -- zona popular sin cambio visible
                            'deterioro'   -- zona en declive
                        )) DEFAULT 'bajo',
        presencia_comercio_formal INTEGER DEFAULT 1,
        presencia_comercio_informal INTEGER DEFAULT 0,
        transito_vehicular TEXT CHECK(transito_vehicular IN ('alto', 'medio', 'bajo')) DEFAULT 'medio',
        observado_en    TEXT DEFAULT (datetime('now')),
        notas           TEXT
    )
    """)

    # ── Índice de cobertura de iluminación por zona ───────────────────────────
    # Vista materializada calculada después de cada levantamiento de campo
    cur.execute("""
    CREATE TABLE IF NOT EXISTS indice_iluminacion_zona (
        zona_id             TEXT PRIMARY KEY REFERENCES zonas_auditadas(id),
        total_luminarias    INTEGER DEFAULT 0,
        funcionando         INTEGER DEFAULT 0,
        no_funcionando      INTEGER DEFAULT 0,
        vandalizadas        INTEGER DEFAULT 0,
        cobertura_pct       REAL DEFAULT 0.0,
        score_iluminacion   REAL DEFAULT 0.0,   -- 0-100
        ultima_actualizacion TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── Score de Seguridad Urbana por zona ────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS score_seguridad_zona (
        zona_id                 TEXT PRIMARY KEY REFERENCES zonas_auditadas(id),
        score_iluminacion       REAL DEFAULT 0.0,   -- peso 35%
        score_cobertura_camara  REAL DEFAULT 0.0,   -- peso 30%
        score_infraestructura   REAL DEFAULT 0.0,   -- peso 20%
        score_entorno           REAL DEFAULT 0.0,   -- peso 15%
        score_total             REAL DEFAULT 0.0,   -- 0-100
        clasificacion           TEXT DEFAULT 'sin_datos',
        n_luminarias_ok         INTEGER DEFAULT 0,
        n_puntos_ciegos         INTEGER DEFAULT 0,
        n_terrenos_abandonados  INTEGER DEFAULT 0,
        calculado_en            TEXT DEFAULT (datetime('now'))
    )
    """)

    conn.commit()
    conn.close()
    logger.info("Base de datos URBANIA inicializada: %s", DB_PATH)


def seed_demo_data():
    """
    Inserta datos de demo para la zona piloto CDMX.
    Solo si la BD está vacía.
    """
    conn = get_connection()
    cur = conn.cursor()

    existing = cur.execute("SELECT COUNT(*) FROM zonas_auditadas").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    import uuid

    # Zonas auditadas piloto
    zonas = [
        ("ZONA-001", "Polanco Centro",      "Miguel Hidalgo",  "Polanco",         19.4308, -99.1776, 480000),
        ("ZONA-002", "Roma Norte",          "Cuauhtémoc",      "Roma Norte",       19.4200, -99.1603, 310000),
        ("ZONA-003", "Tepito",              "Cuauhtémoc",      "Tepito",           19.4362, -99.1285, 290000),
        ("ZONA-004", "Condesa",             "Cuauhtémoc",      "Condesa",          19.4145, -99.1687, 340000),
        ("ZONA-005", "Iztapalapa Centro",   "Iztapalapa",      "Iztapalapa",       19.3970, -99.1190, 420000),
        ("ZONA-006", "Centro Histórico",    "Cuauhtémoc",      "Centro",           19.4315, -99.1330, 390000),
        ("ZONA-007", "Bondojito",           "Iztapalapa",      "Bondojito",        19.4110, -99.1140, 350000),
        ("ZONA-008", "Anzures",             "Miguel Hidalgo",  "Anzures",          19.4360, -99.1806, 260000),
        ("ZONA-009", "Doctores",            "Cuauhtémoc",      "Doctores",         19.4090, -99.1405, 280000),
        ("ZONA-010", "Coyoacán Centro",     "Coyoacán",        "Del Carmen",       19.3900, -99.1570, 320000),
    ]

    for z in zonas:
        cur.execute("""
            INSERT OR IGNORE INTO zonas_auditadas
            (id, nombre, alcaldia, colonia, lat_centro, lng_centro, area_m2, fecha_auditoria, auditor)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (*z, "2026-03-15", "Equipo XOLUM Alpha"))

    # Luminarias por zona (datos representativos de campo)
    luminarias_demo = [
        # (zona_id, lat, lng, calle, estado, tipo, radio)
        # Polanco — buena iluminación
        ("ZONA-001", 19.4310, -99.1778, "Av. Presidente Masaryk", "funciona", "led", 20.0),
        ("ZONA-001", 19.4306, -99.1772, "Av. Presidente Masaryk", "funciona", "led", 20.0),
        ("ZONA-001", 19.4312, -99.1770, "Calle Molière",          "funciona", "led", 18.0),
        ("ZONA-001", 19.4304, -99.1780, "Calle Newton",           "tenue",    "sodio", 12.0),
        ("ZONA-001", 19.4315, -99.1775, "Av. Horacio",            "funciona", "led", 20.0),
        # Roma Norte — iluminación media
        ("ZONA-002", 19.4202, -99.1605, "Álvaro Obregón",         "funciona", "led", 18.0),
        ("ZONA-002", 19.4198, -99.1600, "Orizaba",                "no_funciona", "sodio", 15.0),
        ("ZONA-002", 19.4205, -99.1610, "Orizaba",                "funciona", "led", 18.0),
        ("ZONA-002", 19.4195, -99.1608, "Tonalá",                 "tenue", "mercurio", 10.0),
        # Tepito — iluminación crítica
        ("ZONA-003", 19.4360, -99.1287, "Eje 1 Nte.",             "no_funciona", "sodio", 15.0),
        ("ZONA-003", 19.4365, -99.1283, "Toltecas",               "vandalizada", "fluorescente", 0.0),
        ("ZONA-003", 19.4358, -99.1290, "Peralvillo",             "no_funciona", "sodio", 15.0),
        ("ZONA-003", 19.4362, -99.1285, "Jesús Carranza",         "inexistente", "desconocido", 0.0),
        # Condesa — buena iluminación
        ("ZONA-004", 19.4147, -99.1689, "Ámsterdam",              "funciona", "led", 20.0),
        ("ZONA-004", 19.4143, -99.1685, "Ámsterdam",              "funciona", "led", 20.0),
        ("ZONA-004", 19.4150, -99.1692, "Tamaulipas",             "funciona", "led", 18.0),
        # Iztapalapa — iluminación deficiente
        ("ZONA-005", 19.3972, -99.1192, "Eje 6 Sur",              "no_funciona", "sodio", 15.0),
        ("ZONA-005", 19.3968, -99.1188, "Ermita Iztapalapa",      "tenue", "mercurio", 8.0),
        ("ZONA-005", 19.3975, -99.1195, "Lateral",                "vandalizada", "sodio", 0.0),
        # Bondojito — crítico
        ("ZONA-007", 19.4112, -99.1142, "Calle sin nombre",       "inexistente", "desconocido", 0.0),
        ("ZONA-007", 19.4108, -99.1138, "Eje 4 Ote.",             "no_funciona", "sodio", 15.0),
        ("ZONA-007", 19.4115, -99.1145, "Lateral",                "vandalizada", "fluorescente", 0.0),
    ]

    for i, lum in enumerate(luminarias_demo):
        cur.execute("""
            INSERT OR IGNORE INTO luminarias
            (id, zona_id, lat, lng, calle, estado, tipo, radio_cobertura_m, verificada)
            VALUES (?,?,?,?,?,?,?,?,1)
        """, (f"LUM-{i+1:04d}", *lum))

    # Terrenos abandonados
    terrenos_demo = [
        ("ZONA-003", 19.4355, -99.1282, "Jesús Carranza s/n",      800, "alto",  1, "mas_2a",   1),
        ("ZONA-003", 19.4368, -99.1288, "Toltecas esq. Hernández",  500, "alto",  1, "mas_2a",   1),
        ("ZONA-005", 19.3965, -99.1185, "Ermita Iztapalapa",        1200, "alto", 1, "mas_2a",   1),
        ("ZONA-007", 19.4105, -99.1135, "Eje 4 Ote.",               900, "alto",  1, "6m_a_2a",  1),
        ("ZONA-009", 19.4088, -99.1403, "Dr. Liceaga",              400, "medio", 1, "6m_a_2a",  0),
        ("ZONA-006", 19.4310, -99.1325, "Correo Mayor",             350, "medio", 0, "menos_6m", 0),
    ]

    for i, t in enumerate(terrenos_demo):
        cur.execute("""
            INSERT OR IGNORE INTO terrenos_abandonados
            (id, zona_id, lat, lng, calle_referencia, area_estimada_m2,
             nivel_riesgo, tiene_acceso_publico, tiempo_abandono, signos_actividad_ilegal)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (f"TER-{i+1:04d}", *t))

    # Puntos ciegos de cámara
    puntos_ciegos_demo = [
        ("ZONA-003", 19.4362, -99.1284, "Jesús Carranza",    "sin_camara",           "critica", "alto",  8),
        ("ZONA-003", 19.4358, -99.1289, "Peralvillo",         "sin_iluminacion_nocturna", "critica", "alto", 5),
        ("ZONA-007", 19.4110, -99.1140, "Eje 4 Ote.",         "sin_camara",           "critica", "medio", 3),
        ("ZONA-005", 19.3970, -99.1190, "Ermita Iztapalapa",  "camara_danada",         "alta",   "alto",  4),
        ("ZONA-009", 19.4092, -99.1407, "Dr. Río de la Loza", "angulo_muerto",         "media",  "medio", 1),
        ("ZONA-006", 19.4318, -99.1328, "Rep. de Uruguay",    "sin_camara",            "alta",   "alto",  2),
        ("ZONA-002", 19.4196, -99.1602, "Tonalá",             "angulo_muerto",         "media",  "medio", 0),
    ]

    for i, pc in enumerate(puntos_ciegos_demo):
        cur.execute("""
            INSERT OR IGNORE INTO puntos_ciegos
            (id, zona_id, lat, lng, calle, tipo_punto_ciego, severidad, flujo_peatonal, incidentes_reportados)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (f"PC-{i+1:04d}", *pc))

    # Observaciones de calle
    obs_demo = [
        ("ZONA-001", "Av. Presidente Masaryk", "bueno",   "buena",   "alto",        1, 0, "alto"),
        ("ZONA-002", "Álvaro Obregón",         "bueno",   "regular", "en_proceso",  1, 1, "medio"),
        ("ZONA-003", "Jesús Carranza",         "malo",    "nula",    "deterioro",   0, 1, "bajo"),
        ("ZONA-004", "Ámsterdam",              "bueno",   "buena",   "en_proceso",  1, 0, "medio"),
        ("ZONA-005", "Ermita Iztapalapa",      "regular", "mala",    "bajo",        1, 1, "alto"),
        ("ZONA-006", "Rep. de Uruguay",        "regular", "regular", "en_proceso",  1, 1, "alto"),
        ("ZONA-007", "Eje 4 Ote.",             "malo",    "mala",    "deterioro",   0, 1, "bajo"),
        ("ZONA-008", "Ejército Nacional",      "bueno",   "buena",   "alto",        1, 0, "alto"),
        ("ZONA-009", "Dr. Río de la Loza",     "regular", "regular", "bajo",        1, 0, "medio"),
        ("ZONA-010", "Francisco Sosa",         "bueno",   "buena",   "bajo",        1, 0, "bajo"),
    ]

    for i, obs in enumerate(obs_demo):
        cur.execute("""
            INSERT OR IGNORE INTO observaciones_calle
            (id, zona_id, nombre_calle, estado_pavimento, iluminacion_general,
             nivel_gentrificacion, presencia_comercio_formal, presencia_comercio_informal, transito_vehicular)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (f"OBS-{i+1:04d}", *obs))

    conn.commit()
    conn.close()
    logger.info("Datos demo insertados correctamente.")
