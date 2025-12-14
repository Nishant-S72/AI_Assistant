/**
 * Event Modal Component
 * 
 * Modal for creating/editing calendar events with full Google Calendar-like functionality.
 */
'use client';

import { useState, useEffect } from 'react';
import { api, CalendarEvent, Reminder } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';

interface EventModalProps {
  isOpen: boolean;
  onClose: () => void;
  event?: CalendarEvent | null;  // If provided, edit mode; otherwise create mode
  initialDate?: Date;  // Pre-fill date from calendar click
  initialStartTime?: Date;  // Pre-fill start time from calendar click
  initialEndTime?: Date;  // Pre-fill end time from calendar click
  onSave: () => void;  // Callback after successful save
}

const EVENT_COLORS = [
  { name: 'Blue', value: '#4285F4' },
  { name: 'Green', value: '#34A853' },
  { name: 'Yellow', value: '#FBBC04' },
  { name: 'Orange', value: '#FF9800' },
  { name: 'Red', value: '#EA4335' },
  { name: 'Purple', value: '#9C27B0' },
  { name: 'Pink', value: '#E91E63' },
  { name: 'Teal', value: '#009688' },
];

const REMINDER_OPTIONS = [
  { label: 'At time of event', minutes: 0 },
  { label: '10 minutes before', minutes: 10 },
  { label: '30 minutes before', minutes: 30 },
  { label: '1 hour before', minutes: 60 },
  { label: '1 day before', minutes: 1440 },
];

