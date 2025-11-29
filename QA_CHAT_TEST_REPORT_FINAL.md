# QA Test Report: Chat System (POST /api/chat)

**Date:** 2025-11-30  
**Base URL:** http://localhost:3001  
**Backend:** Python (FastAPI)  
**LLM:** Ollama (tinyllama, USE_OLLAMA=true)  
**Test Engineer:** QA Automation

---

## Executive Summary

**Total Tests:** 6  
**Passed:** 2 (33%)  
**Failed:** 4 (67%)  
**Critical Issues:** 4

### Key Findings

1. ✅ **General Intent Routing:** Working correctly
2. ❌ **RAG Citations:** Vector store not returning citations (empty array)
3. ❌ **Action Intent Detection:** Intent classifier not detecting action requests
4. ❌ **Policy Escalation:** Escalation logic not triggering for sensitive content
5. ⚠️ **Low Confidence Detection:** All intents returning confidence=1.0 (no low-confidence cases detected)

---

## Detailed Test Results

### TEST 1: General Intent (Conversational)

**Status:** ✅ **PASS**

**Request:**
```json
{
  "userMessage": "How do I write a short follow-up email after a meeting?",
  "tone": "warm"
}
```

**Response:**
```json
{
  "kind": "assistant",
  "text": "Dear [Recipient],\n\nI hope this email finds you well...",
  "citations": [],
  "suggestionId": "b868a705-aead-45d2-991c-0da5164d9e18",
  "intent": "general_intent",
  "intent_confidence": 1.0,
  "escalated": false
}
```

**Assertions:**
- ✅ HTTP 200
- ✅ `intent === "general_intent"`
- ✅ `kind === "assistant"`
- ✅ `citations` is empty array
- ✅ No `(Policy` tokens in text
- ✅ Friendly, conversational response

**Notes:** Test passed. General intent routing works correctly.

---

### TEST 2: Policy Intent (RAG)

**Status:** ❌ **FAIL**

**Request:**
```json
{
  "userMessage": "What does our refund policy say about partial refunds for delayed shipments?",
  "tone": "formal",
  "rag": true
}
```

**Response:**
```json
{
  "kind": "policy",
  "text": "Our refund policy (Policy §X.Y) says that:\n\n1. For eligible purchase returns...",
  "citations": [],
  "suggestionId": "d8d000c0-af61-41c4-9a3b-1832bff3ac6d",
  "intent": "policy_intent",
  "intent_confidence": 1.0,
  "escalated": false
}
```

**Assertions:**
- ✅ HTTP 200
- ✅ `intent === "policy_intent"`
- ✅ `kind === "policy"`
- ✅ Text contains `(Policy` citation token
- ❌ **FAIL:** `citations` array is empty (expected k>=1 chunks)
- ❌ **FAIL:** No actual policy chunks retrieved from vector store

**Root Cause:**
- Vector store (Chroma/JSON fallback) is not returning chunks
- Possible issues:
  1. Vector store not initialized/seeded with policy documents
  2. Embedding generation failing
  3. Query returning no results

**Recommendation:**
- Check vector store health: `GET /api/health`
- Verify policy documents are seeded into vector store
- Check `backend_python/app/clients/vectorstore/` logs
- Verify embeddings service is working

---

### TEST 3: Agentic Intent (Complete Data)

**Status:** ❌ **FAIL**

**Request:**
```json
{
  "userMessage": "Schedule a 30 minute call with Jane Doe next Thursday at 3pm Dubai time. Email: jane@example.com",
  "tone": "crisp"
}
```

**Response:**
```json
{
  "kind": "assistant",
  "text": "Dear Jane,\n\nI hope this email finds you well. I am writing to schedule a 30-minute call...",
  "citations": [],
  "suggestionId": "ebb8b871-46a4-48b6-a16c-261cf12cd044",
  "intent": "general_intent",
  "intent_confidence": 1.0,
  "escalated": false
}
```

