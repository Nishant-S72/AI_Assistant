/**
 * Contact Detail Page
 * Shows contact details, preferences, interaction summary, and message history
 */

'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, Contact, ContactMessage, ContactSummary } from '@/lib/api';
import GlassCard from '@/components/GlassCard';
import { motion } from 'framer-motion';
import { formatDate } from '@/lib/utils';

export default function ContactDetailPage() {
  const params = useParams();
  const router = useRouter();
  const contactId = params.id as string;

  const [contact, setContact] = useState<Contact | null>(null);
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [summary, setSummary] = useState<ContactSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);

  useEffect(() => {
    if (contactId) {
      loadContactData();
    }
  }, [contactId]);

  const loadContactData = async () => {
    try {
      setLoading(true);
      const [contactData, messagesData] = await Promise.all([
        api.getContact(contactId),
        api.getContactMessages(contactId),
      ]);
      setContact(contactData);
      setMessages(messagesData);
    } catch (error) {
      console.error('Error loading contact data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      setSummaryLoading(true);
      console.log('[Contact Detail] Loading summary for contact:', contactId);
      
      const summaryData = await api.getContactSummary(contactId);
      console.log('[Contact Detail] API Response received:', {
        hasSummary: !!summaryData?.summary,
        summaryLength: summaryData?.summary?.length || 0,
        hasRecommendations: !!summaryData?.recommendations?.length,
        hasConversations: !!summaryData?.recentConversations?.length,
        fullData: summaryData
      });
      
      // Always set the summary data - API returns 200 even on error with error message in summary field
      if (summaryData) {
        setSummary(summaryData);
        console.log('[Contact Detail] Summary set in state');
      } else {
        console.warn('[Contact Detail] Summary returned but is null/undefined');
        setSummary({
          summary: 'No summary data received from API.',
          recommendations: [],
          recentConversations: [],
          messageCount: 0,
          taskStats: { total: 0, pending: 0, completed: 0 },
        });
      }
    } catch (error: any) {
      console.error('[Contact Detail] Error loading summary:', error);
      console.error('[Contact Detail] Error details:', error.message, error.stack);
      // Network errors or API errors - set error state
      setSummary({
        summary: `Network error: ${error.message || 'Could not connect to API'}. Please check backend is running.`,
        recommendations: ['Check backend is running on port 3001', 'Check browser console for details'],
        recentConversations: [],
        messageCount: 0,
        taskStats: { total: 0, pending: 0, completed: 0 },
      });
    } finally {
      setSummaryLoading(false);
      console.log('[Contact Detail] Summary loading complete');
    }
  };

  useEffect(() => {
    if (contact && !summary && !summaryLoading) {
      loadSummary();
    }
  }, [contact]);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const handleCompose = () => {
    // Find the most recent thread or create a new one
    const latestMessage = messages[0];
    if (latestMessage) {
      router.push(`/thread/${latestMessage.id}`);
    } else {
      // Navigate to inbox to start a new conversation
      router.push('/inbox');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-theme-muted font-medium">Loading contact...</div>
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-4xl mb-4">👤</div>
        <div className="text-theme-muted font-medium text-lg mb-4">Contact not found</div>
        <Link
          href="/contacts"
          className="px-4 py-2 rounded-xl bg-[var(--primary)] text-white hover:bg-[var(--primary)]/90 transition-colors"
        >
          Back to Contacts
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
        <div className="flex items-center gap-4 mb-4">
          <Link
            href="/contacts"
            className="text-theme-muted hover:text-theme-primary transition-colors"
          >
            ← Back
          </Link>
          <div className="flex-1" />
          <button
            onClick={handleCompose}
            className="px-4 py-2 rounded-xl bg-[var(--primary)] text-white hover:bg-[var(--primary)]/90 transition-colors font-medium"
          >
            ✉️ Compose
          </button>
        </div>

        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--primary)]/20 to-[var(--accent)]/20 flex items-center justify-center text-[var(--primary)] font-semibold text-2xl">
            {getInitials(contact.name)}
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold text-theme-primary heading-premium mb-2">
              {contact.name}
            </h1>
            <div className="space-y-1">
              <p className="text-theme-secondary">{contact.email}</p>
              {contact.phone && <p className="text-theme-muted">{contact.phone}</p>}
              {contact.company && <p className="text-theme-muted">{contact.company}</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Details & Summary */}
          <div className="lg:col-span-2 space-y-6">
            {/* Contact Details */}
            <GlassCard className="p-6">
              <h2 className="text-xl font-semibold text-theme-primary mb-4 heading-premium">
                Contact Details
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-theme-muted">Email</label>
                  <p className="text-theme-primary">{contact.email}</p>
                </div>
                {contact.phone && (
                  <div>
                    <label className="text-sm font-medium text-theme-muted">Phone</label>
                    <p className="text-theme-primary">{contact.phone}</p>
                  </div>
                )}
                {contact.company && (
                  <div>
                    <label className="text-sm font-medium text-theme-muted">Company</label>
                    <p className="text-theme-primary">{contact.company}</p>
                  </div>
                )}
                <div>
                  <label className="text-sm font-medium text-theme-muted">Tone Preference</label>
                  <p className="text-theme-primary capitalize">{contact.tone_pref || 'warm'}</p>
                </div>
                {contact.tags && contact.tags.length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-theme-muted mb-2 block">Tags</label>
                    <div className="flex flex-wrap gap-2">
                      {contact.tags.map((tag, i) => (
                        <span
                          key={i}
                          className="px-3 py-1 text-sm rounded-full bg-[var(--primary)]/10 text-[var(--primary)] border border-[var(--primary)]/20"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </GlassCard>

            {/* Interaction Summary */}
            <GlassCard className="p-6">
              <h2 className="text-xl font-semibold text-theme-primary mb-4 heading-premium">
                Interaction Summary
              </h2>
              {summaryLoading ? (
                <div className="flex items-center gap-3 text-theme-muted">
                  <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-[var(--primary)]"></div>
                  <span className="text-sm font-medium">Loading summary...</span>
                </div>
              ) : summary && summary.summary ? (
                <div className="space-y-6">
                  {/* Summary Text */}
                  <div className="prose prose-sm max-w-none">
                    {summary.summary?.includes('Error') || summary.summary?.includes('Unable to generate') ? (
                      <div className="p-4 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
                        <p className="text-yellow-800 dark:text-yellow-200 leading-relaxed whitespace-pre-wrap mb-3">
                          {summary.summary}
                        </p>
                        {summary.recommendations && summary.recommendations.length > 0 && (
                          <div className="mt-3 space-y-1">
                            <p className="text-sm font-semibold text-yellow-900 dark:text-yellow-100 mb-2">To fix this:</p>
                            {summary.recommendations.map((rec, idx) => (
                              <code key={idx} className="block p-2 bg-white dark:bg-gray-800 rounded text-xs text-yellow-900 dark:text-yellow-100">
                                {rec}
                              </code>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-theme-secondary leading-relaxed whitespace-pre-wrap">
                        {summary.summary}
                      </p>
                    )}
                  </div>

                  {/* Debug info in development */}
                  {process.env.NODE_ENV === 'development' && (
                    <div className="mt-4 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs text-gray-600 dark:text-gray-400">
                      <strong>Debug:</strong> Summary length: {summary.summary?.length || 0} chars | 
                      Recommendations: {summary.recommendations?.length || 0} | 
                      Conversations: {summary.recentConversations?.length || 0}
                    </div>
                  )}

                  {/* Recent Conversations */}
                  {summary.recentConversations && summary.recentConversations.length > 0 && (
                    <div className="pt-4 border-t border-[var(--glass-border)]">
                      <h3 className="text-lg font-semibold text-theme-primary mb-3 heading-premium">
                        Last 3 Conversations
                      </h3>
                      <div className="space-y-4">
                        {summary.recentConversations.map((conv, index) => (
                          <div key={conv.thread_id} className="p-4 rounded-lg bg-white/40 dark:bg-[var(--card-bg)] border border-[var(--glass-border)]">
                            <div className="flex items-start justify-between mb-2">
                              <span className="text-sm font-semibold text-[var(--primary)]">
                                Conversation {index + 1}
                              </span>
                              {conv.last_date && (
                                <span className="text-xs text-theme-muted">
                                  {formatDate(conv.last_date)}
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-theme-secondary leading-relaxed mb-2">
                              {conv.summary}
                            </p>
                            <span className="text-xs text-theme-muted">
                              {conv.message_count} message{conv.message_count !== 1 ? 's' : ''}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recommendations */}
                  {summary.recommendations && summary.recommendations.length > 0 && (
                    <div className="pt-4 border-t border-[var(--glass-border)]">
                      <h3 className="text-lg font-semibold text-theme-primary mb-3 heading-premium">
                        Recommendations
                      </h3>
                      <ul className="space-y-3">
                        {summary.recommendations.map((rec, index) => (
                          <li key={index} className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] flex items-center justify-center text-sm font-semibold mt-0.5">
                              {index + 1}
                            </span>
                            <span className="text-theme-secondary leading-relaxed flex-1">
                              {rec}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Stats */}
                  <div className="flex items-center gap-6 pt-4 border-t border-[var(--glass-border)]">
                    <div>
                      <span className="text-sm font-medium text-theme-muted">Messages</span>
                      <p className="text-lg font-semibold text-theme-primary">
                        {summary.messageCount}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-theme-muted">Tasks</span>
                      <p className="text-lg font-semibold text-theme-primary">
                        {summary.taskStats.pending} pending / {summary.taskStats.total} total
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-theme-muted text-sm">No summary available</div>
              )}
            </GlassCard>
          </div>

          {/* Right Column - Messages List */}
          <div className="lg:col-span-1">
            <GlassCard className="p-6 h-full">
              <h2 className="text-xl font-semibold text-theme-primary mb-4 heading-premium">
                Messages ({messages.length})
              </h2>
              <div className="space-y-3 max-h-[600px] overflow-y-auto custom-scrollbar">
                {messages.length === 0 ? (
                  <div className="text-center py-8 text-theme-muted">
                    <div className="text-3xl mb-2">📭</div>
                    <p className="text-sm">No messages yet</p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <Link
                      key={message.id}
                      href={`/thread/${message.id}`}
                      className="block p-3 rounded-lg border border-[var(--glass-border)] hover:bg-[var(--bg-hover)] hover:border-[var(--primary)]/30 transition-all duration-300 cursor-pointer group"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded ${
                            message.sender === 'contact'
                              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                              : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                          }`}
                        >
                          {message.sender === 'contact' ? 'From' : 'To'}
                        </span>
                        <span className="text-xs text-theme-muted">
                          {formatDate(message.created_at)}
                        </span>
                      </div>
                      <p className="text-sm text-theme-secondary line-clamp-2 group-hover:text-theme-primary transition-colors">
                        {message.body}
                      </p>
                    </Link>
                  ))
                )}
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
    </div>
  );
}

