# Chat Bubble Directives & Configuration

## System Prompt (Base)

```
You are Soraya AI. Answer questions about inbox, tasks, policies, and calendar.

Context: [Inbox Stats] [Tasks Stats]

You can help create calendar events. When a user wants to schedule something, I will automatically create the event for them. Just acknowledge naturally that you're adding it to their calendar.
```

## Additional Context Added Dynamically

### 1. Inbox Context
- Total messages count
- Unread messages count
- Leads count
- Format: `Inbox Stats: X total messages, Y unread, Z leads.`

### 2. Tasks Context
- P0 (urgent) tasks count
- P1 (high priority) tasks count
- P2 (normal) tasks count
- Pending tasks count
- Format: `Tasks: X pending (Y P0 urgent, Z P1 high, W P2 normal).`

### 3. Policy Rules (if available)
- Escalation keywords (first 3 rules)
- Added as: `Escalation keywords: [JSON array]`

### 4. Policy Document (conditional)
- **If question mentions**: policy, rule, escalat, guideline, procedure
  - Includes **FULL policy document**
- **Otherwise**: 
  - Includes **first 500 characters** as summary

### 5. Final Instruction
```
Keep answers short and direct. Maximum 250 words. Be concise.
```

## LLM Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| **Model** | `tinyllama` (default) | From `LLM_MODEL` env var |
| **Temperature** | `0.6` | Optimized for tinyllama |
| **Max Tokens** | `200` | ~150 words (under 250 word limit) |
| **System Prompt Limit** | `1000 chars` | Truncated before sending |
| **Question Limit** | `200 chars` | User question truncated |
| **Conversation History** | Last 10 messages | Sent with each request |

## Message Structure Sent to LLM

```javascript
[
  {
    role: 'system',
    content: systemPrompt.substring(0, 1000) // Truncated to 1000 chars
  },
  ...conversationHistory.slice(0, -1), // Last 10 messages (except current)
  {
    role: 'user',
    content: question.substring(0, 200) // Current question
  }
]
```

## Calendar Event Detection

The chat automatically detects calendar requests using keyword matching:
- Keywords: `schedule`, `book`, `plan`, `meeting`, `event`, `calendar`, `appointment`, `remind`
- Time indicators: `tomorrow`, `today`, `next`, `at`, `on`, day names
- Action words: `add`, `create`, `set`

When detected:
1. Automatically calls `/api/calendar/parse` endpoint
2. Creates calendar event
3. Updates response to confirm event creation

## Session Management

- **Session ID**: Generated on frontend, maintained across messages
- **Context Storage**: In-memory Map in backend
- **Context Limit**: Last 20 messages per session
- **Inactivity Timeout**: 1 hour (auto-cleanup)
- **Cleanup Interval**: Every 5 minutes

## Potential Issues

### 1. System Prompt Truncation
- **Problem**: System prompt limited to 1000 characters
- **Impact**: Policy document or context may be cut off
- **Location**: Line 253 in `chat.ts`

### 2. Question Truncation
- **Problem**: User questions limited to 200 characters
- **Impact**: Long questions may be cut off
- **Location**: Line 126, 285 in `chat.ts`

### 3. Conversation History Limit
- **Problem**: Only last 10 messages sent to LLM
- **Impact**: Earlier context may be lost
- **Location**: Line 114, 255 in `chat.ts`

### 4. Policy Document Loading
- **Problem**: Multiple path attempts, may fail silently
- **Impact**: Policy context may not be available
- **Location**: Lines 52-80 in `chat.ts`

## Recommendations for Fixes

1. **Increase system prompt limit** or use smarter truncation
2. **Remove or increase question length limit** (200 chars may be too restrictive)
3. **Increase conversation history** from 10 to 15-20 messages
4. **Add logging** for policy document loading failures
5. **Add error handling** for truncated prompts

