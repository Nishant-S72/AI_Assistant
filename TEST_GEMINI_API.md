# Direct Gemini API Test Commands

## Quick Test (Single Line)

Replace `YOUR_API_KEY` with your valid Gemini API key:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_API_KEY" \
  -d '{"contents":[{"parts":[{"text":"Say hello in one word only"}]}],"generationConfig":{"maxOutputTokens":50,"temperature":0.3}}' \
  --max-time 30 | python3 -m json.tool
```

## Detailed Test with Timing

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_API_KEY" \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Say hello in one word only"
          }
        ]
      }
    ],
    "generationConfig": {
      "maxOutputTokens": 50,
      "temperature": 0.3
    }
  }' \
  --max-time 30 \
  -w "\n\n⏱️  Response Time: %{time_total}s\n📊 HTTP Status: %{http_code}\n" \
  | python3 -m json.tool
```

## Test with Environment Variable

```bash
# Set your API key
export GEMINI_API_KEY="YOUR_API_KEY"

# Run test
curl -X POST \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}" \
  -d '{"contents":[{"parts":[{"text":"What is 2+2? Answer in one word."}]}],"generationConfig":{"maxOutputTokens":50,"temperature":0.3}}' \
  --max-time 30 | python3 -m json.tool
```

## Expected Response Format

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "Hello"
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0,
      "safetyRatings": [...]
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 8,
    "candidatesTokenCount": 2,
    "totalTokenCount": 10
  }
}
```

## Response Time Benchmarks

- **< 1 second**: Excellent
- **1-3 seconds**: Good
- **3-5 seconds**: Acceptable
- **5-10 seconds**: Slow
- **> 10 seconds**: Very slow (consider timeout)

## Common Errors

### 400 - Invalid API Key
```json
{
  "error": {
    "code": 400,
    "message": "API key not valid. Please pass a valid API key.",
    "status": "INVALID_ARGUMENT"
  }
}
```
**Solution**: Get a valid API key from [Google AI Studio](https://aistudio.google.com)

### 429 - Rate Limit Exceeded
```json
{
  "error": {
    "code": 429,
    "message": "Resource has been exhausted (e.g. check quota).",
    "status": "RESOURCE_EXHAUSTED"
  }
}
```
**Solution**: Wait and retry, or upgrade your quota

### 503 - Service Unavailable
```json
{
  "error": {
    "code": 503,
    "message": "The service is currently unavailable.",
    "status": "UNAVAILABLE"
  }
}
```
**Solution**: Retry after a few seconds

## Get Your API Key

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Click "Get API Key"
3. Create a new API key or use an existing one
4. Copy the key and use it in the curl commands above

## Test Script

Use the provided `test_gemini_direct.sh` script:

```bash
# Edit the script to add your API key
nano test_gemini_direct.sh

# Run the test
./test_gemini_direct.sh
```

