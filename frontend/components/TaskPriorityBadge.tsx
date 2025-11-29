'use client';

import React from 'react';

export type Priority = 'P0' | 'P1' | 'P2';

interface TaskPriorityBadgeProps {
  priority: Priority;
  className?: string;
  variant?: 'default' | 'on-pane'; // 'on-pane' for badges inside glass cards
}

export function TaskPriorityBadge({ priority, className = '', variant = 'default' }: TaskPriorityBadgeProps) {
  // Styles for badges on background (default)
  const defaultStyles = {
    P0: 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800/50',
    P1: 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800/50',
    P2: 'bg-gray-50 dark:bg-gray-800/30 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700/50',
  };

  // Styles for badges on glass panes (lighter, more contrast)
  const paneStyles = {
    P0: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200 border-red-300 dark:border-red-700/50',
    P1: 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200 border-amber-300 dark:border-amber-700/50',
    P2: 'bg-gray-100 dark:bg-gray-800/40 text-gray-800 dark:text-gray-200 border-gray-300 dark:border-gray-700/50',
  };

  const styles = variant === 'on-pane' ? paneStyles : defaultStyles;

  const labels = {
    P0: 'P0 - Urgent',
    P1: 'P1 - High',
    P2: 'P2 - Normal',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors duration-300 ease-out ${styles[priority]} ${className}`}
      aria-label={`Priority ${priority}`}
    >
      {labels[priority]}
    </span>
  );
}

