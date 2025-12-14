/**
 * Tasks Page - Scrollable and Clickable
 * Lists all tasks from the API with improved UX
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, Task } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { TaskPriorityBadge, Priority } from '@/components/TaskPriorityBadge';
import { TaskActions } from '@/components/TaskActions';
import GlassCard from '@/components/GlassCard';

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const data = await api.tasks.getTasks();
      setTasks(data);
    } catch (error) {
      console.error('Error loading tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[var(--muted)] font-medium">Loading tasks...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="p-6 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
        <h1 className="text-3xl font-semibold text-theme-primary heading-premium">Tasks</h1>
      </div>
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {tasks.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-[var(--muted)] font-medium text-lg">No tasks found</p>
            </div>
          ) : (
            tasks.map((task) => {
              const threadLink = task.message_id 
                ? `/thread/${task.message_id}`
                : task.thread_id
                ? `/thread/${task.thread_id}`
                : '#';
              
              return (
                <div key={task.id} className="relative">
                  <GlassCard className="group p-5 hover:bg-[var(--primary)] dark:hover:bg-[var(--primary)]/80 hover:shadow-lg transition-all duration-300 ease-out">
                    <Link href={threadLink} className="block">
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold text-theme-primary group-hover:text-white heading-premium transition-colors duration-300 ease-out">
                              {task.title}
                            </h3>
                            {task.priority && (
                              <TaskPriorityBadge priority={task.priority as Priority} variant="on-pane" />
                            )}
                          </div>
                          {task.contact_name && (
                            <p className="text-sm text-theme-muted group-hover:text-white/90 font-medium mb-1 transition-colors duration-300 ease-out">
                              Contact: {task.contact_name}
                              {task.contact_email && ` • ${task.contact_email}`}
                            </p>
                          )}
                          {task.due_at && (
                            <p className="text-sm text-theme-muted group-hover:text-white/80 font-medium transition-colors duration-300 ease-out">
                              Due: {formatDate(task.due_at)}
                            </p>
                          )}
                        </div>
                        <div className="flex-shrink-0">
                          <span
                            className={`px-4 py-2 text-xs font-semibold rounded-xl transition-colors duration-300 ease-out ${
                              task.status === 'completed'
                                ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/50 group-hover:bg-white/20 group-hover:text-white'
                                : task.status === 'cancelled'
                                ? 'bg-gray-50 dark:bg-gray-900/30 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800/50 group-hover:bg-white/20 group-hover:text-white'
                                : 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/50 group-hover:bg-white/20 group-hover:text-white'
                            }`}
                          >
                            {task.status}
                          </span>
                        </div>
                      </div>
                    </Link>
                    {/* Action buttons below status */}
                    <div className="pt-3 border-t border-[var(--glass-border)] mt-3">
                      <TaskActions task={task} onUpdate={loadTasks} />
                    </div>
                  </GlassCard>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

