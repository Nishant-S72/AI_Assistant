'use client';

import React from 'react';
import Link from 'next/link';
import { TaskPriorityBadge, Priority } from './TaskPriorityBadge';
import { Task } from '@/lib/api';

interface TaskPriorityListProps {
  tasks: Task[];
  maxItems?: number;
  showContact?: boolean;
}

export function TaskPriorityList({ 
  tasks, 
  maxItems = 6,
  showContact = true 
}: TaskPriorityListProps) {
  const formatDate = (dateString?: string | null) => {
    if (!dateString) return 'No due date';
    const date = new Date(dateString);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dueDate = new Date(date);
    dueDate.setHours(0, 0, 0, 0);
    
    if (dueDate < today) {
      return `Overdue: ${date.toLocaleDateString()}`;
    }
    if (dueDate.getTime() === today.getTime()) {
      return 'Due today';
    }
    return date.toLocaleDateString();
  };

  const displayedTasks = tasks.slice(0, maxItems);

  if (displayedTasks.length === 0) {
    return (
      <div className="text-base text-[var(--muted)] py-6 text-center font-medium">
        No tasks in this priority
      </div>
    );
  }

  return (
    <ul className="space-y-3" role="list">
      {displayedTasks.map((task) => {
        // Use message_id if available, otherwise fallback to tasks page
        const threadLink = task.message_id 
          ? `/thread/${task.message_id}`
          : task.thread_id
          ? `/thread/${task.thread_id}`
          : '/tasks';
        
        return (
          <li key={task.id}>
            <Link
              href={threadLink}
              className="group block p-4 rounded-xl border border-[var(--glass-border)] bg-white/60 dark:bg-[var(--card-bg)] hover:bg-[var(--primary)] dark:hover:bg-[var(--primary)]/80 hover:shadow-md transition-all duration-300 ease-out focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2"
              aria-label={`Task: ${task.title}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className="text-base font-semibold text-theme-primary group-hover:text-white truncate heading-premium transition-colors duration-300 ease-out">
                      {task.title}
                    </h4>
                    {task.priority && <TaskPriorityBadge priority={task.priority as Priority} variant="on-pane" />}
                  </div>
                  {showContact && task.contact_name && (
                    <p className="text-sm text-theme-muted group-hover:text-white/90 truncate mb-1 font-medium transition-colors duration-300 ease-out">
                      {task.contact_name}
                      {task.contact_email && ` • ${task.contact_email}`}
                    </p>
                  )}
                  <p className="text-sm text-theme-muted group-hover:text-white/80 mt-2 font-medium transition-colors duration-300 ease-out">
                    {formatDate(task.due_at)}
                  </p>
                </div>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

