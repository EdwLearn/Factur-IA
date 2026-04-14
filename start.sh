#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — Arranca FacturIA completo (infra + backend + frontend)
# Uso: ./start.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/edwlearn/miniconda3/envs/facturIA/bin/python"
API_LOG="/tmp/facturIA_api.log"
WEB_LOG="/tmp/facturIA_web.log"
API_PORT=8001
WEB_PORT=3000

# ── Colores ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; }
step() { echo -e "\n${YELLOW}▶${NC} $*"; }

# ── 1. Infraestructura Docker (postgres + redis) ──────────────────────────────
step "Levantando postgres y redis..."

cd "$ROOT"
docker compose up -d postgres redis 2>/dev/null

# Esperar postgres
for i in $(seq 1 20); do
  docker exec document_processing_db pg_isready -U postgres -q 2>/dev/null && break
  sleep 1
done
docker exec document_processing_db pg_isready -U postgres -q 2>/dev/null \
  && ok "PostgreSQL listo" \
  || { err "PostgreSQL no respondió"; exit 1; }

# Esperar redis
for i in $(seq 1 10); do
  docker exec document_processing_redis redis-cli ping 2>/dev/null | grep -q PONG && break
  sleep 1
done
docker exec document_processing_redis redis-cli ping 2>/dev/null | grep -q PONG \
  && ok "Redis listo" \
  || warn "Redis no respondió (continuando)"

# ── 2. Backend (conda facturIA) ───────────────────────────────────────────────
step "Iniciando backend (Python 3.11 — entorno facturIA)..."

# Matar instancias previas en el puerto
fuser -k ${API_PORT}/tcp 2>/dev/null || true
sleep 1

cd "$ROOT"
"$PYTHON" -m uvicorn apps.api.src.api.main:app \
  --host 0.0.0.0 --port "$API_PORT" --reload \
  > "$API_LOG" 2>&1 &
API_PID=$!

# Esperar a que responda
for i in $(seq 1 20); do
  curl -s "http://localhost:${API_PORT}/health" | grep -q '"healthy"' && break
  sleep 1
done

if curl -s "http://localhost:${API_PORT}/health" | grep -q '"healthy"'; then
  ok "Backend corriendo en http://localhost:${API_PORT}  (PID ${API_PID})"
else
  err "Backend no respondió. Últimas líneas del log:"
  tail -20 "$API_LOG"
  exit 1
fi

# ── 3. Frontend (Next.js) ─────────────────────────────────────────────────────
step "Iniciando frontend (Next.js)..."

# Matar instancias previas en el puerto
fuser -k ${WEB_PORT}/tcp 2>/dev/null || true
sleep 1

cd "$ROOT/apps/web"
pnpm dev > "$WEB_LOG" 2>&1 &
WEB_PID=$!

# Esperar a que responda
for i in $(seq 1 30); do
  curl -s -o /dev/null -w "%{http_code}" "http://localhost:${WEB_PORT}" 2>/dev/null \
    | grep -q "200\|304" && break
  sleep 1
done

if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${WEB_PORT}" 2>/dev/null \
    | grep -q "200\|304"; then
  ok "Frontend corriendo en http://localhost:${WEB_PORT}  (PID ${WEB_PID})"
else
  warn "Frontend aún iniciando (puede tardar unos segundos más)"
fi

# ── Resumen ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  FacturIA corriendo"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Frontend  →  http://localhost:${WEB_PORT}"
echo -e "  Backend   →  http://localhost:${API_PORT}"
echo -e "  API docs  →  http://localhost:${API_PORT}/docs"
echo -e ""
echo -e "  Logs:"
echo -e "    API  →  tail -f ${API_LOG}"
echo -e "    Web  →  tail -f ${WEB_LOG}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
