# QA Fixes Changelog

**Date:** 2025-11-30  
**Purpose:** Fix 4 critical issues identified in QA report

---

## Summary of Changes

### Files Created
1. `backend_python/scripts/seed_policy_docs.py` - Policy document seeding script
2. `backend_python/tests/test_intent_classifier.py` - Intent classifier unit tests
3. `backend_python/tests/test_policy_engine.py` - Policy engine escalation tests
4. `backend_python/tests/test_vectorstore.py` - Vector store seed/query tests
5. `backend_python/tests/test_chat_integration.py` - Chat endpoint integration tests
6. `scripts/run_qa_suite.sh` - Automated QA test runner
7. `VERIFY.md` - Verification guide with curl commands

### Files Modified

#### Core Fixes

1. **`backend_python/app/policy/intent_classifier.py`** (REWRITTEN)
   - Added hybrid rule+LLM classification approach
   - Improved action intent detection with comprehensive keyword patterns
   - Added time/date/timezone/email pattern matching
   - Implemented LLM fallback for ambiguous cases
   - Returns confidence scores < 1.0 for uncertain queries
   - Added `classify_intent_async()` for async LLM calls

2. **`backend_python/app/policy/policy_engine.py`**
   - Added HR/termination keywords: "fire", "misconduct", "employee misconduct"
   - Added harassment keywords: "harassment", "sexual harassment", "discrimination"
   - Expanded sensitive data keywords: "passport", "visa", "medical record", "criminal record"
   - Enhanced legal keywords: "litigation", "court", "legal complaint"

3. **`backend_python/app/routes/chat.py`** (MAJOR UPDATE)
   - **CRITICAL FIX:** Policy escalation now checked BEFORE intent classification
   - Updated to use `classify_intent_async()` for LLM fallback support
   - Added `needs_manual_label` flag when confidence < threshold
   - Improved action intent handler with actual calendar event creation
   - Enhanced audit logging with intent metadata
   - Added graceful error handling for empty vectorstore

4. **`backend_python/app/services/embeddings.py`**
   - Added retry logic (3 attempts with exponential backoff)
   - Added timeout handling for Ollama requests
   - Improved error logging
   - Validates embedding vector length > 0

5. **`backend_python/app/clients/vectorstore/json_adapter.py`**
   - Added empty store detection and warning
   - Added embedding validation before query
   - Added score filtering (min 0.1) to reduce noise
   - Improved error handling

6. **`backend_python/app/routes/health.py`** (ENHANCED)
   - Added comprehensive health checks:
     - Database connection
     - LLM availability (Ollama/OpenAI)
     - Embeddings service reachability
     - Vectorstore status and chunk count
   - Added `GET /api/health/vectorstore` endpoint
   - Returns `last_seeded_at` from metadata

7. **`backend_python/app/routes/admin.py`**
   - Fixed auth to support `x-demo-token` header
   - Improved error messages for unauthorized access

8. **`backend_python/app/routes/calendar.py`**
   - Added `parse_event_text()` helper function for use by chat route
   - Improved date/time parsing with fallback regex patterns
   - Better error handling for missing fields

---

## Issue Fixes

### Issue #1: Vectorstore Not Returning Citations ✅ FIXED

**Root Cause:** Policy documents not seeded into vectorstore

**Fix:**
- Created `scripts/seed_policy_docs.py` to chunk and seed policy documents
- Added chunking logic (1024 chars with 50 char overlap)
- Generates embeddings using Ollama/OpenAI
- Upserts chunks to JSON vectorstore with metadata
- Added health endpoint to check chunk count

**Verification:**
```bash
# Seed policy docs
python3 backend_python/scripts/seed_policy_docs.py backend/policies/company-policy.md

# Check health
curl http://localhost:3001/api/health/vectorstore
```

---

### Issue #2: Action Intent Not Detected ✅ FIXED

