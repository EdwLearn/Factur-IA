docker-compose up -d postgres redis
cd apps/api && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 &
cd apps/web && npm run dev &
wait