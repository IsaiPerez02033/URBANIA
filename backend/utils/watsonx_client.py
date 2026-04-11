"""
SUSVI — Cliente IBM Watsonx AI (Granite 3-8B)
=================================================
Conecta con Granite 3-8B para generar narrativas ejecutivas de seguridad urbana.
Fallback algorítmico si no hay conexión (modo demo).
"""
# Importamos las librerías del sistema para manejo de entorno, JSON, tiempo y logging
import os, json, time, logging
# Importamos las utilidades HTTP de la librería estándar para evitar dependencias externas
import urllib.request, urllib.parse
# Importamos Optional para tipar parámetros opcionales en las funciones
from typing import Optional

# Creamos el logger específico para el cliente de Watsonx
logger = logging.getLogger("susvi.watsonx")

# Declaramos los identificadores de los modelos disponibles en IBM Watsonx
MODEL_GRANITE_3  = "ibm/granite-3-8b-instruct"   # Modelo principal: rápido y eficiente
MODEL_GRANITE_13 = "ibm/granite-13b-instruct-v2"  # Modelo de mayor capacidad
MODEL_LLAMA      = "meta-llama/llama-3-1-70b-instruct"  # Alternativa de Meta

# Declaramos el caché de tokens IAM para evitar solicitar uno nuevo en cada llamada
_token_cache: dict = {"token": None, "expiry": 0.0}


