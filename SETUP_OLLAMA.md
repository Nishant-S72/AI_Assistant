# Setting Up Ollama for Local LLM

## Install Ollama

### macOS
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Or download from: https://ollama.com/download

### Start Ollama
```bash
ollama serve
```

This will start Ollama on http://localhost:11434

## Pull a Model

For fast responses (recommended for demo):
```bash
ollama pull phi3
```

For better quality:
```bash
ollama pull llama2
# or
ollama pull mistral
```

## Verify Installation

```bash
# Check if running
curl http://localhost:11434/api/tags

# Test a simple query
ollama run phi3 "Hello, how are you?"
```

## Configure Backend

The backend is already configured to use Ollama when:
- `USE_OLLAMA=true` in `.env`
- `LLM_BASE_URL=http://localhost:11434`
- `LLM_MODEL=phi3` (or your chosen model)

## Test LLM Generation

Once Ollama is running, test the API:
```bash
# Generate a suggestion for a message
curl -X POST http://localhost:3001/api/messages/{message_id}/generate \
  -H "Content-Type: application/json" \
  -d '{"tone": "warm"}'
```

## Troubleshooting

- **Port conflict**: Ollama uses port 11434 by default
- **Model not found**: Run `ollama pull <model_name>` first
- **Slow responses**: Use smaller models like `phi3` for faster demo

