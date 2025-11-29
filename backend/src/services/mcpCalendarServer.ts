/**
 * MCP Server for Calendar Events
 * Provides agentic calendar event creation via Model Context Protocol
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { pool } from '../db';

// Calendar event creation tool
const createCalendarEventTool: Tool = {
  name: 'create_calendar_event',
  description: 'Create a calendar event from natural language. Automatically parses date, time, title, and other details.',
  inputSchema: {
    type: 'object',
    properties: {
      text: {
        type: 'string',
        description: 'Natural language description of the event to create (e.g., "Meeting tomorrow at 2pm with John")',
      },
    },
    required: ['text'],
  },
};

export class MCPCalendarServer {
  private server: Server;
  private transport: StdioServerTransport | null = null;

  constructor() {
    this.server = new Server(
      {
        name: 'calendar-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  private setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [createCalendarEventTool],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      if (name === 'create_calendar_event') {
        return await this.handleCreateCalendarEvent(args as { text: string });
      }

      throw new Error(`Unknown tool: ${name}`);
    });
  }

  private async handleCreateCalendarEvent(args: { text: string }) {
    try {
      const { text } = args;

      if (!text) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ error: 'Text is required' }),
            },
          ],
          isError: true,
        };
      }

      // Parse natural language using LLM
      const parsedEvent = await this.parseEventText(text);

      if (!parsedEvent) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ error: 'Failed to parse event details' }),
            },
          ],
          isError: true,
        };
      }

      // Create the event in database
      const result = await pool.query(
        `INSERT INTO calendar_events 
         (title, description, start_time, end_time, is_recurring, recurrence_pattern, 
          recurrence_end_date, location, attendees)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
         RETURNING *`,
        [
          parsedEvent.title,
          parsedEvent.description || null,
          parsedEvent.start_time,
          parsedEvent.end_time,
          parsedEvent.is_recurring || false,
          parsedEvent.recurrence_pattern || null,
          parsedEvent.recurrence_end_date ? new Date(parsedEvent.recurrence_end_date) : null,
          parsedEvent.location || null,
          parsedEvent.attendees ? JSON.stringify(parsedEvent.attendees) : '[]',
        ]
      );

      const event = result.rows[0];

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              event: {
                id: event.id,
                title: event.title,
                start_time: event.start_time,
                end_time: event.end_time,
                location: event.location,
                is_recurring: event.is_recurring,
              },
              message: `Calendar event "${event.title}" created successfully`,
            }),
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              error: 'Failed to create calendar event',
              details: error.message,
            }),
          },
        ],
        isError: true,
      };
    }
  }

  private async parseEventText(text: string): Promise<any> {
    // Use LLM to parse natural language into structured event data
    const { generateChatCompletion } = await import('../clients/llm');

    const prompt = `Parse this calendar event request into structured JSON:
"${text}"

Return ONLY valid JSON with these fields:
{
  "title": "event title",
  "description": "optional description",
  "start_time": "ISO 8601 datetime",
  "end_time": "ISO 8601 datetime",
  "is_recurring": false,
  "recurrence_pattern": null or "Daily"/"Weekly"/"Monthly",
  "recurrence_end_date": null or "ISO 8601 date",
  "location": null or "location string",
  "attendees": [] or ["email1", "email2"]
}

Rules:
- If no time specified, default to 1 hour duration
- If only date specified, default to 9am
- Parse relative dates (today, tomorrow, next week, etc.)
- Parse time formats (2pm, 14:00, 2:00 PM, etc.)
- Extract location if mentioned
- Extract attendees if mentioned
- Set is_recurring and recurrence_pattern if recurring event mentioned

Return ONLY the JSON, no other text.`;

    try {
      const response = await generateChatCompletion({
        model: process.env.LLM_MODEL || 'tinyllama',
        messages: [
          {
            role: 'system',
            content: 'You are a calendar event parser. Return only valid JSON, no explanations.',
          },
          {
            role: 'user',
            content: prompt,
          },
        ],
        temperature: 0.3,
        max_tokens: 300,
        useLocal: process.env.USE_OLLAMA !== 'false',
      });

      const jsonText = response.content.trim();
      // Extract JSON from response (handle markdown code blocks)
      const jsonMatch = jsonText.match(/\{[\s\S]*\}/);
      const parsed = jsonMatch ? JSON.parse(jsonMatch[0]) : JSON.parse(jsonText);

      // Ensure dates are valid
      if (parsed.start_time) {
        parsed.start_time = new Date(parsed.start_time);
      }
      if (parsed.end_time) {
        parsed.end_time = new Date(parsed.end_time);
      }

      return parsed;
    } catch (error: any) {
      console.error('[MCP] Error parsing event:', error);
      // Fallback to simple parsing
      return this.fallbackParse(text);
    }
  }

  private fallbackParse(text: string): any {
    // Simple fallback parser
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(14, 0, 0, 0); // Default to 2pm tomorrow

    return {
      title: text.substring(0, 100) || 'New Event',
      description: text,
      start_time: tomorrow,
      end_time: new Date(tomorrow.getTime() + 60 * 60 * 1000), // 1 hour later
      is_recurring: false,
      recurrence_pattern: null,
      recurrence_end_date: null,
      location: null,
      attendees: [],
    };
  }

  async start() {
    this.transport = new StdioServerTransport();
    await this.server.connect(this.transport);
    console.log('[MCP] Calendar server started');
  }

  async stop() {
    if (this.transport) {
      await this.transport.close();
    }
  }
}

// Export singleton instance
export const mcpCalendarServer = new MCPCalendarServer();

