/**
 * Toast Component
 * Displays temporary notifications for user actions
 */

'use client';

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '@/lib/store';

export default function Toast() {
  const { toast, hideToast } = useAppStore();

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        hideToast();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [toast, hideToast]);

  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          initial={{ opacity: 0, y: -20, x: '-50%' }}
          animate={{ opacity: 1, y: 0, x: '-50%' }}
          exit={{ opacity: 0, y: -20, x: '-50%' }}
          className="fixed top-4 left-1/2 z-50 px-6 py-3 rounded-lg shadow-lg"
          style={{
            backgroundColor:
              toast.type === 'success'
                ? '#10b981'
                : toast.type === 'error'
                ? '#ef4444'
                : '#3b82f6',
            color: 'white',
          }}
          role="alert"
          aria-live="polite"
        >
          <div className="flex items-center gap-2">
            <span>{toast.message}</span>
            <button
              onClick={hideToast}
              className="ml-2 hover:opacity-80"
              aria-label="Close notification"
            >
              ×
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

