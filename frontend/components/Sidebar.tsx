/**
 * Sidebar Component
 * Navigation sidebar with app name, nav links, and profile
 */

'use client';

import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAppStore } from '@/lib/store';
import { userMetadata, getUserInitials } from '@/lib/userMetadata';
import MiniCalendar from './MiniCalendar';

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { isOfflineMode } = useAppStore();

  const navItems = [
    { href: '/', label: 'Overview', icon: '📊', shortcut: 'G O' },
    { href: '/inbox', label: 'Inbox', icon: '📥', shortcut: 'G I' },
    { href: '/contacts', label: 'Contacts', icon: '👥', shortcut: 'G C' },
    { href: '/tasks', label: 'Tasks', icon: '✓', shortcut: 'G T' },
    { href: '/calendar', label: 'Calendar', icon: '📅', shortcut: 'G L' },
    { href: '/drafts', label: 'Drafts', icon: '📝' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    if (href === '/inbox') {
      return pathname === '/inbox';
    }
    return pathname?.startsWith(href);
  };

  return (
    <aside
      className="w-64 glass-pane border-r border-[var(--glass-border)] flex flex-col h-screen shadow-sm relative"
      aria-label="Main navigation"
    >
      {/* App Header */}
      <div className="p-6 border-b border-[var(--glass-border)]">
        <h1 className="text-xl font-bold text-theme-primary">
          Soraya AI
        </h1>
        {isOfflineMode && (
          <div className="mt-2 px-2 py-1 glass-card rounded-full text-xs text-theme-secondary border border-[var(--glass-border)]">
            🧠 Offline Mode
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4" aria-label="Main navigation">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-300 ease-out ${
                  isActive(item.href)
                    ? 'bg-[var(--primary)]/10 text-[var(--primary)] font-medium'
                    : 'text-theme-primary hover:text-[var(--text-hover)] hover:bg-[var(--bg-hover)]'
                }`}
                aria-current={isActive(item.href) ? 'page' : undefined}
              >
                <span className="text-lg" aria-hidden="true">
                  {item.icon}
                </span>
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="ml-auto text-xs text-theme-muted">
                    {item.shortcut}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {/* Mini Calendar */}
      <div className="border-t border-[var(--glass-border)]">
        <MiniCalendar />
      </div>

      {/* Profile Section */}
      <div className="p-4 border-t border-[var(--glass-border)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[var(--primary)] flex items-center justify-center text-white font-medium shadow-sm">
            {getUserInitials()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-theme-primary truncate">
              {userMetadata.name}
            </div>
            <div className="text-xs text-theme-muted truncate">
              {userMetadata.email}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

