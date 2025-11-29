# AI Chief-of-Staff Backend (Python)

Python backend for the AI Chief-of-Staff application, converted from TypeScript.

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Ollama (optional, for local LLM)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or using poetry (if preferred)
poetry install
```

### Environment Variables

Create a `.env` file:

```env
# Database
DATABASE_URL=postgres://postgres:postgres@localhost:5432/aichief

# LLM Configuration
USE_OLLAMA=true
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=tinyllama
OPENAI_API_KEY=your_openai_key_here

# Server
PORT=3001

# Optional
USE_DUMMY_INBOX=true
REDIS_URL=redis://localhost:6379
```

### Database Setup

The database schema and migrations are the same as the TypeScript version. SQL files are located in:
- `backend/db/migrations/` - Migration files
- `backend/src/db/schema.sql` - Main schema

Run migrations automatically on startup, or manually:

```bash
psql -d aichief -f backend/src/db/schema.sql
```

### Running the Server

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001

# Production
uvicorn app.main:app --host 0.0.0.0 --port 3001 --workers 4
```

## API Endpoints

All endpoints match the TypeScript version:

- `GET /api/messages` - List messages
- `GET /api/messages/{id}` - Get thread
- `POST /api/messages/{id}/generate` - Generate AI suggestion
- `GET /api/contacts` - List contacts
- `GET /api/contacts/{id}` - Get contact details
- `GET /api/contacts/{id}/summary` - Get contact summary
- `GET /api/summary` - Get inbox summary
- `GET /api/calendar/events` - List calendar events
- `POST /api/calendar/parse` - Parse and create event from natural language
- `POST /api/chat` - Chat assistant
- `GET /api/health` - Health check

## Project Structure

```
backend_python/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── db/
│   │   ├── __init__.py
│   │   └── connection.py   # Database connection pool
│   ├── clients/
│   │   └── llm/             # LLM adapters (Ollama, OpenAI, fallback)
│   ├── routes/              # API routes
│   ├── services/            # Business logic services
│   ├── agents/              # Agentic AI systems
│   ├── policy/              # Policy engine
│   ├── utils/               # Utility functions
│   └── scripts/             # Database seeding scripts
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Key Differences from TypeScript Version

1. **Async/Await**: Uses Python's `async/await` with `asyncpg` for database operations
2. **Type Hints**: Uses Python type hints instead of TypeScript types
3. **FastAPI**: Uses FastAPI instead of Express.js
4. **Pydantic**: Uses Pydantic models for request/response validation
5. **Database**: Uses `asyncpg` instead of `pg` (node-postgres)

## Development

### Code Style

- Black for formatting
- isort for import sorting
- mypy for type checking

```bash
# Format code
black app/

# Sort imports
isort app/

# Type check
mypy app/
```

## Testing

```bash
# Run tests (when implemented)
pytest
```

## Migration from TypeScript

See `CONVERSION_STATUS.md` for detailed conversion status and remaining work.

