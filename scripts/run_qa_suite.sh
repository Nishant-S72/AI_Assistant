#!/bin/bash
# QA Test Suite Runner
# Runs all tests and generates a report

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== QA Test Suite ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "Checking services..."
BACKEND_PORT=${PORT:-3001}
if ! curl -s "http://localhost:${BACKEND_PORT}/api/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Backend not running on port ${BACKEND_PORT}${NC}"
    echo "Please start the backend first:"
    echo "  cd backend_python && uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}"
    exit 1
fi
echo -e "${GREEN}✅ Backend is running${NC}"

# Check if vectorstore is seeded
echo ""
echo "Checking vectorstore..."
VECTORSTORE_STATUS=$(curl -s "http://localhost:${BACKEND_PORT}/api/health/vectorstore" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('count_chunks', 0))" 2>/dev/null || echo "0")
if [ "$VECTORSTORE_STATUS" -eq "0" ]; then
    echo -e "${YELLOW}⚠️  Vectorstore is empty. Seeding policy documents...${NC}"
    cd backend_python
    python3 scripts/seed_policy_docs.py || echo "Warning: Seed script failed"
    cd ..
else
    echo -e "${GREEN}✅ Vectorstore has ${VECTORSTORE_STATUS} chunks${NC}"
fi

# Run tests
echo ""
echo "=== Running Tests ==="
echo ""

cd backend_python

# Run pytest if available
if command -v pytest &> /dev/null; then
    echo "Running pytest..."
    pytest tests/ -v --tb=short || echo "Some tests failed"
else
    echo "pytest not found. Install with: pip install pytest pytest-asyncio"
    echo "Skipping unit tests..."
fi

cd ..

# Run integration tests (curl-based)
echo ""
echo "=== Running Integration Tests ==="
echo ""

TEST_DIR="/tmp/qa_tests_$(date +%s)"
mkdir -p "$TEST_DIR"

# Test 1: General Intent
echo "TEST 1: General Intent..."
REQ_ID="test-general-$(date +%s)"
RESPONSE=$(curl -s -X POST "http://localhost:${BACKEND_PORT}/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: $REQ_ID" \
  -d '{"userMessage": "How do I write a short follow-up email after a meeting?", "tone": "warm"}')
echo "$RESPONSE" > "$TEST_DIR/test1.json"

INTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intent', 'N/A'))" 2>/dev/null || echo "ERROR")
if [ "$INTENT" == "general_intent" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL (got: $INTENT)${NC}"
fi

# Test 2: Policy Intent
echo "TEST 2: Policy Intent (RAG)..."
REQ_ID="test-policy-$(date +%s)"
RESPONSE=$(curl -s -X POST "http://localhost:${BACKEND_PORT}/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: $REQ_ID" \
  -d '{"userMessage": "What does our refund policy say about partial refunds?", "tone": "formal"}')
echo "$RESPONSE" > "$TEST_DIR/test2.json"

CITATIONS=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('citations', [])))" 2>/dev/null || echo "0")
INTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intent', 'N/A'))" 2>/dev/null || echo "ERROR")
if [ "$INTENT" == "policy_intent" ] && [ "$CITATIONS" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS (${CITATIONS} citations)${NC}"
elif [ "$INTENT" == "policy_intent" ]; then
    echo -e "${YELLOW}⚠️  PARTIAL (policy_intent detected but no citations - vectorstore may need seeding)${NC}"
else
    echo -e "${RED}❌ FAIL (got: $INTENT)${NC}"
fi

# Test 3: Action Intent (Complete)
echo "TEST 3: Action Intent (Complete Data)..."
REQ_ID="test-action-$(date +%s)"
RESPONSE=$(curl -s -X POST "http://localhost:${BACKEND_PORT}/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: $REQ_ID" \
  -d '{"userMessage": "Schedule a 30 minute call with Jane Doe next Thursday at 3pm Dubai time. Email: jane@example.com", "tone": "crisp"}')
echo "$RESPONSE" > "$TEST_DIR/test3.json"

INTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intent', 'N/A'))" 2>/dev/null || echo "ERROR")
SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('action_result', {}).get('success', False))" 2>/dev/null || echo "False")
if [ "$INTENT" == "action_intent" ] && [ "$SUCCESS" == "True" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
elif [ "$INTENT" == "action_intent" ]; then
    echo -e "${YELLOW}⚠️  PARTIAL (action_intent detected but event not created)${NC}"
else
    echo -e "${RED}❌ FAIL (got: $INTENT)${NC}"
fi

# Test 4: Action Intent (Missing Info)
echo "TEST 4: Action Intent (Missing Info)..."
REQ_ID="test-action-missing-$(date +%s)"
RESPONSE=$(curl -s -X POST "http://localhost:${BACKEND_PORT}/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: $REQ_ID" \
  -d '{"userMessage": "Please schedule a meeting with the client next week.", "tone": "formal"}')
echo "$RESPONSE" > "$TEST_DIR/test4.json"

INTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intent', 'N/A'))" 2>/dev/null || echo "ERROR")
CONFIRM_NEEDED=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('action_suggestion', {}).get('confirm_needed', False))" 2>/dev/null || echo "False")
if [ "$INTENT" == "action_intent" ] && [ "$CONFIRM_NEEDED" == "True" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
elif [ "$INTENT" == "action_intent" ]; then
    echo -e "${YELLOW}⚠️  PARTIAL (action_intent detected but no clarifying question)${NC}"
else
    echo -e "${RED}❌ FAIL (got: $INTENT)${NC}"
fi

# Test 5: Policy Escalation
echo "TEST 5: Policy Escalation..."
REQ_ID="test-escalate-$(date +%s)"
RESPONSE=$(curl -s -X POST "http://localhost:${BACKEND_PORT}/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: $REQ_ID" \
  -d '{"userMessage": "We need to fire an employee for misconduct. Do we follow the standard termination clause?", "tone": "formal"}')
echo "$RESPONSE" > "$TEST_DIR/test5.json"

ESCALATED=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('escalated', False))" 2>/dev/null || echo "False")
if [ "$ESCALATED" == "True" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL (escalated: $ESCALATED)${NC}"
fi

# Test 6: Low Confidence
echo "TEST 6: Low Confidence Fallback..."
REQ_ID="test-lowconf-$(date +%s)"
RESPONSE=$(curl -s -X POST "http://localhost:${BACKEND_PORT}/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: $REQ_ID" \
  -d '{"userMessage": "What is our stance on refunds for third-party providers?", "tone": "warm"}')
echo "$RESPONSE" > "$TEST_DIR/test6.json"

CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intent_confidence', 1.0))" 2>/dev/null || echo "1.0")
if (( $(echo "$CONFIDENCE < 1.0" | bc -l) )); then
    echo -e "${GREEN}✅ PASS (confidence: $CONFIDENCE)${NC}"
else
    echo -e "${YELLOW}⚠️  Confidence is $CONFIDENCE (expected < 1.0 for ambiguous queries)${NC}"
fi

echo ""
echo "=== Test Results Summary ==="
echo "Test responses saved to: $TEST_DIR"
echo ""
echo "To view detailed results:"
echo "  cat $TEST_DIR/test*.json | python3 -m json.tool"
echo ""
echo "✅ QA Suite Complete!"

