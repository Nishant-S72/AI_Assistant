# Full Functionality Demo Guide

## 🎉 Everything is Running!

### Services Status
- ✅ **Ollama**: http://localhost:11434 (phi3 model loaded)
- ✅ **Backend API**: http://localhost:3001
- ✅ **Frontend**: http://localhost:3000
- ✅ **Database**: Postgres with 8 enriched message threads

## 📱 Test in Browser

### 1. Open Inbox
**URL**: http://localhost:3000/inbox

**What you'll see:**
- 8 varied message threads in the inbox list
- Each thread shows:
  - Contact name and company
  - Message snippet
  - Tags (lead, complaint, meeting, etc.)
  - Message count
  - Timestamp

### 2. Open a Thread
Click any message thread to open it.

**What you'll see:**
- **Left side**: Conversation history
  - Customer messages (left-aligned, white/gray)
  - Assistant messages (right-aligned, blue)
  - Timestamps for each message

- **Right side**: Context Panel
  - Contact information
  - Tags and tone preference
  - Message count
  - Pending tasks
  - AI personality insights

- **Bottom**: AI Suggestion Panel
  - Tone selector (Formal/Warm/Crisp)
  - Generate button
  - Textarea for AI suggestions
  - Send/Save Draft/Discard buttons

### 3. Generate AI Reply
Click the **"Generate"** button.

**What happens:**
1. **AI Thinking Animation**: Pulsing dots appear
2. **Backend Processing**:
   - Retrieves conversation context
   - Queries vector store (RAG)
   - Builds prompt with context
   - Calls Ollama LLM
   - Generates reply (10-20 seconds)
3. **Response Appears**: Generated reply fades into textarea

### 4. View Generated Reply
**What you'll see:**
- AI-generated reply in the textarea (editable)
- Reply is context-aware and tone-appropriate
- Can edit before sending

### 5. Expand Prompt & Sources
Click **"Prompt & Sources"** to see:
- **Prompt**: Full prompt sent to LLM (truncated to 4000 chars)
- **Sources**: Retrieved document IDs from vector store
- Shows how RAG works

### 6. Try Different Tones
Change tone selector and click Generate again:
- **Formal**: Professional, structured
- **Warm**: Friendly, empathetic
- **Crisp**: Direct, action-oriented

### 7. Send Reply
Click **"Send"** button:
- Shows toast: "Reply sent (simulated)"
- Message appears in thread
- Thread updates

## 🧪 Test via API

### List Messages
```bash
curl http://localhost:3001/api/messages
```

### Get Thread Details
```bash
MESSAGE_ID=$(curl -s http://localhost:3001/api/messages | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
curl http://localhost:3001/api/messages/$MESSAGE_ID
```

### Generate AI Reply
```bash
curl -X POST http://localhost:3001/api/messages/$MESSAGE_ID/generate \
  -H "Content-Type: application/json" \
  -d '{"tone":"warm"}'
```

### Test Different Tones
```bash
# Warm
curl -X POST http://localhost:3001/api/messages/$MESSAGE_ID/generate \
  -d '{"tone":"warm"}'

# Formal
curl -X POST http://localhost:3001/api/messages/$MESSAGE_ID/generate \
  -d '{"tone":"formal"}'

# Crisp
curl -X POST http://localhost:3001/api/messages/$MESSAGE_ID/generate \
  -d '{"tone":"crisp"}'
```

## 📊 Enriched Message Threads

1. **Sarah Martinez** - Bulk Order Inquiry
   - 200 vegan leather bags
   - Custom branding questions
   - 3 messages in thread

2. **Michael Chen** - Shipping Complaint
   - Urgent delivery issue
   - Express shipping request
   - 3 messages in thread

3. **Emily Rodriguez** - Partnership Request
   - Enterprise integration
   - Meeting scheduling
   - 2 messages in thread

4. **David Kim** - Product Question
   - Material specifications
   - Sustainability certifications
   - 1 message (needs reply)

5. **Jennifer White** - Return Request
   - Item not as described
   - Refund process
   - 2 messages in thread

6. **Robert Taylor** - Feature Request
   - API integration inquiry
   - Technical documentation
   - 3 messages in thread

7. **Lisa Anderson** - Support Question
   - Setup help needed
   - Installation guide unclear
   - 1 message (needs reply)

8. **James Wilson** - Enterprise Pricing
   - 500+ employees
   - Volume discounts
   - 2 messages in thread

## ✨ Features to Test

### Keyboard Shortcuts
- **Cmd/Ctrl+K**: Open command palette
- **G I**: Go to Inbox
- **G T**: Go to Tasks
- **Shift+Enter**: Send reply
- **Esc**: Close dialogs

### Command Palette
Press `Cmd/Ctrl+K` and try:
- "Summarize thread"
- "Send follow-up"
- "Show tasks"

### Navigation
- Click sidebar links
- Use keyboard shortcuts
- Navigate between pages

### Responsive Design
- Resize browser window
- See layout adapt
- Mobile-friendly

## 🎯 Expected Behavior

### AI Generation
- Takes 10-20 seconds for first generation
- Subsequent generations are faster (cached)
- Response is context-aware
- Uses retrieved knowledge base info
- Respects selected tone

### UI Animations
- AI thinking dots (pulsing)
- Suggestion fade-in
- Toast notifications (slide in)
- Message appearance (staggered)

### Error Handling
- Graceful fallbacks
- Clear error messages
- Retry buttons
- Loading states

## 📝 Notes

- **First generation** may be slower (model loading)
- **Policy engine** may flag some responses (can be adjusted)
- **Vector store** uses simple hash-based embeddings for demo
- **All actions are simulated** (no actual emails sent)

## 🚀 Ready to Demo!

Open **http://localhost:3000/inbox** and start exploring!

