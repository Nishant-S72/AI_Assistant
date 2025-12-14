/**
 * API client for backend endpoints
 * Uses native fetch with error handling and type safety
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

interface ApiError {
  error: string;
  details?: string;
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  try {
    // Add longer timeout for slow endpoints (contact summary takes ~30-60 seconds)
    const timeout = endpoint.includes('/summary') ? 120000 : 60000; // 120s for summaries, 60s for others
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        error: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(error.error || error.details || 'Request failed');
    }

    return response.json();
  } catch (error: any) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out - the summary is taking longer than expected. Please try again.');
    }
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Network error: Could not connect to backend');
  }
}

// Types
export interface Message {
  id: string;
  thread_id: string;
  sender: 'contact' | 'assistant';
  body: string;
  channel: string;
  created_at: string;
  contact_name: string;
  contact_company?: string;
  contact_email: string;
  message_count: number;
}

export interface ThreadMessage {
  id: string;
  sender: 'contact' | 'assistant';
  body: string;
  created_at: string;
}

export interface Contact {
  id: string;
  name: string;
  email: string;
  phone?: string;
  company?: string;
  tags: string[];
  tone_pref: string;
  message_count?: number;
  pending_tasks?: number;
  last_message_at?: string;
}

export interface ContactMessage {
  id: string;
  thread_id: string;
  sender: 'contact' | 'assistant';
  body: string;
  channel: string;
  created_at: string;
  processed: boolean;
}

export interface ConversationSummary {
  thread_id: string;
  summary: string;
  message_count: number;
  last_date?: string;
}

export interface ContactSummary {
  summary: string;
  recommendations?: string[];
  recentConversations?: ConversationSummary[];
  messageCount: number;
  taskStats: {
    total: number;
    pending: number;
    completed: number;
  };
}

export interface Suggestion {
  id: string;
  message_id: string;
  prompt: string;
  retrieved_ids: string[];
  model_response: string;
  final_text: string;
  edited: boolean;
  edit_diff?: string;
  created_at: string;
}

export interface ThreadData {
  message: Message;
  thread: ThreadMessage[];
  suggestion: Suggestion | null;
  contact: Contact;
}

export interface Task {
  id: string;
  contact_id?: string;
  title: string;
  due_at?: string;
  status: string;
  created_at: string;
  contact_name?: string;
  contact_email?: string;
  priority?: 'P0' | 'P1' | 'P2';
  message_id?: string;
  thread_id?: string;
  reminder_enabled?: boolean;
  reminder_minutes_before?: number;
  reminder_sent?: boolean;
  reminder_sent_at?: string;
  postponed_until?: string;
  cancelled_at?: string;
  cancelled_reason?: string;
  completed_at?: string;
  time_until_due?: {
    days: number;
    hours: number;
    minutes: number;
  };
}

export interface HealthLocal {
  llm?: string;
  model?: string;
  status?: string;
  database?: string;
  vectorstore?: {
    status: string;
    count_chunks?: number;
  };
}

export interface CalendarEvent {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  location?: string;
  video_link?: string;
  start: string;  // ISO 8601
  end: string;  // ISO 8601
  all_day: boolean;
  color: string;
  timezone: string;
  recurrence_rule?: string;  // RRULE format
  attendees: Array<{ email: string; name?: string; status?: string }>;
  source: 'local' | 'google';
  source_event_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Reminder {
  id: string;
  user_id: string;
  event_id?: string;
  minutes_before?: number;
  when?: string;  // ISO 8601
  channel: 'inapp' | 'email' | 'slack';
  repeat_rule?: string;
  delivered: boolean;
  created_at: string;
  updated_at: string;
}

// API functions
export const api = {
  // Seed demo data
  seedDemo: async (token?: string): Promise<{ success: boolean; message: string }> => {
    return fetchApi('/api/seed/demo', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  },

  // Messages
  getMessages: async (folder?: string): Promise<Message[]> => {
    const params = folder ? `?folder=${folder}` : '';
    try {
      return await fetchApi<Message[]>(`/api/messages${params}`);
    } catch (error: any) {
      // Fallback to demo threads if DB unavailable
      if (error.message.includes('404') || error.message.includes('Network')) {
        try {
          return await fetchApi<Message[]>('/api/demo/threads');
        } catch {
          return [];
        }
      }
      throw error;
    }
  },

  getMessage: async (id: string): Promise<ThreadData> => {
    return fetchApi<ThreadData>(`/api/messages/${id}`);
  },

  generateSuggestion: async (
    id: string,
    tone: 'formal' | 'warm' | 'crisp' = 'warm'
  ): Promise<{ suggestion: Suggestion; policyCheck: { action: string; reasons: string[] } }> => {
    return fetchApi(`/api/messages/${id}/generate`, {
      method: 'POST',
      body: JSON.stringify({ tone }),
    });
  },

  sendMessage: async (
    id: string,
    text: string,
    suggestionId?: string
  ): Promise<{ success: boolean; message: any; simulated?: boolean }> => {
    return fetchApi(`/api/messages/${id}/send`, {
      method: 'POST',
      body: JSON.stringify({ text, suggestionId }),
    });
  },

  // Suggestions
  submitFeedback: async (
    id: string,
    accepted: boolean,
    editedText?: string
  ): Promise<{ success: boolean }> => {
    return fetchApi(`/api/suggestions/${id}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ accepted, editedText }),
    });
  },

  // Contacts
  getContacts: async (search?: string, tag?: string): Promise<Contact[]> => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (tag) params.append('tag', tag);
    const queryString = params.toString();
    return fetchApi<Contact[]>(`/api/contacts${queryString ? `?${queryString}` : ''}`);
  },

  getContact: async (id: string): Promise<Contact> => {
    return fetchApi<Contact>(`/api/contacts/${id}`);
  },

  getContactMessages: async (id: string, limit = 50, offset = 0): Promise<ContactMessage[]> => {
    return fetchApi<ContactMessage[]>(`/api/contacts/${id}/messages?limit=${limit}&offset=${offset}`);
  },

  getContactSummary: async (id: string): Promise<ContactSummary> => {
    return fetchApi<ContactSummary>(`/api/contacts/${id}/summary`);
  },

  // Tasks
  tasks: {
    getTasks: async (status?: string): Promise<Task[]> => {
      const params = status ? `?status=${status}` : '';
      return fetchApi<Task[]>(`/api/tasks${params}`);
    },
    createTask: async (task: Partial<Task>): Promise<Task> => {
      return fetchApi<Task>('/api/tasks', {
        method: 'POST',
        body: JSON.stringify(task),
      });
    },
    getReminders: async (): Promise<Task[]> => {
      return fetchApi<Task[]>('/api/tasks/reminders');
    },
    completeTask: async (taskId: string): Promise<Task> => {
      return fetchApi<Task>(`/api/tasks/${taskId}/complete`, {
        method: 'PATCH',
      });
    },
    cancelTask: async (taskId: string, reason?: string): Promise<Task> => {
      return fetchApi<Task>(`/api/tasks/${taskId}/cancel`, {
        method: 'PATCH',
        body: JSON.stringify({ reason }),
      });
    },
    postponeTask: async (taskId: string, newDueDate: string): Promise<Task> => {
      return fetchApi<Task>(`/api/tasks/${taskId}/postpone`, {
        method: 'PATCH',
        body: JSON.stringify({ new_due_date: newDueDate }),
      });
    },
  },

  // Health
  getHealthLocal: async (): Promise<HealthLocal> => {
    return fetchApi<HealthLocal>('/api/health');
  },

  // Calendar
  getCalendarEvents: async (start: string, end: string): Promise<CalendarEvent[]> => {
    try {
      const response = await fetchApi<{ events?: CalendarEvent[] } | CalendarEvent[]>(
        `/api/calendar/events?start=${start}&end=${end}`
      );
      // Handle both response formats: { events: [...] } or [...]
      if (Array.isArray(response)) {
        return response;
      } else if (response && typeof response === 'object' && 'events' in response) {
        return Array.isArray(response.events) ? response.events : [];
      }
      return [];
    } catch (error) {
      console.error('[API] Error fetching calendar events:', error);
      return [];
    }
  },

  createCalendarEvent: async (event: Partial<CalendarEvent>): Promise<CalendarEvent> => {
    return fetchApi<CalendarEvent>('/api/calendar/events', {
      method: 'POST',
      body: JSON.stringify(event),
    });
  },

  parseCalendarEvent: async (text: string): Promise<{ event: CalendarEvent; parsed: any }> => {
    return fetchApi<{ event: CalendarEvent; parsed: any }>('/api/calendar/parse', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },

  updateCalendarEvent: async (id: string, updates: Partial<CalendarEvent>): Promise<CalendarEvent> => {
    return fetchApi<CalendarEvent>(`/api/calendar/events/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  },

  deleteCalendarEvent: async (id: string): Promise<void> => {
    return fetchApi(`/api/calendar/events/${id}`, {
      method: 'DELETE',
    });
  },

  // New Scheduler API (replaces old calendar API)
  scheduler: {
    // Chat with scheduler assistant
    chat: async (messages: Array<{ role: string; content: string }>, conversationId?: string): Promise<{ response: string; function_call?: any }> => {
      return fetchApi('/api/v1/scheduler/chat', {
        method: 'POST',
        body: JSON.stringify({ messages, conversation_id: conversationId }),
      });
    },

    // Parse natural language scheduling request
    parseSchedule: async (naturalLanguage: string): Promise<any> => {
      return fetchApi('/api/v1/scheduler/parse', {
        method: 'POST',
        body: JSON.stringify({ natural_language: naturalLanguage }),
      });
    },

    // Create event
    createEvent: async (event: {
      title: string;
      start_time: string;
      end_time: string;
      calendar_provider?: string;
      attendees?: string[];
      location?: string;
      description?: string;
      timezone?: string;
      recurrence_rule?: string;
    }): Promise<any> => {
      return fetchApi('/api/v1/scheduler/create_event', {
        method: 'POST',
        body: JSON.stringify(event),
      });
    },

    // Find availability
    findAvailability: async (startDate: string, endDate: string, durationMinutes?: number, calendarProvider?: string): Promise<any> => {
      return fetchApi('/api/v1/scheduler/find_availability', {
        method: 'POST',
        body: JSON.stringify({
          start_date: startDate,
          end_date: endDate,
          duration_minutes: durationMinutes || 60,
          calendar_provider: calendarProvider || 'google',
        }),
      });
    },

    // List events (from event_mirror)
    listEvents: async (startDate?: string, endDate?: string): Promise<{ events: any[] }> => {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      const queryString = params.toString();
      return fetchApi(`/api/v1/scheduler/events${queryString ? `?${queryString}` : ''}`);
    },

    // Reschedule event
    rescheduleEvent: async (eventId: string, newStartTime: string, newEndTime: string): Promise<any> => {
      return fetchApi(`/api/v1/scheduler/reschedule/${eventId}`, {
        method: 'POST',
        body: JSON.stringify({
          new_start_time: newStartTime,
          new_end_time: newEndTime,
        }),
      });
    },

    // Cancel event
    cancelEvent: async (eventId: string): Promise<any> => {
      return fetchApi(`/api/v1/scheduler/cancel_event/${eventId}`, {
        method: 'POST',
      });
    },

    // OAuth - Google
    connectGoogle: async (redirectUri: string): Promise<{ oauth_url: string; state: string }> => {
      return fetchApi(`/api/v1/scheduler/connect/google?redirect_uri=${encodeURIComponent(redirectUri)}`, {
        method: 'POST',
      });
    },

    // OAuth - Outlook
    connectOutlook: async (redirectUri: string): Promise<{ oauth_url: string; state: string }> => {
      return fetchApi(`/api/v1/scheduler/connect/outlook?redirect_uri=${encodeURIComponent(redirectUri)}`, {
        method: 'POST',
      });
    },
  },

  // Calendar API (v1 - standalone events and reminders)
  calendar: {
    // List events
    listEvents: async (start: string, end: string, source?: 'local' | 'google'): Promise<{ events: CalendarEvent[] }> => {
      const params = new URLSearchParams();
      params.append('start', start);
      params.append('end', end);
      if (source) params.append('source', source);
      return fetchApi(`/api/v1/calendar/events?${params.toString()}`);
    },

    // Create event
    createEvent: async (event: {
      title: string;
      description?: string;
      location?: string;
      video_link?: string;
      start: string;
      end: string;
      all_day?: boolean;
      color?: string;
      timezone?: string;
      recurrence_rule?: string;
      attendees?: Array<{ email: string; name?: string; status?: string }>;
      sync_to_google?: boolean;
    }): Promise<CalendarEvent> => {
      return fetchApi('/api/v1/calendar/events', {
        method: 'POST',
        body: JSON.stringify(event),
      });
    },

    // Update event
    updateEvent: async (eventId: string, updates: {
      title?: string;
      description?: string;
      location?: string;
      video_link?: string;
      start?: string;
      end?: string;
      all_day?: boolean;
      color?: string;
      timezone?: string;
      recurrence_rule?: string;
      attendees?: Array<{ email: string; name?: string; status?: string }>;
      sync_to_google?: boolean;
    }): Promise<CalendarEvent> => {
      return fetchApi(`/api/v1/calendar/events/${eventId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      });
    },

    // Delete event
    deleteEvent: async (eventId: string, syncToGoogle?: boolean): Promise<{ success: boolean }> => {
      const params = new URLSearchParams();
      if (syncToGoogle) params.append('sync_to_google', 'true');
      return fetchApi(`/api/v1/calendar/events/${eventId}?${params.toString()}`, {
        method: 'DELETE',
      });
    },

    // Create reminder
    createReminder: async (eventId: string, reminder: {
      minutes_before?: number;
      when?: string;
      channel?: 'inapp' | 'email' | 'slack';
      repeat_rule?: string;
    }): Promise<Reminder> => {
      return fetchApi(`/api/v1/calendar/events/${eventId}/reminders`, {
        method: 'POST',
        body: JSON.stringify(reminder),
      });
    },

    // List reminders
    listReminders: async (eventId?: string): Promise<{ reminders: Reminder[] }> => {
      const params = new URLSearchParams();
      if (eventId) params.append('event_id', eventId);
      return fetchApi(`/api/v1/calendar/reminders?${params.toString()}`);
    },

    // Import from Google
    importGoogle: async (start: string, end: string): Promise<{
      success: boolean;
      imported: number;
      updated: number;
      skipped: number;
      total: number;
    }> => {
      const params = new URLSearchParams();
      params.append('start', start);
      params.append('end', end);
      return fetchApi(`/api/v1/calendar/import/google?${params.toString()}`, {
        method: 'POST',
      });
    },
  },
};

export interface SummaryResponse {
  totals: {
    totalMessages: number;
    unread: number;
    leads: number;
    complaints: number;
    urgent?: number;
    highPriority?: number;
  };
  tasks: {
    counts: { P0: number; P1: number; P2: number };
    P0: Task[];
    P1: Task[];
    P2: Task[];
  };
  topLeads: Array<{
    id: string;
    name: string;
    company?: string;
    email?: string;
    message_count?: number;
  }>;
  performance?: {
    avgLatencyMs: number | null;
    suggestionsGenerated: number;
    acceptanceRate: number;
    messagesSent: number;
  };
  urgentContext?: {
    contactName: string;
    taskTitle: string;
    messageBody: string;
  } | null;
  summaryParagraph?: string | null;
  summaryGenerating?: boolean;
  simulated?: boolean;
}

// Export getSummary function
export async function getSummary(): Promise<SummaryResponse> {
  return fetchApi<SummaryResponse>('/api/summary');
}

// Chat API (Intent-Based)
export interface ChatRequest {
  threadId?: string;
  userMessage: string;
  tone?: 'formal' | 'warm' | 'crisp';
  correlationId?: string;
}

export interface Citation {
  id: string;
  score: number;
  textSnippet: string;
}

export interface ChatResponse {
  kind: 'assistant' | 'policy' | 'action' | 'suggestion' | 'action_planned' | 'action_executed';
  text: string;
  citations?: Citation[];
  suggestionId: string | null;
  intent: 'policy_intent' | 'action_intent' | 'general_intent' | 'general' | 'rag' | 'action_candidate';
  intent_confidence: number;
  action_plan?: {
    action_type: string;
    parameters: any;
    confidence: number;
    missing_fields: string[];
  };
  action_execution?: {
    executed: boolean;
    result?: any;
    error?: string;
    reason?: string;
  };
  action_suggestion?: {
    action_type: string;
    confirm_needed: boolean;
    extracted_data?: any;
  };
  action_result?: {
    success: boolean;
    eventId?: string;
    event?: any;
  };
  tier?: 'assist' | 'pro';
  escalated?: boolean;
}

export interface ChatFeedbackRequest {
  suggestionId: string;
  accepted: boolean;
  editedText?: string;
}

export const chat = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    return fetchApi<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  sendFeedback: async (request: ChatFeedbackRequest): Promise<{ success: boolean }> => {
    return fetchApi<{ success: boolean }>('/api/chat/feedback', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
};

// RAG Chat API (Deprecated - kept for backwards compatibility)
export interface RAGChatRequest {
  threadId?: string;
  userMessage: string;
  tone?: 'formal' | 'warm' | 'crisp';
  rag?: boolean;
}

export interface RAGChatResponse {
  reply: string;
  citations: Citation[];
  suggestionId: string | null;
  escalated?: boolean;
  reasons?: string[];
}

export const ragChat = {
  sendMessage: async (request: RAGChatRequest): Promise<RAGChatResponse> => {
    return fetchApi<RAGChatResponse>('/api/chat/rag', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  sendFeedback: async (request: ChatFeedbackRequest): Promise<{ success: boolean }> => {
    return fetchApi<{ success: boolean }>('/api/chat/feedback', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
};

// Policy Document API
export interface PolicyChunk {
  id: string;
  title: string;
  summary: string;
  score: number;
}

export const policyDoc = {
  getChunks: async (): Promise<{ chunks: PolicyChunk[] }> => {
    return fetchApi<{ chunks: PolicyChunk[] }>('/api/policydoc/chunks');
  },
};

// Phase 1 Chat API (v1)
export const chatV1 = {
  chat: async (request: {
    userMessage: string;
    threadId?: string;
    tone?: 'formal' | 'warm' | 'crisp';
    conversationHistory?: Array<{ role: string; content: string }>;
  }): Promise<ChatResponse> => {
    return fetchApi<ChatResponse>('/api/v1/chat', {
      method: 'POST',
      headers: {
        'X-User-ID': 'demo-user', // TODO: Get from auth
      },
      body: JSON.stringify(request),
    });
  },

  executeAction: async (actionPlan: {
    action_type: string;
    parameters: any;
  }): Promise<{ executed: boolean; result?: any; error?: string }> => {
    return fetchApi('/api/v1/chat/execute', {
      method: 'POST',
      headers: {
        'X-User-ID': 'demo-user', // TODO: Get from auth
      },
      body: JSON.stringify(actionPlan),
    });
  },
};
