/**
 * Header Component - Matte White Theme
 * Top header bar with brand area, user avatar, and status chip
 * To revert: delete this file and remove import from layout.tsx
 */

'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { getUserInitials } from '@/lib/userMetadata';
import { useAppStore, Theme } from '@/lib/store';

export default function Header() {
  const [isSimulated, setIsSimulated] = useState(false);
  const { theme, setTheme } = useAppStore();

  useEffect(() => {
    checkSimulatedMode();
  }, []);

  const checkSimulatedMode = async () => {
    try {
      const health = await api.getHealthLocal();
      // Check if we're in offline mode based on LLM status
      setIsSimulated(health.llm !== 'openai_configured' && health.status !== 'ok');
    } catch {
      setIsSimulated(false);
    }
  };

  const themes: { value: Theme; label: string; icon: string }[] = [
    { value: 'rainbow', label: 'Rainbow', icon: '🌈' },
    { value: 'dark', label: 'Dark', icon: '🌙' },
    { value: 'luxury', label: 'Luxury', icon: '✨' },
    { value: 'late-night', label: 'Late Night', icon: '🌃' },
  ];

  return (
    <header className="sticky top-0 z-30 glass-pane border-b border-[var(--glass-border)] shadow-sm relative">
      <div className="max-w-full mx-auto px-6 py-3 flex items-center justify-between">
        {/* Brand Area */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-[var(--text-primary)]">Soraya</span>
            <span className="text-xs text-[var(--muted)] font-medium">AI</span>
          </div>
        </div>

        {/* Right Side: Theme Switcher, Status & User */}
        <div className="flex items-center gap-3">
          {/* Theme Switcher */}
          <div className="flex items-center gap-1 px-2 py-1 glass-card rounded-lg border border-[var(--glass-border)]">
            {themes.map((t) => (
              <button
                key={t.value}
                onClick={() => setTheme(t.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-300 ease-out ${
                  theme === t.value
                    ? 'bg-[var(--primary)] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-hover)] hover:bg-[var(--bg-hover)]'
                }`}
                title={t.label}
                aria-label={`Switch to ${t.label} theme`}
              >
                <span className="mr-1">{t.icon}</span>
                <span className="hidden sm:inline">{t.label}</span>
              </button>
            ))}
          </div>

          {isSimulated && (
            <div className="px-3 py-1.5 glass-card rounded-full text-xs font-medium text-[var(--text-secondary)] backdrop-blur-sm border border-[var(--glass-border)]">
              Demo
            </div>
          )}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-sm font-medium">
              {getUserInitials()}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

