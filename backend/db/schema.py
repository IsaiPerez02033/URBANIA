"""
URBANIA SEGURIDAD — Esquema de Base de Datos Propia
=====================================================
# Definimos la descripción general del sistema de base de datos que estamos construyendo,
# explicando su propósito, alcance y diferenciador principal.

SQLite local para la fase piloto CDMX.
# Indicamos que usamos SQLite como motor local para pruebas iniciales en CDMX.

Diseñado para escalar a PostgreSQL en producción.
# Dejamos claro que la arquitectura está pensada para migrar fácilmente a un sistema más robusto.

Entidades propias levantadas en campo por equipo XOLUM:
# Documentamos que los datos no provienen de terceros, sino de levantamiento propio.

  - Luminarias (funciona / no funciona / vandalizada)
  - Terrenos abandonados
  - Puntos ciegos de cámara
  - Observaciones de calle (gentrificación, estado)
  - Zonas auditadas (polígono con fecha de revisión)
# Enumeramos las entidades principales que modelamos en la base de datos.

Esta base de datos es el activo diferenciador de URBANIA:
datos verificados en campo, no dependientes de fuentes gubernamentales.
# Reforzamos el valor del sistema: datos propios, confiables y verificables.
"""

# Importamos las librerías necesarias para manejar la base de datos, sistema de archivos y logging
import sqlite3
import os
import logging

# Importamos utilidades de fecha con zona horaria para registros temporales
from datetime import datetime, timezone

# Configuramos un logger específico para el módulo de base de datos
logger = logging.getLogger("urbania.db")

# Construimos la ruta absoluta del archivo de base de datos local
# Usamos el directorio actual del archivo para asegurar portabilidad
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "urbania_campo.db")


def get_connection() -> sqlite3.Connection:
    # Creamos una conexión a la base de datos SQLite
    conn = sqlite3.connect(DB_PATH)
    
    # Configuramos el retorno de filas como diccionarios (más fácil de usar que tuplas)
    conn.row_factory = sqlite3.Row
    
    # Activamos el soporte de llaves foráneas (por defecto SQLite no lo tiene activo)
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Activamos el modo WAL para mejorar concurrencia y rendimiento en escritura
    conn.execute("PRAGMA journal_mode = WAL")
    
    # Retornamos la conexión lista para usarse
    return conn


def init_db():
    """Inicializa todas las tablas. Idempotente."""
    # Definimos una función que crea todas las tablas necesarias
    # Es idempotente: puede ejecutarse múltiples veces sin duplicar estructuras

    # Obtenemos la conexión a la base de datos
    conn = get_connection()
    
    # Creamos un cursor para ejecutar comandos SQL
    cur = conn.cursor()

    # ── Zonas auditadas ───────────────────────────────────────────────────────
    # Definimos la tabla principal que agrupa todas las observaciones por zona
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
    # Creamos la tabla de luminarias verificadas en campo por nuestro equipo
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
    # Modelamos terrenos que representan posibles focos de riesgo urbano
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
    # Registramos zonas sin vigilancia o con fallas en cámaras
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
    # Almacenamos información cualitativa del entorno urbano
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
                            'alto',
                            'en_proceso',
                            'bajo',
                            'deterioro'
                        )) DEFAULT 'bajo',
        presencia_comercio_formal INTEGER DEFAULT 1,
        presencia_comercio_informal INTEGER DEFAULT 0,
        transito_vehicular TEXT CHECK(transito_vehicular IN ('alto', 'medio', 'bajo')) DEFAULT 'medio',
        observado_en    TEXT DEFAULT (datetime('now')),
        notas           TEXT
    )
    """)

    # ── Índice de iluminación por zona ────────────────────────────────────────
    # Creamos una tabla agregada para métricas de iluminación
    cur.execute("""
    CREATE TABLE IF NOT EXISTS indice_iluminacion_zona (
        zona_id             TEXT PRIMARY KEY REFERENCES zonas_auditadas(id),
        total_luminarias    INTEGER DEFAULT 0,
        funcionando         INTEGER DEFAULT 0,
        no_funcionando      INTEGER DEFAULT 0,
        vandalizadas        INTEGER DEFAULT 0,
        cobertura_pct       REAL DEFAULT 0.0,
        score_iluminacion   REAL DEFAULT 0.0,
        ultima_actualizacion TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── Score de seguridad urbana ─────────────────────────────────────────────
    # Consolidamos métricas para generar un score global por zona
    cur.execute("""
    CREATE TABLE IF NOT EXISTS score_seguridad_zona (
        zona_id                 TEXT PRIMARY KEY REFERENCES zonas_auditadas(id),
        score_iluminacion       REAL DEFAULT 0.0,
        score_cobertura_camara  REAL DEFAULT 0.0,
        score_infraestructura   REAL DEFAULT 0.0,
        score_entorno           REAL DEFAULT 0.0,
        score_total             REAL DEFAULT 0.0,
        clasificacion           TEXT DEFAULT 'sin_datos',
        n_luminarias_ok         INTEGER DEFAULT 0,
        n_puntos_ciegos         INTEGER DEFAULT 0,
        n_terrenos_abandonados  INTEGER DEFAULT 0,
        calculado_en            TEXT DEFAULT (datetime('now'))
    )
    """)

    # Guardamos todos los cambios en la base de datos
    conn.commit()
    
    # Cerramos la conexión
    conn.close()
    
    # Registramos en logs que la base fue inicializada correctamente
    logger.info("Base de datos URBANIA inicializada: %s", DB_PATH)