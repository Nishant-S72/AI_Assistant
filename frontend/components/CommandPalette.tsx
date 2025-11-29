/**
 * Command Palette Component
 * Activated with Cmd/Ctrl+K, provides quick actions
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';

interface Command {
  id: string;
  label: string;
  shortcut?: string;
  action: () => void;
}

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { currentThreadId, showToast } = useAppStore();

  const commands: Command[] = [
    {
      id: 'summarize',
      label: 'Summarize thread',
      action: async () => {
        if (currentThreadId) {
          try {
            // Generate summary using the generate endpoint with a summarize prompt
            const data = await api.getMessage(currentThreadId);
            const summary = data.thread
              .slice(-10)
              .map((m) => `${m.sender}: ${m.body}`)
              .join('\n\n');
            showToast(`Thread summary: ${summary.substring(0, 100)}...`, 'info');
          } catch (error) {
            showToast('Could not summarize thread', 'error');
          }
        } else {
          showToast('No thread selected', 'error');
        }
        setIsOpen(false);
      },
    },
    {
      id: 'followup',
      label: 'Send follow-up',
      action: async () => {
        if (currentThreadId) {
          try {
            await api.generateSuggestion(currentThreadId, 'warm');
            showToast('Follow-up suggestion generated', 'success');
          } catch (error) {
            showToast('Could not generate follow-up', 'error');
          }
        } else {
          showToast('No thread selected', 'error');
        }
        setIsOpen(false);
      },
    },
    {
      id: 'tasks',
      label: 'Show tasks',
      action: () => {
        router.push('/tasks');
        setIsOpen(false);
      },
    },
  ];

  const filteredCommands = commands.filter((cmd) =>
    cmd.label.toLowerCase().includes(searchQuery.toLowerCase())
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setSearchQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        setIsOpen(false);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2 }}
            className="fixed top-1/4 left-1/2 transform -translate-x-1/2 z-50 w-full max-w-md"
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
          >
            <div className="glass-card overflow-hidden shadow-2xl">
              <div className="p-4 border-b border-[var(--glass-border)]">
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Type a command..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setSelectedIndex(0);
                  }}
                  className="w-full bg-transparent outline-none text-gray-900 placeholder-[var(--muted)]"
                  aria-label="Search commands"
                />
              </div>
              <div className="max-h-64 overflow-y-auto custom-scrollbar">
                {filteredCommands.length === 0 ? (
                  <div className="px-4 py-8 text-center text-[var(--muted)]">
                    No commands found
                  </div>
                ) : (
                  filteredCommands.map((cmd, idx) => (
                    <button
                      key={cmd.id}
                      onClick={cmd.action}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`w-full px-4 py-3 text-left transition-colors ${
                        idx === selectedIndex
                          ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                          : 'hover:bg-white/50 text-gray-900'
                      }`}
                      aria-selected={idx === selectedIndex}
                    >
                      <div className="font-medium">{cmd.label}</div>
                      {cmd.shortcut && (
                        <div className="text-xs text-[var(--muted)] mt-1">
                          {cmd.shortcut}
                        </div>
                      )}
                    </button>
                  ))
                )}
              </div>
              <div className="p-2 text-xs text-[var(--muted)] border-t border-[var(--glass-border)] bg-white/50">
                <div className="flex items-center justify-between">
                  <span>Press Esc to close</span>
                  <span>↑↓ to navigate, Enter to select</span>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
