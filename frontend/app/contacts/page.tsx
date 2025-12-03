/**
 * Contacts Page - Searchable contact list
 * Parses complete inbox to generate contact cards
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, Contact } from '@/lib/api';
import GlassCard from '@/components/GlassCard';
import { motion } from 'framer-motion';

export default function ContactsPage() {
  const router = useRouter();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [availableTags, setAvailableTags] = useState<string[]>([]);

  useEffect(() => {
    loadContacts();
  }, []);

  useEffect(() => {
    // Debounce search
    const timer = setTimeout(() => {
      loadContacts(searchQuery, selectedTag || undefined);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery, selectedTag]);

  const loadContacts = async (search = '', tag?: string) => {
    try {
      setLoading(true);
      const data = await api.getContacts(search, tag);
      setContacts(data);
      
      // Extract unique tags from all contacts, but only show the 6 allowed categories
      const allowedTags = [
        'new-lead',
        'long-standing',
        'urgent-action-required',
        'potential-interest',
        'escalation',
        'high-priority'
      ];
      const allTags = new Set<string>();
      data.forEach((contact) => {
        contact.tags?.forEach((tag) => {
          // Only include tags that are in the allowed list
          if (allowedTags.includes(tag)) {
            allTags.add(tag);
          }
        });
      });
      // Sort by the order in allowedTags
      setAvailableTags(Array.from(allTags).sort((a, b) => {
        const indexA = allowedTags.indexOf(a);
        const indexB = allowedTags.indexOf(b);
        return (indexA === -1 ? 999 : indexA) - (indexB === -1 ? 999 : indexB);
      }));
    } catch (error) {
      console.error('Error loading contacts:', error);
    } finally {
      setLoading(false);
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'No recent messages';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-[var(--glass-border)] bg-white/50 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-3xl font-semibold text-theme-primary heading-premium">Contacts</h1>
          <div className="text-sm text-theme-muted">
            {contacts.length} {contacts.length === 1 ? 'contact' : 'contacts'}
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative mb-4">
          <input
            type="text"
            placeholder="Search contacts by name, email, or company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-3 pl-10 rounded-xl border border-[var(--glass-border)] bg-white/80 dark:bg-[var(--card-bg)] text-theme-primary placeholder-theme-muted focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent transition-all duration-300"
          />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-theme-muted">🔍</span>
        </div>

        {/* Tag Filters */}
        {availableTags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedTag(null)}
              className={`px-3 py-1.5 text-sm rounded-full border transition-all duration-300 ${
                selectedTag === null
                  ? 'bg-[var(--primary)] text-white border-[var(--primary)] shadow-md'
                  : 'bg-white/60 dark:bg-[var(--card-bg)] text-theme-primary border-[var(--glass-border)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-hover)]'
              }`}
            >
              All
            </button>
            {availableTags.map((tag) => {
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
                  <button
                    onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                    className={`px-3 py-1.5 text-sm rounded-full border transition-all duration-300 font-medium flex items-center gap-1.5 ${
                      selectedTag === tag
                        ? 'bg-[var(--primary)] text-white border-[var(--primary)] shadow-md'
                        : 'bg-white/60 dark:bg-[var(--card-bg)] text-theme-primary border-[var(--glass-border)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-hover)]'
                    }`}
                  >
                    {tagLabels[tag] || tag.replace(/-/g, ' ')}
                    <span className="text-xs opacity-70 cursor-help" title={tagDescriptions[tag] || ''}>
                      ℹ️
                    </span>
                  </button>
                  {/* Tooltip on hover */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    <div className="font-semibold mb-1">{tagLabels[tag] || tag.replace(/-/g, ' ')}</div>
                    <div className="text-gray-300">{tagDescriptions[tag] || 'No description available'}</div>
                    <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Contacts List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-theme-muted font-medium">Loading contacts...</div>
          </div>
        ) : contacts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64">
            <div className="text-4xl mb-4">👥</div>
            <div className="text-theme-muted font-medium text-lg">
              {searchQuery ? 'No contacts found' : 'No contacts yet'}
            </div>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="mt-4 text-sm text-[var(--primary)] hover:underline"
              >
                Clear search
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-7xl mx-auto">
            {contacts.map((contact, index) => (
              <motion.div
                key={contact.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <Link href={`/contacts/${contact.id}`}>
                  <GlassCard className="p-5 hover:shadow-lg transition-all duration-300 cursor-pointer group">
                    <div className="flex items-start gap-4">
                      {/* Avatar */}
                      <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[var(--primary)]/20 to-[var(--accent)]/20 flex items-center justify-center text-[var(--primary)] font-semibold text-lg flex-shrink-0">
                        {getInitials(contact.name)}
                      </div>

                      {/* Contact Info */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-theme-primary mb-1 heading-premium group-hover:text-[var(--primary)] transition-colors duration-300 truncate">
                          {contact.name}
                        </h3>
                        {contact.company && (
                          <p className="text-sm text-theme-muted mb-2 truncate">{contact.company}</p>
                        )}
                        <p className="text-sm text-theme-muted mb-3 truncate">{contact.email}</p>

                        {/* Stats */}
                        <div className="flex items-center gap-4 text-xs text-theme-muted">
                          {contact.message_count !== undefined && contact.message_count > 0 && (
                            <span className="flex items-center gap-1">
                              <span>📧</span>
                              <span>{contact.message_count}</span>
                            </span>
                          )}
                          {contact.pending_tasks !== undefined && contact.pending_tasks > 0 && (
                            <span className="flex items-center gap-1 text-amber-600">
                              <span>✓</span>
                              <span>{contact.pending_tasks} tasks</span>
                            </span>
                          )}
                        </div>

                        {/* Last Message */}
                        <p className="text-xs text-theme-muted mt-2">
                          {formatDate(contact.last_message_at)}
                        </p>

                        {/* Tags */}
                        {contact.tags && contact.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-3">
                            {contact.tags.map((tag, i) => {
                              // Only show the 6 allowed tags
                              const allowedTags = ['new-leads', 'long-standing-customers', 'enterprise', 'high-value', 'urgent', 'vip'];
                              if (!allowedTags.includes(tag)) return null;
                              
                              const tagColors: Record<string, string> = {
                                'new-leads': 'bg-blue-100 text-blue-800 border-blue-200',
                                'long-standing-customers': 'bg-green-100 text-green-800 border-green-200',
                                'enterprise': 'bg-purple-100 text-purple-800 border-purple-200',
                                'high-value': 'bg-amber-100 text-amber-800 border-amber-200',
                                'urgent': 'bg-red-100 text-red-800 border-red-200',
                                'vip': 'bg-indigo-100 text-indigo-800 border-indigo-200',
                              };
                              
                              const tagLabels: Record<string, string> = {
                                'new-leads': 'New Leads',
                                'long-standing-customers': 'Long Standing',
                                'enterprise': 'Enterprise',
                                'high-value': 'High Value',
                                'urgent': 'Urgent',
                                'vip': 'VIP',
                              };
                              
                              return (
                                <button
                                  key={i}
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    setSelectedTag(selectedTag === tag ? null : tag);
                                  }}
                                  className={`px-2 py-0.5 text-xs rounded-full border transition-all duration-300 font-medium ${
                                    selectedTag === tag
                                      ? 'bg-[var(--primary)] text-white border-[var(--primary)] shadow-md'
                                      : tagColors[tag] || 'bg-gray-100 text-gray-700 border-gray-200'
                                  }`}
                                >
                                  {tagLabels[tag] || tag.replace(/-/g, ' ')}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  </GlassCard>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

