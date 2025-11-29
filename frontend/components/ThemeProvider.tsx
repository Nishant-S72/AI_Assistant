/**
 * Theme Provider Component
 * Initializes theme from localStorage and applies it to the document
 */

'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/lib/store';

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme, setTheme } = useAppStore();

  useEffect(() => {
    // Initialize theme from localStorage or default
    const savedTheme = (typeof window !== 'undefined' ? localStorage.getItem('theme') : null) || 'rainbow';
    setTheme(savedTheme as any);
  }, [setTheme]);

  useEffect(() => {
    // Apply theme to document
    if (typeof window !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }, [theme]);

  return <>{children}</>;
}


