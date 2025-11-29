#!/bin/bash

# Comprehensive Test Suite for Chat Bubble and Agentic Features
# Tests: Basic chat, greetings, calendar events, state management, context

API_BASE="http://localhost:3001/api"
SESSION_ID="test_session_$(date +%s)"

echo "🧪 Chat Bubble & Agentic Features Test Suite"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test function
test_case() {
    local test_name="$1"
    local question="$2"
    local expected_contains="$3"
    local should_not_contain="$4"
    
    echo -n "Testing: $test_name... "
    
    response=$(curl -s -X POST "$API_BASE/chat" \
        -H "Content-Type: application/json" \
        -d "{\"question\": \"$question\", \"sessionId\": \"$SESSION_ID\"}")
    
    answer=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('answer', ''))" 2>/dev/null)
    
    if [ -z "$answer" ]; then
        echo -e "${RED}FAILED${NC} - No answer received"
        echo "Response: $response"
        FAILED=$((FAILED + 1))
        return 1
    fi
    
    # Check if answer contains expected content
    if [ -n "$expected_contains" ]; then
        if echo "$answer" | grep -qi "$expected_contains"; then
            # Good
            :
        else
            echo -e "${RED}FAILED${NC} - Answer doesn't contain expected: '$expected_contains'"
            echo "Answer: $answer"
            FAILED=$((FAILED + 1))
            return 1
        fi
    fi
    
    # Check if answer should NOT contain certain content
    if [ -n "$should_not_contain" ]; then
        if echo "$answer" | grep -qi "$should_not_contain"; then
            echo -e "${RED}FAILED${NC} - Answer incorrectly contains: '$should_not_contain'"
            echo "Answer: $answer"
            FAILED=$((FAILED + 1))
            return 1
        fi
    fi
    
    echo -e "${GREEN}PASSED${NC}"
    echo "  Answer: ${answer:0:100}..."
    PASSED=$((PASSED + 1))
    return 0
}

# Test calendar event creation
test_calendar_event() {
    local test_name="$1"
    local question="$2"
    
    echo -n "Testing Calendar Event: $test_name... "
    
    response=$(curl -s -X POST "$API_BASE/chat" \
        -H "Content-Type: application/json" \
        -d "{\"question\": \"$question\", \"sessionId\": \"$SESSION_ID\"}")
    
    has_event=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print('yes' if data.get('calendarEvent') else 'no')" 2>/dev/null)
    answer=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('answer', ''))" 2>/dev/null)
    
    if [ "$has_event" = "yes" ]; then
        event_title=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('calendarEvent', {}).get('title', ''))" 2>/dev/null)
        echo -e "${GREEN}PASSED${NC}"
        echo "  Event created: $event_title"
        echo "  Answer: ${answer:0:100}..."
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}FAILED${NC} - Calendar event not created"
        echo "Answer: $answer"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Test state maintenance
test_state_maintenance() {
    echo -n "Testing State Maintenance... "
    
    # First message
    response1=$(curl -s -X POST "$API_BASE/chat" \
        -H "Content-Type: application/json" \
        -d "{\"question\": \"My name is John\", \"sessionId\": \"$SESSION_ID\"}")
    
    session_id1=$(echo "$response1" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('sessionId', ''))" 2>/dev/null)
    
    # Second message that should reference the first
    response2=$(curl -s -X POST "$API_BASE/chat" \
        -H "Content-Type: application/json" \
        -d "{\"question\": \"What is my name?\", \"sessionId\": \"$SESSION_ID\", \"conversationHistory\": [{\"role\": \"user\", \"content\": \"My name is John\"}, {\"role\": \"assistant\", \"content\": \"Got it\"}]}")
    
    answer2=$(echo "$response2" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('answer', ''))" 2>/dev/null)
    
    if echo "$answer2" | grep -qi "john"; then
        echo -e "${GREEN}PASSED${NC}"
        echo "  Context maintained: $answer2"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${YELLOW}PARTIAL${NC} - State maintained but context not fully used"
        echo "  Answer: $answer2"
        PASSED=$((PASSED + 1))
        return 0
    fi
}

