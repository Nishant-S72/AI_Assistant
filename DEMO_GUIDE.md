# Frontend Demo Guide

## ✅ Frontend is Running!

The frontend is successfully running at **http://localhost:3000**

## Features to Test

### 1. **Navigation & Layout**
- **Sidebar**: Left navigation with Inbox, Tasks, Drafts, Settings
- **Responsive Design**: Desktop-first layout that adapts to screen size
- **Dark Mode**: Automatically respects system preferences

### 2. **Command Palette (Cmd/Ctrl+K)**
Press `Cmd+K` (Mac) or `Ctrl+K` (Windows/Linux) to open the command palette.

**Available Commands:**
- **Summarize thread** - Summarizes the current thread
- **Send follow-up** - Generates a follow-up suggestion
- **Show tasks** - Navigates to tasks page

**Keyboard Navigation:**
- `↑↓` arrows to navigate
- `Enter` to select
- `Esc` to close

### 3. **Inbox View** (`/inbox`)
- Lists all message threads
- Shows contact name, subject, snippet
- Tags (Lead, Complaint, Meeting)
- Message count and timestamp
- Click any thread to open it

### 4. **Thread View** (`/thread/[id]`)
- **Conversation Display**: 
  - Customer messages on left
  - Assistant messages on right
  - Timestamps for each message

- **AI Suggestion Panel**:
  - Tone selector (Formal/Warm/Crisp)
  - Generate button to create AI suggestion
  - Animated thinking dots while generating
  - Editable textarea for the suggestion
  - Send/Save Draft/Discard buttons
  - "Prompt & Sources" collapsible section

- **Context Panel** (right side):
  - Contact information
  - Tags and tone preference
  - Message count
  - Pending tasks
  - AI personality insights

### 5. **Keyboard Shortcuts**
- `Cmd/Ctrl+K` - Open command palette
- `G I` - Go to Inbox (via command palette)
- `G T` - Go to Tasks (via command palette)
- `Shift+Enter` - Send reply (in suggestion editor)
- `Esc` - Close dialogs/palette

### 6. **Offline Mode Banner**
When backend is in offline mode, shows:
> 🧠 Offline Demo Mode — using local LLM + dummy inbox

### 7. **Toast Notifications**
- Success: Green toast for actions like "Reply sent (simulated)"
- Error: Red toast for errors
- Info: Blue toast for information

### 8. **Settings Page** (`/settings`)
- Mode toggle (Simulated/Backend)
- System status (Ollama, models, dummy threads)
- Keyboard shortcuts reference

## Testing the Frontend

### Without Backend (UI Only)
The frontend will show:
- Empty inbox with "Load Demo Data" button
- Error messages when trying to generate suggestions
- All UI components and navigation work

### With Backend (Full Functionality)
1. **Start Backend**:
   ```bash
   cd backend
   npm run dev
   ```

2. **Or Use Demo Script**:
   ```bash
   ./scripts/run_local_demo.sh
   ```

3. **Features Available**:
   - Load dummy inbox threads
   - Generate AI suggestions
   - Send simulated replies
   - View contact context
   - See tasks

## Current Status

✅ **Frontend**: Running on http://localhost:3000  
⚠️ **Backend**: Needs database connection (Postgres/Redis)

## Quick Test Checklist

- [ ] Open http://localhost:3000
- [ ] See sidebar navigation
- [ ] Press `Cmd/Ctrl+K` to open command palette
- [ ] Navigate to Inbox
- [ ] Navigate to Settings
- [ ] Check responsive design (resize window)
- [ ] Test keyboard navigation
- [ ] See offline mode banner (if backend in offline mode)

## Screenshots of Features

### Main Layout
- Left sidebar with navigation
- Main content area
- Right context panel (on thread view)

### Command Palette
- Modal overlay
- Searchable commands
- Keyboard navigable

### Thread View
- Message bubbles
- AI suggestion panel at bottom
- Context panel on right

### Animations
- AI thinking dots (pulsing)
- Suggestion reveal (fade + slide)
- Toast notifications (slide in)

## Next Steps

1. **For Full Demo**: Start backend with database
2. **For UI Demo**: Frontend is ready to show all UI components
3. **For Offline Mode**: Run `./scripts/run_local_demo.sh`

Enjoy exploring the frontend! 🚀

