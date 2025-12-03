# Gemini API Performance Optimizations

**Date:** 2025-11-30  
**Issue:** Gemini API responses taking too long  
**Status:** ✅ Optimized

## Optimizations Applied

### 1. Async Execution with Timeout
- **Problem:** Gemini client is synchronous and blocks event loop
- **Solution:** Run Gemini calls in `ThreadPoolExecutor` with timeout
- **Timeout:** 20 seconds (configurable via `GEMINI_TIMEOUT`)

### 2. Prompt Optimization
- **Truncation:** Long prompts truncated to 6000 chars (configurable)
- **System Prompt:** Truncated to last 2000 chars if too long
- **Reduced Context:** Less context = faster processing

### 3. Response Length Limits
- **RAG Chat:** `max_tokens=200` (reduced from 250)
- **General Chat:** `max_tokens=150` (reduced from 200)
- **Intent Classification:** `max_tokens=80` (reduced from 100)
- **Calendar Parsing:** `max_tokens=120` (reduced from 150)

### 4. Temperature Optimization
- **Lower Temperature:** 0.3 for general, 0.1 for classification
- **Faster Responses:** Lower temperature = more deterministic = faster

### 5. Model Selection
- **Default Model:** `gemini-2.5-flash` (fastest Gemini model)
- **Skip Ollama:** Set `use_local=False` when Gemini is available

## Configuration

### Environment Variables

```bash
# Timeout for Gemini API calls (seconds)
GEMINI_TIMEOUT=20.0

# Maximum prompt length (characters)
GEMINI_MAX_PROMPT_LENGTH=6000

# Gemini model (default: gemini-2.5-flash - fastest)
GEMINI_MODEL=gemini-2.5-flash

# API Key
GEMINI_API_KEY=your_key_here
```

## Performance Improvements

### Before
- Synchronous blocking calls
- No timeout (could hang indefinitely)
- Long prompts (8000+ chars)
- High max_tokens (250-500)
- Ollama fallback attempted first

### After
- Async with thread pool executor
- 20-second timeout
- Truncated prompts (6000 chars max)
- Reduced max_tokens (80-200)
- Gemini tried first (fastest)

## Expected Response Times

- **Simple Greetings:** < 2 seconds (hardcoded response)
- **General Questions:** 3-8 seconds
- **Policy RAG:** 5-12 seconds
- **Action Intent:** 4-10 seconds
- **Intent Classification:** 2-5 seconds

## Troubleshooting

### Still Slow?

1. **Check Timeout:**
   ```bash
   echo $GEMINI_TIMEOUT  # Should be 20.0 or less
   ```

2. **Check Model:**
   ```bash
   echo $GEMINI_MODEL  # Should be gemini-2.5-flash (fastest)
   ```

3. **Monitor Logs:**
   ```bash
   tail -f /tmp/backend.log | grep Gemini
   ```

4. **Test Directly:**
   ```python
   from google import genai
   import time
   
   client = genai.Client(api_key="your_key")
   start = time.time()
   response = client.models.generate_content(
       model="gemini-2.5-flash",
       contents="Hello"
   )
   print(f"Time: {time.time() - start:.2f}s")
   ```

### Fallback Options

If Gemini is consistently slow:
1. Set `USE_OLLAMA=true` to use local Ollama
2. Set `OPENAI_API_KEY` to use OpenAI
3. The system will automatically fallback if Gemini times out

## Code Changes

### Files Modified
- `backend_python/app/clients/llm/gemini_adapter.py` - Added async executor + timeout
- `backend_python/app/routes/chat.py` - Optimized max_tokens and model selection
- `backend_python/app/policy/intent_classifier.py` - Reduced tokens for classification
- `backend_python/app/routes/calendar.py` - Optimized calendar parsing

### Key Implementation

```python
# Run synchronous Gemini call in thread pool with timeout
_executor = ThreadPoolExecutor(max_workers=4)

async def generate_with_gemini(options: LLMOptions):
    def _call_gemini():
        client = genai.Client(api_key=api_key)
        return client.models.generate_content(...)
    
    # Run with timeout
    response = await asyncio.wait_for(
        loop.run_in_executor(_executor, _call_gemini),
        timeout=20.0
    )
```

## References

- [Gemini API Quickstart](https://ai.google.dev/gemini-api/docs/quickstart)
- [Gemini Performance Issues Discussion](https://discuss.ai.google.dev/t/very-slow-response-time-on-the-new-2-5-pro-0605-model/87456)

