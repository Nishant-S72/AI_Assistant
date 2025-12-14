/**
 * ThreadView Component
 * Displays conversation thread with messages and suggestion panel
 */

'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { api, ThreadData, ThreadMessage } from '@/lib/api';
import SuggestionPanel from './SuggestionPanel';
import { formatDate, formatTime, cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';
import { SkeletonLoader } from './SkeletonLoader';
import { ErrorState } from './ErrorState';

interface ThreadViewProps {
  messageId: string;
}

export default function ThreadView({ messageId }: ThreadViewProps) {
  const [threadData, setThreadData] = useState<ThreadData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { setCurrentThreadId } = useAppStore();

  useEffect(() => {
    setCurrentThreadId(messageId);
    loadThread();
    return () => setCurrentThreadId(null);
  }, [messageId]);

  const loadThread = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMessage(messageId);
      setThreadData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load thread');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-6 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
          <SkeletonLoader variant="text" lines={2} width="200px" />
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
          <div className="max-w-3xl mx-auto">
            <SkeletonLoader variant="message" count={3} />
          </div>
        </div>
        <div className="p-4 border-t border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
          <SkeletonLoader variant="text" lines={2} />
        </div>
      </div>
    );
  }

  if (error || !threadData) {
    return (
      <ErrorState
        message={error || 'Thread not found'}
        onRetry={loadThread}
        className="h-full"
      />
    );
  }

  const { thread, contact, suggestion } = threadData;

  // Handle case where contact might be undefined
  if (!contact) {
    return (
      <ErrorState
        message="Contact information not available"
        onRetry={loadThread}
        className="h-full"
      />
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Thread Header */}
      <div className="p-6 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">
          {contact.name || 'Unknown Contact'}
        </h2>
        {contact.company && (
          <p className="text-sm text-[var(--muted)]">{contact.company}</p>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {thread.map((msg: ThreadMessage, idx: number) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={cn(
                'flex',
                msg.sender === 'assistant' ? 'justify-end' : 'justify-start'
              )}
            >
              <div
                className={cn(
                  'max-w-[80%] rounded-2xl p-4',
                  msg.sender === 'assistant'
                    ? 'bg-[var(--primary)] text-white shadow-sm'
                    : 'glass-card text-gray-900'
                )}
              >
                <div className="text-sm mb-1 opacity-80">
                  {msg.sender === 'assistant' ? 'You' : (contact?.name || 'Contact')}
                </div>
                <div className="whitespace-pre-wrap">{msg.body}</div>
                <div className="text-xs mt-2 opacity-70">
                  {formatTime(msg.created_at)}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Suggestion Panel */}
      <SuggestionPanel
        messageId={messageId}
        initialSuggestion={suggestion}
        onSuggestionGenerated={(suggestion) => {
          setThreadData({ ...threadData, suggestion });
        }}
      />
    </div>
  );
}

