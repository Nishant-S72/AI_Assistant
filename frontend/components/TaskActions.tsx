'use client';

import React, { useState } from 'react';
import { Check, X, Calendar, MoreVertical } from 'lucide-react';
import { api, Task } from '@/lib/api';

interface TaskActionsProps {
  task: Task;
  onUpdate: () => void;
}

export function TaskActions({ task, onUpdate }: TaskActionsProps) {
  const [loading, setLoading] = useState(false);
  const [showPostpone, setShowPostpone] = useState(false);
  const [newDueDate, setNewDueDate] = useState('');

  const handleComplete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (loading) return;
    
    setLoading(true);
    try {
      await api.tasks.completeTask(task.id);
      onUpdate();
    } catch (error) {
      console.error('Error completing task:', error);
      alert('Failed to complete task');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (loading) return;
    
    const reason = prompt('Reason for cancellation (optional):');
    if (reason === null) return; // User cancelled prompt
    
    setLoading(true);
    try {
      await api.tasks.cancelTask(task.id, reason || undefined);
      onUpdate();
    } catch (error) {
      console.error('Error cancelling task:', error);
      alert('Failed to cancel task');
    } finally {
      setLoading(false);
    }
  };

  const handlePostpone = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!showPostpone) {
      setShowPostpone(true);
      return;
    }
    
    if (!newDueDate) {
      alert('Please select a new due date');
      return;
    }
    
    if (loading) return;
    
    setLoading(true);
    try {
      await api.tasks.postponeTask(task.id, newDueDate);
      setShowPostpone(false);
      setNewDueDate('');
      onUpdate();
    } catch (error) {
      console.error('Error postponing task:', error);
      alert('Failed to postpone task');
    } finally {
      setLoading(false);
    }
  };

  if (task.status === 'completed' || task.status === 'cancelled') {
    return null; // Don't show actions for completed/cancelled tasks
  }

  return (
    <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
      {showPostpone ? (
        <div className="flex items-center gap-2">
          <input
            type="datetime-local"
            value={newDueDate}
            onChange={(e) => setNewDueDate(e.target.value)}
            className="px-2 py-1 text-xs border rounded"
            min={new Date().toISOString().slice(0, 16)}
          />
          <button
            onClick={handlePostpone}
            disabled={loading}
            className="p-1.5 text-green-600 hover:bg-green-50 rounded transition-colors"
            title="Confirm postpone"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setShowPostpone(false);
              setNewDueDate('');
            }}
            className="p-1.5 text-gray-600 hover:bg-gray-50 rounded transition-colors"
            title="Cancel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <>
          <button
            onClick={handleComplete}
            disabled={loading}
            className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
            title="Mark as completed"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={handlePostpone}
            disabled={loading}
            className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
            title="Postpone task"
          >
            <Calendar className="w-4 h-4" />
          </button>
          <button
            onClick={handleCancel}
            disabled={loading}
            className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
            title="Cancel task"
          >
            <X className="w-4 h-4" />
          </button>
        </>
      )}
    </div>
  );
}

