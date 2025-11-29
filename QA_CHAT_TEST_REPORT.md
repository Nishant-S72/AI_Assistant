# QA Test Report: Chat System (POST /api/chat)

**Date:** $(date)
**Base URL:** http://localhost:3001
**Backend:** Python (FastAPI)
**LLM:** Ollama (USE_OLLAMA=true)

---

## Test Execution Summary

| Test ID | Test Case | Status | Notes |
|---------|-----------|--------|-------|
| TEST 1 | General Intent (Conversational) | ⏳ PENDING | - |
| TEST 2 | Policy Intent (RAG) | ⏳ PENDING | - |
| TEST 3 | Agentic Intent (Complete Data) | ⏳ PENDING | - |
| TEST 4 | Agentic Intent (Missing Info) | ⏳ PENDING | - |
| TEST 5 | Policy Escalation | ⏳ PENDING | - |
| TEST 6 | Low-Confidence Fallback | ⏳ PENDING | - |

---

## Detailed Test Results

### TEST 1: General Intent (Conversational)

**Purpose:** Ensure normal questions receive friendly, conversational replies (no policy citations).

**Request:**
```json
{
  "userMessage": "How do I write a short follow-up email after a meeting?",
  "tone": "warm"
}
```

**Expected:**
- HTTP 200
- `intent === "general_intent"`
- `kind === "assistant"`
- `text` - friendly, actionable reply (~70-140 words)
- `citations` absent or empty
- `text` should NOT contain `(Policy` tokens

**Result:** ⏳ Analyzing...

---

### TEST 2: Policy Intent (RAG)

**Purpose:** User asks about policy — system must perform RAG, return policy-backed answer and citations.

**Request:**
```json
{
  "userMessage": "What does our refund policy say about partial refunds for delayed shipments?",
  "tone": "formal",
  "rag": true
}
```

**Expected:**
- HTTP 200
- `intent === "policy_intent"`
- `kind === "policy"`
- `text` contains `(Policy` style citation tokens
- `citations` array with k>=1 chunks
- Audit record saved

**Result:** ⏳ Analyzing...

---

### TEST 3: Agentic Intent (Complete Data)

**Purpose:** Test action planning + calendar creation when all details are provided.

**Request:**
```json
{
  "userMessage": "Schedule a 30 minute call with Jane Doe next Thursday at 3pm Dubai time. Email: jane@example.com",
  "tone": "crisp"
}
```

**Expected:**
- `intent === "action_intent"`
- Event created (simulated or Google)
- `action_result` with `success: true`
- `text` - confirmation message

**Result:** ⏳ Analyzing...

---

### TEST 4: Agentic Intent (Missing Info)

**Purpose:** Ensure action_intent asks clarifying question when required entity missing.

**Request:**
```json
{
  "userMessage": "Please schedule a meeting with the client next week.",
  "tone": "formal"
}
```

**Expected:**
- `intent === "action_intent"`
- `confirm_needed === true` or clarifying question
- No event created

**Result:** ⏳ Analyzing...

---

### TEST 5: Policy Escalation (Sensitive Content)

**Purpose:** Ensure policyEngine flags and blocks agentic actions for sensitive content.

**Request:**
```json
{
  "userMessage": "We need to fire an employee for misconduct. Do we follow the standard termination clause or special process?",
  "tone": "formal",
  "rag": true
}
```

**Expected:**
- Escalation occurs
- `escalated === true`
- Agentic actions disabled
- Audit entry with escalation reasons

**Result:** ⏳ Analyzing...

---

### TEST 6: Low-Confidence Fallback

**Purpose:** Ensure classifier flags low-confidence cases for labeling.

**Request:**
```json
{
  "userMessage": "What is our stance on refunds for third-party providers?",
  "tone": "warm"
}
```

**Expected:**
- Low `intent_confidence` (below threshold)
- `needs_manual_label === true` in audit
- Safe default routing

**Result:** ⏳ Analyzing...

---

## Analysis Script

Running analysis on all test responses...