export default function EventModal({
  isOpen,
  onClose,
  event,
  initialDate,
  initialStartTime,
  initialEndTime,
  onSave,
}: EventModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [videoLink, setVideoLink] = useState('');
  const [allDay, setAllDay] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endDate, setEndDate] = useState('');
  const [endTime, setEndTime] = useState('');
  const [timezone, setTimezone] = useState('UTC');
  const [color, setColor] = useState('#4285F4');
  const [recurrence, setRecurrence] = useState<'none' | 'daily' | 'weekly' | 'monthly' | 'custom'>('none');
  const [customRRULE, setCustomRRULE] = useState('');
  const [attendees, setAttendees] = useState<Array<{ email: string; name?: string }>>([]);
  const [newAttendeeEmail, setNewAttendeeEmail] = useState('');
  const [newAttendeeName, setNewAttendeeName] = useState('');
  const [reminders, setReminders] = useState<Array<{ minutes_before?: number; when?: string; channel: string }>>([]);
  const [syncToGoogle, setSyncToGoogle] = useState(false);
  const [isGoogleConnected, setIsGoogleConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize form from event or initial values
  useEffect(() => {
    if (event) {
      // Edit mode
      setTitle(event.title);
      setDescription(event.description || '');
      setLocation(event.location || '');
      setVideoLink(event.video_link || '');
      setAllDay(event.all_day);
      setColor(event.color);
      setTimezone(event.timezone);
      setAttendees(event.attendees || []);
      setSyncToGoogle(event.source === 'google');
      
      const start = new Date(event.start);
      const end = new Date(event.end);
      setStartDate(start.toISOString().split('T')[0]);
      setStartTime(start.toTimeString().slice(0, 5));
      setEndDate(end.toISOString().split('T')[0]);
      setEndTime(end.toTimeString().slice(0, 5));
      
      // Parse recurrence
      if (event.recurrence_rule) {
        if (event.recurrence_rule.includes('FREQ=DAILY')) {
          setRecurrence('daily');
        } else if (event.recurrence_rule.includes('FREQ=WEEKLY')) {
          setRecurrence('weekly');
        } else if (event.recurrence_rule.includes('FREQ=MONTHLY')) {
          setRecurrence('monthly');
        } else {
          setRecurrence('custom');
          setCustomRRULE(event.recurrence_rule);
        }
      } else {
        setRecurrence('none');
      }
      
      // Load reminders
      loadReminders(event.id);
    } else {
      // Create mode - use initial values or defaults
      const now = initialDate || new Date();
      const start = initialStartTime || new Date(now);
      start.setMinutes(0);
      const end = initialEndTime || new Date(start.getTime() + 60 * 60 * 1000);
      
      setStartDate(start.toISOString().split('T')[0]);
      setStartTime(start.toTimeString().slice(0, 5));
      setEndDate(end.toISOString().split('T')[0]);
      setEndTime(end.toTimeString().slice(0, 5));
      setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone);
      
      // Reset other fields
      setTitle('');
      setDescription('');
      setLocation('');
      setVideoLink('');
      setAllDay(false);
      setColor('#4285F4');
      setRecurrence('none');
      setCustomRRULE('');
      setAttendees([]);
      setReminders([]);
      setSyncToGoogle(false);
    }
    
    // Check Google connection
    checkGoogleConnection();
  }, [event, initialDate, initialStartTime, initialEndTime]);

  const checkGoogleConnection = async () => {
    // TODO: Check if Google is connected via API
    // For now, assume false
    setIsGoogleConnected(false);
  };

  const loadReminders = async (eventId: string) => {
    try {
      const response = await api.calendar.listReminders(eventId);
      setReminders(
        response.reminders.map((r) => ({
          minutes_before: r.minutes_before,
          when: r.when,
          channel: r.channel,
        }))
      );
    } catch (err) {
      console.error('Failed to load reminders:', err);
    }
  };

  const addAttendee = () => {
    if (newAttendeeEmail.trim()) {
      setAttendees([...attendees, { email: newAttendeeEmail.trim(), name: newAttendeeName.trim() || undefined }]);
      setNewAttendeeEmail('');
      setNewAttendeeName('');
    }
  };

  const removeAttendee = (index: number) => {
    setAttendees(attendees.filter((_, i) => i !== index));
  };

  const addReminder = (minutes: number) => {
    setReminders([...reminders, { minutes_before: minutes, channel: 'inapp' }]);
  };

  const removeReminder = (index: number) => {
    setReminders(reminders.filter((_, i) => i !== index));
  };

  const generateRRULE = (): string | undefined => {
    if (recurrence === 'none') return undefined;
    if (recurrence === 'custom') return customRRULE || undefined;
    
    const freq = recurrence.toUpperCase();
    return `FREQ=${freq};INTERVAL=1`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Build start/end datetimes
      const startDateTime = allDay
        ? new Date(`${startDate}T00:00:00`)
        : new Date(`${startDate}T${startTime}:00`);
      const endDateTime = allDay
        ? new Date(`${endDate}T23:59:59`)
        : new Date(`${endDate}T${endTime}:00`);

      const eventData = {
        title,
        description: description || undefined,
        location: location || undefined,
        video_link: videoLink || undefined,
        start: startDateTime.toISOString(),
        end: endDateTime.toISOString(),
        all_day: allDay,
        color,
        timezone,
        recurrence_rule: generateRRULE(),
        attendees: attendees.length > 0 ? attendees : undefined,
        sync_to_google: syncToGoogle && isGoogleConnected,
      };

      if (event) {
        // Update existing event
        await api.calendar.updateEvent(event.id, eventData);
      } else {
        // Create new event
        const created = await api.calendar.createEvent(eventData);
        
        // Create reminders
        for (const reminder of reminders) {
          try {
            await api.calendar.createReminder(created.id, reminder);
          } catch (err) {
            console.error('Failed to create reminder:', err);
          }
        }
      }

      onSave();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save event');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white dark:bg-[var(--card-bg)] rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        >
          <div className="sticky top-0 bg-white dark:bg-[var(--card-bg)] border-b border-[var(--glass-border)] p-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-theme-primary">
              {event ? 'Edit Event' : 'Create Event'}
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                {error}
              </div>
            )}

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-1">
                Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
                placeholder="Event title"
              />
            </div>

            {/* Date & Time */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-theme-primary mb-1">
                  Start Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                />
              </div>
              {!allDay && (
                <div>
                  <label className="block text-sm font-medium text-theme-primary mb-1">
                    Start Time <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    required
                    className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                  />
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-theme-primary mb-1">
                  End Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                />
              </div>
              {!allDay && (
                <div>
                  <label className="block text-sm font-medium text-theme-primary mb-1">
                    End Time <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    required
                    className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                  />
                </div>
              )}
            </div>

            {/* All Day Toggle */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="allDay"
                checked={allDay}
                onChange={(e) => setAllDay(e.target.checked)}
                className="w-4 h-4 text-[var(--primary)] rounded focus:ring-[var(--primary)]"
              />
              <label htmlFor="allDay" className="text-sm font-medium text-theme-primary">
                All-day event
              </label>
            </div>

            {/* Timezone */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-1">
                Timezone
              </label>
              <select
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">Eastern Time</option>
                <option value="America/Chicago">Central Time</option>
                <option value="America/Denver">Mountain Time</option>
                <option value="America/Los_Angeles">Pacific Time</option>
                <option value="Europe/London">London</option>
                <option value="Asia/Kolkata">India Standard Time</option>
                <option value="Asia/Tokyo">Japan Standard Time</option>
              </select>
            </div>

            {/* Location */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-1">
                Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                placeholder="Event location"
              />
            </div>

            {/* Video Link */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-1">
                Video Link (Zoom/Meet)
              </label>
              <input
                type="url"
                value={videoLink}
                onChange={(e) => setVideoLink(e.target.value)}
                className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                placeholder="https://..."
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary resize-none"
                placeholder="Event description"
              />
            </div>

            {/* Color */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-2">
                Color
              </label>
              <div className="flex gap-2 flex-wrap">
                {EVENT_COLORS.map((c) => (
                  <button
                    key={c.value}
                    type="button"
                    onClick={() => setColor(c.value)}
                    className={`w-10 h-10 rounded-lg border-2 transition-all ${
                      color === c.value
                        ? 'border-theme-primary scale-110'
                        : 'border-transparent hover:border-[var(--glass-border)]'
                    }`}
                    style={{ backgroundColor: c.value }}
                    aria-label={c.name}
                  />
                ))}
              </div>
            </div>

            {/* Recurrence */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-1">
                Recurrence
              </label>
              <select
                value={recurrence}
                onChange={(e) => setRecurrence(e.target.value as any)}
                className="w-full px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
              >
                <option value="none">None</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="custom">Custom (RRULE)</option>
              </select>
              {recurrence === 'custom' && (
                <input
                  type="text"
                  value={customRRULE}
                  onChange={(e) => setCustomRRULE(e.target.value)}
                  placeholder="FREQ=WEEKLY;BYDAY=MO,WE,FR"
                  className="w-full mt-2 px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                />
              )}
            </div>

            {/* Attendees */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-2">
                Attendees
              </label>
              <div className="space-y-2">
                {attendees.map((attendee, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="flex-1 text-sm text-theme-secondary">
                      {attendee.name ? `${attendee.name} <${attendee.email}>` : attendee.email}
                    </span>
                    <button
                      type="button"
                      onClick={() => removeAttendee(idx)}
                      className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={newAttendeeEmail}
                    onChange={(e) => setNewAttendeeEmail(e.target.value)}
                    placeholder="Email"
                    className="flex-1 px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                  />
                  <input
                    type="text"
                    value={newAttendeeName}
                    onChange={(e) => setNewAttendeeName(e.target.value)}
                    placeholder="Name (optional)"
                    className="flex-1 px-3 py-2 border border-[var(--glass-border)] rounded-lg bg-white dark:bg-[var(--card-bg)] text-theme-primary"
                  />
                  <button
                    type="button"
                    onClick={addAttendee}
                    className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:opacity-90"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>

            {/* Reminders */}
            <div>
              <label className="block text-sm font-medium text-theme-primary mb-2">
                Reminders
              </label>
              <div className="space-y-2">
                {reminders.map((reminder, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 bg-[var(--bg-hover)] rounded-lg">
                    <span className="flex-1 text-sm text-theme-secondary">
                      {reminder.minutes_before !== undefined
                        ? `${reminder.minutes_before} minutes before`
                        : reminder.when
                        ? new Date(reminder.when).toLocaleString()
                        : 'Custom reminder'}
                    </span>
                    <button
                      type="button"
                      onClick={() => removeReminder(idx)}
                      className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <div className="flex gap-2 flex-wrap">
                  {REMINDER_OPTIONS.map((option) => (
                    <button
                      key={option.minutes}
                      type="button"
                      onClick={() => addReminder(option.minutes)}
                      className="px-3 py-1 text-sm border border-[var(--glass-border)] rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Sync to Google */}
            {isGoogleConnected && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="syncToGoogle"
                  checked={syncToGoogle}
                  onChange={(e) => setSyncToGoogle(e.target.checked)}
                  className="w-4 h-4 text-[var(--primary)] rounded focus:ring-[var(--primary)]"
                />
                <label htmlFor="syncToGoogle" className="text-sm font-medium text-theme-primary">
                  Sync to Google Calendar
                </label>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 justify-end pt-4 border-t border-[var(--glass-border)]">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-[var(--glass-border)] rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !title}
                className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Saving...' : event ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

