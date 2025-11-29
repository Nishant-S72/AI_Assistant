/**
 * Zustand store for global state management
 */

import { create } from 'zustand';
import { SummaryResponse } from './api';

export type Theme = 'rainbow' | 'dark' | 'luxury' | 'late-night';

interface AppState {
  isOfflineMode: boolean;
  setIsOfflineMode: (value: boolean) => void;
  currentThreadId: string | null;
  setCurrentThreadId: (id: string | null) => void;
  toast: { message: string; type: 'success' | 'error' | 'info' } | null;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
  hideToast: () => void;
  // Summary cache
  summaryCache: SummaryResponse | null;
  summaryCacheTimestamp: number | null;
  setSummaryCache: (summary: SummaryResponse) => void;
  clearSummaryCache: () => void;
  shouldRefreshSummary: () => boolean;
  // Theme
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const SUMMARY_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export const useAppStore = create<AppState>((set, get) => ({
  isOfflineMode: false,
  setIsOfflineMode: (value) => set({ isOfflineMode: value }),
  currentThreadId: null,
  setCurrentThreadId: (id) => set({ currentThreadId: id }),
  toast: null,
  showToast: (message, type = 'success') =>
    set({ toast: { message, type } }),
  hideToast: () => set({ toast: null }),
  // Summary cache
  summaryCache: null,
  summaryCacheTimestamp: null,
  setSummaryCache: (summary: SummaryResponse) => {
    set({ 
      summaryCache: summary, 
      summaryCacheTimestamp: Date.now() 
    });
  },
  clearSummaryCache: () => {
    set({ summaryCache: null, summaryCacheTimestamp: null });
  },
  shouldRefreshSummary: () => {
    const { summaryCacheTimestamp } = get();
    if (!summaryCacheTimestamp) return true;
    const age = Date.now() - summaryCacheTimestamp;
    return age > SUMMARY_CACHE_TTL;
  },
  // Theme
  theme: (typeof window !== 'undefined' ? (localStorage.getItem('theme') as Theme) : null) || 'rainbow',
  setTheme: (theme: Theme) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme', theme);
      document.documentElement.setAttribute('data-theme', theme);
    }
    set({ theme });
  },
}));

