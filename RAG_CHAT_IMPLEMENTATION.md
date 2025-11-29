# RAG Chat Bubble Implementation

## Overview

This document describes the Retrieval-Augmented Generation (RAG) Chat Bubble feature implementation for the AI Chief-of-Staff application.

## Features Implemented

### 1. RAG-Enabled Chat Endpoint
- **Endpoint**: `POST /api/chat/rag`
- **Location**: `backend_python/app/routes/chat.py`
- **Features**:
  - Policy document retrieval via vector store (Chroma or JSON fallback)
  - Tone selection (formal/warm/crisp)
  - RAG toggle (enable/disable policy retrieval)
  - Policy safety checks (escalation for sensitive content)
  - Prompt template-based generation
  - Gzipped prompt storage for audit
  - Citations with chunk IDs and scores

### 2. Vector Store Adapters
- **Chroma Adapter**: `backend_python/app/clients/vectorstore/chroma_adapter.py`
- **JSON Adapter**: `backend_python/app/clients/vectorstore/json_adapter.py`
- **Main Interface**: `backend_python/app/clients/vectorstore/__init__.py`
- **Features**:
  - Auto-detection of Chroma availability
  - Automatic fallback to JSON storage
  - Embedding generation via Ollama/OpenAI/simple hash-based

### 3. Enhanced Frontend Chat Bubble
- **Location**: `frontend/components/FloatingChatbox.tsx`
- **Features**:
  - Tone selector dropdown (Formal/Warm/Crisp)
  - RAG toggle checkbox
  - Citation display with "Show sources" expandable sections
  - Escalation banner (red warning when content requires human review)
  - Multi-line input support (Shift+Enter for newline)
  - Automatic feedback submission

### 4. Policy Safety Engine
- **Location**: `backend_python/app/policy/policy_engine.py`
- **Enhanced Keywords**:
  - Legal: lawsuit, litigation, court, legal action
  - HR: termination, dismissal, layoff
  - PII: SSN, passport, visa, credit card
  - Medical: diagnosis, health condition, disability
  - Criminal: felony, arrest, conviction
  - Legal services: contract drafting, legal opinion

### 5. Calendar Events Enhancement
- **Endpoint**: `POST /api/calendar/events`
- **Features**:
  - Google Calendar OAuth support (if `GOOGLE_OAUTH_TOKEN` configured)
  - Simulated event storage in JSON file
  - Database storage in `calendar_events` table
  - Source tracking (google/simulated)
  - Audit logging

### 6. Feedback Endpoint
- **Endpoint**: `POST /api/chat/feedback`
- **Features**:
  - Accept/reject suggestions
  - Edit tracking
  - Audit logging

### 7. Policy Document Chunks Endpoint
- **Endpoint**: `GET /api/policydoc/chunks`
- **Features**:
  - Returns available policy chunks metadata
  - Shows chunk IDs, titles, summaries, scores

## File Structure

```
backend_python/
├── app/
│   ├── clients/
│   │   └── vectorstore/
│   │       ├── __init__.py          # Vector store interface
│   │       ├── chroma_adapter.py    # Chroma integration
│   │       └── json_adapter.py      # JSON fallback
│   ├── routes/
│   │   ├── chat.py                  # RAG chat endpoint
│   │   ├── calendar.py              # Enhanced calendar events
│   │   └── policydoc.py             # Policy chunks endpoint
│   ├── services/
│   │   └── embeddings.py            # Embedding generation
│   └── policy/
│       └── policy_engine.py         # Enhanced safety checks

frontend/
├── components/
│   └── FloatingChatbox.tsx          # Enhanced RAG chat UI
└── lib/
    └── api.ts                       # RAG API functions

prompts/
└── policy_chat_template.md         # Prompt template

backend/db/migrations/
└── 20251129_add_events_source.sql   # Calendar events source tracking
```

## Environment Variables

```bash
# LLM Configuration
USE_OLLAMA=true
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=tinyllama
OPENAI_API_KEY=your_key_here

# Vector Store
VECTORSTORE_MODE=auto  # 'auto', 'chroma', or 'json'
CHROMA_BASE_URL=http://localhost:8000
CHROMA_COLLECTION=policy_documents

# Google Calendar (optional)
GOOGLE_OAUTH_TOKEN=your_token_here
```

## Usage

1. **Start the backend**:
   ```bash
   cd backend_python
   source venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 3001
   ```

2. **Start the frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Use the chat bubble**:
   - Click the floating chat button (bottom-right)
   - Toggle "RAG: Policy" to enable/disable policy retrieval
   - Select tone (Formal/Warm/Crisp)
   - Ask questions about policies
   - View citations by clicking "Show sources"

## API Examples

### RAG Chat Request
```bash
curl -X POST http://localhost:3001/api/chat/rag \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "What is our refund policy?",
    "tone": "warm",
    "rag": true
  }'
```

### Send Feedback
```bash
curl -X POST http://localhost:3001/api/chat/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "suggestionId": "uuid-here",
    "accepted": true
  }'
```

### Create Calendar Event
```bash
curl -X POST http://localhost:3001/api/calendar/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Meeting",
    "start": "2025-12-01T14:00:00Z",
    "end": "2025-12-01T15:00:00Z",
    "attendees": ["user@example.com"]
  }'
```

## Database Migrations

Run the migration to add source tracking to calendar events:
```bash
psql -d aichief -f backend/db/migrations/20251129_add_events_source.sql
```

## Notes

- Vector store automatically falls back to JSON if Chroma is unavailable
- Policy documents should be indexed in the vector store for RAG to work
- Escalation disables agentic actions until manually cleared
- All interactions are logged to the `events` and `suggestions` tables
- Prompts are stored gzipped in `backend/storage/prompts/` for audit

