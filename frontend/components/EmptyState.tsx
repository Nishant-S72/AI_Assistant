'use client';

import React from 'react';

interface EmptyStateProps {
  icon?: string | React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 ${className}`}>
      {icon && (
        <div className="text-6xl mb-4 text-[var(--muted)]">
          {typeof icon === 'string' ? <span>{icon}</span> : icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-theme-primary mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-theme-muted text-center max-w-md mb-4">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 transition-opacity font-medium"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

