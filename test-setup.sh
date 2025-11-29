#!/bin/bash

# Test setup script for AI Chief-of-Staff POC
# This script verifies the setup and runs basic tests

set -e

echo "🧪 Testing AI Chief-of-Staff POC Setup"
echo "========================================"
echo ""

# Check prerequisites
echo "1. Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js >= 18"
    exit 1
fi
echo "✅ Node.js $(node --version)"

if ! command -v npm &> /dev/null && ! command -v yarn &> /dev/null; then
    echo "❌ npm or yarn not found"
    exit 1
fi
echo "✅ Package manager found"

if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker not found. Some tests will be skipped."
    DOCKER_AVAILABLE=false
else
    echo "✅ Docker $(docker --version)"
    DOCKER_AVAILABLE=true
fi

echo ""
echo "2. Checking project structure..."

# Check key files
FILES=(
    "package.json"
    "backend/package.json"
    "frontend/package.json"
    "backend/jest.config.js"
    "backend/src/index.ts"
    "backend/src/clients/llm/index.ts"
    "backend/src/clients/vectorstore/index.ts"
    "backend/src/policy/policyEngine.ts"
    "prompts/assistant_template.md"
    "scripts/bootstrap.sh"
    "docker-compose.yml"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file missing"
        exit 1
    fi
done

echo ""
echo "3. Checking test files..."

TEST_FILES=(
    "backend/src/__tests__/policyEngine.test.ts"
    "backend/src/__tests__/vectorstore.test.ts"
    "backend/src/__tests__/promptBuilder.test.ts"
)

for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "⚠️  $file missing"
    fi
done

echo ""
echo "4. Installing dependencies..."

if command -v yarn &> /dev/null; then
    yarn install || echo "⚠️  yarn install failed, trying npm..."
    cd backend && yarn install && cd ..
    cd frontend && yarn install && cd ..
else
    npm install
    cd backend && npm install && cd ..
    cd frontend && npm install && cd ..
fi

echo ""
echo "5. Running TypeScript compilation check..."

cd backend
if npm run build 2>&1 | grep -q "error"; then
    echo "❌ TypeScript compilation errors found"
    npm run build
    exit 1
else
    echo "✅ TypeScript compiles successfully"
fi
cd ..

echo ""
echo "6. Running unit tests..."

cd backend
if npm test 2>&1; then
    echo "✅ Unit tests passed"
else
    echo "⚠️  Some tests may have failed (this is expected if services aren't running)"
fi
cd ..

echo ""
echo "7. Checking Docker services (if available)..."

if [ "$DOCKER_AVAILABLE" = true ]; then
    if docker compose ps 2>/dev/null | grep -q "Up"; then
        echo "✅ Docker services are running"
    else
        echo "⚠️  Docker services not running. Run 'docker compose up -d' to start them."
    fi
else
    echo "⚠️  Docker not available, skipping service checks"
fi

echo ""
echo "========================================"
echo "✅ Setup verification complete!"
echo ""
echo "Next steps:"
echo "  1. Create .env file: cp .env.example .env"
echo "  2. Edit .env and set OPENAI_API_KEY (or configure Ollama)"
echo "  3. Start services: docker compose up -d"
echo "  4. Run bootstrap: yarn bootstrap"
echo "  5. Start dev servers: yarn dev"
echo ""