**Assertions:**
- ✅ HTTP 200
- ❌ **FAIL:** `intent === "general_intent"` (expected `"action_intent"`)
- ❌ **FAIL:** No calendar event created
- ❌ **FAIL:** No `action_result` in response
- ❌ **FAIL:** Response is conversational email draft, not event confirmation

**Root Cause:**
- Intent classifier (`backend_python/app/policy/intent_classifier.py`) is not detecting action keywords
- Keywords like "schedule", "next Thursday", "3pm" should trigger `action_intent`
- Current classifier may have insufficient keyword patterns

**Recommendation:**
- Review `intent_classifier.py` action keyword patterns
- Add more comprehensive action detection (time references, scheduling verbs)
- Test intent classifier directly with action phrases
- Implement action handler for `action_intent` routing

---

### TEST 4: Agentic Intent (Missing Info)

**Status:** ❌ **FAIL**

**Request:**
```json
{
  "userMessage": "Please schedule a meeting with the client next week.",
  "tone": "formal"
}
```

**Response:**
```json
{
  "kind": "assistant",
  "text": "Thank you for your suggestion, I will schedule a meeting with the client next week...",
  "citations": [],
  "suggestionId": "badaf6bf-92d0-48f4-a172-759c86a43afd",
  "intent": "general_intent",
  "intent_confidence": 1.0,
  "escalated": false
}
```

**Assertions:**
- ✅ HTTP 200
- ❌ **FAIL:** `intent === "general_intent"` (expected `"action_intent"`)
- ❌ **FAIL:** No clarifying question asked
- ❌ **FAIL:** No `confirm_needed` or `clarifyingQuestion` field
- ❌ **FAIL:** Response is conversational, not action-oriented

**Root Cause:**
- Same as TEST 3: Intent classifier not detecting action intent
- Even with missing details, should still classify as `action_intent` and ask clarifying question

**Recommendation:**
- Same as TEST 3
- Additionally: Implement action planner that extracts entities and asks clarifying questions when fields are missing

---

### TEST 5: Policy Escalation (Sensitive Content)

**Status:** ❌ **FAIL**

**Request:**
```json
{
  "userMessage": "We need to fire an employee for misconduct. Do we follow the standard termination clause or special process?",
  "tone": "formal",
  "rag": true
}
```

**Response:**
```json
{
  "kind": "policy",
  "text": "The question you are referring to is regarding whether the standard terminations clause...",
  "citations": [],
  "suggestionId": "e49a942d-0acd-4b13-a3c8-f24a16955456",
  "intent": "policy_intent",
  "intent_confidence": 1.0,
  "escalated": false
}
```

**Assertions:**
- ✅ HTTP 200
- ✅ `intent === "policy_intent"`
- ❌ **FAIL:** `escalated === false` (expected `true`)
- ❌ **FAIL:** No escalation message
- ❌ **FAIL:** System answered policy question instead of escalating

**Root Cause:**
- Policy engine (`backend_python/app/policy/policy_engine.py`) is not detecting sensitive keywords
- Keywords like "fire", "employee", "misconduct", "termination" should trigger escalation
- Current policy check may be bypassed for policy questions (see `chat.py` line ~115)

**Recommendation:**
- Review policy engine keyword list
- Ensure escalation triggers for HR/legal terms even in policy questions
- Update escalation logic to check for sensitive content before RAG retrieval
- Add escalation reasons to response

---

### TEST 6: Low-Confidence Fallback

**Status:** ⚠️ **PARTIAL PASS** (Low confidence not detected, but system handled gracefully)

**Request:**
```json
{
  "userMessage": "What is our stance on refunds for third-party providers?",
  "tone": "warm"
}
```

**Response:**
```json
{
  "kind": "policy",
  "text": "I do not have access to the policies of a particular company...",
  "citations": [],
  "suggestionId": "63ebc883-9eed-41fb-8df1-38e97ed40932",
  "intent": "policy_intent",
  "intent_confidence": 1.0,
  "escalated": false
}
```

