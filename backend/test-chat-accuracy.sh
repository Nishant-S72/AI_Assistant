#!/bin/bash

# Comprehensive Chat Bubble Accuracy Test Suite
# Tests various scenarios and evaluates response accuracy

API_BASE="http://localhost:3001/api"
SESSION_ID="accuracy_test_$(date +%s)"

echo "🧪 Chat Bubble Accuracy Test Suite"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
WARNINGS=0

# Test function with detailed evaluation
test_chat() {
    local test_name="$1"
    local question="$2"
    local expected_behavior="$3"
    local should_contain="$4"
    local should_not_contain="$5"
    local check_calendar="$6"
    
    echo -e "${BLUE}Testing: ${test_name}${NC}"
    echo "Question: \"$question\""
    echo "Expected: $expected_behavior"
    echo -n "Response: "
    
    response=$(curl -s -X POST "$API_BASE/chat" \
        -H "Content-Type: application/json" \
        -d "{\"question\": \"$question\", \"sessionId\": \"$SESSION_ID\"}")
    
    answer=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('answer', ''))" 2>/dev/null)
    has_calendar=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print('yes' if data.get('calendarEvent') else 'no')" 2>/dev/null)
    session_id=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('sessionId', ''))" 2>/dev/null)
    
    if [ -z "$answer" ]; then
        echo -e "${RED}FAILED${NC} - No answer received"
        echo "Full response: $response"
        FAILED=$((FAILED + 1))
        echo ""
        return 1
    fi
    
    # Check answer length (should be reasonable)
    answer_length=${#answer}
    if [ $answer_length -lt 10 ]; then
        echo -e "${YELLOW}WARNING${NC} - Answer too short ($answer_length chars)"
        WARNINGS=$((WARNINGS + 1))
    elif [ $answer_length -gt 500 ]; then
        echo -e "${YELLOW}WARNING${NC} - Answer too long ($answer_length chars)"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    # Check if answer contains expected content
    local contains_expected=true
    if [ -n "$should_contain" ]; then
        if ! echo "$answer" | grep -qi "$should_contain"; then
            echo -e "${YELLOW}WARNING${NC} - Answer doesn't contain expected: '$should_contain'"
            contains_expected=false
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
    
    # Check if answer should NOT contain certain content
    local contains_forbidden=false
    if [ -n "$should_not_contain" ]; then
        if echo "$answer" | grep -qi "$should_not_contain"; then
            echo -e "${RED}FAILED${NC} - Answer incorrectly contains: '$should_not_contain'"
            contains_forbidden=true
            FAILED=$((FAILED + 1))
        fi
    fi
    
    # Check calendar event creation
    if [ "$check_calendar" = "yes" ]; then
        if [ "$has_calendar" != "yes" ]; then
            echo -e "${RED}FAILED${NC} - Calendar event not created"
            FAILED=$((FAILED + 1))
        else
            event_title=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('calendarEvent', {}).get('title', ''))" 2>/dev/null)
            echo -e "${GREEN}✓${NC} Calendar event created: $event_title"
        fi
    fi
    
    # Overall evaluation
    if [ "$contains_forbidden" = "true" ]; then
        echo -e "${RED}❌ FAILED${NC}"
        FAILED=$((FAILED + 1))
    elif [ "$contains_expected" = "true" ] && [ "$check_calendar" != "yes" ] || [ "$has_calendar" = "yes" ]; then
        echo -e "${GREEN}✅ PASSED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠️  PARTIAL${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    echo "Answer preview: ${answer:0:150}..."
    echo ""
}

echo "📋 Test Suite Starting..."
echo ""

# Test 1: Simple Greeting (should be brief, no policy/escalation)
test_chat "Simple Greeting - Hi" \
    "Hi" \
    "Brief, friendly greeting without policy/escalation info" \
    "" \
    "policy|escalation|Escalation|refund|lawsuit|context|Context" \
    "no"

# Test 2: Simple Greeting - Hello
test_chat "Simple Greeting - Hello" \
    "Hello" \
    "Brief, friendly greeting without policy/escalation info" \
    "" \
    "policy|escalation|Escalation|context|Context" \
    "no"

# Test 3: Calendar Event Creation
test_chat "Calendar Event - Basic" \
    "Schedule a meeting tomorrow at 2pm" \
    "Should create calendar event and confirm" \
    "" \
    "" \
    "yes"

# Test 4: Calendar Event with Details
test_chat "Calendar Event - With Details" \
    "Add a team standup meeting every Monday at 9am" \
    "Should create recurring calendar event" \
    "" \
    "" \
    "yes"

