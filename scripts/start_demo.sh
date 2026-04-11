#!/bin/bash
# SUSVI — Script de arranque para demo hackathon
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   SUSVI — Demo Hackathon Talent Land   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Backend
echo "▶ Iniciando backend FastAPI (puerto 8000)..."
cd "$BACKEND_DIR"
if [ -d ".venv" ]; then
  source .venv/bin/activate 2>/dev/null || true
fi
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Esperar backend
sleep 3

# Frontend
echo "▶ Iniciando frontend Vite (puerto 5173)..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "═══════════════════════════════════════════"
echo "  🌐 Frontend: http://localhost:5173"
echo "  🔧 API docs: http://localhost:8000/docs"
echo "  ❤️  Health:  http://localhost:8000/api/v1/health"
echo "═══════════════════════════════════════════"
echo ""
echo "Ctrl+C para detener ambos procesos."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Detenido.'" EXIT
wait
