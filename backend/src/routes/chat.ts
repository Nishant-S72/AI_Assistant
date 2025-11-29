/**
 * Chat API Route
 * Handles questions about inbox, policies, tasks, etc.
 */

import { Router, Request, Response } from 'express';
import { pool } from '../db';
import { generateChatCompletion, LLMMessage } from '../clients/llm';
import { checkPolicy } from '../policy/policyEngine';
import { runAgenticChat } from '../agents/agenticChat';
import * as fs from 'fs';
import * as path from 'path';

const router = Router();

// In-memory session storage for conversation context
// Key: sessionId, Value: { messages: LLMMessage[], lastActivity: Date }
interface SessionContext {
  messages: LLMMessage[];
  lastActivity: Date;
}

const sessionContexts = new Map<string, SessionContext>();

// Clean up inactive sessions (older than 1 hour)
setInterval(() => {
  const now = Date.now();
  const oneHour = 60 * 60 * 1000; // 1 hour in milliseconds
  
  for (const [sessionId, context] of sessionContexts.entries()) {
    if (now - context.lastActivity.getTime() > oneHour) {
      sessionContexts.delete(sessionId);
      console.log(`[Chat] Cleared inactive session: ${sessionId}`);
    }
  }
}, 5 * 60 * 1000); // Check every 5 minutes

// Load policy rules for context
function getPolicyContext(): string {
  try {
    const policyPath = path.join(__dirname, '../../policy.json');
    if (fs.existsSync(policyPath)) {
      const policy = JSON.parse(fs.readFileSync(policyPath, 'utf-8'));
      return JSON.stringify(policy.rules || [], null, 2);
    }
  } catch (error) {
    console.error('Error loading policy:', error);
  }
  return 'No policy rules available';
}

// Load comprehensive policy document
function getPolicyDocument(): string {
  try {
    // Try multiple possible paths (dev and production)
    const possiblePaths = [
      // Production (compiled to dist/)
      path.join(__dirname, '../../policies/company-policy.md'),
      path.join(__dirname, '../../../backend/policies/company-policy.md'),
      // Development
      path.join(process.cwd(), 'backend/policies/company-policy.md'),
      path.join(process.cwd(), 'policies/company-policy.md'),
      // Absolute path fallback
      path.resolve(process.cwd(), 'backend/policies/company-policy.md'),
      path.resolve(process.cwd(), 'policies/company-policy.md'),
    ];

    for (const policyPath of possiblePaths) {
      if (fs.existsSync(policyPath)) {
        const content = fs.readFileSync(policyPath, 'utf-8');
        console.log(`[Chat] Policy document loaded from: ${policyPath} (${content.length} chars)`);
        return content;
      }
    }
    
    console.warn('[Chat] Policy document not found. Tried paths:', possiblePaths);
  } catch (error: any) {
    console.error('[Chat] Error loading policy document:', error.message);
  }
  return '';
}

