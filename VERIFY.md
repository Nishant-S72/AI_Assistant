# Verification Guide: QA Fixes

This document provides commands to verify that all 4 critical issues from the QA report have been fixed.

## Prerequisites

1. **Backend running**: `cd backend_python && uvicorn app.main:app --host 0.0.0.0 --port 3001`
2. **Ollama running**: `ollama serve` (or ensure `USE_OLLAMA=true`)
3. **Database connected**: PostgreSQL running with schema initialized

## Quick Verification

Run the automated QA suite:
```bash
./scripts/run_qa_suite.sh
```

## Manual Verification (6 Tests)

### TEST 1: General Intent (Conversational)

**Expected:** Friendly response, no policy citations, `intent: "general_intent"`

```bash
curl -X POST "http://localhost:3001/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: verify-general-$(date +%s)" \
  -d '{
    "userMessage": "How do I write a short follow-up email after a meeting?",
    "tone": "warm"
  }' | python3 -m json.tool
```

**Assertions:**
- `intent === "general_intent"`
- `kind === "assistant"`
- `citations` is empty or absent
- `text` does NOT contain `(Policy`

---

### TEST 2: Policy Intent (RAG with Citations)

**Expected:** Policy-backed answer with citations array length >= 1

**First, seed policy documents:**
```bash
cd backend_python
python3 scripts/seed_policy_docs.py backend/policies/company-policy.md
```

**Then test:**
```bash
curl -X POST "http://localhost:3001/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: verify-policy-$(date +%s)" \
  -d '{
    "userMessage": "What does our refund policy say about partial refunds for delayed shipments?",
    "tone": "formal"
  }' | python3 -m json.tool
```

**Assertions:**
- `intent === "policy_intent"`
- `kind === "policy"`
- `citations.length >= 1`
- `text` contains `(Policy` citation token

**Check vectorstore health:**
```bash
curl "http://localhost:3001/api/health/vectorstore" | python3 -m json.tool
```

Expected: `count_chunks >= 1`

---

### TEST 3: Action Intent (Complete Data - Event Creation)

**Expected:** `intent: "action_intent"`, event created, `action_result.success === true`

```bash
curl -X POST "http://localhost:3001/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: verify-action-$(date +%s)" \
  -d '{
    "userMessage": "Schedule a 30 minute call with Jane Doe next Thursday at 3pm Dubai time. Email: jane@example.com",
    "tone": "crisp"
  }' | python3 -m json.tool
```

**Assertions:**
- `intent === "action_intent"`
- `action_result.success === true`
- `action_result.eventId` is present
- Event exists in `calendar_events` table

**Verify event in database:**
```sql
SELECT * FROM calendar_events ORDER BY created_at DESC LIMIT 1;
```

---

### TEST 4: Action Intent (Missing Info - Clarifying Question)

**Expected:** `intent: "action_intent"`, `confirm_needed: true`, clarifying question

```bash
curl -X POST "http://localhost:3001/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: verify-action-missing-$(date +%s)" \
  -d '{
    "userMessage": "Please schedule a meeting with the client next week.",
    "tone": "formal"
  }' | python3 -m json.tool
```

**Assertions:**
- `intent === "action_intent"`
- `action_suggestion.confirm_needed === true`
- `text` contains a clarifying question
- No event created (check DB)

---

### TEST 5: Policy Escalation (Sensitive Content)

**Expected:** `escalated: true`, no agentic action, audit entry with reasons

```bash
curl -X POST "http://localhost:3001/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: verify-escalate-$(date +%s)" \
  -d '{
    "userMessage": "We need to fire an employee for misconduct. Do we follow the standard termination clause or special process?",
    "tone": "formal"
  }' | python3 -m json.tool
```

**Assertions:**
- `escalated === true`
- `reasons` array is non-empty
- Response indicates human review required
- No calendar event created

**Check audit log:**
```bash
curl -H "x-demo-token: changeme" "http://localhost:3001/api/admin/audit?limit=5" | python3 -m json.tool
```

Look for `type: "chat_escalated"` entry with escalation reasons.

---

### TEST 6: Low-Confidence Fallback

**Expected:** `intent_confidence < 0.75` (or `INTENT_RULES_CONFIDENCE_THRESHOLD`), `needs_manual_label: true` in audit

```bash
curl -X POST "http://localhost:3001/api/chat" \
  -H "Content-Type: application/json" \
  -H "x-request-id: verify-lowconf-$(date +%s)" \
  -d '{
    "userMessage": "What is our stance on refunds for third-party providers?",
    "tone": "warm"
  }' | python3 -m json.tool
```

**Assertions:**
- `intent_confidence < 0.75` (or configured threshold)
- Response handled gracefully (may ask clarifying question or use general flow)
- Audit entry has `needs_manual_label: true` (check payload)

---

## Health Checks

### System Health
```bash
curl "http://localhost:3001/api/health" | python3 -m json.tool
```

Expected: `status: "ok"`, `database: "connected"`, `llm: "ollama_available"`

### Vectorstore Health
```bash
curl "http://localhost:3001/api/health/vectorstore" | python3 -m json.tool
```

Expected: `status: "ok"`, `count_chunks >= 1`, `adapter: "json"`

---

## Troubleshooting

### Issue: Vectorstore returns empty citations

**Solution:**
1. Seed policy documents:
   ```bash
   cd backend_python
   python3 scripts/seed_policy_docs.py backend/policies/company-policy.md
   ```

2. Verify seeding:
   ```bash
   curl "http://localhost:3001/api/health/vectorstore"
   ```

3. Check embeddings service:
   ```bash
   curl "http://localhost:3001/api/health"
   # Look for embeddings_service: "reachable"
   ```

### Issue: Action intent not detected

**Solution:**
1. Check intent classifier logs in backend console
2. Verify action keywords are present in message
3. Test with explicit scheduling phrase: "Schedule a meeting tomorrow at 3pm"

### Issue: Escalation not triggering

**Solution:**
1. Check policy engine keyword list in `backend_python/app/policy/policy_engine.py`
2. Verify escalation check runs BEFORE intent classification (see `chat.py`)
3. Test with explicit HR terms: "fire employee", "termination", "misconduct"

### Issue: Confidence always 1.0

**Solution:**
1. Check `INTENT_RULES_CONFIDENCE_THRESHOLD` env var (default: 0.75)
2. Test with ambiguous query that should trigger LLM fallback
3. Verify LLM fallback is working (check logs for `method: "llm"`)

---

## Acceptance Criteria Checklist

- [ ] TEST 1: General intent returns conversational response (no policy citations)
- [ ] TEST 2: Policy intent returns citations array length >= 1
- [ ] TEST 3: Action intent creates calendar event successfully
- [ ] TEST 4: Action intent asks clarifying question when fields missing
- [ ] TEST 5: Escalation triggers for sensitive content
- [ ] TEST 6: Low confidence cases flagged in audit

**All tests passing?** ✅ System is ready for production!

