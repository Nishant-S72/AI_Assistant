/**
 * Calendar Page
 * Extended with full event + reminder functionality similar to Google Calendar
 */
'use client';

import { useEffect, useState } from 'react';
import { api, CalendarEvent } from '@/lib/api';
import GlassCard from '@/components/GlassCard';
import EventModal from '@/components/EventModal';
import { motion } from 'framer-motion';
import { SkeletonLoader } from '@/components/SkeletonLoader';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isEventModalOpen, setIsEventModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);
  const [initialDate, setInitialDate] = useState<Date | undefined>();
  const [initialStartTime, setInitialStartTime] = useState<Date | undefined>();
  const [initialEndTime, setInitialEndTime] = useState<Date | undefined>();
  const [showGoogleEvents, setShowGoogleEvents] = useState(true);
  const [isGoogleConnected, setIsGoogleConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get start and end of month for fetching events
  const monthStart = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
  const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0, 23, 59, 59);

  useEffect(() => {
    loadEvents();
    checkGoogleConnection();
  }, [currentDate, showGoogleEvents]);

  const checkGoogleConnection = async () => {
    // TODO: Check if Google is connected via API
    setIsGoogleConnected(false);
  };

  const loadEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const start = monthStart.toISOString();
      const end = monthEnd.toISOString();
      
      // Use new calendar API
      const response = await api.calendar.listEvents(
        start,
        end,
        showGoogleEvents ? undefined : 'local'
      );
      
      setEvents(response.events);
    } catch (err: any) {
      console.error('Error loading calendar events:', err);
      setError(err.message || 'Failed to load calendar events');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEvent = (date?: Date, startTime?: Date, endTime?: Date) => {
    setEditingEvent(null);
    setInitialDate(date);
    setInitialStartTime(startTime);
    setInitialEndTime(endTime);
    setIsEventModalOpen(true);
  };

  const handleEditEvent = (event: CalendarEvent) => {
    setEditingEvent(event);
    setInitialDate(undefined);
    setInitialStartTime(undefined);
    setInitialEndTime(undefined);
    setIsEventModalOpen(true);
  };

  const handleDeleteEvent = async (eventId: string) => {
    if (!confirm('Are you sure you want to delete this event?')) return;
    
    try {
      await api.calendar.deleteEvent(eventId, false); // TODO: Add sync option
      loadEvents();
    } catch (error) {
      console.error('Error deleting event:', error);
      alert('Failed to delete event');
    }
  };

  const handleImportGoogle = async () => {
    if (!isGoogleConnected) {
      alert('Google Calendar is not connected. Please connect it first.');
      return;
    }
    
    try {
      const start = new Date().toISOString();
      const end = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(); // Next 30 days
      
      const result = await api.calendar.importGoogle(start, end);
      alert(`Imported ${result.imported} events, updated ${result.updated} events`);
      loadEvents();
    } catch (error) {
      console.error('Error importing Google events:', error);
      alert('Failed to import events from Google');
    }
  };

  // Get today's events
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  const todayEvents = events.filter((event) => {
    const eventDate = new Date(event.start);
    return eventDate >= today && eventDate < tomorrow;
  });

  // Get events for selected date
  const selectedDateEvents = events.filter((event) => {
    const eventDate = new Date(event.start);
    const selected = new Date(selectedDate);
    selected.setHours(0, 0, 0, 0);
    const selectedNext = new Date(selected);
    selectedNext.setDate(selectedNext.getDate() + 1);
    return eventDate >= selected && eventDate < selectedNext;
  });

  // Calendar grid helpers
  const daysInMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0).getDate();
  const firstDayOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1).getDay();
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  const getEventsForDate = (date: Date) => {
    const dateStr = date.toDateString();
    return events.filter((event) => {
      const eventDate = new Date(event.start);
      return eventDate.toDateString() === dateStr;
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const isSelected = (date: Date) => {
    return date.toDateString() === selectedDate.toDateString();
  };

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentDate((prev) => {
      const newDate = new Date(prev);
      if (direction === 'prev') {
        newDate.setMonth(newDate.getMonth() - 1);
      } else {
        newDate.setMonth(newDate.getMonth() + 1);
      }
      return newDate;
    });
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6" style={{ maxHeight: 'calc(100vh - 4rem)' }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-theme-primary heading-premium">Calendar</h1>
        <div className="flex items-center gap-4">
          {/* Google Import Button */}
          {isGoogleConnected && (
            <button
              onClick={handleImportGoogle}
              className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 transition-opacity"
            >
              Import from Google
            </button>
          )}
          
          {/* Filter Toggle */}
          {isGoogleConnected && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showGoogleEvents}
                onChange={(e) => setShowGoogleEvents(e.target.checked)}
                className="w-4 h-4 text-[var(--primary)] rounded focus:ring-[var(--primary)]"
              />
              <span className="text-sm text-theme-primary">Show Google events</span>
            </label>
          )}
          
          {/* Create Event Button */}
          <button
            onClick={() => handleCreateEvent()}
            className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 transition-opacity"
          >
            + Create Event
          </button>
          
          <div className="text-lg text-theme-secondary">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Today's Events */}
        <div className="lg:col-span-1">
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-theme-primary mb-4 heading-premium">
              Today's Events
            </h2>
            {loading ? (
              <SkeletonLoader variant="event" count={3} />
            ) : error ? (
              <ErrorState
                message={error}
                onRetry={loadEvents}
                className="py-4"
              />
            ) : todayEvents.length === 0 ? (
              <EmptyState
                icon="📅"
                title="No events today"
                description="You have no events scheduled for today."
                className="py-4"
              />
            ) : (
              <div className="space-y-3">
                {todayEvents.map((event) => (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 rounded-lg bg-white/40 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] hover:bg-white/60 dark:hover:bg-[var(--card-bg)]/90 transition-all cursor-pointer group"
                    onClick={() => handleEditEvent(event)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: event.color }}
                          />
                          <h3 className="font-semibold text-theme-primary">{event.title}</h3>
                        </div>
                        {!event.all_day && (
                          <p className="text-sm text-theme-secondary mt-1">
                            {formatTime(event.start)} - {formatTime(event.end)}
                          </p>
                        )}
                        {event.location && (
                          <p className="text-xs text-theme-muted mt-1">📍 {event.location}</p>
                        )}
                        {event.recurrence_rule && (
                          <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-[var(--primary)]/10 text-[var(--primary)] rounded">
                            Recurring
                          </span>
                        )}
                        {event.source === 'google' && (
                          <span className="inline-block mt-1 ml-2 px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                            Google
                          </span>
                        )}
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteEvent(event.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-opacity"
                        aria-label="Delete event"
                      >
                        ✕
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </GlassCard>
        </div>

        {/* Calendar Grid */}
        <div className="lg:col-span-2">
          <GlassCard className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 8rem)' }}>
            <div className="flex items-center justify-between mb-6">
              <button
                onClick={() => navigateMonth('prev')}
                className="p-2 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
                aria-label="Previous month"
              >
                ←
              </button>
              <h2 className="text-xl font-semibold text-theme-primary heading-premium">
                {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
              </h2>
              <button
                onClick={() => navigateMonth('next')}
                className="p-2 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
                aria-label="Next month"
              >
                →
              </button>
            </div>

            {/* Day names */}
            <div className="grid grid-cols-7 gap-1 mb-2">
              {dayNames.map((day) => (
                <div key={day} className="text-center text-sm font-semibold text-theme-muted py-2">
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar days */}
            <div className="grid grid-cols-7 gap-1">
              {/* Empty cells for days before month starts */}
              {Array.from({ length: firstDayOfMonth }).map((_, i) => (
                <div key={`empty-${i}`} className="aspect-square"></div>
              ))}

              {/* Days of the month */}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), i + 1);
                const dateEvents = getEventsForDate(date);
                const isTodayDate = isToday(date);
                const isSelectedDate = isSelected(date);

                return (
                  <div
                    key={i}
                    className={`aspect-square p-1 rounded-lg transition-all relative ${
                      isTodayDate
                        ? 'bg-[var(--primary)] text-white font-semibold'
                        : isSelectedDate
                        ? 'bg-[var(--primary)]/20 text-[var(--primary)] font-semibold'
                        : 'hover:bg-[var(--bg-hover)] text-theme-primary'
                    }`}
                  >
                    <button
                      onClick={() => setSelectedDate(date)}
                      className="w-full h-full flex flex-col items-start"
                    >
                      <div className="text-sm mb-1">{i + 1}</div>
                      {dateEvents.length > 0 && (
                        <div className="flex gap-0.5 justify-center flex-wrap w-full">
                          {dateEvents.slice(0, 3).map((event, idx) => (
                            <div
                              key={event.id}
                              className="w-1.5 h-1.5 rounded-full"
                              style={{ backgroundColor: event.color }}
                              title={event.title}
                            />
                          ))}
                          {dateEvents.length > 3 && (
                            <div className="text-xs">+{dateEvents.length - 3}</div>
                          )}
                        </div>
                      )}
                    </button>
                    {/* Click to add event */}
                    <button
                      onClick={() => handleCreateEvent(date)}
                      className="absolute inset-0 opacity-0 hover:opacity-100 flex items-center justify-center text-xs text-theme-muted hover:text-[var(--primary)] transition-opacity"
                      aria-label={`Add event on ${date.toLocaleDateString()}`}
                    >
                      +
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Selected date events */}
            {selectedDateEvents.length > 0 && (
              <div className="mt-6 pt-6 border-t border-[var(--glass-border)]">
                <h3 className="text-lg font-semibold text-theme-primary mb-3 heading-premium">
                  {selectedDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                </h3>
                <div className="space-y-2">
                  {selectedDateEvents.map((event) => (
                    <div
                      key={event.id}
                      className="p-3 rounded-lg bg-white/40 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] hover:bg-white/60 dark:hover:bg-[var(--card-bg)]/90 transition-all cursor-pointer"
                      onClick={() => handleEditEvent(event)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: event.color }}
                            />
                            <h4 className="font-semibold text-theme-primary">{event.title}</h4>
                          </div>
                          {!event.all_day && (
                            <p className="text-sm text-theme-secondary mt-1">
                              {formatTime(event.start)} - {formatTime(event.end)}
                            </p>
                          )}
                          {event.description && (
                            <p className="text-sm text-theme-secondary mt-1">{event.description}</p>
                          )}
                          {event.location && (
                            <p className="text-xs text-theme-muted mt-1">📍 {event.location}</p>
                          )}
                          {event.attendees && event.attendees.length > 0 && (
                            <p className="text-xs text-theme-muted mt-1">
                              👥 {event.attendees.length} attendee{event.attendees.length !== 1 ? 's' : ''}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteEvent(event.id);
                          }}
                          className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                          aria-label="Delete event"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      {/* Event Modal */}
      <EventModal
        isOpen={isEventModalOpen}
        onClose={() => {
          setIsEventModalOpen(false);
          setEditingEvent(null);
        }}
        event={editingEvent}
        initialDate={initialDate}
        initialStartTime={initialStartTime}
        initialEndTime={initialEndTime}
        onSave={loadEvents}
      />
    </div>
  );
}
