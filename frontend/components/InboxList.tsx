/**
 * InboxList Component
 * Displays list of message threads with filtering
 */

'use client';

import { useEffect, useState } from 'react';
import { api, Message } from '@/lib/api';
import MessageCard from './MessageCard';
import { useAppStore } from '@/lib/store';
import { SkeletonLoader } from './SkeletonLoader';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';

interface InboxListProps {
  folder?: 'all' | 'leads' | 'tasks';
}

export default function InboxList({ folder = 'all' }: InboxListProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { showToast } = useAppStore();

  useEffect(() => {
    loadMessages();
  }, [folder]);

  const loadMessages = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMessages(folder === 'all' ? undefined : folder);
      setMessages(data);

      // Auto-seed if empty
      if (data.length === 0) {
        try {
          await api.seedDemo();
          const refreshed = await api.getMessages();
          setMessages(refreshed);
        } catch (seedError) {
          console.warn('Could not seed demo data:', seedError);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load messages');
      console.error('Error loading messages:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
          <SkeletonLoader variant="text" lines={1} width="200px" />
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
          <SkeletonLoader variant="message" count={5} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-gray-900">Inbox</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          <ErrorState
            message={error}
            onRetry={loadMessages}
            className="h-full"
          />
        </div>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-gray-900">Inbox</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          <EmptyState
            icon="📬"
            title="No messages found"
            description="Your inbox is empty. Load demo data to get started."
            action={{
              label: 'Load Demo Data',
              onClick: async () => {
                try {
                  await api.seedDemo();
                  await loadMessages();
                  showToast('Demo data loaded', 'success');
                } catch (err) {
                  showToast('Failed to load demo data', 'error');
                }
              },
            }}
            className="h-full"
          />
        </div>
      </div>
    );
  }

  // Get unique threads
  const threadMap = new Map<string, Message>();
  messages.forEach((msg) => {
    if (!threadMap.has(msg.thread_id)) {
      threadMap.set(msg.thread_id, msg);
    }
  });
  const uniqueThreads = Array.from(threadMap.values());

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          Inbox ({uniqueThreads.length})
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {uniqueThreads.map((message) => (
          <MessageCard key={message.thread_id} message={message} />
        ))}
      </div>
    </div>
  );
}