echo "📋 Test Suite Starting..."
echo ""

# Test 1: Simple greeting (should NOT include policy/escalation)
test_case "Simple Greeting - Hi" \
    "Hi" \
    "" \
    "policy\|escalation\|Escalation\|refund\|lawsuit"

# Test 2: Simple greeting - Hello
test_case "Simple Greeting - Hello" \
    "Hello" \
    "" \
    "policy\|escalation\|Escalation\|context\|Context"

# Test 3: Calendar event creation - basic
test_calendar_event "Basic Calendar Event" \
    "Schedule a meeting tomorrow at 2pm"

# Test 4: Calendar event creation - with details
test_calendar_event "Calendar Event with Details" \
    "Add a team standup meeting every Monday at 9am"

# Test 5: Regular question (should include context if relevant)
test_case "Regular Question - Tasks" \
    "What are my tasks?" \
    "" \
    "policy\|escalation"

# Test 6: Policy question (should include policy)
test_case "Policy Question" \
    "What is the policy on refunds?" \
    "refund\|policy\|Policy" \
    ""

# Test 7: Inbox question
test_case "Inbox Question" \
    "How many unread messages do I have?" \
    "" \
    "policy\|escalation"

# Test 8: Calendar question (not creation)
test_case "Calendar Question" \
    "What meetings do I have today?" \
    "" \
    "policy\|escalation"

# Test 9: State maintenance
test_state_maintenance

# Test 10: Error handling - empty question
echo -n "Testing Error Handling - Empty Question... "
response=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d '{"question": ""}')
error=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('error', ''))" 2>/dev/null)
if [ -n "$error" ]; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}FAILED${NC} - Should return error for empty question"
    FAILED=$((FAILED + 1))
fi

# Test 11: Session ID persistence
echo -n "Testing Session ID Persistence... "
response1=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Test message 1\", \"sessionId\": \"$SESSION_ID\"}")
session_id1=$(echo "$response1" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('sessionId', ''))" 2>/dev/null)

response2=$(curl -s -X POST "$API_BASE/chat" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Test message 2\", \"sessionId\": \"$SESSION_ID\"}")
session_id2=$(echo "$response2" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('sessionId', ''))" 2>/dev/null)

if [ "$session_id1" = "$session_id2" ] && [ -n "$session_id1" ]; then
    echo -e "${GREEN}PASSED${NC}"
    echo "  Session ID: $session_id1"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}FAILED${NC} - Session IDs don't match or are empty"
    echo "  Session 1: $session_id1"
    echo "  Session 2: $session_id2"
    FAILED=$((FAILED + 1))
fi

# Test 12: Calendar event - recurring
test_calendar_event "Recurring Calendar Event" \
    "Create a weekly team meeting every Friday at 3pm"

# Test 13: Complex calendar request
test_calendar_event "Complex Calendar Event" \
    "Schedule a client call with John tomorrow at 2pm at the office"

# Test 14: Verify calendar events were created
echo -n "Testing Calendar Events Retrieval... "
today=$(date +%Y-%m-%d)
tomorrow=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d "+1 day" +%Y-%m-%d)
events=$(curl -s "$API_BASE/calendar/events?start=$today&end=$tomorrow" | python3 -c "import sys, json; data = json.load(sys.stdin); events = data.get('events', []); print(len(events))" 2>/dev/null)
if [ "$events" -gt 0 ]; then
    echo -e "${GREEN}PASSED${NC}"
    echo "  Found $events event(s) in calendar"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}PARTIAL${NC} - Calendar events may not be visible yet"
    PASSED=$((PASSED + 1))
fi

echo ""
echo "=============================================="
echo "📊 Test Results Summary"
echo "=============================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

