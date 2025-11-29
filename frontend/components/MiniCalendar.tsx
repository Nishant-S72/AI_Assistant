/**
 * Mini Calendar Component
 * Compact calendar widget for sidebar
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, CalendarEvent } from '@/lib/api';

export default function MiniCalendar() {
  const router = useRouter();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selectedDate, setSelectedDate] = useState(new Date());

  const monthStart = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
  const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0, 23, 59, 59);

  useEffect(() => {
    loadEvents();
  }, [currentDate]);

  const loadEvents = async () => {
    try {
      const start = monthStart.toISOString();
      const end = monthEnd.toISOString();
      const eventsData = await api.getCalendarEvents(start, end);
      // Ensure eventsData is always an array
      if (Array.isArray(eventsData)) {
        setEvents(eventsData);
      } else if (eventsData && typeof eventsData === 'object' && 'events' in eventsData) {
        // Handle case where API returns { events: [...] }
        setEvents(Array.isArray(eventsData.events) ? eventsData.events : []);
      } else {
        setEvents([]);
      }
    } catch (error) {
      // Silently fail - mini calendar is non-critical
      console.warn('[MiniCalendar] Failed to load events:', error);
      setEvents([]);
    }
  };

  const daysInMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0).getDate();
  const firstDayOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1).getDay();
  const dayNames = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

  const getEventsForDate = (date: Date) => {
    // Ensure events is always an array before filtering
    if (!Array.isArray(events)) {
      return [];
    }
    const dateStr = date.toDateString();
    return events.filter((event) => {
      if (!event || !event.start_time) return false;
      const eventDate = new Date(event.start_time);
      return eventDate.toDateString() === dateStr;
    });
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const handleDateClick = (date: Date) => {
    setSelectedDate(date);
    router.push('/calendar');
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
    <div className="p-3 border-b border-[var(--glass-border)]">
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={() => navigateMonth('prev')}
          className="p-1 rounded hover:bg-[var(--bg-hover)] transition-colors text-theme-muted hover:text-theme-primary"
          aria-label="Previous month"
        >
          ←
        </button>
        <span className="text-xs font-semibold text-theme-primary">
          {currentDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
        </span>
        <button
          onClick={() => navigateMonth('next')}
          className="p-1 rounded hover:bg-[var(--bg-hover)] transition-colors text-theme-muted hover:text-theme-primary"
          aria-label="Next month"
        >
          →
        </button>
      </div>

      {/* Day names */}
      <div className="grid grid-cols-7 gap-0.5 mb-1">
        {dayNames.map((day, idx) => (
          <div key={idx} className="text-center text-[10px] font-medium text-theme-muted py-0.5">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar days */}
      <div className="grid grid-cols-7 gap-0.5">
        {/* Empty cells for days before month starts */}
        {Array.from({ length: firstDayOfMonth }).map((_, i) => (
          <div key={`empty-${i}`} className="aspect-square"></div>
        ))}

        {/* Days of the month */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), i + 1);
          const dateEvents = getEventsForDate(date);
          const isTodayDate = isToday(date);

          return (
            <button
              key={i}
              onClick={() => handleDateClick(date)}
              className={`aspect-square text-[10px] rounded transition-all ${
                isTodayDate
                  ? 'bg-[var(--primary)] text-white font-semibold'
                  : 'hover:bg-[var(--bg-hover)] text-theme-primary'
              }`}
              title={dateEvents.length > 0 ? `${dateEvents.length} event${dateEvents.length > 1 ? 's' : ''}` : ''}
            >
              <div className="flex flex-col items-center justify-center h-full">
                <span>{i + 1}</span>
                {dateEvents.length > 0 && (
                  <div className="w-1 h-1 rounded-full bg-[var(--primary)] mt-0.5" />
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

