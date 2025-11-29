/**
 * Floating Chatbox Component
 * AI assistant that can answer questions about inbox, policies, and tasks
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import AiThinkingDots from './AiThinkingDots';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function FloatingChatbox() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hi! I'm Soraya AI. I can help you with questions about your inbox, tasks, policies, and more. What would you like to know?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const lastActivityRef = useRef<Date>(new Date());
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Initialize session ID on mount
  useEffect(() => {
    if (!sessionIdRef.current) {
      sessionIdRef.current = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
  }, []);

  // Initialize inactivity timer on mount
  useEffect(() => {
    const resetInactivityTimer = () => {
      lastActivityRef.current = new Date();
      
      // Clear existing timer
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
      
      // Set new timer for 1 hour (3600000 ms)
      inactivityTimerRef.current = setTimeout(() => {
        // Reset conversation after 1 hour of inactivity
        setMessages([
          {
            role: 'assistant',
            content: "Hi! I'm Soraya AI. I can help you with questions about your inbox, tasks, policies, and more. What would you like to know?",
            timestamp: new Date(),
          },
        ]);
        // Generate new session ID
        sessionIdRef.current = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        console.log('[Chat] Context cleared after 1 hour of inactivity');
      }, 3600000); // 1 hour
    };

    // Initialize timer
    resetInactivityTimer();

    // Cleanup on unmount
    return () => {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
    };
  }, []); // Only run on mount

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    // Reset inactivity timer on user activity
    lastActivityRef.current = new Date();
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }
    inactivityTimerRef.current = setTimeout(() => {
      setMessages([
        {
          role: 'assistant',
          content: "Hi! I'm Soraya AI. I can help you with questions about your inbox, tasks, policies, and more. What would you like to know?",
          timestamp: new Date(),
        },
      ]);
      sessionIdRef.current = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      console.log('[Chat] Context cleared after 1 hour of inactivity');
    }, 3600000);

    try {
      // Prepare conversation history (last 10 messages for context)
      const conversationHistory = messages
        .slice(-10) // Last 10 messages for context
        .map((msg) => ({
          role: msg.role,
          content: msg.content,
        }));

      // Use Next.js API rewrite (routes to backend on port 3001)
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: userMessage.content,
          conversationHistory,
          sessionId: sessionIdRef.current,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
        throw new Error(errorData.error || errorData.details || 'Failed to get response');
      }

      const data = await response.json();
      
      if (!data.answer) {
        throw new Error('No answer received from server');
      }

      // Update session ID if provided by backend
      if (data.sessionId && data.sessionId !== sessionIdRef.current) {
        sessionIdRef.current = data.sessionId;
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.answer,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // If a calendar event was created, show a success notification and refresh calendar if on calendar page
      if (data.calendarEvent) {
        const event = data.calendarEvent;
        // Trigger a custom event that the calendar page can listen to
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('calendarEventCreated', { detail: event }));
        }
      }
    } catch (error: any) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message || 'Please check if the backend is running and try again.'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* Floating Button */}
      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-[var(--primary)] text-white rounded-full shadow-lg hover:shadow-xl transition-shadow z-50 flex items-center justify-center"
        aria-label="Open chat"
      >
        {isOpen ? (
          <span className="text-2xl">✕</span>
        ) : (
          <span className="text-2xl">💬</span>
        )}
      </motion.button>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-6 w-96 h-[600px] glass-card shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="p-4 border-b border-[var(--glass-border)] bg-white/80 backdrop-blur-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[var(--primary)] flex items-center justify-center text-white font-semibold">
                  S
                </div>
                <div>
                  <h3 className="font-semibold text-theme-primary">Soraya AI</h3>
                  <p className="text-xs text-theme-muted">Ask me anything</p>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl p-3 ${
                      msg.role === 'user'
                        ? 'bg-[var(--primary)] text-white'
                        : 'bg-white/60 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] text-theme-primary'
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{msg.content}</p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white/60 border border-[var(--glass-border)] rounded-2xl p-3">
                    <AiThinkingDots message="Thinking..." size="sm" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-[var(--glass-border)] bg-white/80 backdrop-blur-sm">
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about inbox, tasks, policies..."
                  className="flex-1 px-4 py-2 bg-white/80 border border-[var(--glass-border)] rounded-xl focus:outline-none focus:ring-2 focus:ring-[var(--primary)] text-sm"
                  disabled={isLoading}
                />
                <button
                  onClick={sendMessage}
                  disabled={isLoading || !input.trim()}
                  className="px-4 py-2 bg-[var(--primary)] text-white rounded-xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
                  aria-label="Send message"
                >
                  →
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

