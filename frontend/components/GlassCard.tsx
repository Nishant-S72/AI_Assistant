/**
 * GlassCard Component
 * Reusable glass card wrapper with matte white theme styling
 * To revert: delete this file
 */

'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}

export default function GlassCard({ children, className, hover = true }: GlassCardProps) {
  return (
    <div
      className={cn(
        'glass-card',
        hover && 'hover:scale-[1.01]',
        className
      )}
    >
      {children}
    </div>
  );
}


