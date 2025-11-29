/**
 * Calendar Page
 * Shows today's events and a monthly calendar view
 */

'use client';

import { useEffect, useState } from 'react';
import { api, CalendarEvent } from '@/lib/api';
import GlassCard from '@/components/GlassCard';
import { motion } from 'framer-motion';

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date());

  // Get start and end of month for fetching events
  const monthStart = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
  const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0, 23, 59, 59);

  useEffect(() => {
    loadEvents();
  }, [currentDate]);

  // Listen for calendar events created via chat
  useEffect(() => {
    const handleCalendarEventCreated = () => {
      // Reload events when a new one is created via chat
      loadEvents();
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('calendarEventCreated', handleCalendarEventCreated);
      return () => {
        window.removeEventListener('calendarEventCreated', handleCalendarEventCreated);
      };
    }
  }, []);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const start = monthStart.toISOString();
      const end = monthEnd.toISOString();
      const eventsData = await api.getCalendarEvents(start, end);
      setEvents(eventsData);
    } catch (error) {
      console.error('Error loading calendar events:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get today's events
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  const todayEvents = events.filter((event) => {
    const eventDate = new Date(event.start_time);
    return eventDate >= today && eventDate < tomorrow;
  });

  // Get events for selected date
  const selectedDateEvents = events.filter((event) => {
    const eventDate = new Date(event.start_time);
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
      const eventDate = new Date(event.start_time);
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
        <div className="text-lg text-theme-secondary">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
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
              <div className="flex items-center gap-2 text-theme-muted">
                <div className="w-4 h-4 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
                <span>Loading...</span>
              </div>
            ) : todayEvents.length === 0 ? (
              <p className="text-theme-secondary">No events scheduled for today.</p>
            ) : (
              <div className="space-y-3">
                {todayEvents.map((event) => (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 rounded-lg bg-white/40 dark:bg-[var(--card-bg)] border border-[var(--glass-border)] hover:bg-white/60 dark:hover:bg-[var(--card-bg)]/90 transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-theme-primary">{event.title}</h3>
                        <p className="text-sm text-theme-secondary mt-1">
                          {formatTime(event.start_time)} - {formatTime(event.end_time)}
                        </p>
                        {event.location && (
                          <p className="text-xs text-theme-muted mt-1">📍 {event.location}</p>
                        )}
                        {event.is_recurring && (
                          <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-[var(--primary)]/10 text-[var(--primary)] rounded">
                            {event.recurrence_pattern}
                          </span>
                        )}
                      </div>
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
              >
                ←
              </button>
              <h2 className="text-xl font-semibold text-theme-primary heading-premium">
                {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
              </h2>
              <button
                onClick={() => navigateMonth('next')}
                className="p-2 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
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
                  <button
                    key={i}
                    onClick={() => setSelectedDate(date)}
                    className={`aspect-square p-1 rounded-lg transition-all ${
                      isTodayDate
                        ? 'bg-[var(--primary)] text-white font-semibold'
                        : isSelectedDate
                        ? 'bg-[var(--primary)]/20 text-[var(--primary)] font-semibold'
                        : 'hover:bg-[var(--bg-hover)] text-theme-primary'
                    }`}
                  >
                    <div className="text-sm mb-1">{i + 1}</div>
                    {dateEvents.length > 0 && (
                      <div className="flex gap-0.5 justify-center flex-wrap">
                        {dateEvents.slice(0, 3).map((event, idx) => (
                          <div
                            key={event.id}
                            className="w-1.5 h-1.5 rounded-full bg-[var(--primary)]"
                            title={event.title}
                          />
                        ))}
                        {dateEvents.length > 3 && (
                          <div className="text-xs">+{dateEvents.length - 3}</div>
                        )}
                      </div>
                    )}
                  </button>
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
                      className="p-3 rounded-lg bg-white/40 dark:bg-[var(--card-bg)] border border-[var(--glass-border)]"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-semibold text-theme-primary">{event.title}</h4>
                          <p className="text-sm text-theme-secondary mt-1">
                            {formatTime(event.start_time)} - {formatTime(event.end_time)}
                          </p>
                          {event.description && (
                            <p className="text-sm text-theme-secondary mt-1">{event.description}</p>
                          )}
                          {event.location && (
                            <p className="text-xs text-theme-muted mt-1">📍 {event.location}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