**Root Cause:** Intent classifier had insufficient keyword patterns and no time/date detection

**Fix:**
- Expanded action keywords: "schedule", "meeting", "calendar", "book", "appointment", etc.
- Added time pattern matching: weekdays, dates, "next", time expressions, timezones
- Added email pattern detection (attendees)
- Added duration pattern matching
- Improved confidence scoring (0.85-0.9 for strong matches, not 1.0)

**Verification:**
```bash
curl -X POST http://localhost:3001/api/chat \
  -d '{"userMessage": "Schedule a meeting tomorrow at 3pm"}'
# Should return intent: "action_intent"
```

---

### Issue #3: Policy Escalation Not Triggering ✅ FIXED

**Root Cause:** Escalation check was bypassed for policy questions; keyword list incomplete

**Fix:**
- **CRITICAL:** Moved escalation check to run BEFORE intent classification
- Added HR keywords: "fire", "misconduct", "employee misconduct"
- Added harassment keywords: "harassment", "sexual harassment", "discrimination"
- Expanded legal keywords: "litigation", "court", "legal complaint"
- Escalation now blocks all further processing (no RAG, no actions)

**Verification:**
```bash
curl -X POST http://localhost:3001/api/chat \
  -d '{"userMessage": "We need to fire an employee for misconduct"}'
# Should return escalated: true
```

---

### Issue #4: Confidence Always 1.0 ✅ FIXED

**Root Cause:** No LLM fallback for ambiguous cases; rules always returned high confidence

**Fix:**
- Implemented LLM-based classification for ambiguous queries
- Rules return confidence 0.85-0.9 (not 1.0)
- LLM fallback returns confidence 0.6-0.8 for uncertain cases
- Added `INTENT_RULES_CONFIDENCE_THRESHOLD` (default 0.75)
- Flags `needs_manual_label: true` in audit when confidence < threshold

**Verification:**
```bash
curl -X POST http://localhost:3001/api/chat \
  -d '{"userMessage": "What should I do about refunds?"}'
# Should return intent_confidence < 1.0
```

---

## Testing

### Unit Tests Added
- `test_intent_classifier.py` - Intent classification (greeting, policy, action, LLM fallback)
- `test_policy_engine.py` - Escalation triggers (HR, legal, sensitive data)
- `test_vectorstore.py` - Seed and query functionality
- `test_chat_integration.py` - Full chat endpoint integration

### Run Tests
```bash
cd backend_python
pytest tests/ -v
```

### Run QA Suite
```bash
./scripts/run_qa_suite.sh
```

---

## Environment Variables

New/Updated:
- `INTENT_RULES_CONFIDENCE_THRESHOLD` (default: 0.75) - Threshold for manual labeling
- `USE_OLLAMA` (default: true) - Use Ollama for LLM/embeddings
- `LLM_MODEL` (default: tinyllama) - Model name for Ollama
- `LLM_BASE_URL` (default: http://localhost:11434) - Ollama base URL

---

## Manual Steps Required

1. **Seed Policy Documents:**
   ```bash
   cd backend_python
   python3 scripts/seed_policy_docs.py backend/policies/company-policy.md
   ```

2. **Verify Vectorstore:**
   ```bash
   curl http://localhost:3001/api/health/vectorstore
   ```
   Should show `count_chunks >= 1`

3. **Run QA Suite:**
   ```bash
   ./scripts/run_qa_suite.sh
   ```

---

## Breaking Changes

None - all changes are backward compatible.

---

## Performance Impact

- **Intent Classification:** Slightly slower for ambiguous queries (LLM fallback), but only when rules are inconclusive
- **RAG Queries:** No change (same vectorstore query)
- **Escalation Check:** Minimal overhead (keyword matching only)

---

## Next Steps

1. Monitor intent classification accuracy in production
2. Tune confidence thresholds based on real usage
3. Expand policy document corpus
4. Add more action types (tasks, emails) beyond calendar events

