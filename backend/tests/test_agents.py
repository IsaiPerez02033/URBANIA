"""
URBANIA — Test Suite Completa
==============================
Corre con:  cd backend && pytest tests/ -v
Cubre:
  - Ingesta y normalización de datos
  - DemandAgent: scores, tiers, pesos por sector, GeoJSON output
  - RiskAgent: scores, clasificaciones, factores, descarte
  - BusinessAgent: fórmula SV, 3 escenarios, reporte ejecutivo
  - PDF generator: genera sin crashear
  - Consistencia cruzada entre agentes
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ingest import run_ingestion, load_mock_fixture, _normalize_feature
from agents.demand_agent import DemandAgent, _compute_demand_score, _demand_tier, SECTOR_WEIGHTS
from agents.risk_agent import RiskAgent, _compute_risk_score, _risk_tier
from agents.business_agent import BusinessAgent, _score_viabilidad, _ti_norm, _categoria_viabilidad
from utils.pdf_generator import URBANIAReportGenerator

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "../data/mock_fixture.json")

PARAMS_DEFAULT = {
    "ticket_inversion_mxn": 2_000_000,
    "vida_util_anios": 8,
    "tasa_descuento": 0.12,
    "n_unidades_objetivo": 12,
    "sector": "telecomunicaciones",
}


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES PYTEST
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def features():
    return run_ingestion({}, "telecomunicaciones")


@pytest.fixture(scope="module")
def demand_scores(features):
    da = DemandAgent("telecomunicaciones", use_fallback_only=True)
    return da.score(features, "telecomunicaciones")


@pytest.fixture(scope="module")
def risk_scores(features):
    ra = RiskAgent(use_fallback_only=True)
    return ra.score(features)


@pytest.fixture(scope="module")
def business_result(demand_scores, risk_scores):
    ba = BusinessAgent(use_fallback_only=True)
    return ba.generate_scenarios(demand_scores, risk_scores, PARAMS_DEFAULT)


# ─────────────────────────────────────────────────────────────────────────────
# TEST: INGESTA
# ─────────────────────────────────────────────────────────────────────────────

class TestIngest:
    def test_fixture_existe(self):
        assert os.path.exists(FIXTURE_PATH), "mock_fixture.json no encontrado"

    def test_fixture_valido_geojson(self):
        data = load_mock_fixture(FIXTURE_PATH)
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        assert len(data["features"]) >= 50, "Se esperan al menos 50 features"

    def test_run_ingestion_retorna_50_features(self, features):
        assert len(features) == 50

    def test_campos_obligatorios_presentes(self, features):
        campos = [
            "id", "nombre", "lat", "lng",
            "densidad_poblacional", "actividad_economica_denue",
            "luminosidad_viirs", "acceso_gtfs",
            "incidencia_delictiva_snsp", "iluminacion_publica", "accesibilidad_logistica",
        ]
        for feat in features:
            for campo in campos:
                assert campo in feat, f"Campo '{campo}' falta en feature {feat.get('id')}"

    def test_coordenadas_en_rango_cdmx(self, features):
        for f in features:
            assert 19.0 <= f["lat"] <= 20.0, f"Lat fuera de rango CDMX: {f['lat']}"
            assert -100.0 <= f["lng"] <= -98.5, f"Lng fuera de rango CDMX: {f['lng']}"

    def test_valores_numericos_positivos(self, features):
        for f in features:
            assert f["densidad_poblacional"] > 0
            assert f["actividad_economica_denue"] > 0
            assert 0 <= f["luminosidad_viirs"] <= 255
            assert 0 <= f["iluminacion_publica"] <= 100
            assert 0 <= f["accesibilidad_logistica"] <= 100

    def test_ids_unicos(self, features):
        ids = [f["id"] for f in features]
        assert len(ids) == len(set(ids)), "Hay IDs duplicados"

    def test_feature_normaliza_correctamente(self):
        raw = {
            "type": "Feature", "id": "TEST-001",
            "geometry": {"type": "Polygon", "coordinates": [[
                [-99.1674, 19.4284], [-99.1654, 19.4284],
                [-99.1654, 19.4304], [-99.1674, 19.4304],
                [-99.1674, 19.4284],
            ]]},
            "properties": {
                "id": "TEST-001", "nombre": "Test Zona",
                "densidad_poblacional": 20000,
                "actividad_economica_denue": 150,
                "luminosidad_viirs": 180,
                "acceso_gtfs": True,
                "incidencia_delictiva_snsp": 30,
                "tipo_delito_predominante": "robo_transeúnte",
                "iluminacion_publica": 75,
                "accesibilidad_logistica": 80,
            }
        }
        norm = _normalize_feature(raw)
        assert norm["id"] == "TEST-001"
        assert norm["densidad_poblacional"] == 20000.0
        assert norm["acceso_gtfs"] is True
        assert abs(norm["lat"] - 19.4294) < 0.001


# ─────────────────────────────────────────────────────────────────────────────
# TEST: DEMAND AGENT
# ─────────────────────────────────────────────────────────────────────────────

class TestDemandAgent:
    def test_retorna_50_scores(self, demand_scores):
        assert len(demand_scores) == 50

    def test_score_rango_valido(self, demand_scores):
        for d in demand_scores:
            assert 0 <= d["score_demanda"] <= 100, \
                f"Score fuera de rango: {d['score_demanda']} en {d['id']}"

    def test_campos_completos(self, demand_scores):
        campos = ["id", "nombre", "score_demanda", "demand_tier", "color_leaflet",
                  "justificacion_top3", "narrativa_ejecutiva", "lat", "lng"]
        for d in demand_scores:
            for c in campos:
                assert c in d, f"Campo '{c}' falta en {d.get('id')}"

    def test_tiers_validos(self, demand_scores):
        tiers_validos = {"alta", "media", "baja"}
        for d in demand_scores:
            assert d["demand_tier"] in tiers_validos

    def test_justificacion_top3_tiene_3_items(self, demand_scores):
        for d in demand_scores:
            assert len(d["justificacion_top3"]) == 3

    def test_narrativa_no_vacia(self, demand_scores):
        for d in demand_scores:
            assert len(d["narrativa_ejecutiva"]) > 20

    def test_color_leaflet_es_hex(self, demand_scores):
        for d in demand_scores:
            color = d["color_leaflet"]
            assert color.startswith("#") and len(color) == 7

    def test_pesos_sector_suman_uno(self):
        for sector, pesos in SECTOR_WEIGHTS.items():
            total = sum(pesos.values())
            assert abs(total - 1.0) < 0.001, \
                f"Pesos de {sector} no suman 1.0: {total}"

    def test_polanco_mayor_que_tepito(self, features):
        """Polanco debe tener más demanda que Tepito (validación de sentido)."""
        da = DemandAgent("telecomunicaciones", use_fallback_only=True)
        scored = da.score(features, "telecomunicaciones")
        score_map = {d["nombre"]: d["score_demanda"] for d in scored}
        polanco = score_map.get("Polanco Centro") or score_map.get("Polanco Oriente")
        tepito = score_map.get("Tepito")
        if polanco and tepito:
            assert polanco > tepito, \
                f"Error de sentido: Polanco ({polanco}) <= Tepito ({tepito})"

    def test_scores_distintos_entre_sectores(self, features):
        """El mismo fixture debe producir scores distintos por sector."""
        da_tele = DemandAgent("telecomunicaciones", use_fallback_only=True)
        da_inmo = DemandAgent("inmobiliario", use_fallback_only=True)
        s_tele = da_tele.score(features, "telecomunicaciones")
        s_inmo = da_inmo.score(features, "inmobiliario")
        # Al menos un score debe diferir
        diffs = [abs(a["score_demanda"] - b["score_demanda"])
                 for a, b in zip(s_tele, s_inmo)]
        assert max(diffs) > 0.5, "Todos los scores son iguales entre sectores"

    def test_geojson_output_valido(self, demand_scores):
        data_dir = os.path.join(os.path.dirname(__file__), "../data")
        geojson = load_mock_fixture(os.path.join(data_dir, "mock_fixture.json"))
        da = DemandAgent("telecomunicaciones", use_fallback_only=True)
        result = da.to_geojson(demand_scores, geojson)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 50
        # Verificar que las propiedades se enriquecieron
        for feat in result["features"]:
            props = feat.get("properties", {})
            assert "score_demanda" in props
            assert "color_leaflet" in props


# ─────────────────────────────────────────────────────────────────────────────
# TEST: RISK AGENT
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskAgent:
    def test_retorna_50_scores(self, risk_scores):
        assert len(risk_scores) == 50

    def test_score_rango_valido(self, risk_scores):
        for r in risk_scores:
            assert 0 <= r["score_riesgo"] <= 100, \
                f"Score riesgo fuera de rango: {r['score_riesgo']}"

    def test_clasificaciones_validas(self, risk_scores):
        validas = {"verde", "cautela", "descarte"}
        for r in risk_scores:
            assert r["clasificacion"] in validas

    def test_descarte_tiene_razon(self, risk_scores):
        descartes = [r for r in risk_scores if r["clasificacion"] == "descarte"]
        assert len(descartes) > 0, "No hay zonas de descarte (datos anómalos)"
        for d in descartes:
            assert len(d["razon_descarte"]) > 20, \
                f"Zona {d['id']} marcada como descarte sin razón"

    def test_verde_sin_razon_descarte(self, risk_scores):
        verdes = [r for r in risk_scores if r["clasificacion"] == "verde"]
        for v in verdes:
            assert v["razon_descarte"] == ""

    def test_campos_completos(self, risk_scores):
        campos = ["id", "nombre", "score_riesgo", "clasificacion",
                  "color_leaflet", "factores_riesgo", "recomendaciones_mitigacion"]
        for r in risk_scores:
            for c in campos:
                assert c in r, f"Campo '{c}' falta en {r.get('id')}"

    def test_tepito_es_descarte(self, features):
        """Tepito (alta incidencia) debe clasificar como descarte."""
        ra = RiskAgent(use_fallback_only=True)
        scored = ra.score(features)
        risk_map = {r["nombre"]: r for r in scored}
        tepito = risk_map.get("Tepito")
        if tepito:
            assert tepito["clasificacion"] == "descarte", \
                f"Tepito debería ser descarte, es {tepito['clasificacion']}"

    def test_polanco_es_verde(self, features):
        """Polanco (baja incidencia) debe clasificar como verde."""
        ra = RiskAgent(use_fallback_only=True)
        scored = ra.score(features)
        risk_map = {r["nombre"]: r for r in scored}
        polanco = risk_map.get("Polanco Centro") or risk_map.get("Polanco Oriente")
        if polanco:
            assert polanco["clasificacion"] == "verde", \
                f"Polanco debería ser verde, es {polanco['clasificacion']}"

    def test_cautela_tiene_mitigaciones(self, risk_scores):
        cautelas = [r for r in risk_scores if r["clasificacion"] == "cautela"]
        for c in cautelas:
            assert len(c["recomendaciones_mitigacion"]) > 0

    def test_geojson_riesgo_valido(self, risk_scores):
        data_dir = os.path.join(os.path.dirname(__file__), "../data")
        geojson = load_mock_fixture(os.path.join(data_dir, "mock_fixture.json"))
        ra = RiskAgent(use_fallback_only=True)
        result = ra.generate_risk_geojson(risk_scores, geojson)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 50
        for feat in result["features"]:
            assert "score_riesgo" in feat["properties"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST: BUSINESS AGENT
# ─────────────────────────────────────────────────────────────────────────────

class TestBusinessAgent:
    def test_formula_sv_basica(self):
        """SV = SD × (1 - SR/100) × FP / TI_norm."""
        sv = _score_viabilidad(sd=80, sr=20, fp=1.15, ti_norm=1.0)
        expected = 80 * (1 - 20/100) * 1.15 / 1.0
        assert abs(sv - min(expected, 100)) < 0.01

    def test_sv_cero_si_riesgo_maximo(self):
        sv = _score_viabilidad(sd=100, sr=100, fp=1.0, ti_norm=1.0)
        assert sv == 0.0

    def test_sv_clipeado_a_100(self):
        sv = _score_viabilidad(sd=100, sr=0, fp=2.0, ti_norm=0.5)
        assert sv <= 100.0

    def test_ti_norm_baseline(self):
        assert _ti_norm(2_000_000) == 1.0

    def test_ti_norm_escala(self):
        assert _ti_norm(4_000_000) == 2.0
        assert _ti_norm(1_000_000) == 0.5

    def test_categoria_viabilidad(self):
        assert _categoria_viabilidad(75) == "Alta viabilidad"
        assert _categoria_viabilidad(55) == "Viabilidad media"
        assert _categoria_viabilidad(30) == "Descarte"
        assert _categoria_viabilidad(70) == "Alta viabilidad"
        assert _categoria_viabilidad(40) == "Viabilidad media"

    def test_retorna_3_escenarios(self, business_result):
        assert len(business_result["escenarios_algoritmicos"]) == 3

    def test_exactamente_un_recomendado(self, business_result):
        recs = [s for s in business_result["escenarios_algoritmicos"] if s["recomendado"]]
        assert len(recs) == 1, f"Se esperaba 1 recomendado, hay {len(recs)}"

    def test_escenarios_tienen_campos_financieros(self, business_result):
        campos = ["nombre", "n_unidades", "sv_promedio",
                  "roi_estimado_pct", "payback_anios", "npv_mxn",
                  "inversion_total_mxn", "riesgo_exposicion"]
        for esc in business_result["escenarios_algoritmicos"]:
            for c in campos:
                assert c in esc, f"Campo '{c}' falta en escenario {esc.get('nombre')}"

    def test_roi_razonable(self, business_result):
        for esc in business_result["escenarios_algoritmicos"]:
            roi = esc["roi_estimado_pct"]
            assert -10 <= roi <= 60, f"ROI fuera de rango razonable: {roi}%"

    def test_payback_dentro_vida_util(self, business_result):
        vida = PARAMS_DEFAULT["vida_util_anios"]
        for esc in business_result["escenarios_algoritmicos"]:
            assert esc["payback_anios"] <= vida, \
                f"Payback {esc['payback_anios']} > vida útil {vida}"

    def test_viability_scores_tienen_clasificacion(self, business_result):
        validas = {"Alta viabilidad", "Viabilidad media", "Descarte"}
        for v in business_result["viability_scores"]:
            assert v["clasificacion"] in validas

    def test_hay_zonas_de_cada_tipo(self, business_result):
        clases = {v["clasificacion"] for v in business_result["viability_scores"]}
        assert len(clases) >= 2, "El análisis solo produce un tipo de zona"

    def test_reporte_ejecutivo_completo(self, business_result):
        report = business_result["reporte_ejecutivo"]
        campos = ["titulo", "resumen_ejecutivo", "hallazgos_clave",
                  "top_zonas_inversion", "zonas_descarte_explicitas",
                  "escenario_recomendado", "advertencias", "proximos_pasos"]
        for c in campos:
            assert c in report, f"Campo '{c}' falta en reporte ejecutivo"

    def test_resumen_ejecutivo_contiene_datos(self, business_result):
        resumen = business_result["reporte_ejecutivo"]["resumen_ejecutivo"]
        assert len(resumen) > 100
        assert "%" in resumen  # Debe mencionar porcentaje

    def test_top_zonas_son_de_alta_viabilidad(self, business_result):
        top = business_result["reporte_ejecutivo"]["top_zonas_inversion"]
        for z in top:
            assert z["score_viabilidad"] >= 60, \
                f"Zona top con score bajo: {z['zona']} → {z['score_viabilidad']}"

    def test_zonas_descarte_son_bajas(self, business_result):
        descartes = business_result["reporte_ejecutivo"]["zonas_descarte_explicitas"]
        for z in descartes:
            assert z["score_viabilidad"] < 50, \
                f"Zona descarte con score alto: {z['zona']} → {z['score_viabilidad']}"

    def test_distintos_sectores_producen_distintos_sv(self, features):
        """El sector afecta el Score de Viabilidad final."""
        ra = RiskAgent(use_fallback_only=True)
        rs = ra.score(features)

        ba = BusinessAgent(use_fallback_only=True)

        params_tele = {**PARAMS_DEFAULT, "sector": "telecomunicaciones"}
        params_inmo = {**PARAMS_DEFAULT, "sector": "inmobiliario"}

        da_tele = DemandAgent("telecomunicaciones", use_fallback_only=True)
        da_inmo = DemandAgent("inmobiliario", use_fallback_only=True)

        ds_tele = da_tele.score(features, "telecomunicaciones")
        ds_inmo = da_inmo.score(features, "inmobiliario")

        res_tele = ba.generate_scenarios(ds_tele, rs, params_tele)
        res_inmo = ba.generate_scenarios(ds_inmo, rs, params_inmo)

        sv_tele = {v["id"]: v["score_viabilidad"] for v in res_tele["viability_scores"]}
        sv_inmo = {v["id"]: v["score_viabilidad"] for v in res_inmo["viability_scores"]}

        diffs = [abs(sv_tele[k] - sv_inmo[k]) for k in sv_tele if k in sv_inmo]
        assert max(diffs) > 0.1, "El sector no afecta los scores de viabilidad"


# ─────────────────────────────────────────────────────────────────────────────
# TEST: CONSISTENCIA CRUZADA
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossConsistency:
    def test_ids_consistentes_entre_agentes(self, demand_scores, risk_scores, business_result):
        demand_ids = {d["id"] for d in demand_scores}
        risk_ids = {r["id"] for r in risk_scores}
        biz_ids = {v["id"] for v in business_result["viability_scores"]}
        assert demand_ids == risk_ids == biz_ids, "Los IDs no son consistentes entre agentes"

    def test_alta_demanda_bajo_riesgo_implica_alta_viabilidad(
        self, demand_scores, risk_scores, business_result
    ):
        """Zona con alta demanda y bajo riesgo debe tener alta viabilidad."""
        dm = {d["id"]: d["score_demanda"] for d in demand_scores}
        rm = {r["id"]: r["score_riesgo"] for r in risk_scores}
        vm = {v["id"]: v["score_viabilidad"] for v in business_result["viability_scores"]}

        for fid in dm:
            if dm[fid] > 70 and rm.get(fid, 100) < 25:
                sv = vm.get(fid, 0)
                assert sv > 50, \
                    f"Zona {fid}: alta demanda ({dm[fid]}) + bajo riesgo ({rm[fid]}) → SV bajo ({sv})"

    def test_alto_riesgo_implica_no_alta_viabilidad(
        self, risk_scores, business_result
    ):
        """Ninguna zona con riesgo > 75 debe tener Alta viabilidad."""
        rm = {r["id"]: r["score_riesgo"] for r in risk_scores}
        vm = {v["id"]: (v["score_viabilidad"], v["clasificacion"])
              for v in business_result["viability_scores"]}

        for fid, sr in rm.items():
            if sr > 75:
                sv, cat = vm.get(fid, (0, "Descarte"))
                assert cat != "Alta viabilidad", \
                    f"Zona {fid} con riesgo {sr} tiene Alta viabilidad (SV={sv})"

    def test_conteo_50_en_todos_los_agentes(
        self, demand_scores, risk_scores, business_result
    ):
        assert len(demand_scores) == 50
        assert len(risk_scores) == 50
        assert len(business_result["viability_scores"]) == 50


# ─────────────────────────────────────────────────────────────────────────────
# TEST: PDF GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

class TestPDFGenerator:
    def test_genera_pdf_sin_crash(self, business_result, tmp_path):
        ba = BusinessAgent(use_fallback_only=True)
        pdf_dict = ba.to_pdf_ready_dict(business_result)
        vs = business_result["viability_scores"]
        pdf_dict["kpis"] = {
            "verdes":   len([v for v in vs if v["clasificacion"] == "Alta viabilidad"]),
            "cautela":  len([v for v in vs if v["clasificacion"] == "Viabilidad media"]),
            "descarte": len([v for v in vs if v["clasificacion"] == "Descarte"]),
        }
        pdf_dict["analysis_id"] = "test-abc12345"

        gen = URBANIAReportGenerator()
        out_path = str(tmp_path / "test_report.pdf")
        result = gen.generate(pdf_dict, out_path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 1000, "PDF generado está vacío o muy pequeño"

    def test_pdf_tiene_contenido_ejecutivo(self, business_result, tmp_path):
        """El PDF debe incluir resumen, hallazgos y escenario recomendado."""
        ba = BusinessAgent(use_fallback_only=True)
        pdf_dict = ba.to_pdf_ready_dict(business_result)
        vs = business_result["viability_scores"]
        pdf_dict["kpis"] = {
            "verdes": len([v for v in vs if v["clasificacion"] == "Alta viabilidad"]),
            "cautela": len([v for v in vs if v["clasificacion"] == "Viabilidad media"]),
            "descarte": len([v for v in vs if v["clasificacion"] == "Descarte"]),
        }
        pdf_dict["analysis_id"] = "test-pdf-content"

        assert pdf_dict["resumen_ejecutivo"], "Resumen ejecutivo vacío"
        assert len(pdf_dict["hallazgos_clave"]) >= 3
        assert pdf_dict["escenario_recomendado"]
        assert pdf_dict["kpis"]["verdes"] + pdf_dict["kpis"]["cautela"] + pdf_dict["kpis"]["descarte"] == 50
