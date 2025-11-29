/**
 * Keyboard shortcuts hook
 * Handles global keyboard shortcuts like Cmd/Ctrl+K, G I, G T, etc.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Shortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  alt?: boolean;
  handler: () => void;
  description?: string;
}

export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const ctrlMatch = shortcut.ctrl ? e.ctrlKey : !e.ctrlKey;
        const metaMatch = shortcut.meta ? e.metaKey : !e.metaKey;
        const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey;
        const altMatch = shortcut.alt ? e.altKey : !e.altKey;
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();

        // Special handling for Cmd/Ctrl
        if (shortcut.ctrl || shortcut.meta) {
          const modifierMatch = (shortcut.ctrl && e.ctrlKey) || (shortcut.meta && e.metaKey);
          if (modifierMatch && keyMatch && !e.shiftKey && !e.altKey) {
            e.preventDefault();
            shortcut.handler();
            return;
          }
        } else if (ctrlMatch && metaMatch && shiftMatch && altMatch && keyMatch) {
          e.preventDefault();
          shortcut.handler();
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

export function useNavigationShortcuts() {
  const router = useRouter();

  useKeyboardShortcuts([
    {
      key: 'k',
      ctrl: true,
      meta: true,
      handler: () => {
        // Command palette will handle this
        const event = new CustomEvent('open-command-palette');
        window.dispatchEvent(event);
      },
      description: 'Open command palette',
    },
    {
      key: 'g',
      handler: () => {
        // G I or G T - handled by command palette
      },
    },
  ]);
}

