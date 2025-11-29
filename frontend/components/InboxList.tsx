/**
 * InboxList Component
 * Displays list of message threads with filtering
 */

'use client';

import { useEffect, useState } from 'react';
import { api, Message } from '@/lib/api';
import MessageCard from './MessageCard';
import { useAppStore } from '@/lib/store';

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
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">Loading messages...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-red-600 dark:text-red-400">{error}</div>
        <button
          onClick={loadMessages}
          className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
        >
          Retry
        </button>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-gray-500 dark:text-gray-400">No messages found</div>
        <button
          onClick={async () => {
            try {
              await api.seedDemo();
              await loadMessages();
              showToast('Demo data loaded', 'success');
            } catch (err) {
              showToast('Failed to load demo data', 'error');
            }
          }}
          className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
        >
          Load Demo Data
        </button>
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

