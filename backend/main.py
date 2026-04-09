"""
URBANIA SEGURIDAD — API REST v2.0
===================================
IBM Watsonx AI (Granite 3-8B) + Base de datos propia de campo XOLUM
"""
# Importamos las herramientas de logging y medición de tiempo
import logging, time
# Importamos utilidades de fecha con soporte de zona horaria
from datetime import datetime, timezone
# Importamos dotenv para cargar variables de entorno desde el archivo .env
from dotenv import load_dotenv
load_dotenv()  # Cargamos el archivo .env ANTES de cualquier otro import para garantizar disponibilidad de variables

# Importamos FastAPI y el modelo de Request para gestionar la aplicación y las solicitudes HTTP
from fastapi import FastAPI, Request
# Importamos el middleware de CORS para habilitar peticiones desde el frontend
from fastapi.middleware.cors import CORSMiddleware

# Importamos las funciones de inicialización y semilla de la base de datos
from db.schema import init_db, seed_demo_data
# Importamos el router de seguridad que contiene todos los endpoints de la API
from routes.security import router as security_router

# Configuramos el formato global del sistema de logs para toda la aplicación
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
# Creamos el logger específico para el módulo principal de la API
logger = logging.getLogger("urbania.api")

# Inicializamos la aplicación FastAPI con su título, descripción y versión
app = FastAPI(
    title="URBANIA Seguridad",
    description=(
        "Inteligencia de Seguridad Urbana B2B — IBM Watsonx AI (Granite 3-8B) + "
        "datos propios verificados en campo. Sector piloto: CDMX."
    ),
    version="2.0.0",
    docs_url="/docs",      # Ruta para la documentación Swagger UI
    redoc_url="/redoc",    # Ruta para la documentación ReDoc
)

# Agregamos el middleware de CORS para permitir peticiones desde los orígenes del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",  # Vite dev server
        "http://localhost:4173", "http://localhost:3000",   # Vite preview y CRA
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Definimos un middleware HTTP para registrar en logs todas las peticiones entrantes con su tiempo de respuesta
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Registramos el tiempo de inicio de la petición
    start = time.time()
    # Procesamos la petición y obtenemos la respuesta
    response = await call_next(request)
    # Registramos el método, ruta, código de respuesta y tiempo total transcurrido
    logger.info("%s %s -> %s (%.3fs)",
                request.method, request.url.path,
                response.status_code, time.time() - start)
    return response

# Definimos el evento de arranque para inicializar recursos al levantar el servidor
@app.on_event("startup")
async def startup():
    logger.info("Inicializando BD y Watsonx...")
    # Creamos las tablas de la base de datos si no existen
    init_db()
    # Insertamos datos de demostración para el entorno piloto
    seed_demo_data()

    # Verificamos si Watsonx está correctamente configurado
    from utils.watsonx_client import get_watsonx_client
    wx = get_watsonx_client()
    if wx.is_available():
        logger.info("IBM Watsonx AI activo — modelo: %s", wx.model_id)
    else:
        # Si no hay credenciales válidas, operamos en modo fallback algorítmico
        logger.warning("Watsonx no disponible — modo fallback algorítmico")

    logger.info("URBANIA Seguridad lista.")

# Registramos el router de seguridad en la aplicación principal
app.include_router(security_router)

# Definimos el endpoint de salud del sistema para monitoreo y comprobación de estado
@app.get("/api/v1/health", tags=["Sistema"])
def health():
    # Importamos localmente para evitar ciclos de importación al arrancar
    from db.schema import get_connection, DB_PATH
    from utils.watsonx_client import get_watsonx_client
    # Abrimos conexión a la base de datos para consultar estadísticas
    conn = get_connection()
    # Contamos los registros principales en la base de datos de campo
    stats = {
        "zonas":     conn.execute("SELECT COUNT(*) FROM zonas_auditadas").fetchone()[0],
        "luminarias":conn.execute("SELECT COUNT(*) FROM luminarias").fetchone()[0],
        "p_ciegos":  conn.execute("SELECT COUNT(*) FROM puntos_ciegos").fetchone()[0],
        "terrenos":  conn.execute("SELECT COUNT(*) FROM terrenos_abandonados").fetchone()[0],
    }
    # Cerramos la conexión después de obtener los datos
    conn.close()
    # Consultamos el estado actual del cliente de Watsonx
    wx = get_watsonx_client()
    # Retornamos el estado general del sistema con métricas de base de datos y Watsonx
    return {
        "status": "ok",
        "version": "2.0.0",
        "sector": "seguridad_urbana",
        "watsonx": {
            "activo": wx.is_available(),
            "modelo": wx.model_id if wx.is_available() else "fallback_algorítmico",
        },
        "db_stats": stats,
        "datos": "Campo propio XOLUM — no gubernamental",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