def _get_iam_token(api_key: str) -> str:
    # Verificamos si el token en caché aún es válido antes de solicitar uno nuevo
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expiry"]:
        return _token_cache["token"]
    # Construimos el cuerpo de la petición de token IAM con el tipo de grant correcto
    data = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key,
    }).encode("utf-8")
    # Creamos la petición HTTP POST al endpoint de autenticación de IBM Cloud
    req = urllib.request.Request(
        "https://iam.cloud.ibm.com/identity/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    # Ejecutamos la petición y guardamos el token y su tiempo de expiración en caché
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
        _token_cache["token"] = body["access_token"]
        # Restamos 300 segundos al tiempo de expiración para renovar con margen de seguridad
        _token_cache["expiry"] = now + body.get("expires_in", 3600) - 300
        logger.info("Token IAM renovado")
        return _token_cache["token"]


def _call_watsonx(prompt: str, model_id: str, api_key: str,
                  project_id: str, base_url: str,
                  max_new_tokens: int = 300) -> str:
    # Obtenemos el token IAM vigente para autenticar la petición
    token = _get_iam_token(api_key)
    # Construimos el prompt completo con la plantilla de chat según el modelo
    if "granite-3" in model_id:
        # Usamos el formato de chat con etiquetas de sistema y usuario para Granite 3
        full_prompt = (
            "<|system|>\nEres un analista experto en seguridad urbana e infraestructura "
            "en México. Generas análisis concisos y precisos en español para directores "
            "de empresas. Responde directamente sin preámbulos.\n"
            f"<|user|>\n{prompt}\n<|assistant|>\n"
        )
    else:
        # Para otros modelos usamos un formato de chat más simple
        full_prompt = f"Sistema: Analista de seguridad urbana en México.\n\nUsuario: {prompt}\n\nAsistente:"

    # Construimos el payload con los parámetros de generación del modelo
    payload = {
        "model_id": model_id,
        "input": full_prompt,
        "parameters": {
            "decoding_method": "greedy",       # Selección determinista del token de mayor probabilidad
            "max_new_tokens": max_new_tokens,  # Límite de tokens generados en la respuesta
            "repetition_penalty": 1.1,         # Penalizamos repetición para textos más variados
            "stop_sequences": ["\n\n\n", "<|user|>", "<|system|>"],  # Secuencias que detienen la generación
        },
        "project_id": project_id,
    }
    # Creamos la petición HTTP POST al endpoint de generación de texto de Watsonx
    req = urllib.request.Request(
        f"{base_url}/ml/v1/text/generation?version=2024-05-31",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    # Ejecutamos la petición y extraemos el texto generado de la respuesta
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
        # Extraemos y limpiamos el texto generado por el modelo
        text = body["results"][0]["generated_text"].strip()
        # Registramos cuántos tokens se consumieron en esta llamada
        tokens = body["results"][0].get("generated_token_count", 0)
        logger.info("Watsonx OK — modelo=%s tokens=%d", model_id, tokens)
        return text


class WatsonxClient:
    def __init__(self):
        # Cargamos las credenciales desde las variables de entorno configuradas en .env
        self.api_key    = os.environ.get("WATSONX_API_KEY", "")
        self.project_id = os.environ.get("WATSONX_PROJECT_ID", "")
        # Usamos el endpoint de Dallas como región por defecto para IBM Cloud
        self.base_url   = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        # El modelo de negocio por defecto es Granite 3-8B
        self.model_id   = os.environ.get("WATSONX_MODEL_ID_BUSINESS", MODEL_GRANITE_3)

    def is_available(self) -> bool:
        # El cliente solo está disponible si tenemos tanto la API key como el project ID
        return bool(self.api_key and self.project_id)

    def generate(self, prompt: str, max_new_tokens: int = 300,
                 model_id: Optional[str] = None) -> str:
        # Delegamos la generación a la función de bajo nivel pasando los parámetros del cliente
        return _call_watsonx(
            prompt=prompt,
            model_id=model_id or self.model_id,  # Usamos el modelo específico o el configurado
            api_key=self.api_key,
            project_id=self.project_id,
            base_url=self.base_url,
            max_new_tokens=max_new_tokens,
        )

    def narrativa_zona(self, zona: dict, ssu: float, breakdown: dict) -> str:
        # Extraemos los sub-scores del breakdown para construir el contexto del prompt
        ilum    = breakdown.get("iluminacion", {})
        cam     = breakdown.get("cobertura_camara", {})
        infra   = breakdown.get("infraestructura", {})
        entorno = breakdown.get("entorno", {})
        # Construimos el prompt con datos reales de campo para Granite 3-8B
        prompt = (
            f'Analiza la seguridad urbana de "{zona["nombre"]}" en {zona.get("alcaldia","CDMX")}, México.\n\n'
            f"Datos verificados en campo:\n"
            f"- SSU total: {ssu:.0f}/100\n"
            f"- Iluminación: {ilum.get('score',0):.0f}/100 — {ilum.get('detalle','')}\n"
            f"- Cobertura cámaras: {cam.get('score',0):.0f}/100 — {cam.get('detalle','')}\n"
            f"- Infraestructura: {infra.get('score',0):.0f}/100 — {infra.get('detalle','')}\n"
            f"- Entorno: {entorno.get('score',0):.0f}/100 — {entorno.get('detalle','')}\n\n"
            f"Escribe UN párrafo ejecutivo de 3 oraciones para un director de seguridad. "
            f"Menciona el SSU, el problema principal y una acción concreta. Sin bullet points."
        )
        try:
            # Generamos la narrativa con un límite de 200 tokens para mantener concisión
            return self.generate(prompt, max_new_tokens=200)
        except Exception as e:
            # Si falla Watsonx retornamos cadena vacía para que el fallback algorítmico tome el control
            logger.warning("narrativa_zona falló: %s", e)
            return ""

    def recomendacion_videovigilancia(self, zona: dict, cam: dict, ilum: dict) -> str:
        # Construimos el prompt orientado a una empresa instaladora de cámaras de seguridad
        prompt = (
            f'Una empresa instaladora de cámaras evalúa "{zona["nombre"]}" en CDMX.\n\n'
            f"Datos de campo:\n"
            f"- Puntos ciegos: {cam.get('n_puntos_ciegos',0)} (críticos: {cam.get('criticos',0)})\n"
            f"- Score cobertura: {cam.get('score',0):.0f}/100\n"
            f"- Luminarias fuera de servicio: {ilum.get('mal',0)} de {ilum.get('total',0)}\n"
            f"- Luminarias vandalizadas: {ilum.get('vandalizadas',0)}\n\n"
            f"Escribe una recomendación comercial de 2-3 oraciones para el director de operaciones. "
            f"Incluye qué instalar, dónde enfocar y el argumento de negocio. Directo y específico."
        )
        try:
            return self.generate(prompt, max_new_tokens=180)
        except Exception as e:
            logger.warning("rec_videovig falló: %s", e)
            return ""

    def recomendacion_constructora(self, zona: dict, ssu: float,
                                   infra: dict, entorno: dict) -> str:
        prompt = (
            f'Una constructora evalúa licitar obra pública en "{zona["nombre"]}", {zona.get("alcaldia","CDMX")}.\n\n'
            f"Datos XOLUM:\n"
            f"- SSU: {ssu:.0f}/100\n"
            f"- Terrenos abandonados: {infra.get('n_terrenos_abandonados',0)}\n"
            f"- Estado vial: {infra.get('score_pavimento',0):.0f}/100\n"
            f"- Gentrificación: {entorno.get('nivel_gentrificacion_predominante','desconocido')}\n\n"
            f"Escribe 2-3 oraciones para el director de licitaciones. "
            f"Indica si la zona es viable, qué considerar en la propuesta técnica y el argumento ante gobierno."
        )
        try:
            return self.generate(prompt, max_new_tokens=180)
        except Exception as e:
            logger.warning("rec_constructora falló: %s", e)
            return ""

    def recomendacion_inmobiliaria(self, zona: dict, ssu: float,
                                   entorno: dict, infra: dict) -> str:
        prompt = (
            f'Una desarrolladora inmobiliaria evalúa invertir en "{zona["nombre"]}", {zona.get("alcaldia","CDMX")}.\n\n'
            f"Datos XOLUM:\n"
            f"- SSU: {ssu:.0f}/100\n"
            f"- Gentrificación: {entorno.get('nivel_gentrificacion_predominante','desconocido')}\n"
            f"- Terrenos abandonados: {infra.get('n_terrenos_abandonados',0)}\n"
            f"- Estado vial: {infra.get('score_pavimento',0):.0f}/100\n\n"
            f"Escribe 2-3 oraciones para el comité de inversión. "
            f"Incluye valorización esperada, riesgo operativo y argumento para due diligence."
        )
        try:
            return self.generate(prompt, max_new_tokens=180)
        except Exception as e:
            logger.warning("rec_inmobiliaria falló: %s", e)
            return ""

    def alerta_critica(self, zona: dict, ssu: float, problemas: list) -> str:
        prompt = (
            f'"{zona["nombre"]}" tiene SSU crítico de {ssu:.0f}/100.\n'
            f"Problemas: {' | '.join(problemas)}\n\n"
            f"Escribe una alerta ejecutiva de 2 oraciones para un comité de inversión. "
            f"Directa, sin eufemismos. Recomienda explícitamente no invertir o la acción mínima requerida."
        )
        try:
            return self.generate(prompt, max_new_tokens=120)
        except Exception as e:
            logger.warning("alerta_critica falló: %s", e)
            return ""


# Declaramos la variable global del cliente singleton para reutilizarlo entre llamadas
_client: Optional[WatsonxClient] = None

def get_watsonx_client() -> WatsonxClient:
    """Retorna la instancia singleton del cliente de Watsonx."""
    global _client
    # Si aún no existe el cliente, lo inicializamos por primera vez
    if _client is None:
        _client = WatsonxClient()
        if _client.is_available():
            logger.info("Watsonx client listo — modelo: %s", _client.model_id)
        else:
            # Si no hay credenciales configuradas, operamos en modo fallback algorítmico
            logger.warning("Watsonx no configurado — fallback algorítmico activo")
    return _client
