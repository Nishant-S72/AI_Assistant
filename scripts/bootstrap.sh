#!/bin/bash

set -e

echo "🚀 Bootstrapping AI Chief-of-Staff POC..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is installed and running"

# Check .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set at least DEMO_SEED_TOKEN and OPENAI_API_KEY (or configure Ollama)"
else
    echo "✅ .env file exists"
fi

# Start Docker services
echo "🐳 Starting Docker services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check Postgres
until docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "⏳ Waiting for Postgres..."
    sleep 2
done
echo "✅ Postgres is ready"

# Check Redis
until docker compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo "⏳ Waiting for Redis..."
    sleep 2
done
echo "✅ Redis is ready"

# Install dependencies
echo "📦 Installing dependencies..."
if [ -f yarn.lock ]; then
    yarn install
    cd backend && yarn install && cd ..
    cd frontend && yarn install && cd ..
else
    npm install
    cd backend && npm install && cd ..
    cd frontend && npm install && cd ..
fi

echo "✅ Dependencies installed"

# Run seed if token is set
if [ -f .env ] && grep -q "DEMO_SEED_TOKEN=" .env && ! grep -q "DEMO_SEED_TOKEN=$" .env && ! grep -q "DEMO_SEED_TOKEN=REPLACE_ME" .env; then
    echo "🌱 Seeding demo data..."
    cd backend
    npm run seed
    cd ..
    echo "✅ Demo data seeded"
else
    echo "⚠️  Skipping seed (DEMO_SEED_TOKEN not set or is placeholder)"
fi

echo ""
echo "🎉 Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and set OPENAI_API_KEY (or configure Ollama with USE_OLLAMA=true)"
echo "  2. Run 'yarn dev' to start the development servers"
echo "  3. Open http://localhost:3001 in your browser"
echo ""
echo "Health check: http://localhost:3000/api/health"

