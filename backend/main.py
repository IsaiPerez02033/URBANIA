"""
URBANIA SEGURIDAD — API REST v2.0
===================================
IBM Watsonx AI (Granite 3-8B) + Base de datos propia de campo XOLUM
"""
import logging, time
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()  # Cargar .env ANTES de cualquier otro import

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from db.schema import init_db, seed_demo_data
from routes.security import router as security_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("urbania.api")

app = FastAPI(
    title="URBANIA Seguridad",
    description=(
        "Inteligencia de Seguridad Urbana B2B — IBM Watsonx AI (Granite 3-8B) + "
        "datos propios verificados en campo. Sector piloto: CDMX."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://localhost:3000",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info("%s %s -> %s (%.3fs)",
                request.method, request.url.path,
                response.status_code, time.time() - start)
    return response

@app.on_event("startup")
async def startup():
    logger.info("Inicializando BD y Watsonx...")
    init_db()
    seed_demo_data()

    from utils.watsonx_client import get_watsonx_client
    wx = get_watsonx_client()
    if wx.is_available():
        logger.info("IBM Watsonx AI activo — modelo: %s", wx.model_id)
    else:
        logger.warning("Watsonx no disponible — modo fallback algorítmico")

    logger.info("URBANIA Seguridad lista.")

app.include_router(security_router)

@app.get("/api/v1/health", tags=["Sistema"])
def health():
    from db.schema import get_connection, DB_PATH
    from utils.watsonx_client import get_watsonx_client
    conn = get_connection()
    stats = {
        "zonas":     conn.execute("SELECT COUNT(*) FROM zonas_auditadas").fetchone()[0],
        "luminarias":conn.execute("SELECT COUNT(*) FROM luminarias").fetchone()[0],
        "p_ciegos":  conn.execute("SELECT COUNT(*) FROM puntos_ciegos").fetchone()[0],
        "terrenos":  conn.execute("SELECT COUNT(*) FROM terrenos_abandonados").fetchone()[0],
    }
    conn.close()
    wx = get_watsonx_client()
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
