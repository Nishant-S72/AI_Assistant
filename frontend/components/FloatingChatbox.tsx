/**
 * Floating Chatbox Component with RAG
 * AI assistant with policy document retrieval and citations
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { chat, ChatResponse, Citation } from '@/lib/api';
import AiThinkingDots from './AiThinkingDots';
import { BookOpen, AlertTriangle } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  citations?: Citation[];
  suggestionId?: string | null;
  escalated?: boolean;
  escalationReasons?: string[];
  intent?: 'policy_intent' | 'action_intent' | 'general_intent';
  action_suggestion?: {
    action_type: string;
    confirm_needed: boolean;
    extracted_data?: any;
  };
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
  const [tone, setTone] = useState<'formal' | 'warm' | 'crisp'>('warm');
  const [showSources, setShowSources] = useState<number | null>(null);
  const [escalated, setEscalated] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const lastActivityRef = useRef<Date>(new Date());
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);
  const threadIdRef = useRef<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, showSources]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Initialize thread ID on mount
  useEffect(() => {
    if (!threadIdRef.current) {
      threadIdRef.current = `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
  }, []);

  // Initialize inactivity timer
  useEffect(() => {
    const resetInactivityTimer = () => {
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
        threadIdRef.current = `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        setEscalated(false);
        console.log('[Chat] Context cleared after 1 hour of inactivity');
      }, 3600000);
    };

    resetInactivityTimer();

    return () => {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
    };
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || isLoading || escalated) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    // Reset inactivity timer
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
      threadIdRef.current = `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setEscalated(false);
      console.log('[Chat] Context cleared after 1 hour of inactivity');
    }, 3600000);

    try {
      const response = await chat.sendMessage({
        threadId: threadIdRef.current || undefined,
        userMessage: userMessage.content,
        tone,
      });

      // Check for escalation
      if (response.escalated) {
        setEscalated(true);
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.text,
        timestamp: new Date(),
        citations: response.citations,
        suggestionId: response.suggestionId,
        escalated: response.escalated,
        intent: response.intent,
        action_suggestion: response.action_suggestion,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Send feedback automatically (accepted)
      if (response.suggestionId) {
        try {
          await chat.sendFeedback({
            suggestionId: response.suggestionId,
            accepted: true,
          });
        } catch (e) {
          console.warn('Failed to send feedback:', e);
        }
      }
      
      // Handle action confirmations
      if (response.action_suggestion?.confirm_needed && response.action_suggestion.extracted_data) {
        // Could show confirmation buttons here
        console.log('[Chat] Action requires confirmation:', response.action_suggestion);
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

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
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
              <div className="flex items-center justify-between mb-3">
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
              
              {/* Controls */}
              <div className="flex items-center gap-3 text-xs">
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value as 'formal' | 'warm' | 'crisp')}
                  className="text-xs px-2 py-1 bg-white/80 border border-[var(--glass-border)] rounded"
                >
                  <option value="formal">Formal</option>
                  <option value="warm">Warm</option>
                  <option value="crisp">Crisp</option>
                </select>
              </div>
            </div>

            {/* Escalation Banner */}
            {escalated && (
              <div className="px-4 py-2 bg-red-100 border-b border-red-300 text-red-800 text-sm">
                <p className="font-semibold">⚠️ Requires Human Review</p>
                <p className="text-xs mt-1">This request has been escalated. Agentic actions are disabled.</p>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[80%] rounded-2xl p-3 ${
                      msg.role === 'user'
                        ? 'bg-[var(--primary)] text-white'
                        : 'bg-white/60 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] text-theme-primary'
                    }`}
                  >
                    {/* Policy Badge */}
                    {msg.intent === 'policy_intent' && (
                      <div className="mb-2 flex items-center gap-1.5 text-xs text-blue-600">
                        <BookOpen className="w-3 h-3" />
                        <span className="font-medium">Policy-backed answer</span>
                      </div>
                    )}
                    
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    
                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-300/30">
                        <button
                          onClick={() => setShowSources(showSources === idx ? null : idx)}
                          className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <BookOpen className="w-3 h-3" />
                          {showSources === idx ? 'Hide' : 'Show'} sources ({msg.citations.length})
                        </button>
                        {showSources === idx && (
                          <div className="mt-2 space-y-1 text-xs">
                            {msg.citations.map((citation, cIdx) => (
                              <div key={cIdx} className="text-gray-600">
                                <span className="font-semibold">§{cIdx + 1}</span> (Score: {citation.score.toFixed(2)})
                                <p className="text-gray-500 mt-0.5">{citation.textSnippet}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Action Confirmation */}
                    {msg.action_suggestion?.confirm_needed && (
                      <div className="mt-2 pt-2 border-t border-gray-300/30">
                        <p className="text-xs text-gray-600 mb-2">Action requires confirmation:</p>
                        <div className="flex gap-2">
                          <button className="text-xs px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600">
                            Confirm
                          </button>
                          <button className="text-xs px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
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
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about inbox, tasks, policies... (Shift+Enter for newline)"
                  className="flex-1 px-4 py-2 bg-white/80 border border-[var(--glass-border)] rounded-xl focus:outline-none focus:ring-2 focus:ring-[var(--primary)] text-sm resize-none min-h-[40px] max-h-[100px]"
                  disabled={isLoading || escalated}
                  rows={1}
                />
                <button
                  onClick={sendMessage}
                  disabled={isLoading || !input.trim() || escalated}
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
