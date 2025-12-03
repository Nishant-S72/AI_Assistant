/**
 * ContextPanel Component
 * Right-side panel showing contact summary and context
 */

'use client';

import { Contact, Task } from '@/lib/api';
import { getInitials, formatDate } from '@/lib/utils';
import { cn } from '@/lib/utils';
import GlassCard from './GlassCard';

interface ContextPanelProps {
  contact: Contact | null;
  tasks?: Task[];
}

export default function ContextPanel({ contact, tasks = [] }: ContextPanelProps) {
  if (!contact) {
    return (
      <aside className="w-80 bg-white/80 backdrop-blur-sm border-l border-[var(--glass-border)] p-6">
        <div className="text-[var(--muted)] text-sm">
          Select a thread to view contact details
        </div>
      </aside>
    );
  }

  // Normalize tags to ensure it's always an array
  const normalizeTags = (tags: any): string[] => {
    if (!tags) return [];
    if (Array.isArray(tags)) return tags;
    if (typeof tags === 'string') {
      try {
        const parsed = JSON.parse(tags);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }
    return [];
  };

  const contactTags = normalizeTags(contact.tags);
  const pendingTasks = tasks.filter((t) => t.status === 'pending');

  return (
    <aside
      className="w-80 bg-white/80 backdrop-blur-sm border-l border-[var(--glass-border)] p-6 overflow-y-auto custom-scrollbar"
      aria-label="Contact context panel"
    >
      <div className="space-y-6">
        {/* Contact Header */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-[var(--primary)] flex items-center justify-center text-white font-semibold shadow-sm">
              {getInitials(contact.name)}
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                {contact.name}
              </h3>
              {contact.company && (
                <p className="text-sm text-[var(--muted)]">
                  {contact.company}
                </p>
              )}
            </div>
          </div>

          <div className="space-y-2 text-sm">
            {contact.email && (
              <div>
                <span className="text-[var(--muted)]">Email:</span>
                <span className="ml-2 text-gray-900">{contact.email}</span>
              </div>
            )}
            {contact.phone && (
              <div>
                <span className="text-[var(--muted)]">Phone:</span>
                <span className="ml-2 text-gray-900">{contact.phone}</span>
              </div>
            )}
          </div>
        </div>

        {/* Tags */}
        {contactTags && contactTags.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Tags
            </h4>
            <div className="flex flex-wrap gap-2">
              {contactTags.map((tag) => {
                const tagLabels: Record<string, string> = {
                  'new-lead': 'New Lead',
                  'long-standing': 'Long Standing',
                  'urgent-action-required': 'Urgent Action Required',
                  'potential-interest': 'Potential Interest',
                  'escalation': 'Escalation',
                  'high-priority': 'High Priority',
                };
                
                const tagDescriptions: Record<string, string> = {
                  'new-lead': 'New potential customers with minimal interaction history (0-5 messages, recent contact within 7 days, asking initial questions)',
                  'long-standing': 'Established customers with long history (10+ messages over 30+ days, repeat interactions, loyal relationship)',
                  'urgent-action-required': 'Requires immediate attention (complaints, time-sensitive issues, deadlines, critical problems, "asap", "urgent", "emergency")',
                  'potential-interest': 'Showing interest but not committed (asking about products/services, requesting demos, comparing options, but no purchase yet)',
                  'escalation': 'Issues requiring escalation (dissatisfaction, complaints, refund requests, legal concerns, "speak to manager", "cancel")',
                  'high-priority': 'High-priority customers/accounts (large orders, premium services, significant revenue, key accounts, strategic partners, executive contacts)',
                };
                
                return (
                  <div key={tag} className="relative group">
                    <span
                      className={cn(
                        'px-2 py-1 text-xs rounded-full font-medium flex items-center gap-1',
                        tag === 'new-lead' && 'bg-blue-100 text-blue-800',
                        tag === 'long-standing' && 'bg-green-100 text-green-800',
                        tag === 'urgent-action-required' && 'bg-red-100 text-red-800',
                        tag === 'potential-interest' && 'bg-yellow-100 text-yellow-800',
                        tag === 'escalation' && 'bg-orange-100 text-orange-800',
                        tag === 'high-priority' && 'bg-purple-100 text-purple-800',
                        !['new-lead', 'long-standing', 'urgent-action-required', 'potential-interest', 'escalation', 'high-priority'].includes(tag) &&
                          'bg-gray-100 text-gray-700'
                      )}
                    >
                      {tagLabels[tag] || tag.replace(/-/g, ' ')}
                      <span className="text-xs opacity-70 cursor-help" title={tagDescriptions[tag] || ''}>
                        ℹ️
                      </span>
                    </span>
                    {/* Tooltip on hover */}
                    <div className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                      <div className="font-semibold mb-1">{tagLabels[tag] || tag.replace(/-/g, ' ')}</div>
                      <div className="text-gray-300">{tagDescriptions[tag] || 'No description available'}</div>
                      <div className="absolute bottom-0 left-4 translate-y-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tone Preference */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Tone Preference
          </h4>
          <span className="text-sm text-[var(--muted)] capitalize">
            {contact.tone_pref || 'warm'}
          </span>
        </div>

        {/* Stats */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-[var(--muted)]">Messages:</span>
            <span className="text-gray-900 font-medium">
              {contact.message_count || 0}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[var(--muted)]">Pending Tasks:</span>
            <span className="text-gray-900 font-medium">
              {contact.pending_tasks || pendingTasks.length}
            </span>
          </div>
        </div>

        {/* Tasks */}
        {pendingTasks.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Upcoming Tasks
            </h4>
            <div className="space-y-2">
              {pendingTasks.slice(0, 3).map((task) => (
                <div
                  key={task.id}
                  className="p-2 bg-gray-50 rounded-lg text-sm"
                >
                  <div className="font-medium text-gray-900">
                    {task.title}
                  </div>
                  {task.due_at && (
                    <div className="text-xs text-[var(--muted)] mt-1">
                      Due: {formatDate(task.due_at)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Personality Insight */}
        <GlassCard className="p-3 bg-primary-50/50 border-primary-200/50">
          <h4 className="text-xs font-medium text-primary-900 mb-1">
            AI Personality Insight
          </h4>
          <p className="text-xs text-primary-800">
            {contact.tone_pref === 'formal'
              ? 'This contact prefers formal, professional communication.'
              : contact.tone_pref === 'crisp'
              ? 'This contact prefers direct, action-oriented responses.'
              : 'This contact appreciates warm, friendly communication.'}
          </p>
        </GlassCard>
      </div>
    </aside>
  );
}

