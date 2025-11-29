import { Router, Request, Response } from 'express';
import { pool } from '../db';
import { generateChatCompletion, LLMMessage } from '../clients/llm';

const router = Router();

// GET /api/calendar/events - Get events for a date range
router.get('/events', async (req: Request, res: Response) => {
  try {
    const { start, end } = req.query;
    
    if (!start || !end) {
      return res.status(400).json({ error: 'Start and end dates are required' });
    }

    const startDate = new Date(start as string);
    const endDate = new Date(end as string);

    // Get all events in the date range, including recurring ones
    const result = await pool.query(
      `SELECT * FROM calendar_events 
       WHERE (start_time >= $1 AND start_time <= $2)
          OR (is_recurring = true AND recurrence_end_date >= $1)
       ORDER BY start_time ASC`,
      [startDate, endDate]
    );

    // Expand recurring events
    const events: any[] = [];
    for (const event of result.rows) {
      if (event.is_recurring && event.recurrence_pattern) {
        // Generate instances of recurring events
        const instances = generateRecurringInstances(event, startDate, endDate);
        events.push(...instances);
      } else {
        events.push(event);
      }
    }

    res.json({ events: events.sort((a, b) => 
      new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
    ) });
  } catch (error: any) {
    console.error('Error fetching calendar events:', error);
    res.status(500).json({ error: 'Failed to fetch calendar events', details: error.message });
  }
});

// POST /api/calendar/events - Create a new event
router.post('/events', async (req: Request, res: Response) => {
  try {
    const {
      title,
      description,
      start_time,
      end_time,
      is_recurring,
      recurrence_pattern,
      recurrence_end_date,
      recurrence_interval,
      location,
      attendees,
    } = req.body;

    if (!title || !start_time || !end_time) {
      return res.status(400).json({ error: 'Title, start_time, and end_time are required' });
    }

    const result = await pool.query(
      `INSERT INTO calendar_events 
       (title, description, start_time, end_time, is_recurring, recurrence_pattern, 
        recurrence_end_date, recurrence_interval, location, attendees)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING *`,
      [
        title,
        description || null,
        new Date(start_time),
        new Date(end_time),
        is_recurring || false,
        recurrence_pattern || null,
        recurrence_end_date ? new Date(recurrence_end_date) : null,
        recurrence_interval || 1,
        location || null,
        attendees ? JSON.stringify(attendees) : '[]',
      ]
    );

    res.status(201).json({ event: result.rows[0] });
  } catch (error: any) {
    console.error('Error creating calendar event:', error);
    res.status(500).json({ error: 'Failed to create calendar event', details: error.message });
  }
});

