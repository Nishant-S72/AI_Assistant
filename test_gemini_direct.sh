#!/bin/bash

# Direct Gemini API Test Script
# This tests the Gemini API directly without going through our backend

API_KEY="AlzaSyB7RYZeZXKE2Qrh8Q_F2HzKqGmlpNoq0SQ"
MODEL="gemini-2.5-flash"

echo "=== Testing Gemini API Directly ==="
echo "Model: $MODEL"
echo "API Key: ${API_KEY:0:10}..."
echo ""

# Test 1: Simple greeting (fastest)
echo "📝 Test 1: Simple greeting"
echo "---"
time curl -X POST \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}" \
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
  -w "\n\n⏱️  Total Time: %{time_total}s\n📊 HTTP Status: %{http_code}\n" \
  2>&1 | python3 -m json.tool 2>/dev/null | head -30 || echo "❌ Failed to parse JSON"

echo ""
echo "=========================================="
echo ""

# Test 2: Longer question
echo "📝 Test 2: Longer question"
echo "---"
time curl -X POST \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}" \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "What is the capital of France? Answer in one sentence."
          }
        ]
      }
    ],
    "generationConfig": {
      "maxOutputTokens": 100,
      "temperature": 0.3
    }
  }' \
  --max-time 30 \
  -w "\n\n⏱️  Total Time: %{time_total}s\n📊 HTTP Status: %{http_code}\n" \
  2>&1 | python3 -m json.tool 2>/dev/null | head -30 || echo "❌ Failed to parse JSON"

echo ""
echo "=========================================="
echo ""

# Test 3: Chat-like question (similar to our app)
echo "📝 Test 3: Chat-like question"
echo "---"
time curl -X POST \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}" \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "You are a helpful assistant. User: How do I write a short follow-up email after a meeting? Assistant:"
          }
        ]
      }
    ],
    "generationConfig": {
      "maxOutputTokens": 150,
      "temperature": 0.3
    }
  }' \
  --max-time 30 \
  -w "\n\n⏱️  Total Time: %{time_total}s\n📊 HTTP Status: %{http_code}\n" \
  2>&1 | python3 -m json.tool 2>/dev/null | head -30 || echo "❌ Failed to parse JSON"

echo ""
echo "✅ Testing complete!"
echo ""
echo "💡 Tips:"
echo "   - If response time > 10s: API may be slow"
echo "   - If response time < 5s: Good performance"
echo "   - If HTTP 429: Rate limit exceeded"
echo "   - If HTTP 401: Invalid API key"

