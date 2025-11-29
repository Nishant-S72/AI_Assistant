#!/bin/bash

set -e

echo "🧠 Starting local AI Chief-of-Staff demo..."
echo "=========================================="
echo ""

# Check if .env exists, create from example if not
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env created"
    else
        echo "⚠️  .env.example not found, creating default .env..."
        cat > .env << EOF
USE_OLLAMA=true
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=phi3
DUMMY_INBOX_PATH=./demo-inbox
USE_DUMMY_INBOX=true
DATABASE_URL=postgres://postgres:postgres@localhost:5432/aichief
REDIS_URL=redis://localhost:6379
PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:3000
DEMO_SEED_TOKEN=dev-seed-token-12345
EOF
        echo "✅ Default .env created"
    fi
else
    echo "✅ .env already exists"
fi

# Check if Ollama is running
echo ""
echo "🔍 Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama is not running. Please start it with:"
    echo "   ollama serve"
    echo ""
    echo "   Or install Ollama:"
    echo "   curl -fsSL https://ollama.com/install.sh | sh"
    echo "   ollama pull phi3"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start Docker services
echo ""
echo "🐳 Starting Docker services..."
docker compose up -d

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check Postgres
until docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "⏳ Waiting for Postgres..."
    sleep 2
done
echo "✅ Postgres is ready"

# Load dummy inbox
echo ""
echo "📂 Loading dummy inbox..."
export PATH="/opt/homebrew/bin:$PATH"
cd backend
if command -v tsx > /dev/null; then
    tsx src/utils/loadDummyInbox.ts || echo "⚠️  Could not load dummy inbox (may already be loaded)"
else
    npm run build
    node dist/utils/loadDummyInbox.js || echo "⚠️  Could not load dummy inbox (may already be loaded)"
fi
cd ..

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Starting development servers..."
echo ""

# Start dev servers
yarn dev