// POST /api/calendar/parse - Parse natural language to create event
router.post('/parse', async (req: Request, res: Response) => {
  try {
    const { text } = req.body;

    if (!text) {
      return res.status(400).json({ error: 'Text is required' });
    }

    // Use LLM to parse natural language into event details
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowDateStr = tomorrow.toISOString().split('T')[0];
    
    const systemPrompt = `You are a strict JSON parser. Extract calendar event details from natural language.

CRITICAL RULES:
1. Return ONLY valid JSON - no explanations, no markdown, no code blocks
2. Start with { and end with }
3. Use double quotes for all strings
4. Calculate dates relative to: ${now.toISOString()}
5. Tomorrow is: ${tomorrowDateStr}

JSON Schema:
{
  "title": "string (required)",
  "start_time": "ISO 8601 datetime (required)",
  "end_time": "ISO 8601 datetime (required, default: 1 hour after start)",
  "description": "string or null",
  "is_recurring": "boolean",
  "recurrence_pattern": "daily|weekly|monthly|yearly or null",
  "recurrence_interval": "number (default 1)",
  "location": "string or null",
  "attendees": "array of strings or null"
}

Examples (copy format exactly):
"Meeting tomorrow at 2pm" → {"title":"Meeting","start_time":"${tomorrowDateStr}T14:00:00","end_time":"${tomorrowDateStr}T15:00:00"}
"Standup every Monday 9am" → {"title":"Standup","start_time":"2024-11-25T09:00:00","end_time":"2024-11-25T09:30:00","is_recurring":true,"recurrence_pattern":"weekly"}

Return ONLY the JSON object, nothing else.`;

    const llmResponse = await generateChatCompletion({
      model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: text },
      ] as LLMMessage[],
      temperature: 0.0, // Very low temperature for deterministic JSON
      max_tokens: 150,
      useLocal: process.env.USE_OLLAMA !== 'false', // Default to Ollama if not explicitly false
    });

    // Parse LLM response (should be JSON)
    let eventData;
    try {
      let jsonText = llmResponse.content.trim();
      
      // Remove markdown code blocks if present
      jsonText = jsonText.replace(/```json\s*/g, '').replace(/```\s*/g, '');
      
      // Find JSON object (handle multiline)
      const jsonMatch = jsonText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        eventData = JSON.parse(jsonMatch[0]);
      } else {
        // Try parsing the whole response
        eventData = JSON.parse(jsonText);
      }
      
      console.log('[Calendar Parse] Extracted event data:', JSON.stringify(eventData, null, 2));
    } catch (parseError: any) {
      console.error('[Calendar Parse] JSON parse error:', parseError);
      console.error('[Calendar Parse] LLM response:', llmResponse.content.substring(0, 300));
      
      // Enhanced fallback parser
      try {
        console.log('[Calendar Parse] Attempting enhanced fallback parser...');
        const lowerText = text.toLowerCase();
        
        // Extract title - improved patterns
        let title = 'Meeting';
        const titlePatterns = [
          /(?:schedule|add|create|book|plan)\s+(?:a\s+)?(?:meeting|call|appointment|event|standup|sync|review|conference)\s+(?:called|titled|named)?\s*["']?([^"']+)["']?/i,
          /(?:meeting|call|appointment|event|standup|sync|review|conference)\s+(?:called|titled|named)?\s*["']?([^"']+?)(?:\s+tomorrow|\s+today|\s+at|\s+on|$)/i,
          /["']([^"']+?)["']\s+(?:meeting|call|appointment|event)/i,
        ];
        
        for (const pattern of titlePatterns) {
          const match = text.match(pattern);
          if (match && match[1] && match[1].trim().length > 0) {
            title = match[1].trim();
            break;
          }
        }
        
        // If no specific title found, use generic based on keywords
        if (title === 'Meeting') {
          if (lowerText.includes('standup')) title = 'Team Standup';
          else if (lowerText.includes('call')) title = 'Call';
          else if (lowerText.includes('appointment')) title = 'Appointment';
          else if (lowerText.includes('review')) title = 'Review';
          else if (lowerText.includes('sync')) title = 'Sync';
        }
        
        // Extract time
        const now = new Date();
        let startDate = new Date(now);
        let hour = 14; // Default 2pm
        let minute = 0;
        
        // Check for "tomorrow"
        if (lowerText.includes('tomorrow')) {
          startDate = new Date(now.getTime() + 24 * 60 * 60 * 1000);
        }
        
        // Extract time - improved pattern
        const timeMatch = text.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
        if (timeMatch) {
          hour = parseInt(timeMatch[1]);
          if (timeMatch[3]) {
            const ampm = timeMatch[3].toLowerCase();
            if (ampm === 'pm' && hour < 12) {
              hour += 12;
            } else if (ampm === 'am' && hour === 12) {
              hour = 0;
            }
          }
          if (timeMatch[2]) {
            minute = parseInt(timeMatch[2]);
          }
        }
        
        startDate.setHours(hour, minute, 0, 0);
        const endDate = new Date(startDate);
        endDate.setHours(endDate.getHours() + 1);
        
        // Check for recurring
        let isRecurring = false;
        let recurrencePattern = null;
        if (lowerText.includes('every') || lowerText.includes('weekly') || lowerText.includes('daily') || lowerText.includes('monthly')) {
          isRecurring = true;
          if (lowerText.includes('daily') || lowerText.includes('every day')) {
            recurrencePattern = 'daily';
          } else if (lowerText.includes('weekly') || lowerText.includes('every week') || lowerText.includes('every monday')) {
            recurrencePattern = 'weekly';
          } else if (lowerText.includes('monthly') || lowerText.includes('every month')) {
            recurrencePattern = 'monthly';
          } else {
            recurrencePattern = 'weekly'; // Default
          }
        }
        
        eventData = {
          title: title.substring(0, 100),
          start_time: startDate.toISOString(),
          end_time: endDate.toISOString(),
          is_recurring: isRecurring,
          recurrence_pattern: recurrencePattern,
        };
        
        console.log('[Calendar Parse] Enhanced fallback parser result:', JSON.stringify(eventData, null, 2));
      } catch (fallbackError) {
        return res.status(400).json({ 
          error: 'Could not parse event from text',
          details: llmResponse.content.substring(0, 200)
        });
      }
    }

    // Validate required fields
    if (!eventData.title || !eventData.start_time) {
      return res.status(400).json({ 
        error: 'Could not extract required fields (title, start_time)',
        parsed: eventData 
      });
    }

    // Set default end_time if not provided
    if (!eventData.end_time) {
      const start = new Date(eventData.start_time);
      start.setHours(start.getHours() + 1);
      eventData.end_time = start.toISOString();
    }

    // Create the event
    const result = await pool.query(
      `INSERT INTO calendar_events 
       (title, description, start_time, end_time, is_recurring, recurrence_pattern, 
        recurrence_end_date, recurrence_interval, location, attendees)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING *`,
      [
        eventData.title,
        eventData.description || null,
        new Date(eventData.start_time),
        new Date(eventData.end_time),
        eventData.is_recurring || false,
        eventData.recurrence_pattern || null,
        eventData.recurrence_end_date ? new Date(eventData.recurrence_end_date) : null,
        eventData.recurrence_interval || 1,
        eventData.location || null,
        eventData.attendees ? JSON.stringify(eventData.attendees) : '[]',
      ]
    );

    res.status(201).json({ event: result.rows[0], parsed: eventData });
  } catch (error: any) {
    console.error('Error parsing calendar event:', error);
    res.status(500).json({ error: 'Failed to parse calendar event', details: error.message });
  }
});