# Test 5: Policy Question (should load policy)
test_chat "Policy Question - Refund" \
    "What is the refund policy?" \
    "Should mention policy/refund information" \
    "policy|refund|Policy|Refund" \
    "" \
    "no"

# Test 6: Policy Question - Legal
test_chat "Policy Question - Legal" \
    "What happens if someone mentions a lawsuit?" \
    "Should mention policy/escalation information" \
    "policy|escalation|lawsuit|Policy|Escalation" \
    "" \
    "no"

# Test 7: Regular Question - Tasks (should NOT load policy)
test_chat "Regular Question - Tasks" \
    "How many tasks do I have?" \
    "Should answer about tasks without policy info" \
    "" \
    "policy|escalation|Policy|Escalation" \
    "no"

# Test 8: Regular Question - Inbox (should NOT load policy)
test_chat "Regular Question - Inbox" \
    "How many unread messages do I have?" \
    "Should answer about inbox without policy info" \
    "" \
    "policy|escalation|Policy|Escalation" \
    "no"

# Test 9: Regular Question - Calendar Query (not creation)
test_chat "Calendar Question - Query" \
    "What meetings do I have today?" \
    "Should answer about calendar without creating event" \
    "" \
    "policy|escalation|Policy|Escalation" \
    "no"

# Test 10: Ambiguous Request (could be calendar or question)
test_chat "Ambiguous Request" \
    "Tell me about my meetings" \
    "Should answer about meetings, not create event" \
    "" \
    "" \
    "no"

# Test 11: Context Maintenance
echo -e "${BLUE}Testing: Context Maintenance${NC}"
echo "Question 1: \"My name is Alice\""
response1=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"My name is Alice\", \"sessionId\": \"$SESSION_ID\"}")
echo "Question 2: \"What is my name?\""
response2=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"What is my name?\", \"sessionId\": \"$SESSION_ID\", \"conversationHistory\": [{\"role\": \"user\", \"content\": \"My name is Alice\"}, {\"role\": \"assistant\", \"content\": \"Got it\"}]}")
answer2=$(echo "$response2" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('answer', ''))" 2>/dev/null)
if echo "$answer2" | grep -qi "alice"; then
    echo -e "${GREEN}✅ PASSED${NC} - Context maintained"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  PARTIAL${NC} - Context may not be fully used"
    echo "Answer: $answer2"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Test 12: Session Persistence
echo -e "${BLUE}Testing: Session Persistence${NC}"
response1=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Test message 1\", \"sessionId\": \"$SESSION_ID\"}")
session_id1=$(echo "$response1" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('sessionId', ''))" 2>/dev/null)
response2=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Test message 2\", \"sessionId\": \"$SESSION_ID\"}")
session_id2=$(echo "$response2" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('sessionId', ''))" 2>/dev/null)
if [ "$session_id1" = "$session_id2" ] && [ -n "$session_id1" ]; then
    echo -e "${GREEN}✅ PASSED${NC} - Session ID persisted: $session_id1"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ FAILED${NC} - Session IDs don't match"
    echo "Session 1: $session_id1"
    echo "Session 2: $session_id2"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 13: Response Quality - Check for verbosity
echo -e "${BLUE}Testing: Response Quality${NC}"
response=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Hi\", \"sessionId\": \"quality_test\"}")
answer=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('answer', ''))" 2>/dev/null)
answer_length=${#answer}
if [ $answer_length -lt 200 ]; then
    echo -e "${GREEN}✅ PASSED${NC} - Response is concise ($answer_length chars)"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  WARNING${NC} - Response may be too verbose ($answer_length chars)"
    WARNINGS=$((WARNINGS + 1))
fi
echo "Answer: $answer"
echo ""

# Test 14: Error Handling
echo -e "${BLUE}Testing: Error Handling${NC}"
response=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d '{"question": ""}')
error=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('error', ''))" 2>/dev/null)
if [ -n "$error" ]; then
    echo -e "${GREEN}✅ PASSED${NC} - Error handling works"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  WARNING${NC} - Empty question may not be handled"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Summary
echo "===================================="
echo "📊 Test Results Summary"
echo "===================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total Tests: $((PASSED + WARNINGS + FAILED))"
echo ""

# Calculate accuracy percentage
total=$((PASSED + WARNINGS + FAILED))
if [ $total -gt 0 ]; then
    accuracy=$((PASSED * 100 / total))
    echo "Accuracy: ${accuracy}%"
fi

echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Some warnings, but no failures${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

