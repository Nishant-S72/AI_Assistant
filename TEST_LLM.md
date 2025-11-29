# Testing LLM Functionality

## Current Status

✅ **Enriched Data Seeded**: 8 varied message threads including:
- Bulk order inquiries
- Shipping complaints  
- Partnership requests
- Product questions
- Return requests
- Feature requests
- Support questions
- Pricing inquiries

✅ **Backend**: Running on http://localhost:3001
✅ **Frontend**: Running on http://localhost:3000

## Install Ollama (Required for LLM)

### macOS
1. Download from: https://ollama.com/download/mac
2. Or install via Homebrew: `brew install ollama`

### Start Ollama
```bash
ollama serve
```
This starts Ollama on http://localhost:11434

### Pull a Model
For fast demo (recommended):
```bash
ollama pull phi3
```

For better quality:
```bash
ollama pull llama2
# or
ollama pull mistral
```

### Verify
```bash
curl http://localhost:11434/api/tags
```

## Test LLM Generation

### Via Frontend
1. Open http://localhost:3000/inbox
2. Click on any message thread
3. Click "Generate" button in the suggestion panel
4. Watch the AI thinking animation
5. See the generated reply appear!

### Via API
```bash
# Get a message ID
MESSAGE_ID=$(curl -s http://localhost:3001/api/messages | jq -r '.[0].id')

# Generate suggestion
curl -X POST http://localhost:3001/api/messages/$MESSAGE_ID/generate \
  -H "Content-Type: application/json" \
  -d '{"tone": "warm"}'
```

## What You'll See

1. **AI Thinking Animation**: Pulsing dots while generating
2. **Generated Reply**: Context-aware response based on:
   - Conversation history
   - Contact tone preference
   - Retrieved knowledge base chunks
   - Selected tone (Formal/Warm/Crisp)

3. **Prompt & Sources**: Expandable section showing:
   - Full prompt sent to LLM
   - Retrieved document IDs from vector store

## Troubleshooting

- **"Ollama not available"**: Make sure `ollama serve` is running
- **"Model not found"**: Run `ollama pull phi3` first
- **Slow responses**: Use smaller models like `phi3` for faster demo
- **Connection refused**: Check Ollama is on port 11434

## Example Generated Responses

The LLM will generate responses like:
- **Warm tone**: Friendly, approachable, empathetic
- **Formal tone**: Professional, courteous, structured
- **Crisp tone**: Direct, action-oriented, concise

Each response is context-aware and uses RAG (Retrieval-Augmented Generation) to pull relevant information from the knowledge base.