// POST /api/chat - Answer questions about inbox, policies, tasks
router.post('/', async (req: Request, res: Response) => {
  try {
    const { question, conversationHistory, sessionId } = req.body;

    if (!question || typeof question !== 'string') {
      return res.status(400).json({ error: 'Question is required' });
    }

    // Use agentic chat agent (maintains state and context, creates calendar events automatically)
    try {
      const agentSessionId = sessionId || `agent_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const result = await runAgenticChat(question, agentSessionId, conversationHistory);
      
      return res.json({
        answer: result.answer,
        model: process.env.LLM_MODEL || 'tinyllama',
        calendarEvent: result.calendarEvent,
        sessionId: result.sessionId,
      });
    } catch (agentError: any) {
      console.error('[Chat] Agentic chat error, falling back to simple chat:', agentError);
      // Fall through to simple chat implementation below
    }

    // Fallback: Simple chat implementation (if agentic chat fails)
    // Get or create session context
    let sessionContext: SessionContext;
    if (sessionId && sessionContexts.has(sessionId)) {
      sessionContext = sessionContexts.get(sessionId)!;
      sessionContext.lastActivity = new Date();
    } else {
      // Create new session
      const newSessionId = sessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionContext = {
        messages: [],
        lastActivity: new Date(),
      };
      if (sessionId) {
        sessionContexts.set(sessionId, sessionContext);
      }
    }

    // Build conversation history from provided history or session context
    let conversationMessages: LLMMessage[] = [];
    
    // Use provided conversation history if available, otherwise use session context
    if (conversationHistory && Array.isArray(conversationHistory)) {
      conversationMessages = conversationHistory
        .slice(-10) // Limit to last 10 messages
        .map((msg: any) => ({
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content,
        })) as LLMMessage[];
    } else if (sessionContext.messages.length > 0) {
      conversationMessages = sessionContext.messages.slice(-10);
    }

    // Add current question to conversation
    conversationMessages.push({
      role: 'user',
      content: question.substring(0, 200), // Limit question length
    });

    // Gather context about inbox, tasks, and policies
    let inboxContext = '';
    let tasksContext = '';
    
    try {
      // Check if database is available
      await pool.query('SELECT 1');
      
      // Get inbox summary
      const inboxResult = await pool.query(`
        SELECT COUNT(*) as total, 
               COUNT(*) FILTER (WHERE read_at IS NULL) as unread,
               COUNT(*) FILTER (WHERE EXISTS (
                 SELECT 1 FROM contacts c WHERE c.id = messages.contact_id AND c.tags::text LIKE '%lead%'
               )) as leads
        FROM messages
      `);
      
      if (inboxResult.rows.length > 0) {
        const stats = inboxResult.rows[0];
        inboxContext = `Inbox Stats: ${stats.total} total messages, ${stats.unread} unread, ${stats.leads} leads.`;
      }

      // Get tasks summary
      const tasksResult = await pool.query(`
        SELECT 
          COUNT(*) FILTER (WHERE priority = 'P0') as p0,
          COUNT(*) FILTER (WHERE priority = 'P1') as p1,
          COUNT(*) FILTER (WHERE priority = 'P2') as p2,
          COUNT(*) FILTER (WHERE status = 'pending') as pending
        FROM tasks
      `);
      
      if (tasksResult.rows.length > 0) {
        const stats = tasksResult.rows[0];
        tasksContext = `Tasks: ${stats.pending} pending (${stats.p0} P0 urgent, ${stats.p1} P1 high, ${stats.p2} P2 normal).`;
      }
    } catch (dbError: any) {
      console.warn('Could not fetch context from database:', dbError?.message || dbError);
      // Continue without context - use default values
      inboxContext = 'Database unavailable - using offline mode.';
      tasksContext = '';
    }

    // Only load policy if explicitly asked - don't auto-include
    const questionLower = question.toLowerCase();
    const needsPolicyDoc = 
      questionLower.includes('policy') || 
      questionLower.includes('rule') || 
      questionLower.includes('escalat') || 
      questionLower.includes('guideline') || 
      questionLower.includes('procedure') ||
      questionLower.includes('what should i do') ||
      questionLower.includes('how should i handle');
    
    const policyRules = needsPolicyDoc ? getPolicyContext() : 'No policy rules available';
    const policyDocument = needsPolicyDoc ? getPolicyDocument() : ''; // Only load if needed

    // Check if this is a calendar event creation request - be more intelligent
    const isCalendarRequest = 
      (questionLower.includes('schedule') || questionLower.includes('book') || questionLower.includes('plan')) ||
      (questionLower.includes('meeting') && (questionLower.includes('tomorrow') || questionLower.includes('today') || questionLower.includes('next') || questionLower.includes('at') || questionLower.includes('on'))) ||
      (questionLower.includes('event') && (questionLower.includes('add') || questionLower.includes('create') || questionLower.includes('set'))) ||
      (questionLower.includes('calendar') && (questionLower.includes('add') || questionLower.includes('create'))) ||
      (questionLower.includes('appointment')) ||
      (questionLower.includes('remind') && (questionLower.includes('me') || questionLower.includes('tomorrow') || questionLower.includes('today'))) ||
      ((questionLower.includes('add') || questionLower.includes('create') || questionLower.includes('set')) && 
       (questionLower.includes('tomorrow') || questionLower.includes('today') || questionLower.includes('next week') || questionLower.includes('monday') || questionLower.includes('tuesday') || questionLower.includes('wednesday') || questionLower.includes('thursday') || questionLower.includes('friday') || questionLower.includes('saturday') || questionLower.includes('sunday')));

    if (isCalendarRequest) {
      // Forward to calendar parse endpoint
      try {
        const calendarModule = await import('./calendar');
        // We'll handle this in the response by calling the calendar API
        // For now, let's add calendar context to the system prompt
      } catch (error) {
        // Continue with normal chat if calendar module not available
      }
    }

    // Build concise system prompt - check if it's a simple greeting
    const isSimpleGreeting = /^(hi|hello|hey|greetings|good morning|good afternoon|good evening)$/i.test(question.trim());
    
    let systemPrompt = `You are Soraya AI, a helpful assistant for managing inbox, tasks, and calendar.`;

    // Only add context for non-greetings
    if (!isSimpleGreeting && (inboxContext || tasksContext)) {
      systemPrompt += `\n\nCurrent Context:\n${inboxContext} ${tasksContext}`;
    }

    systemPrompt += `\n\nYour capabilities:
- Answer questions about inbox, tasks, and calendar
- Create calendar events when asked (I will handle the creation automatically)

Guidelines:
- Be natural and conversational
- For simple greetings like "Hi" or "Hello", just greet back naturally - don't list capabilities or context
- Only provide information that's directly relevant to the question
- Don't mention policies, rules, escalation keywords, or technical details unless explicitly asked
- Keep responses concise and helpful (maximum 250 words)`;

    try {
      // Only include policy information if explicitly asked AND not a simple greeting
      if (needsPolicyDoc && !isSimpleGreeting) {
        // Safely parse policy rules
        if (policyRules && policyRules !== 'No policy rules available') {
          try {
            const parsedRules = JSON.parse(policyRules);
            if (Array.isArray(parsedRules) && parsedRules.length > 0) {
              systemPrompt += `\n\nEscalation Rules (only mention if relevant): ${JSON.stringify(parsedRules.slice(0, 3))}`;
            }
          } catch (e) {
            // Ignore JSON parse errors
          }
        }

        // Include policy document only if asked
        if (policyDocument) {
          systemPrompt += `\n\nCompany Policy Document:\n${policyDocument}`;
        } else {
          console.warn('[Chat] Policy document not available - check file path');
        }
      }

      systemPrompt += '\n\nKeep answers short, accurate, and direct. Maximum 250 words. Only provide information relevant to the question.';
    } catch (promptError: any) {
      console.warn('[Chat] Error building prompt:', promptError.message);
      // Continue with basic prompt
    }

    // Generate response using LLM
    try {
      // Determine if we should use Ollama (default to true if not explicitly set to false)
      const useOllama = process.env.USE_OLLAMA !== 'false';
      const model = process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama';
      
      console.log(`[Chat] Using model: ${model}, Ollama: ${useOllama}, USE_OLLAMA env: ${process.env.USE_OLLAMA}`);
      
      // Build messages array with system prompt, conversation history, and current question
      const llmMessages: LLMMessage[] = [
        {
          role: 'system',
          content: systemPrompt.substring(0, 1000), // Limit system prompt size for speed
        },
        ...conversationMessages.slice(0, -1), // All conversation history except the current question
        conversationMessages[conversationMessages.length - 1], // Current question (last item)
      ];

      const llmResponse = await generateChatCompletion({
        model,
        messages: llmMessages,
        temperature: 0.6, // Optimized for tinyllama (was 0.3)
        max_tokens: 200, // Limited to ~150 words (under 250 words requirement)
        useLocal: useOllama,
      });

      if (!llmResponse) {
        throw new Error('LLM returned null response');
      }

      if (!llmResponse.content || typeof llmResponse.content !== 'string') {
        throw new Error(`LLM returned invalid response: ${JSON.stringify(llmResponse)}`);
      }

      let answer = llmResponse.content.trim();
      if (!answer) {
        throw new Error('LLM returned empty answer');
      }

      // Update session context with new messages
      if (sessionId && sessionContext) {
        // Add user question and assistant response to session context
        sessionContext.messages.push({
          role: 'user',
          content: question.substring(0, 200),
        });
        sessionContext.messages.push({
          role: 'assistant',
          content: answer,
        });
        
        // Keep only last 20 messages in session context to prevent memory bloat
        if (sessionContext.messages.length > 20) {
          sessionContext.messages = sessionContext.messages.slice(-20);
        }
        
        sessionContext.lastActivity = new Date();
      }

      // If this is a calendar request, automatically parse and create the event (agentic)
      let calendarEvent = null;
      if (isCalendarRequest) {
        try {
          // Use native fetch (Node 18+) to call our own API
          const calendarParseUrl = `http://localhost:${process.env.PORT || 3001}/api/calendar/parse`;
          const calendarResponse = await fetch(calendarParseUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: question }),
          });
          
          if (calendarResponse.ok) {
            const calendarData = await calendarResponse.json() as { event: any; parsed: any };
            calendarEvent = calendarData.event;
            
            // Update the answer to confirm the event was created automatically
            const eventTime = new Date(calendarEvent.start_time).toLocaleString('en-US', {
              weekday: 'long',
              month: 'short',
              day: 'numeric',
              hour: 'numeric',
              minute: '2-digit',
            });
            
            answer = `✅ I've added "${calendarEvent.title}" to your calendar for ${eventTime}.`;
            if (calendarEvent.is_recurring) {
              answer += ` This is a ${calendarEvent.recurrence_pattern} recurring event.`;
            }
            if (calendarEvent.location) {
              answer += ` Location: ${calendarEvent.location}.`;
            }
            if (calendarEvent.description) {
              answer += `\n\n${calendarEvent.description}`;
            }
          }
        } catch (error: any) {
          console.warn('[Chat] Could not create calendar event:', error.message);
          // Continue with normal answer - don't fail the whole request
        }
      }

      return res.json({
        answer,
        model: llmResponse.model || model,
        calendarEvent, // Include created event if applicable
        sessionId: sessionId || undefined, // Return session ID for frontend to maintain
      });
    } catch (llmError: any) {
      console.error('[Chat] LLM generation error:', llmError);
      console.error('[Chat] Error stack:', llmError.stack);
      
      // Provide more helpful error message
      let errorDetails = llmError.message || 'Unknown error';
      if (errorDetails.includes('All LLM adapters failed') || errorDetails.includes('ECONNREFUSED')) {
        const modelName = process.env.LLM_MODEL || 'tinyllama';
        errorDetails = `LLM service unavailable. Please ensure Ollama is running on port 11434 and the ${modelName} model is installed. Run: ollama pull ${modelName}`;
      }
      
      return res.status(500).json({
        error: 'Failed to generate response',
        details: errorDetails,
      });
    }
  } catch (error: any) {
    console.error('Chat error:', error);
    return res.status(500).json({
      error: 'Failed to process question',
      details: error.message || 'Unknown error occurred',
    });
  }
});

export default router;

