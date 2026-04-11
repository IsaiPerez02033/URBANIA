# SUSVI — Plataforma de Inteligencia Territorial

> **SaaS B2B** · Motor de análisis territorial con IBM Watsonx AI · Talent Land 2026

**XOLUM** — Equipo: Pérez Flores Isai Aram · Rueda Manzano Jennifer · Canales Zendreros Diego Damián · Soriano Rosales Irvin Jair

---

## Arranque rápido

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload        # → http://localhost:8000/docs

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                      # → http://localhost:5173
```

---

## Estructura

```
susvi/
├── backend/
│   ├── main.py                 ← FastAPI · 8 endpoints REST
│   ├── agents/
│   │   ├── demand_agent.py     ← Score Demanda (DENUE, VIIRS, GTFS)
│   │   ├── risk_agent.py       ← Score Riesgo (SNSP, iluminación)
│   │   └── business_agent.py   ← Score Viabilidad · 3 escenarios · ROI
│   ├── data/
│   │   ├── ingest.py           ← ETL · normalización GeoJSON
│   │   └── mock_fixture.json   ← 50 manzanas reales CDMX
│   ├── utils/
│   │   ├── pdf_generator.py    ← ReportLab · PDF ejecutivo
│   │   └── watsonx_client.py   ← IBM Watsonx AI (prod + stub)
│   └── tests/
│       └── test_agents.py      ← 53 tests · 100% passing
├── frontend/src/
│   ├── App.jsx                 ← Layout 3 columnas
│   ├── components/Map/         ← Leaflet · 3 capas · popups IA
│   ├── components/Dashboard/   ← KPIs · Escenarios · Exportación
│   ├── components/Scores/      ← Recharts ranking zonas
│   ├── services/api.js         ← HTTP + descarga PDF blob
│   └── store/useStore.js       ← Zustand global state
└── scripts/start_demo.sh       ← Arranca todo junto
```

---

## Fórmula Score de Viabilidad

```
SV = SD × (1 - SR/100) × FP / TI_norm
```

SD = Score Demanda · SR = Score Riesgo · FP = factor sectorial · TI = ticket normalizado

---

## Activar Watsonx en Producción

```env
# backend/.env
SUSVI_PROD_MODE=1
WATSONX_API_KEY=tu_api_key
WATSONX_PROJECT_ID=tu_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

---

## Tests

```bash
cd backend && pytest tests/ -v
# 53 passed in ~0.5s
```

---

*SUSVI © 2026 · XOLUM · Talent Land — Track Ciudades Resilientes*
