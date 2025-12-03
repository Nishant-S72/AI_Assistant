/**
 * MessageCard Component
 * Displays a thread preview in the inbox list
 */

'use client';

import Link from 'next/link';
import { formatDate, truncate, cn } from '@/lib/utils';
import { Message } from '@/lib/api';

interface MessageCardProps {
  message: Message;
  isSelected?: boolean;
}

export default function MessageCard({ message, isSelected }: MessageCardProps) {
  // Tags should come from the contact data, but Message interface doesn't include tags
  // For now, use empty array - tags will be shown in contact detail view
  const tags: string[] = [];

  return (
    <Link
      href={`/thread/${message.id}`}
      className={cn(
        'block p-4 border-b border-[var(--glass-border)] bg-white/30 dark:bg-[var(--card-bg)]/50 hover:bg-white/50 dark:hover:bg-[var(--card-bg)]/80 hover:text-[var(--text-hover)] transition-all duration-300 ease-out',
        isSelected && 'bg-[var(--primary)]/10'
      )}
      aria-label={`Open thread from ${message.contact_name}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-theme-primary truncate">
              {message.contact_name}
            </h3>
            {message.contact_company && (
              <span className="text-xs text-theme-muted truncate">
                {message.contact_company}
              </span>
            )}
          </div>
          <p className="text-sm text-theme-secondary line-clamp-2 mb-2">
            {truncate(message.body, 100)}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            {tags.map((tag) => (
              <span
                key={tag}
                className={cn(
                  'px-2 py-0.5 text-xs rounded-full',
                  tag === 'lead' && 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200',
                  tag === 'complaint' && 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200',
                  tag === 'meeting' && 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200'
                )}
              >
                {tag}
              </span>
            ))}
            <span className="text-xs text-[var(--muted)]">
              {message.message_count} messages
            </span>
          </div>
        </div>
        <div className="text-xs text-[var(--muted)] whitespace-nowrap">
          {formatDate(message.created_at)}
        </div>
      </div>
    </Link>
  );
}

