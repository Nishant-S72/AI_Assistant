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
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  is_recurring: boolean;
  recurrence_pattern?: 'daily' | 'weekly' | 'monthly' | 'yearly';
  recurrence_end_date?: string;
  recurrence_interval?: number;
  location?: string;
  attendees?: string[];
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
  kind: 'assistant' | 'policy' | 'action';
  text: string;
  citations?: Citation[];
  suggestionId: string | null;
  intent: 'policy_intent' | 'action_intent' | 'general_intent';
  intent_confidence: number;
  action_suggestion?: {
    action_type: string;
    confirm_needed: boolean;
    extracted_data?: any;
  };
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