**Assertions:**
- ✅ HTTP 200
- ⚠️ `intent_confidence === 1.0` (expected < 0.75 for ambiguous queries)
- ✅ System handled gracefully (acknowledged uncertainty)
- ❌ No `needs_manual_label` flag in response (should be in audit)

**Root Cause:**
- Intent classifier always returns high confidence (1.0)
- No LLM-based fallback for ambiguous cases
- Keyword-based classifier is too confident

**Recommendation:**
- Implement LLM-based classification for ambiguous cases
- Add confidence threshold checking
- Flag low-confidence cases in audit logs with `needs_manual_label: true`

---

## Server State Verification

### Audit Logs
- **Status:** ❌ Unauthorized (requires `x-demo-token` or API key)
- **Note:** Could not verify audit entries without proper authentication

### Vector Store
- **Status:** ⚠️ Unknown (no health check endpoint tested)
- **Issue:** Citations empty in all RAG responses

### Events Table
- **Status:** ⚠️ Not verified (requires DB access)

---

## Critical Issues Summary

### Issue #1: Vector Store Not Returning Citations
**Severity:** HIGH  
**Impact:** RAG functionality not working  
**Affected Tests:** TEST 2  
**Fix Required:**
- Initialize/seed vector store with policy documents
- Verify embedding generation
- Check vector store query logic

### Issue #2: Action Intent Not Detected
**Severity:** HIGH  
**Impact:** Agentic calendar features not working  
**Affected Tests:** TEST 3, TEST 4  
**Fix Required:**
- Improve intent classifier action keyword detection
- Add time/date pattern matching
- Implement action handler routing

### Issue #3: Policy Escalation Not Triggering
**Severity:** HIGH  
**Impact:** Sensitive content not escalated to humans  
**Affected Tests:** TEST 5  
**Fix Required:**
- Review policy engine keyword list
- Ensure escalation checks run before RAG
- Add HR/legal term detection

### Issue #4: Confidence Always 1.0
**Severity:** MEDIUM  
**Impact:** Low-confidence cases not flagged  
**Affected Tests:** TEST 6  
**Fix Required:**
- Implement LLM-based classification fallback
- Add confidence threshold logic
- Flag ambiguous cases in audit

---

## Recommendations

### Immediate Actions
1. **Fix Vector Store:** Seed policy documents and verify RAG retrieval
2. **Improve Intent Classifier:** Add comprehensive action detection patterns
3. **Fix Escalation:** Ensure sensitive content triggers escalation before processing
4. **Add Confidence Scoring:** Implement LLM-based fallback for ambiguous cases

### Testing Improvements
1. Add vector store health check endpoint
2. Add audit log verification (with proper auth)
3. Add integration tests for action handler
4. Add confidence threshold testing

### Code Quality
1. Add error handling for vector store failures
2. Add logging for intent classification decisions
3. Add unit tests for intent classifier
4. Document expected confidence ranges

---

## Test Artifacts

All test responses saved to:
- `/tmp/test1_response.json` - General intent
- `/tmp/test2_response.json` - Policy intent (RAG)
- `/tmp/test3_response.json` - Action intent (complete)
- `/tmp/test4_response.json` - Action intent (missing)
- `/tmp/test5_response.json` - Policy escalation
- `/tmp/test6_response.json` - Low confidence

Full report: `/tmp/qa_report.md`

---

## Conclusion

The chat system has **basic functionality working** (general intent routing), but **critical features are not operational**:
- RAG citations not working
- Action intent detection failing
- Policy escalation not triggering

**Overall System Health:** 🟡 **DEGRADED** (2/6 tests passing)

**Priority:** Fix vector store and action intent detection before production deployment.

---

**Report Generated:** 2025-11-30  
**Next Review:** After fixes applied

