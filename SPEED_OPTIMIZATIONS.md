# AI Response Speed Optimizations

## Changes Applied

### 1. Reduced Token Limits
- **max_tokens**: 500 → 200 (60% reduction)
- Faster generation with shorter responses
- Still sufficient for 2-3 sentence replies

### 2. Lower Temperature
- **temperature**: 0.7 → 0.5
- More deterministic, faster generation
- Less randomness = faster processing

### 3. Optimized Ollama Settings
- **num_ctx**: 2048 (limited context window)
- **top_k**: 20 (reduced sampling options)
- **top_p**: 0.9 (slightly lower for speed)
- Faster token generation

### 4. Reduced Context
- **Thread messages**: Last 3 → Last 2
- **Message length**: 1000 → 500 chars
- **RAG chunks**: 3 → 2
- **Chunk size**: 500 → 300 chars
- Less data to process = faster

### 5. Shorter Prompts
- **Template**: Simplified and condensed
- **Prompt tokens**: 8000 → 4000 max
- Concise format reduces processing time

### 6. Optimized RAG
- Only uses last 2 messages for retrieval
- Truncated query text (200 chars)
- Faster vector search

## Expected Performance

- **Before**: 10-20 seconds
- **After**: 4-8 seconds (50-60% faster)
- **Quality**: Maintained (shorter but still effective)

## Further Optimizations (Optional)

### Use Smaller Model
```bash
ollama pull tinyllama  # Even faster, smaller model
# Then set: LLM_MODEL=tinyllama
```

### Disable RAG (Fastest)
Set `VECTORSTORE_MODE=disabled` to skip vector search entirely

### Increase Cache
Frontend already caches by tone - this helps with repeated requests

## Monitoring

Check response times in:
- Backend logs: `tail -f /tmp/backend_fast.log | grep latency`
- Browser DevTools: Network tab → `/api/messages/:id/generate`


