/**
 * Inbox Page
 * Main inbox list view with filtering
 */

'use client';

import { useState } from 'react';
import InboxList from '@/components/InboxList';
import ContextPanel from '@/components/ContextPanel';

export default function InboxPage() {
  const [folder, setFolder] = useState<'all' | 'leads' | 'tasks'>('all');

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col">
        {/* Folder Tabs */}
        <div className="p-4 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
          <div className="flex gap-2">
            {(['all', 'leads', 'tasks'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFolder(f)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                  folder === f
                    ? 'bg-[var(--primary)] text-white shadow-sm'
                    : 'bg-white/80 dark:bg-[var(--card-bg)] backdrop-blur-sm border border-[var(--glass-border)] text-theme-primary hover:bg-white dark:hover:bg-[var(--card-bg)]/90 hover:text-[var(--text-hover)] hover:border-[var(--primary)]/30 transition-all duration-300 ease-out'
                }`}
                aria-pressed={folder === f}
                aria-label={`Filter by ${f}`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Inbox List */}
        <InboxList folder={folder} />
      </div>
    </div>
  );
}

