# Testing Guide

This document explains how to test the AI Chief-of-Staff POC.

## Quick Test

Run the test setup script:

```bash
./test-setup.sh
```

Or manually:

```bash
# 1. Verify structure
ls -la backend/jest.config.js
ls -la backend/src/__tests__/

# 2. Install dependencies
yarn install
cd backend && yarn install && cd ..
cd frontend && yarn install && cd ..

# 3. Run unit tests
cd backend && npm test

# 4. Check TypeScript compilation
cd backend && npm run build
```

## Manual Testing Steps

### 1. Start Services

```bash
# Start Docker services
docker compose up -d

# Verify services are running
docker compose ps
```

### 2. Set Up Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env and set at minimum:
# - DEMO_SEED_TOKEN (any value)
# - OPENAI_API_KEY (your OpenAI key) OR USE_OLLAMA=true
```

### 3. Bootstrap

```bash
yarn bootstrap
```

This should:
- ✅ Start Docker services
- ✅ Install dependencies
- ✅ Seed demo data
- ✅ Print success message

### 4. Start Development Servers

```bash
yarn dev
```

This starts:
- Backend on http://localhost:3000
- Frontend on http://localhost:3001

### 5. Test API Endpoints

#### Health Check
```bash
curl http://localhost:3000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "...",
  "database": "connected",
  "vectorstore": "json"
}
```

#### Seed Demo Data
```bash
curl -X POST http://localhost:3000/api/seed/demo \
  -H "Content-Type: application/json" \
  -d '{"token": "your-seed-token"}'
```

#### List Messages
```bash
curl http://localhost:3000/api/messages
```

#### Generate Suggestion
```bash
# First, get a message ID from the list above
MESSAGE_ID="your-message-id"

curl -X POST http://localhost:3000/api/messages/$MESSAGE_ID/generate \
  -H "Content-Type: application/json" \
  -d '{"tone": "warm"}'
```

#### Test Policy Engine
```bash
# This should trigger policy escalation
curl -X POST http://localhost:3000/api/messages/$MESSAGE_ID/generate \
  -H "Content-Type: application/json" \
  -d '{"tone": "warm"}'
# Then check the response for policyCheck.action === "ESCALATE_TO_HUMAN"
```

#### View Audit Logs
```bash
curl -H "Authorization: Bearer your-admin-key" \
  http://localhost:3000/api/admin/audit?limit=10
```

#### Get Metrics
```bash
curl http://localhost:3000/api/metrics
```

### 6. Test Frontend

1. Open http://localhost:3001
2. You should see 3 demo inboxes
3. Click on a message thread
4. Click "Generate" to get AI suggestion
5. Try editing and sending
6. Test Cmd/Ctrl+K command palette

### 7. Test LLM Fallback

#### With Ollama
```bash
# In .env, set:
USE_OLLAMA=true
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama2

# Start Ollama (if installed)
ollama serve

# Generate suggestion - should use Ollama
curl -X POST http://localhost:3000/api/messages/$MESSAGE_ID/generate \
  -H "Content-Type: application/json" \
  -d '{"tone": "warm"}'
```

#### Fallback to OpenAI
```bash
# Stop Ollama or set wrong URL
# Set in .env:
USE_OLLAMA=false
OPENAI_API_KEY=sk-...

# Should automatically fall back to OpenAI
```

### 8. Test Vector Store

#### JSON Adapter (Default)
```bash
# Should automatically use JSON adapter if Chroma not available
curl http://localhost:3000/api/health
# Check vectorstore: "json"
```

#### Chroma Adapter (if available)
```bash
# Start Chroma
docker run -d -p 8000:8000 chromadb/chroma:latest

# Set in .env:
VECTORSTORE_MODE=chroma

# Restart backend, check health
curl http://localhost:3000/api/health
# Check vectorstore: "chroma"
```

## Unit Tests

```bash
cd backend
npm test
```

Tests include:
- Policy engine rules
- Vector store JSON adapter
- Prompt builder truncation

## Integration Tests

For full integration testing:

1. Start all services (Docker, backend, frontend)
2. Seed demo data
3. Test complete flow:
   - List messages
   - Generate suggestion
   - Edit suggestion
   - Send message
   - Check audit logs

## Troubleshooting Tests

### Tests fail with "Cannot find module"
```bash
cd backend
rm -rf node_modules
npm install
```

### TypeScript errors
```bash
cd backend
npm run build
# Fix any errors shown
```

### Database connection errors
```bash
# Ensure Postgres is running
docker compose ps
docker compose logs postgres
```

### Vector store errors
- Check logs for adapter selection
- JSON adapter should work without Chroma
- Verify storage directory exists: `backend/storage/`

## Expected Test Results

✅ All unit tests pass  
✅ TypeScript compiles without errors  
✅ Health endpoint returns all services connected  
✅ Demo data seeds successfully  
✅ AI suggestions generate (with API key or Ollama)  
✅ Policy engine blocks sensitive content  
✅ Audit logs are created  
✅ Frontend loads and displays messages  

