"""
URBANIA — Cliente IBM Watsonx AI (Granite 3-8B)
=================================================
Conecta con Granite 3-8B para generar narrativas ejecutivas de seguridad urbana.
Fallback algorítmico si no hay conexión (modo demo).
"""
import os, json, time, logging
import urllib.request, urllib.parse
from typing import Optional

logger = logging.getLogger("urbania.watsonx")

MODEL_GRANITE_3  = "ibm/granite-3-8b-instruct"
MODEL_GRANITE_13 = "ibm/granite-13b-instruct-v2"
MODEL_LLAMA      = "meta-llama/llama-3-1-70b-instruct"

_token_cache: dict = {"token": None, "expiry": 0.0}


def _get_iam_token(api_key: str) -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expiry"]:
        return _token_cache["token"]
    data = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://iam.cloud.ibm.com/identity/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
        _token_cache["token"] = body["access_token"]
        _token_cache["expiry"] = now + body.get("expires_in", 3600) - 300
        logger.info("Token IAM renovado")
        return _token_cache["token"]


def _call_watsonx(prompt: str, model_id: str, api_key: str,
                  project_id: str, base_url: str,
                  max_new_tokens: int = 300) -> str:
    token = _get_iam_token(api_key)
    if "granite-3" in model_id:
        full_prompt = (
            "<|system|>\nEres un analista experto en seguridad urbana e infraestructura "
            "en México. Generas análisis concisos y precisos en español para directores "
            "de empresas. Responde directamente sin preámbulos.\n"
            f"<|user|>\n{prompt}\n<|assistant|>\n"
        )
    else:
        full_prompt = f"Sistema: Analista de seguridad urbana en México.\n\nUsuario: {prompt}\n\nAsistente:"

    payload = {
        "model_id": model_id,
        "input": full_prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": max_new_tokens,
            "repetition_penalty": 1.1,
            "stop_sequences": ["\n\n\n", "<|user|>", "<|system|>"],
        },
        "project_id": project_id,
    }
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
        text = body["results"][0]["generated_text"].strip()
        tokens = body["results"][0].get("generated_token_count", 0)
        logger.info("Watsonx OK — modelo=%s tokens=%d", model_id, tokens)
        return text


class WatsonxClient:
    def __init__(self):
        self.api_key    = os.environ.get("WATSONX_API_KEY", "")
        self.project_id = os.environ.get("WATSONX_PROJECT_ID", "")
        self.base_url   = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self.model_id   = os.environ.get("WATSONX_MODEL_ID_BUSINESS", MODEL_GRANITE_3)

    def is_available(self) -> bool:
        return bool(self.api_key and self.project_id)

    def generate(self, prompt: str, max_new_tokens: int = 300,
                 model_id: Optional[str] = None) -> str:
        return _call_watsonx(
            prompt=prompt,
            model_id=model_id or self.model_id,
            api_key=self.api_key,
            project_id=self.project_id,
            base_url=self.base_url,
            max_new_tokens=max_new_tokens,
        )

    def narrativa_zona(self, zona: dict, ssu: float, breakdown: dict) -> str:
        ilum    = breakdown.get("iluminacion", {})
        cam     = breakdown.get("cobertura_camara", {})
        infra   = breakdown.get("infraestructura", {})
        entorno = breakdown.get("entorno", {})
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
            return self.generate(prompt, max_new_tokens=200)
        except Exception as e:
            logger.warning("narrativa_zona falló: %s", e)
            return ""

    def recomendacion_videovigilancia(self, zona: dict, cam: dict, ilum: dict) -> str:
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


_client: Optional[WatsonxClient] = None

def get_watsonx_client() -> WatsonxClient:
    global _client
    if _client is None:
        _client = WatsonxClient()
        if _client.is_available():
            logger.info("Watsonx client listo — modelo: %s", _client.model_id)
        else:
            logger.warning("Watsonx no configurado — fallback algorítmico activo")
    return _client
