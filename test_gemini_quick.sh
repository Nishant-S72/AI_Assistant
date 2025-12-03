#!/bin/bash

# Quick Gemini API Test with the configured API key
API_KEY="AIzaSyB7RYZeZXKE2Qrh8Q_F2HzKqGmIpNoq0SQ"
MODEL="gemini-2.5-flash"

echo "=== Testing Gemini API Directly ==="
echo "Model: $MODEL"
echo "API Key: ${API_KEY:0:15}..."
echo ""

# Test 1: Simple greeting
echo "📝 Test 1: Simple greeting"
echo "---"
RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}" \
  -d '{"contents":[{"parts":[{"text":"Say hello in one word only"}]}],"generationConfig":{"maxOutputTokens":50,"temperature":0.3}}' \
  --max-time 30)

TIME=$(echo "$RESPONSE" | grep -o '"totalTokenCount":[0-9]*' | cut -d: -f2 || echo "N/A")
TEXT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'N/A'))" 2>/dev/null || echo "N/A")

echo "Response: $TEXT"
echo "Tokens: $TIME"
echo ""

# Test 2: With timing
echo "📝 Test 2: With timing"
echo "---"
time curl -s -X POST \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}" \
  -d '{"contents":[{"parts":[{"text":"What is 2+2? Answer in one word."}]}],"generationConfig":{"maxOutputTokens":50,"temperature":0.3}}' \
  --max-time 30 | python3 -c "import sys, json; d=json.load(sys.stdin); print('Response:', d.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'N/A')); print('Total Tokens:', d.get('usageMetadata', {}).get('totalTokenCount', 'N/A'))" 2>&1

echo ""
echo "✅ Testing complete!"
