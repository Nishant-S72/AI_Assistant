# AI Assistant - Complete Feature Documentation

This document provides a comprehensive, feature-by-feature breakdown of all capabilities in the AI Assistant repository.

---

## Table of Contents

1. [Core Assistant Features](#core-assistant-features)
2. [Task Management (JIRA-like)](#task-management-jira-like)
3. [Calendar & Scheduling](#calendar--scheduling)
4. [Inbox & Message Management](#inbox--message-management)
5. [Contact Management](#contact-management)
6. [AI-Powered Features](#ai-powered-features)
7. [Tier System (Assist vs Pro)](#tier-system-assist-vs-pro)
8. [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
9. [Notifications & Reminders](#notifications--reminders)
10. [API Endpoints](#api-endpoints)
11. [Database Schema](#database-schema)
12. [Frontend Features](#frontend-features)
13. [Integrations](#integrations)

---

## Core Assistant Features

### 1. Chat Interface
- **Floating Chat Bubble**: Always-accessible chat interface with smooth animations
- **SSE Streaming**: Real-time token-by-token response streaming
- **Conversation History**: Maintains context across multiple turns
- **Tone Selection**: Choose between formal, warm, or crisp response tones
- **Intent Classification**: Automatically routes requests to appropriate handlers
- **Action Suggestions**: Proposes actions for Assist tier users
- **Action Execution**: Direct execution for Pro tier users

### 2. Intent Routing
- **LLM-Based Classification**: Uses GPT-4o-mini to classify user intent
- **Three Intent Types**:
  - `general`: Writing, summarizing, explaining, drafting
  - `rag`: Questions about policies, procedures, documents
  - `action_candidate`: Scheduling, sending, creating tasks, following up
- **Confidence Thresholding**: Falls back to "general" if confidence < 0.65

### 3. Action Planning & Execution
- **Action Planner**: LLM-based component that parses natural language into structured JSON
- **Supported Actions**:
  - `send_email`: Send emails with recipient, subject, body
  - `create_calendar_event`: Schedule meetings with attendees, location, reminders
  - `create_task`: Create tasks with due dates and priorities
  - `schedule_followup`: Schedule follow-up reminders
- **Missing Field Detection**: Asks for clarification when required information is missing
- **Tier-Based Execution**: Assist tier suggests, Pro tier executes

---

## Task Management (JIRA-like)

### 1. Task CRUD Operations
- **Create Tasks**: Manual creation or automatic inference from inbox messages
- **List Tasks**: Filter by status (pending, completed, cancelled)
- **View Task Details**: Title, contact, due date, priority, status
- **Task Priority**: Automatic P0/P1/P2 classification based on urgency

### 2. Task Status Management
- **Mark as Completed**: One-click completion with timestamp tracking
- **Cancel Tasks**: Cancel with optional reason
- **Postpone Tasks**: Reschedule to new due date with automatic reminder rescheduling
- **Status Tracking**: Visual status badges (pending, completed, cancelled)

### 3. Task Reminders
- **Automatic Scheduling**: Reminders scheduled when tasks are created with due dates
- **Configurable Timing**: Default 60 minutes before due date (customizable)
- **Reminder Display**: Upcoming reminders shown on main screen
- **Time Remaining**: Shows days/hours/minutes until due date
- **Reminder Notifications**: In-app notifications when reminders trigger

### 4. Task Inference
- **Automatic Detection**: Analyzes inbox messages to infer actionable tasks
- **Smart Extraction**: Identifies task titles, due dates, and related contacts
- **Background Processing**: Runs automatically in background
- **Quality Filtering**: Limits to 50 high-quality messages for inference

---

## Calendar & Scheduling

### 1. Calendar Events
- **Create Events**: Full event creation with title, description, location, video links
- **All-Day Events**: Support for all-day events
- **Recurring Events**: iCal RRULE format support (daily, weekly, monthly, etc.)
- **Timezone Support**: Timezone-aware event scheduling
- **Event Colors**: Custom color coding for events
- **Attendees Management**: Add attendees with email and status tracking

### 2. Calendar Views
- **Month View**: Full calendar grid with event indicators
- **Today's Events**: Sidebar showing today's scheduled events
- **Date Selection**: Click any date to create/view events
- **Event Details**: Click events to view/edit details

### 3. Calendar Integrations
- **Google Calendar**: OAuth-based integration with Google Calendar
- **Microsoft Outlook**: OAuth-based integration with Outlook Calendar
- **Event Mirroring**: Local database mirror of calendar events for quick access
- **Bi-Directional Sync**: Sync events to/from external calendars
- **Import Events**: Bulk import from Google Calendar

### 4. Event Reminders
- **Multiple Reminders**: Add multiple reminders per event (15 min, 1 hour, etc.)
- **Reminder Channels**: In-app, email, or Slack notifications
- **Automatic Scheduling**: APScheduler manages reminder delivery
- **Reminder Status**: Track delivered/pending reminders

---

## Inbox & Message Management

### 1. Message Organization
- **Folder Support**: Organize messages by folder (inbox, sent, drafts, etc.)
- **Thread View**: Grouped conversation threads
- **Message Threading**: Automatic thread detection and grouping
- **Unread Tracking**: Track read/unread status

### 2. Message Categories
- **Automatic Classification**: Categorize messages as leads, complaints, urgent, etc.
- **Priority Badges**: Visual indicators for message priority
- **Category Summaries**: AI-generated summaries per category

### 3. Message Actions
- **Draft Replies**: AI-generated reply suggestions
- **Send Messages**: Direct message sending (Pro tier)
- **Tone Selection**: Choose response tone (formal, warm, crisp)
- **Policy Checking**: Automatic policy compliance checking

### 4. Inbox Summary
- **Dashboard Overview**: Summary cards showing totals, unread, leads, complaints
- **AI Summary**: Auto-generated paragraph summarizing inbox state
- **Performance Metrics**: Average latency, acceptance rate, messages sent
- **Urgent Context**: Highlights urgent items requiring attention

---

## Contact Management

### 1. Contact Profiles
- **Contact Information**: Name, email, company, tags
- **Contact Summaries**: AI-generated summaries of contact interactions
- **Recent Conversations**: List of recent threads with contact
- **Recommendations**: AI-suggested next actions for contacts

### 2. Contact Insights
- **Interaction History**: View all messages with a contact
- **Contact Tags**: Categorize contacts with tags
- **Company Information**: Track company associations
- **Lead Scoring**: Automatic lead identification and scoring

---

## AI-Powered Features

### 1. LLM Integration
- **Model Selection**: Centralized LLM provider with model routing
- **Model Assignments**:
  - Thread summaries: Gemini 1.5 Flash
  - Priority classification: Gemini 1.5 Flash
  - Draft replies: GPT-4o-mini
  - Intent classification: GPT-4o-mini
  - Action planning: GPT-4o-mini
  - RAG synthesis: GPT-4o-mini
- **Fallback Support**: Automatic fallback to alternative models on failure
- **Temperature Control**: Configurable temperature per use case

### 2. Conversation Summarization
- **Auto-Summarization**: Automatically summarizes long conversations (>30 messages)
- **Summary Regeneration**: Manual trigger to regenerate summaries
- **Context Preservation**: Maintains key information in summaries
- **Summary Caching**: Cached summaries for performance

### 3. Reply Generation
- **Context-Aware**: Uses conversation history for context
- **Tone-Aware**: Respects selected tone (formal/warm/crisp)
- **Policy-Compliant**: Ensures replies follow company policies
- **Quick Actions**: One-click send or edit

### 4. Priority Classification
- **Automatic Classification**: P0 (urgent), P1 (high), P2 (normal)
- **Multi-Factor Analysis**: Considers due dates, message content, contact tags
- **Visual Indicators**: Priority badges throughout UI

---

## Tier System (Assist vs Pro)

### 1. Assist Tier Features
**Allowed Actions:**
- Inbox ingestion
- Thread summarization
- Draft replies
- Tone selection
- Priority classification
- Suggested next actions (JSON)
- RAG read-only answers

**Restrictions:**
- Cannot auto-send emails
- Cannot create calendar events
- Cannot create tasks
- Cannot execute follow-ups
- Cannot update memory
- Cannot run workflows

**Response Pattern**: "Here's what I suggest."

### 2. Pro Tier Features
**Everything in Assist PLUS:**
- Auto-send emails
- Calendar event creation
- Task creation
- Follow-up scheduling
- Workflow execution
- Memory updates
- Behavioral memory
- Multi-step agent workflows

**Response Pattern**: "It's done."

### 3. Tier Gating
- **Backend Enforcement**: Tier checks at API level
- **Graceful Degradation**: Clear messaging when features are restricted
- **Upgrade Prompts**: Helpful prompts to upgrade tier
- **Tier Badges**: Visual indicators of current tier

---

## RAG (Retrieval-Augmented Generation)

### 1. Document Retrieval
- **Vector Store**: ChromaDB or JSON-based fallback
- **Top-K Retrieval**: Retrieves top 3 most relevant chunks
- **Similarity Search**: Semantic similarity matching
- **Metadata Tracking**: Source, filename, fragment index, score

### 2. RAG Responses
- **Citation Support**: Includes [ref1], [ref2] citation tokens
- **Source Attribution**: Shows source documents with snippets
- **Provenance Display**: Expandable source information
- **Graceful Fallback**: Falls back if no relevant documents found

### 3. Knowledge Base
- **Policy Documents**: Company policies, terms, procedures
- **Document Upload**: Support for uploading policy documents
- **Chunking**: Automatic document chunking for retrieval
- **Embedding Generation**: Automatic embedding generation

---

## Notifications & Reminders

### 1. Notification Channels
- **In-App**: Real-time in-app notifications
- **Email**: SMTP-based email notifications
- **Slack**: Slack webhook notifications

### 2. Reminder System
- **APScheduler**: Background job scheduler for reminders
- **Task Reminders**: Reminders for task due dates
- **Event Reminders**: Reminders for calendar events
- **Configurable Timing**: Customizable reminder timing

### 3. Notification Management
- **Snooze**: Snooze reminders to later time
- **Dismiss**: Dismiss notifications
- **Reschedule**: Reschedule reminders
- **Delivery Tracking**: Track notification delivery status

---

## API Endpoints

### Core Endpoints

#### Messages
- `GET /api/messages` - List messages (with folder filter)
- `GET /api/messages/{id}` - Get message/thread details
- `POST /api/messages/{id}/generate` - Generate reply suggestion
- `POST /api/messages/{id}/send` - Send message (Pro only)

#### Tasks
- `GET /api/tasks` - List tasks (with status filter)
- `POST /api/tasks` - Create task
- `PATCH /api/tasks/{id}/complete` - Mark task as completed
- `PATCH /api/tasks/{id}/cancel` - Cancel task
- `PATCH /api/tasks/{id}/postpone` - Postpone task
- `GET /api/tasks/reminders` - Get upcoming task reminders

#### Calendar
- `GET /api/v1/calendar/events` - List calendar events
- `POST /api/v1/calendar/events` - Create calendar event
- `PATCH /api/v1/calendar/events/{id}` - Update calendar event
- `DELETE /api/v1/calendar/events/{id}` - Delete calendar event
- `POST /api/v1/calendar/events/{id}/reminders` - Add reminders
- `GET /api/v1/calendar/reminders` - List reminders
- `POST /api/v1/calendar/import/google` - Import from Google Calendar

#### Scheduler
- `POST /api/v1/scheduler/chat` - Natural language scheduling
- `POST /api/v1/scheduler/parse` - Parse scheduling request
- `POST /api/v1/scheduler/create` - Create scheduled event
- `GET /api/v1/scheduler/events` - List scheduled events
- `POST /api/v1/scheduler/reschedule/{id}` - Reschedule event
- `POST /api/v1/scheduler/cancel_event/{id}` - Cancel event
- `POST /api/v1/scheduler/connect/google` - Connect Google Calendar
- `POST /api/v1/scheduler/connect/outlook` - Connect Outlook Calendar

#### Chat (Phase 1)
- `POST /api/v1/chat` - Main chat endpoint with intent routing
- `POST /api/v1/chat/feedback` - Submit feedback on suggestions

#### RAG
- `POST /api/v1/rag_chat` - RAG-powered chat with provenance

#### Summary
- `GET /api/summary` - Get inbox summary and statistics

#### Contacts
- `GET /api/contacts` - List contacts
- `GET /api/contacts/{id}` - Get contact details
- `GET /api/contacts/{id}/summary` - Get contact summary

#### Health
- `GET /api/health` - Health check endpoint
- `GET /health` - Simple health check

---

## Database Schema

### Core Tables

#### users
- `id` (UUID, PK)
- `email` (VARCHAR)
- `name` (VARCHAR)
- `tier` (VARCHAR) - 'assist' or 'pro'
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### messages
- `id` (UUID, PK)
- `thread_id` (VARCHAR)
- `contact_id` (UUID, FK)
- `body` (TEXT)
- `subject` (VARCHAR)
- `folder` (VARCHAR)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### contacts
- `id` (UUID, PK)
- `name` (VARCHAR)
- `email` (VARCHAR)
- `company` (VARCHAR)
- `tags` (JSONB)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### tasks
- `id` (UUID, PK)
- `contact_id` (UUID, FK)
- `thread_id` (VARCHAR)
- `message_id` (UUID)
- `title` (VARCHAR)
- `due_at` (TIMESTAMPTZ)
- `status` (VARCHAR) - 'pending', 'completed', 'cancelled'
- `reminder_enabled` (BOOLEAN)
- `reminder_minutes_before` (INTEGER)
- `reminder_sent` (BOOLEAN)
- `reminder_sent_at` (TIMESTAMPTZ)
- `postponed_until` (TIMESTAMPTZ)
- `cancelled_at` (TIMESTAMPTZ)
- `cancelled_reason` (TEXT)
- `completed_at` (TIMESTAMPTZ)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### events (Calendar Events)
- `id` (UUID, PK)
- `user_id` (UUID, FK)
- `title` (VARCHAR)
- `description` (TEXT)
- `location` (VARCHAR)
- `video_link` (VARCHAR)
- `start_time` (TIMESTAMPTZ)
- `end_time` (TIMESTAMPTZ)
- `all_day` (BOOLEAN)
- `color` (VARCHAR)
- `timezone` (VARCHAR)
- `recurrence_rule` (TEXT) - iCal RRULE format
- `attendees_json` (JSONB)
- `source` (VARCHAR) - 'local' or 'google'
- `source_event_id` (VARCHAR)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### reminders
- `id` (UUID, PK)
- `user_id` (UUID, FK)
- `event_id` (UUID, FK)
- `minutes_before` (INTEGER)
- `trigger_time` (TIMESTAMPTZ)
- `channel` (VARCHAR) - 'inapp', 'email', 'slack'
- `message` (TEXT)
- `delivered` (BOOLEAN)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### conversations
- `id` (UUID, PK)
- `user_id` (UUID, FK)
- `summary` (TEXT)
- `message_count` (INTEGER)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### events (Audit Log)
- `id` (UUID, PK)
- `type` (VARCHAR)
- `payload` (JSONB)
- `created_at` (TIMESTAMPTZ)

---

## Frontend Features

### 1. User Interface
- **Glass Morphism Design**: Modern glassmorphic UI with backdrop blur
- **Dark Mode Support**: Full dark mode compatibility
- **Responsive Design**: Mobile, tablet, and desktop layouts
- **Smooth Animations**: Framer Motion animations throughout
- **Accessible**: WCAG 2.1 AA compliant

### 2. Main Dashboard
- **Welcome Header**: Personalized greeting based on time of day
- **Summary Cards**: Total messages, unread, leads, complaints
- **Task Overview**: Priority-filtered task lists (P0, P1, P2)
- **Task Reminders**: Upcoming reminders with time remaining
- **Top Leads**: List of top leads with contact information
- **AI Summary**: Auto-generated inbox summary paragraph
- **Quick Actions**: Quick links to inbox, tasks, follow-ups

### 3. Tasks Page
- **Task List**: Scrollable list of all tasks
- **Task Cards**: Glass cards with task details
- **Action Buttons**: Complete, postpone, cancel actions
- **Status Badges**: Visual status indicators
- **Priority Badges**: P0/P1/P2 priority indicators
- **Contact Links**: Links to related contacts/threads

### 4. Calendar Page
- **Month View**: Full calendar grid
- **Today's Events**: Sidebar with today's events
- **Event Creation**: Click date to create event
- **Event Editing**: Click event to edit
- **Event Colors**: Color-coded events
- **Google Import**: Import events from Google Calendar

### 5. Chat Interface
- **Floating Bubble**: Always-accessible chat button
- **Chat Window**: Expandable chat window
- **Message History**: Scrollable message history
- **SSE Streaming**: Real-time token streaming
- **Citation Display**: Expandable source citations
- **Action Suggestions**: Visual action suggestion cards
- **Tier Badges**: Display current tier (Assist/Pro)

### 6. Thread/Message View
- **Thread Display**: Full conversation thread
- **Contact Info**: Contact details sidebar
- **Related Tasks**: Tasks related to thread
- **Reply Generation**: AI-generated reply suggestions
- **Quick Actions**: Send, edit, regenerate options

---

## Integrations

### 1. LLM Providers
- **OpenAI**: GPT-4o-mini, GPT-4o
- **Google Gemini**: Gemini 1.5 Flash
- **Fallback Support**: Automatic fallback on failure

### 2. Calendar Providers
- **Google Calendar**: OAuth 2.0 integration
- **Microsoft Outlook**: OAuth 2.0 integration
- **Local Calendar**: Built-in calendar system

### 3. Notification Providers
- **SMTP**: Email notifications via SMTP
- **Slack**: Webhook-based Slack notifications
- **In-App**: Real-time in-app notifications

### 4. Vector Store
- **ChromaDB**: Primary vector store (optional)
- **JSON Fallback**: File-based vector store for offline use

---

## Technical Features

### 1. Caching
- **Summary Cache**: Cached inbox summaries with TTL
- **Contact Summary Cache**: Cached contact summaries
- **Badge Cache**: Cached priority badges
- **Auto-Invalidation**: Automatic cache invalidation on updates

### 2. Background Processing
- **Task Inference**: Background task inference from messages
- **Summary Generation**: Background summary generation
- **Reminder Scheduling**: APScheduler for reminder jobs
- **Cleanup Tasks**: Automatic cleanup of old data

### 3. Error Handling
- **Custom Error Classes**: Structured error handling
- **Graceful Degradation**: Fallbacks on failures
- **Error Logging**: Structured JSON logging
- **User-Friendly Messages**: Clear error messages

### 4. Security
- **RBAC**: Role-based access control
- **Tier Gating**: Backend-enforced tier restrictions
- **OAuth 2.0**: Secure calendar integrations
- **Environment Variables**: Secrets via environment variables

### 5. Performance
- **Database Indexing**: Optimized database queries
- **Connection Pooling**: Async database connection pooling
- **Lazy Loading**: Lazy-loaded components
- **Code Splitting**: Next.js automatic code splitting

---

## Development Features

### 1. Testing
- **Unit Tests**: Pytest-based unit tests
- **Integration Tests**: End-to-end integration tests
- **UI Tests**: Playwright-based UI tests
- **Mock Support**: Mocked external integrations

### 2. Database Migrations
- **SQL Migrations**: Versioned SQL migration files
- **Idempotent**: Safe to run multiple times
- **Rollback Support**: Migration rollback capability

### 3. Logging
- **Structured Logging**: JSON-formatted logs
- **Correlation IDs**: Request correlation tracking
- **Event Logging**: Audit trail of all actions

### 4. Configuration
- **Environment Variables**: All config via .env
- **Feature Flags**: Feature flag support
- **Model Configuration**: Configurable LLM models

---

## Future Enhancements

### Planned Features
- **Multi-User Support**: Full multi-tenant support
- **Advanced Workflows**: Complex multi-step workflows
- **Behavioral Memory**: Long-term behavioral memory
- **Analytics Dashboard**: Usage analytics and insights
- **Mobile App**: Native mobile applications
- **Webhooks**: Outgoing webhook support
- **API Keys**: API key management for integrations

---

## Getting Started

See [README.md](README.md) for installation and setup instructions.

---

## Support

For issues, questions, or contributions, please refer to the repository's issue tracker.

---

**Last Updated**: December 2024
**Version**: 1.0.0

