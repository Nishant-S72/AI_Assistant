/**
 * Landing Page - Matte White Theme
 * Overview page with glass cards, welcome header, and inbox summary
 * To revert: restore original page.tsx from git history
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getSummary, SummaryResponse } from '@/lib/api';
import { TaskPriorityList } from '@/components/TaskPriorityList';
import { TaskPriorityBadge } from '@/components/TaskPriorityBadge';
import { useAppStore } from '@/lib/store';
import GlassCard from '@/components/GlassCard';
import { userMetadata } from '@/lib/userMetadata';

// Dynamic greeting based on time of day
function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Morning';
  if (hour < 18) return 'Afternoon';
  return 'Evening';
}

function AnimatedNumber({ value }: { value: number }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 1000;
    const steps = 30;
    const increment = value / steps;
    let current = 0;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      current = Math.min(value, Math.round(increment * step));
      setDisplayValue(current);
      if (step >= steps) {
        clearInterval(timer);
        setDisplayValue(value);
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [value]);

  return <span>{displayValue}</span>;
}

export default function Home() {
  const router = useRouter();
  const { 
    summaryCache, 
    setSummaryCache, 
    shouldRefreshSummary 
  } = useAppStore();
  
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'summary'>('overview');
  const [categorySummary, setCategorySummary] = useState<string>('');
  const [generatingCategorySummary, setGeneratingCategorySummary] = useState(false);
  const [taskFilter, setTaskFilter] = useState<'all' | 'P0' | 'P1' | 'P2'>('all');

  // Poll for summary if it's being generated
  const pollForSummary = async () => {
    const maxAttempts = 10; // Poll for up to 10 seconds
    let attempts = 0;
    
    const poll = async () => {
      if (attempts >= maxAttempts) return;
      
      try {
        const data = await getSummary();
        if (data.summaryParagraph) {
          setSummary(data);
          if (setSummaryCache && typeof setSummaryCache === 'function') {
            setSummaryCache(data);
          }
          return; // Stop polling
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000); // Poll every second
        }
      } catch (error) {
        console.error('Error polling for summary:', error);
      }
    };
    
    setTimeout(poll, 1000); // Start polling after 1 second
  };

  useEffect(() => {
    // Only load if cache is empty or expired
    if (!summaryCache || shouldRefreshSummary()) {
      loadSummary();
    } else {
      // Use cached data
      setSummary(summaryCache);
      setLoading(false);
    }
  }, []); // Only run on mount

  const loadSummary = async (force = false) => {
    // Check cache first unless forcing refresh
    if (!force && summaryCache && !shouldRefreshSummary()) {
      setSummary(summaryCache);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await getSummary();
      setSummary(data);
      // Safety check before calling setSummaryCache
      if (setSummaryCache && typeof setSummaryCache === 'function') {
        setSummaryCache(data); // Cache the result
      } else {
        // Fallback: update store directly
        useAppStore.setState({ summaryCache: data, summaryCacheTimestamp: Date.now() });
      }
      
      // If summary is still generating, start polling
      if (data.summaryGenerating && !data.summaryParagraph) {
        pollForSummary();
      }
    } catch (err: any) {
      console.error('Failed to load summary:', err);
      setError(err.message || 'Failed to load summary');
    } finally {
      setLoading(false);
    }
  };

  const generateCategorySummary = async (category: 'urgent' | 'high' | 'unread' | 'complaints' | 'leads') => {
    if (!summary) return;
    
    setGeneratingCategorySummary(true);
    setCategorySummary('');
    setActiveTab('summary');
    
    try {
      // Call backend to generate category-specific summary
      const response = await fetch(`http://localhost:3001/api/summary/category?type=${category}`, {
        method: 'GET',
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate summary');
      }
      
      const data = await response.json();
      setCategorySummary(data.summary || 'No summary available for this category.');
    } catch (err: any) {
      console.error('Failed to generate category summary:', err);
      setCategorySummary('Failed to generate summary. Please try again.');
    } finally {
      setGeneratingCategorySummary(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-white/50 rounded-2xl w-64"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-24 bg-white/50 rounded-2xl"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto">
          <GlassCard className="p-6">
            <p className="text-red-700 mb-4">{error}</p>
            <button
              onClick={() => loadSummary(true)}
              className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 transition-opacity"
            >
              Retry
            </button>
          </GlassCard>
        </div>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8 max-w-7xl mx-auto space-y-8">
        {/* Welcome Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-5xl font-semibold text-theme-primary mb-3 heading-premium">
                {getGreeting()}, {userMetadata.title} 👋
              </h1>
              <p className="text-theme-muted text-lg font-medium">
                Here's what needs your attention
              </p>
            </div>
            <button
              onClick={() => loadSummary(true)}
              className="px-5 py-2.5 text-sm font-medium bg-white/90 dark:bg-[var(--card-bg)] backdrop-blur-sm border border-[var(--glass-border)] text-theme-primary rounded-xl hover:bg-white dark:hover:bg-[var(--card-bg)]/80 hover:text-[var(--text-hover)] hover:shadow-md transition-all duration-300 ease-out"
              title="Refresh summary"
              aria-label="Refresh summary"
            >
              🔄 Refresh
            </button>
          </div>
        </motion.div>

        {/* Performance & Action Items Summary */}
        {summary && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
          >
            <GlassCard className="p-8">
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0">
                <div className="w-14 h-14 bg-gradient-to-br from-[var(--primary)]/10 to-[var(--accent)]/10 rounded-2xl flex items-center justify-center shadow-sm">
                  <span className="text-2xl">📊</span>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-semibold text-theme-primary mb-4 heading-premium">
                  Performance & Action Items
                </h3>
                <div className="text-base text-theme-secondary space-y-4 text-premium">
                  {/* Performance Summary */}
                  {summary.performance && (
                    <div className="flex flex-wrap items-center gap-6 mb-5">
                      {summary.performance.avgLatencyMs !== null && (
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/60 dark:bg-[var(--card-bg)] rounded-xl border border-[var(--glass-border)] hover:bg-white/80 dark:hover:bg-[var(--card-bg)]/90 transition-all duration-300 ease-out">
                          <span className="text-sm font-medium text-theme-muted">AI Response Time:</span>
                          <span className="text-[var(--primary)] font-semibold">
                            {summary.performance.avgLatencyMs < 5000
                              ? '⚡ Very Fast'
                              : summary.performance.avgLatencyMs < 10000
                              ? '✅ Fast'
                              : '⏱️ Normal'}
                          </span>
                          <span className="text-sm text-[var(--muted)]">
                            ({Math.round(summary.performance.avgLatencyMs / 1000)}s avg)
                          </span>
                        </div>
                      )}
                      {summary.performance.suggestionsGenerated > 0 && (
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/60 dark:bg-[var(--card-bg)] rounded-xl border border-[var(--glass-border)] hover:bg-white/80 dark:hover:bg-[var(--card-bg)]/90 transition-all duration-300 ease-out">
                          <span className="text-sm font-medium text-theme-muted">Suggestions:</span>
                          <span className="text-theme-primary font-semibold">
                            {summary.performance.suggestionsGenerated}
                          </span>
                        </div>
                      )}
                      {summary.performance.acceptanceRate > 0 && (
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/60 dark:bg-[var(--card-bg)] rounded-xl border border-[var(--glass-border)] hover:bg-white/80 dark:hover:bg-[var(--card-bg)]/90 transition-all duration-300 ease-out">
                          <span className="text-sm font-medium text-theme-muted">Acceptance:</span>
                          <span className="text-[var(--accent)] font-semibold">
                            {Math.round(summary.performance.acceptanceRate * 100)}%
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Action Items Summary - Clickable Badges */}
                  <div className="flex flex-wrap items-center gap-3">
                    {summary.tasks.counts.P0 > 0 && (
                      <button
                        onClick={() => generateCategorySummary('urgent')}
                        className="action-badge-on-pane inline-flex items-center gap-2 px-4 py-2.5 bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200 rounded-xl text-sm font-semibold hover:bg-red-200 dark:hover:bg-red-900/60 hover:text-red-900 dark:hover:text-red-100 hover:shadow-md transition-all duration-300 ease-out border border-red-300 dark:border-red-700/50"
                        title="Click to see urgent tasks summary"
                      >
                        <span>🚨</span>
                        <span>{summary.tasks.counts.P0} Urgent</span>
                      </button>
                    )}
                    {summary.tasks.counts.P1 > 0 && (
                      <button
                        onClick={() => generateCategorySummary('high')}
                        className="action-badge-on-pane inline-flex items-center gap-2 px-4 py-2.5 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200 rounded-xl text-sm font-semibold hover:bg-amber-200 dark:hover:bg-amber-900/60 hover:text-amber-900 dark:hover:text-amber-100 hover:shadow-md transition-all duration-300 ease-out border border-amber-300 dark:border-amber-700/50"
                        title="Click to see high priority tasks summary"
                      >
                        <span>⚠️</span>
                        <span>{summary.tasks.counts.P1} High Priority</span>
                      </button>
                    )}
                    {summary.totals.unread > 0 && (
                      <button
                        onClick={() => generateCategorySummary('unread')}
                        className="action-badge-on-pane inline-flex items-center gap-2 px-4 py-2.5 bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200 rounded-xl text-sm font-semibold hover:bg-blue-200 dark:hover:bg-blue-900/60 hover:text-blue-900 dark:hover:text-blue-100 hover:shadow-md transition-all duration-300 ease-out border border-blue-300 dark:border-blue-700/50"
                        title="Click to see unread messages summary"
                      >
                        <span>📬</span>
                        <span>{summary.totals.unread} Unread</span>
                      </button>
                    )}
                    {summary.totals.complaints > 0 && (
                      <button
                        onClick={() => generateCategorySummary('complaints')}
                        className="action-badge-on-pane inline-flex items-center gap-2 px-4 py-2.5 bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-200 rounded-xl text-sm font-semibold hover:bg-yellow-200 dark:hover:bg-yellow-900/60 hover:text-yellow-900 dark:hover:text-yellow-100 hover:shadow-md transition-all duration-300 ease-out border border-yellow-300 dark:border-yellow-700/50"
                        title="Click to see complaints summary"
                      >
                        <span>⚠️</span>
                        <span>{summary.totals.complaints} Complaints</span>
                      </button>
                    )}
                    {summary.totals.leads > 0 && (
                      <button
                        onClick={() => generateCategorySummary('leads')}
                        className="action-badge-on-pane inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 rounded-xl text-sm font-semibold hover:bg-emerald-200 dark:hover:bg-emerald-900/60 hover:text-emerald-900 dark:hover:text-emerald-100 hover:shadow-md transition-all duration-300 ease-out border border-emerald-300 dark:border-emerald-700/50"
                        title="Click to see leads summary"
                      >
                        <span>💼</span>
                        <span>{summary.totals.leads} Leads</span>
                      </button>
                    )}
                  </div>
                  
                  {/* Summary Text - Generated by LLM */}
                  {summary.summaryGenerating && !summary.summaryParagraph ? (
                    <div className="mt-5 flex items-center gap-3 text-[var(--muted)]">
                      <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-[var(--primary)]"></div>
                      <span className="text-sm font-medium">Generating AI summary...</span>
                    </div>
                  ) : summary.summaryParagraph ? (
                    <div className="mt-5 p-5 bg-white/60 rounded-xl border border-[var(--glass-border)]">
                      <p className="text-gray-800 leading-relaxed text-base font-normal text-premium">
                        {summary.summaryParagraph}
                      </p>
                    </div>
                  ) : (
                    <div className="mt-5 p-5 bg-white/60 rounded-xl border border-[var(--glass-border)]">
                      <p className="text-gray-800 leading-relaxed text-sm">
                        Unable to generate AI summary. Please ensure Ollama is running:
                      </p>
                      <div className="mt-3 space-y-1">
                        <code className="block p-2 bg-white/40 rounded text-xs">ollama serve</code>
                        <code className="block p-2 bg-white/40 rounded text-xs">ollama pull tinyllama</code>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-[var(--glass-border)] mb-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-3 text-sm font-semibold transition-all rounded-t-xl ${
              activeTab === 'overview'
                ? 'text-[var(--primary)] border-b-2 border-[var(--primary)] bg-white/50'
                : 'text-theme-muted hover:text-[var(--text-hover)] hover:bg-[var(--bg-hover)]'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('summary')}
            className={`px-6 py-3 text-sm font-semibold transition-all rounded-t-xl ${
              activeTab === 'summary'
                ? 'text-[var(--primary)] border-b-2 border-[var(--primary)] bg-white/50'
                : 'text-theme-muted hover:text-[var(--text-hover)] hover:bg-[var(--bg-hover)]'
            }`}
          >
            Summary
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'summary' ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="glass-card p-8"
          >
            <h2 className="text-xl font-semibold text-theme-primary mb-4 heading-premium">
              Category Summary
            </h2>
            {generatingCategorySummary ? (
              <div className="py-8 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--primary)]"></div>
                <p className="mt-4 text-[var(--muted)] font-medium">Generating summary...</p>
              </div>
            ) : categorySummary ? (
              <div className="prose max-w-none">
                <p className="text-theme-secondary leading-relaxed text-base whitespace-pre-wrap text-premium">
                  {categorySummary}
                </p>
              </div>
            ) : (
              <div className="text-center py-8 text-[var(--muted)]">
                <p>Click on a badge above to generate a summary for that category.</p>
              </div>
            )}
          </motion.div>
        ) : (
          <>
            {/* Summary Cards */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5"
            >
              <GlassCard className="p-6">
                <p className="text-sm font-medium text-[var(--muted)] mb-3 uppercase tracking-wide">Total Messages</p>
                <p className="text-4xl font-bold text-theme-primary heading-premium">
                  <AnimatedNumber value={summary.totals.totalMessages} />
                </p>
              </GlassCard>
              <GlassCard className="p-6">
                <p className="text-sm font-medium text-[var(--muted)] mb-3 uppercase tracking-wide">Unread</p>
                <p className="text-4xl font-bold text-theme-primary heading-premium">
                  <AnimatedNumber value={summary.totals.unread} />
                </p>
              </GlassCard>
              <GlassCard className="p-6">
                <p className="text-sm font-medium text-[var(--muted)] mb-3 uppercase tracking-wide">Leads</p>
                <p className="text-4xl font-bold text-theme-primary heading-premium">
                  <AnimatedNumber value={summary.totals.leads} />
                </p>
              </GlassCard>
              <GlassCard className="p-6">
                <p className="text-sm font-medium text-[var(--muted)] mb-3 uppercase tracking-wide">Complaints</p>
                <p className="text-4xl font-bold text-theme-primary heading-premium">
                  <AnimatedNumber value={summary.totals.complaints} />
                </p>
              </GlassCard>
            </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Tasks Panel - Wider */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="lg:col-span-3"
          >
            <GlassCard className="p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-theme-primary heading-premium">Tasks</h2>
              <Link
                href="/tasks"
                className="text-sm text-[var(--primary)] hover:underline font-medium"
              >
                View all
              </Link>
            </div>

            {/* Priority Counts - Clickable Filters */}
            <div className="flex gap-3 mb-8 pb-6 border-b border-[var(--glass-border)]">
              <button
                onClick={() => setTaskFilter('all')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                  taskFilter === 'all'
                    ? 'bg-[var(--primary)]/10 border-2 border-[var(--primary)]'
                    : 'bg-white/60 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] hover:bg-white/80 dark:hover:bg-[var(--card-bg)]/90 hover:text-[var(--text-hover)]'
                }`}
                aria-label="Show all tasks"
              >
                <span className="text-sm font-semibold text-theme-primary">All</span>
                <span className="text-sm font-bold text-theme-primary">
                  {summary.tasks.counts.P0 + summary.tasks.counts.P1 + summary.tasks.counts.P2}
                </span>
              </button>
              <button
                onClick={() => setTaskFilter('P0')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                  taskFilter === 'P0'
                    ? 'bg-red-50 dark:bg-red-900/30 border-2 border-red-300 dark:border-red-700/50'
                    : 'bg-white/60 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] hover:bg-white/80 dark:hover:bg-[var(--card-bg)]/90 hover:text-[var(--text-hover)]'
                }`}
                aria-label="Filter P0 tasks"
              >
                <TaskPriorityBadge priority="P0" variant="on-pane" />
                <span className="text-base font-semibold text-theme-primary">
                  {summary.tasks.counts.P0}
                </span>
              </button>
              <button
                onClick={() => setTaskFilter('P1')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                  taskFilter === 'P1'
                    ? 'bg-amber-50 dark:bg-amber-900/30 border-2 border-amber-300 dark:border-amber-700/50'
                    : 'bg-white/60 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] hover:bg-white/80 dark:hover:bg-[var(--card-bg)]/90 hover:text-[var(--text-hover)]'
                }`}
                aria-label="Filter P1 tasks"
              >
                <TaskPriorityBadge priority="P1" variant="on-pane" />
                <span className="text-base font-semibold text-theme-primary">
                  {summary.tasks.counts.P1}
                </span>
              </button>
              <button
                onClick={() => setTaskFilter('P2')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                  taskFilter === 'P2'
                    ? 'bg-gray-50 dark:bg-gray-800/30 border-2 border-gray-300 dark:border-gray-700/50'
                    : 'bg-white/60 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] hover:bg-white/80 dark:hover:bg-[var(--card-bg)]/90 hover:text-[var(--text-hover)]'
                }`}
                aria-label="Filter P2 tasks"
              >
                <TaskPriorityBadge priority="P2" variant="on-pane" />
                <span className="text-base font-semibold text-theme-primary">
                  {summary.tasks.counts.P2}
                </span>
              </button>
            </div>

            {/* Filtered Tasks Display - Scrollable */}
            <div className="max-h-[600px] overflow-y-auto custom-scrollbar pr-2">
              {(taskFilter === 'all' || taskFilter === 'P0') && summary.tasks.P0.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-lg font-semibold text-theme-primary mb-5 heading-premium">
                    P0 - Urgent ({summary.tasks.P0.length})
                  </h3>
                  <TaskPriorityList tasks={summary.tasks.P0} maxItems={taskFilter === 'P0' ? 20 : 6} />
                </div>
              )}

              {(taskFilter === 'all' || taskFilter === 'P1') && summary.tasks.P1.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-lg font-semibold text-theme-primary mb-5 heading-premium">
                    P1 - High ({summary.tasks.P1.length})
                  </h3>
                  <TaskPriorityList tasks={summary.tasks.P1} maxItems={taskFilter === 'P1' ? 20 : 6} />
                </div>
              )}

              {(taskFilter === 'all' || taskFilter === 'P2') && summary.tasks.P2.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-theme-primary mb-5 heading-premium">
                    P2 - Normal ({summary.tasks.P2.length})
                  </h3>
                  <TaskPriorityList tasks={summary.tasks.P2} maxItems={taskFilter === 'P2' ? 20 : 6} />
                </div>
              )}
            </div>

            {((taskFilter === 'all' && summary.tasks.P0.length === 0 && summary.tasks.P1.length === 0 && summary.tasks.P2.length === 0) ||
              (taskFilter === 'P0' && summary.tasks.P0.length === 0) ||
              (taskFilter === 'P1' && summary.tasks.P1.length === 0) ||
              (taskFilter === 'P2' && summary.tasks.P2.length === 0)) && (
              <p className="text-base text-[var(--muted)] py-8 font-medium text-center">
                No {taskFilter === 'all' ? '' : taskFilter + ' '}tasks at the moment
              </p>
            )}
            </GlassCard>
          </motion.div>

          {/* Top Leads */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.3 }}
            className="lg:col-span-1"
          >
            <GlassCard className="p-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6 heading-premium">
              Top Leads
            </h2>
            {summary.topLeads.length > 0 ? (
              <div className="space-y-3">
                {summary.topLeads.map((lead) => (
                  <div
                    key={lead.id}
                    className="p-4 rounded-xl border border-[var(--glass-border)] bg-white/40 dark:bg-[var(--card-bg)] hover:bg-white/60 dark:hover:bg-[var(--card-bg)]/90 hover:text-[var(--text-hover)] hover:shadow-sm transition-all duration-300 ease-out cursor-pointer"
                  >
                    <p className="text-base font-semibold text-gray-900 mb-1 heading-premium">
                      {lead.name}
                    </p>
                    {lead.company && (
                      <p className="text-sm text-[var(--muted)] font-medium mb-1">
                        {lead.company}
                      </p>
                    )}
                    {lead.email && (
                      <p className="text-xs text-[var(--muted)] break-words mb-2">
                        {lead.email}
                      </p>
                    )}
                    {lead.message_count !== undefined && (
                      <p className="text-xs font-medium text-[var(--primary)] mt-2">
                        {lead.message_count} message{lead.message_count !== 1 ? 's' : ''}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--muted)] py-8 text-center font-medium">
                No leads at the moment
              </p>
            )}
            </GlassCard>
          </motion.div>
        </div>
          </>
        )}

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.4 }}
          className="flex flex-wrap gap-4 pt-4"
        >
          <Link
            href="/inbox"
            className="px-6 py-3 bg-[var(--primary)] text-white rounded-xl hover:opacity-90 transition-all shadow-md hover:shadow-lg font-semibold focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2"
            aria-label="Open inbox"
          >
            Open Inbox
          </Link>
          <Link
            href="/tasks"
            className="px-6 py-3 bg-white/90 dark:bg-[var(--card-bg)] backdrop-blur-sm border border-[var(--glass-border)] text-theme-primary rounded-xl hover:bg-white dark:hover:bg-[var(--card-bg)]/90 hover:text-[var(--text-hover)] hover:shadow-md transition-all duration-300 ease-out font-semibold focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2"
            aria-label="View tasks"
          >
            View Tasks
          </Link>
          <button
            onClick={() => router.push('/inbox?action=create')}
            className="px-6 py-3 bg-white/90 dark:bg-[var(--card-bg)] backdrop-blur-sm border border-[var(--glass-border)] text-theme-primary rounded-xl hover:bg-white dark:hover:bg-[var(--card-bg)]/90 hover:text-[var(--text-hover)] hover:shadow-md transition-all duration-300 ease-out font-semibold focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2"
            aria-label="Create follow-up"
          >
            Create Follow-up
          </button>
        </motion.div>
      </div>
    </div>
  );
}
