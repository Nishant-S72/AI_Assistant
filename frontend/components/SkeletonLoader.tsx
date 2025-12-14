'use client';

import React from 'react';

interface SkeletonLoaderProps {
  className?: string;
  variant?: 'text' | 'card' | 'list' | 'circle' | 'message' | 'task' | 'contact' | 'event';
  lines?: number;
  width?: string;
  height?: string;
  count?: number;
}

export function SkeletonLoader({
  className = '',
  variant = 'text',
  lines = 1,
  width,
  height,
  count = 1,
}: SkeletonLoaderProps) {
  const baseClasses = 'animate-pulse bg-gray-200 dark:bg-gray-700 rounded';

  if (variant === 'card') {
    return (
      <div className={`${baseClasses} ${className}`} style={{ width, height: height || '200px' }} />
    );
  }

  if (variant === 'circle') {
    return (
      <div
        className={`${baseClasses} rounded-full ${className}`}
        style={{ width: width || '40px', height: height || '40px' }}
      />
    );
  }

  if (variant === 'list') {
    return (
      <div className={`space-y-3 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className={`${baseClasses} h-4`} style={{ width: width || '100%' }} />
        ))}
      </div>
    );
  }

  if (variant === 'message') {
    return (
      <div className={`space-y-4 ${className}`}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <div className={`${baseClasses} rounded-full w-10 h-10 flex-shrink-0`} />
            <div className="flex-1 space-y-2">
              <div className={`${baseClasses} h-4 w-1/4`} />
              <div className={`${baseClasses} h-4 w-full`} />
              <div className={`${baseClasses} h-4 w-3/4`} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'task') {
    return (
      <div className={`space-y-4 ${className}`}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="p-5 rounded-xl border border-[var(--glass-border)] bg-white/40 dark:bg-[var(--card-bg)]">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className={`${baseClasses} h-6 w-3/4`} />
                <div className={`${baseClasses} h-6 w-20 rounded-full`} />
              </div>
              <div className={`${baseClasses} h-4 w-1/2`} />
              <div className={`${baseClasses} h-4 w-1/3`} />
              <div className="pt-3 border-t border-[var(--glass-border)]">
                <div className={`${baseClasses} h-8 w-32`} />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'contact') {
    return (
      <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 ${className}`}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="p-5 rounded-xl border border-[var(--glass-border)] bg-white/40 dark:bg-[var(--card-bg)]">
            <div className="flex items-start gap-4">
              <div className={`${baseClasses} rounded-full w-14 h-14 flex-shrink-0`} />
              <div className="flex-1 space-y-2">
                <div className={`${baseClasses} h-5 w-3/4`} />
                <div className={`${baseClasses} h-4 w-full`} />
                <div className={`${baseClasses} h-4 w-2/3`} />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'event') {
    return (
      <div className={`space-y-3 ${className}`}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="p-3 rounded-lg border border-[var(--glass-border)] bg-white/40 dark:bg-[var(--card-bg)]">
            <div className="flex items-start gap-2">
              <div className={`${baseClasses} w-3 h-3 rounded-full flex-shrink-0`} />
              <div className="flex-1 space-y-2">
                <div className={`${baseClasses} h-4 w-2/3`} />
                <div className={`${baseClasses} h-3 w-1/2`} />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Default: text variant
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`${baseClasses} h-4`}
          style={{
            width: i === lines - 1 ? width || '80%' : '100%',
          }}
        />
      ))}
    </div>
  );
}