// PUT /api/calendar/events/:id - Update an event
router.put('/events/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const updates = req.body;

    const allowedFields = [
      'title', 'description', 'start_time', 'end_time', 'is_recurring',
      'recurrence_pattern', 'recurrence_end_date', 'recurrence_interval',
      'location', 'attendees'
    ];

    const updateFields: string[] = [];
    const values: any[] = [];
    let paramIndex = 1;

    for (const field of allowedFields) {
      if (updates[field] !== undefined) {
        updateFields.push(`${field} = $${paramIndex}`);
        if (field === 'attendees') {
          values.push(JSON.stringify(updates[field]));
        } else if (field.includes('_time') || field.includes('_date')) {
          values.push(new Date(updates[field]));
        } else {
          values.push(updates[field]);
        }
        paramIndex++;
      }
    }

    if (updateFields.length === 0) {
      return res.status(400).json({ error: 'No valid fields to update' });
    }

    updateFields.push(`updated_at = NOW()`);
    values.push(id);

    const result = await pool.query(
      `UPDATE calendar_events SET ${updateFields.join(', ')} WHERE id = $${paramIndex} RETURNING *`,
      values
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }

    res.json({ event: result.rows[0] });
  } catch (error: any) {
    console.error('Error updating calendar event:', error);
    res.status(500).json({ error: 'Failed to update calendar event', details: error.message });
  }
});

// DELETE /api/calendar/events/:id - Delete an event
router.delete('/events/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const result = await pool.query('DELETE FROM calendar_events WHERE id = $1 RETURNING *', [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }

    res.json({ success: true, deleted: result.rows[0] });
  } catch (error: any) {
    console.error('Error deleting calendar event:', error);
    res.status(500).json({ error: 'Failed to delete calendar event', details: error.message });
  }
});

// Helper function to generate recurring event instances
function generateRecurringInstances(event: any, startDate: Date, endDate: Date): any[] {
  const instances: any[] = [];
  const eventStart = new Date(event.start_time);
  const eventEnd = new Date(event.end_time);
  const duration = eventEnd.getTime() - eventStart.getTime();
  
  let currentDate = new Date(Math.max(eventStart.getTime(), startDate.getTime()));
  const recurrenceEnd = event.recurrence_end_date ? new Date(event.recurrence_end_date) : endDate;
  const end = new Date(Math.min(recurrenceEnd.getTime(), endDate.getTime()));

  while (currentDate <= end) {
    if (currentDate >= startDate) {
      const instanceStart = new Date(currentDate);
      instanceStart.setHours(eventStart.getHours(), eventStart.getMinutes(), 0, 0);
      
      const instanceEnd = new Date(instanceStart.getTime() + duration);

      // Check if this date matches the recurrence pattern
      let shouldInclude = false;
      
      switch (event.recurrence_pattern) {
        case 'daily':
          shouldInclude = true;
          currentDate.setDate(currentDate.getDate() + (event.recurrence_interval || 1));
          break;
        case 'weekly':
          // Check if it's the same day of week
          if (instanceStart.getDay() === eventStart.getDay()) {
            shouldInclude = true;
            currentDate.setDate(currentDate.getDate() + 7 * (event.recurrence_interval || 1));
          } else {
            currentDate.setDate(currentDate.getDate() + 1);
          }
          break;
        case 'monthly':
          // Same day of month
          if (instanceStart.getDate() === eventStart.getDate()) {
            shouldInclude = true;
            currentDate.setMonth(currentDate.getMonth() + (event.recurrence_interval || 1));
          } else {
            currentDate.setDate(currentDate.getDate() + 1);
          }
          break;
        case 'yearly':
          // Same month and day
          if (instanceStart.getMonth() === eventStart.getMonth() && 
              instanceStart.getDate() === eventStart.getDate()) {
            shouldInclude = true;
            currentDate.setFullYear(currentDate.getFullYear() + (event.recurrence_interval || 1));
          } else {
            currentDate.setDate(currentDate.getDate() + 1);
          }
          break;
        default:
          currentDate.setDate(currentDate.getDate() + 1);
      }

      if (shouldInclude) {
        instances.push({
          ...event,
          id: `${event.id}-${instanceStart.toISOString()}`,
          start_time: instanceStart.toISOString(),
          end_time: instanceEnd.toISOString(),
          is_instance: true,
          parent_event_id: event.id,
        });
      }
    } else {
      currentDate.setDate(currentDate.getDate() + 1);
    }
  }

  return instances;
}

export default router;

