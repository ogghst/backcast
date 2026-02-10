#!/bin/bash
set -e

echo "🚀 Starting Backcast EVS Development Environment"
echo "================================================"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# 1. Start dev containers
echo "📦 Starting dev containers (postgres, etc.)..."
docker compose up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker compose exec -T postgres pg_isready -U backcast -d backcast_evs >/dev/null 2>&1; do
    sleep 1
done
echo "✅ PostgreSQL is ready"

# 2. Run database migrations
echo "🔄 Running database migrations..."
cd backend
uv run alembic upgrade head

# 3. Reseed database
echo "🌱 Reseeding database..."
echo "y" | uv run python scripts/reseed_db.py

# 4. Start backend
echo "🔧 Starting backend server..."
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8020 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID) - http://localhost:8020"

# Wait a moment for backend to initialize
sleep 2

# 5. Start frontend
echo "🎨 Starting frontend server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID) - http://localhost:5173"

# Go back to root
cd ..

echo ""
echo "================================================"
echo "✨ Development environment is ready!"
echo ""
echo "📍 Services:"
echo "  - Backend:  http://localhost:8020"
echo "  - Frontend: http://localhost:5173"
echo "  - API Docs: http://localhost:8020/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo "================================================"

# Wait for any background process to exit
wait
