# Starting the Python Backend

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/aichief
export USE_OLLAMA=true
export LLM_MODEL=tinyllama
export PORT=3001

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
```

## API Endpoints

All endpoints are available at `http://localhost:3001/api/`:

- `GET /api/messages` - List messages
- `GET /api/messages/{id}` - Get thread
- `POST /api/messages/{id}/generate` - Generate AI suggestion
- `GET /api/contacts` - List contacts
- `GET /api/contacts/{id}` - Get contact details
- `GET /api/contacts/{id}/summary` - Get contact summary
- `GET /api/summary` - Get inbox summary
- `GET /api/calendar/events` - List calendar events
- `POST /api/calendar/parse` - Parse and create event
- `POST /api/chat` - Chat assistant
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `GET /api/health` - Health check

## Testing

```bash
# Test health endpoint
curl http://localhost:3001/api/health

# Test chat
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'

# Test calendar parse
curl -X POST http://localhost:3001/api/calendar/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting tomorrow at 2pm"}'
```

## Notes

- The Python backend uses the same database schema as the TypeScript version
- All SQL migrations are compatible
- The frontend can connect to this backend without changes (same API structure)
- LLM configuration is the same (USE_OLLAMA, LLM_MODEL, etc.)

