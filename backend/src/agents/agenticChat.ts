/**
 * Agentic AI Chat Agent with LLM-Based Function Calling
 * LLM decides which function to call (calendar event, policy docs, or direct answer)
 */

import { pool } from '../db';
import { generateChatCompletion, LLMMessage } from '../clients/llm';
import * as fs from 'fs';
import * as path from 'path';

// Agent state interface
export interface AgentState {
  messages: Array<{ role: 'user' | 'assistant'; content: string; timestamp: Date }>;
  sessionId: string;
  context: {
    inboxStats?: string;
    tasksStats?: string;
    lastActivity: Date;
  };
  tools: {
    calendarEventCreated?: any;
  };
}

// Session storage
const agentSessions = new Map<string, AgentState>();

// Clean up inactive sessions (older than 1 hour)
setInterval(() => {
  const now = Date.now();
  const oneHour = 60 * 60 * 1000;
  
  for (const [sessionId, state] of agentSessions.entries()) {
    if (now - state.context.lastActivity.getTime() > oneHour) {
      agentSessions.delete(sessionId);
      console.log(`[Agent] Cleared inactive session: ${sessionId}`);
    }
  }
}, 5 * 60 * 1000); // Every 5 minutes

// Tool: Create calendar event
async function createCalendarEvent(text: string): Promise<{ success: boolean; event?: any; message: string }> {
  try {
    const port = process.env.PORT || 3001;
    const calendarParseUrl = `http://localhost:${port}/api/calendar/parse`;
    
    console.log(`[Agent] Creating calendar event via: ${calendarParseUrl}`);
    console.log(`[Agent] Request text: ${text}`);
    
    const response = await fetch(calendarParseUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    console.log(`[Agent] Calendar API response status: ${response.status}`);

    if (response.ok) {
      const data = await response.json() as { event?: any; parsed?: any };
      console.log(`[Agent] Calendar API response:`, JSON.stringify(data).substring(0, 200));
      
      if (data.event) {
        console.log(`[Agent] ✅ Calendar event created: ${data.event.title}`);
        return {
          success: true,
          event: data.event,
          message: `Calendar event "${data.event.title}" created successfully.`,
        };
      } else {
        console.warn(`[Agent] Calendar API returned OK but no event in response`);
      }
    } else {
      const errorText = await response.text();
      console.error(`[Agent] Calendar API error (${response.status}): ${errorText}`);
    }
    
    return { success: false, message: 'Failed to create calendar event.' };
  } catch (error: any) {
    console.error('[Agent] Calendar event creation error:', error);
    console.error('[Agent] Error stack:', error.stack);
    return { success: false, message: `Error: ${error.message}` };
  }
}

// Tool: Get policy document
function getPolicyDocument(): string {
  const possiblePaths = [
    path.join(__dirname, '../../policies/company-policy.md'),
    path.join(__dirname, '../../../backend/policies/company-policy.md'),
    path.join(process.cwd(), 'backend/policies/company-policy.md'),
    path.join(process.cwd(), 'policies/company-policy.md'),
    path.resolve(process.cwd(), 'backend/policies/company-policy.md'),
    path.resolve(process.cwd(), 'policies/company-policy.md'),
  ];

  try {
    for (const policyPath of possiblePaths) {
      if (fs.existsSync(policyPath)) {
        const content = fs.readFileSync(policyPath, 'utf-8');
        console.log(`[Agent] Policy document loaded from: ${policyPath}`);
        return content;
      }
    }
    console.warn('[Agent] Policy document not found');
    return '';
  } catch (error: any) {
    console.error('[Agent] Error loading policy document:', error.message);
    return '';
  }
}

// Tool: Get policy context (rules)
function getPolicyContext(): string {
  try {
    const policyPath = path.join(__dirname, '../../policy.json');
    if (fs.existsSync(policyPath)) {
      const policy = JSON.parse(fs.readFileSync(policyPath, 'utf-8'));
      return JSON.stringify(policy.rules || [], null, 2);
    }
  } catch (error) {
    console.error('[Agent] Error loading policy:', error);
  }
  return 'No policy rules available';
}

// Tool: Get inbox stats
async function getInboxStats(): Promise<string> {
  try {
    const result = await pool.query(`
      SELECT COUNT(*) as total, 
             COUNT(*) FILTER (WHERE read_at IS NULL) as unread,
             COUNT(*) FILTER (WHERE EXISTS (
               SELECT 1 FROM contacts c WHERE c.id = messages.contact_id AND c.tags::text LIKE '%lead%'
             )) as leads
      FROM messages
    `);
    
    if (result.rows.length > 0) {
      const stats = result.rows[0];
      return `Inbox: ${stats.total} total messages, ${stats.unread} unread, ${stats.leads} leads.`;
    }
    return 'Inbox stats unavailable.';
  } catch (error: any) {
    return `Error fetching inbox stats: ${error.message}`;
  }
}

// Tool: Get tasks stats
async function getTasksStats(): Promise<string> {
  try {
    const result = await pool.query(`
      SELECT 
        COUNT(*) FILTER (WHERE priority = 'P0') as p0,
        COUNT(*) FILTER (WHERE priority = 'P1') as p1,
        COUNT(*) FILTER (WHERE priority = 'P2') as p2,
        COUNT(*) FILTER (WHERE status = 'pending') as pending
      FROM tasks
    `);
    
    if (result.rows.length > 0) {
      const stats = result.rows[0];
      return `Tasks: ${stats.pending} pending (${stats.p0} P0 urgent, ${stats.p1} P1 high, ${stats.p2} P2 normal).`;
    }
    return 'Tasks stats unavailable.';
  } catch (error: any) {
    return `Error fetching tasks stats: ${error.message}`;
  }
}

// LLM-based function calling: Determine which function to call
async function decideFunctionCall(question: string): Promise<{
  function: 'create_calendar_event' | 'get_policy_document' | 'answer_directly';
  confidence: number;
  reasoning: string;
}> {
  const systemPrompt = `You are a function router. Analyze the user's question and decide which function to call.

Available functions:
1. create_calendar_event - Call this if the user wants to schedule, book, plan, or create a calendar event, meeting, or appointment. Look for time/date references.
2. get_policy_document - Call this ONLY if the user explicitly mentions "policy", "policies", "rules", "guidelines", "escalation", or asks about company policies/rules.
3. answer_directly - Call this for all other questions (general chat, inbox questions, task questions, etc.)

Respond with ONLY a JSON object in this exact format:
{
  "function": "create_calendar_event" | "get_policy_document" | "answer_directly",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}

Examples:
User: "Schedule a meeting tomorrow at 2pm"
→ {"function": "create_calendar_event", "confidence": 0.95, "reasoning": "User wants to schedule a meeting with specific time"}

User: "What is the refund policy?"
→ {"function": "get_policy_document", "confidence": 0.9, "reasoning": "User explicitly asks about policy"}

User: "Hi"
→ {"function": "answer_directly", "confidence": 1.0, "reasoning": "Simple greeting"}

User: "How many unread messages do I have?"
→ {"function": "answer_directly", "confidence": 1.0, "reasoning": "Question about inbox, not calendar or policy"}

Return ONLY the JSON, no other text.`;

  try {
    const llmResponse = await generateChatCompletion({
      model: process.env.LLM_MODEL || 'tinyllama',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: question },
      ] as LLMMessage[],
      temperature: 0.1, // Low temperature for consistent function selection
      max_tokens: 150,
      useLocal: process.env.USE_OLLAMA !== 'false',
    });

    // Parse JSON response
    let decision;
    try {
      const jsonMatch = llmResponse.content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        decision = JSON.parse(jsonMatch[0]);
      } else {
        decision = JSON.parse(llmResponse.content.trim());
      }
    } catch (parseError) {
      console.warn('[Agent] Failed to parse function decision, defaulting to answer_directly');
      console.warn('[Agent] LLM response:', llmResponse.content);
      return {
        function: 'answer_directly',
        confidence: 0.5,
        reasoning: 'Failed to parse LLM response',
      };
    }

    // Validate function name
    if (!['create_calendar_event', 'get_policy_document', 'answer_directly'].includes(decision.function)) {
      console.warn(`[Agent] Invalid function name: ${decision.function}, defaulting to answer_directly`);
      decision.function = 'answer_directly';
    }

    console.log(`[Agent] Function decision: ${decision.function} (confidence: ${decision.confidence})`);
    console.log(`[Agent] Reasoning: ${decision.reasoning}`);

    return {
      function: decision.function as 'create_calendar_event' | 'get_policy_document' | 'answer_directly',
      confidence: decision.confidence || 0.5,
      reasoning: decision.reasoning || 'No reasoning provided',
    };
  } catch (error: any) {
    console.error('[Agent] Error in function decision:', error);
    return {
      function: 'answer_directly',
      confidence: 0.5,
      reasoning: `Error: ${error.message}`,
    };
  }
}

// Main agentic chat function
export async function runAgenticChat(
  question: string,
  sessionId: string,
  conversationHistory?: Array<{ role: string; content: string }>
): Promise<{ answer: string; sessionId: string; calendarEvent?: any }> {
  try {
    // Remove question length limit (was 200 chars) - allow full questions
    // Only trim excessive whitespace
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      throw new Error('Question cannot be empty');
    }
    // Get or create session state
    let state: AgentState;
    if (agentSessions.has(sessionId)) {
      state = agentSessions.get(sessionId)!;
      state.context.lastActivity = new Date();
    } else {
      state = {
        messages: [],
        sessionId,
        context: {
          lastActivity: new Date(),
        },
        tools: {},
      };
      agentSessions.set(sessionId, state);
    }

    // Load context if not already loaded
    if (!state.context.inboxStats || !state.context.tasksStats) {
      try {
        state.context.inboxStats = await getInboxStats();
        state.context.tasksStats = await getTasksStats();
      } catch (error) {
        console.warn('[Agent] Could not load context:', error);
      }
    }

    // Add conversation history to state
    if (conversationHistory && conversationHistory.length > 0) {
      const historyMessages = conversationHistory
        .slice(-10) // Last 10 messages
        .map((msg) => ({
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          timestamp: new Date(),
        }));
      state.messages.push(...historyMessages);
    }

    // Add current user message (no length limit - was 200 chars)
    state.messages.push({
      role: 'user',
      content: trimmedQuestion,
      timestamp: new Date(),
    });

    // Step 1: LLM decides which function to call
    const functionDecision = await decideFunctionCall(question);
    console.log(`[Agent] Decided to call: ${functionDecision.function} (confidence: ${functionDecision.confidence})`);

    let calendarEvent = null;
    let policyContext = '';
    let policyDocument = '';

    // Step 2: Execute the chosen function
    if (functionDecision.function === 'create_calendar_event' && functionDecision.confidence > 0.7) {
      console.log('[Agent] Executing: create_calendar_event (confidence:', functionDecision.confidence, ')');
      const result = await createCalendarEvent(question);
      console.log('[Agent] Calendar creation result:', result.success ? 'SUCCESS' : 'FAILED', result.message);
      
      if (result.success && result.event) {
        calendarEvent = result.event;
        state.tools.calendarEventCreated = result.event;
        
        // Format confirmation message
        const eventTime = new Date(calendarEvent.start_time).toLocaleString('en-US', {
          weekday: 'long',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
        });
        
        const confirmationMessage = `✅ I've added "${calendarEvent.title}" to your calendar for ${eventTime}.${calendarEvent.location ? ` Location: ${calendarEvent.location}.` : ''}${calendarEvent.is_recurring ? ` This is a ${calendarEvent.recurrence_pattern} recurring event.` : ''}`;
        
        // Add confirmation to messages
        state.messages.push({
          role: 'assistant',
          content: confirmationMessage,
          timestamp: new Date(),
        });
        
        // Update session
        agentSessions.set(sessionId, state);
        
        console.log('[Agent] ✅ Returning calendar event confirmation');
        return {
          answer: confirmationMessage,
          sessionId,
          calendarEvent,
        };
      } else {
        // Calendar creation failed, fall through to answer with error
        console.warn('[Agent] Calendar event creation failed:', result.message);
        // Continue to generate a response explaining the failure
      }
    } else if (functionDecision.function === 'get_policy_document') {
      console.log('[Agent] Executing: get_policy_document');
      policyContext = getPolicyContext();
      policyDocument = getPolicyDocument();
      console.log(`[Agent] Loaded policy document (${policyDocument.length} chars)`);
    }
    // else: answer_directly - continue to LLM response

    // Step 3: Generate LLM response with appropriate context
    const isSimpleGreeting = /^(hi|hello|hey|greetings|good morning|good afternoon|good evening)$/i.test(question.trim());
    
    let systemPrompt: string;
    
    if (isSimpleGreeting) {
      // Minimal prompt for greetings
      systemPrompt = `You are Soraya AI. The user just said "${question}". Respond with a brief, friendly greeting. Do not list capabilities, context, policies, or any technical information. Keep it to 1-2 sentences maximum (under 50 words).`;
    } else {
      // Full prompt for other questions
      systemPrompt = `You are Soraya AI, a helpful assistant for managing inbox, tasks, and calendar.`;

      // Always add context if available - use it in your answers
      if (state.context.inboxStats || state.context.tasksStats) {
        systemPrompt += `\n\nIMPORTANT - Use this actual data when answering questions:\n${state.context.inboxStats || ''}\n${state.context.tasksStats || ''}\n\nWhen asked about inbox or tasks, use the numbers above. Don't say "I don't have access" - you have the data.`;
      }

      // Add policy information ONLY if get_policy_document was called
      if (functionDecision.function === 'get_policy_document' && policyDocument) {
        systemPrompt += `\n\nCompany Policy Document:\n${policyDocument}`;
        if (policyContext && policyContext !== 'No policy rules available') {
          try {
            const parsedRules = JSON.parse(policyContext);
            systemPrompt += `\n\nEscalation Rules:\n${JSON.stringify(parsedRules.slice(0, 5), null, 2)}`;
          } catch (e) {
            // Ignore parse errors
          }
        }
      }

      systemPrompt += `\n\nYour capabilities:
- Answer questions about inbox, tasks, and calendar using the context data provided above
- Create calendar events when asked (I will handle the creation automatically)

CRITICAL GUIDELINES:
- Use the actual context data provided above when answering questions
- Be natural and conversational
- Only provide information that's directly relevant to the question
- Don't mention policies, rules, or escalation keywords unless explicitly asked
- Keep responses SHORT and concise - maximum 150 words (preferably under 100 words)
- When user wants to schedule something, acknowledge that you'll add it to their calendar
- If you have context data, USE IT - don't say "I don't have access"`;

      if (calendarEvent) {
        systemPrompt += `\n\nNote: A calendar event was just created: ${(calendarEvent as any).title}`;
      }
    }

    // Build conversation messages for LLM
    // Include recent conversation history for context (increased from 8 to 15)
    const recentMessages = state.messages
      .slice(-15) // Last 15 messages for context (increased from 8)
      .map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));
    
    // Smart truncation: prioritize policy document and context, truncate less important parts
    let finalSystemPrompt = systemPrompt;
    const maxSystemPromptLength = 3000; // Increased from 2000
    
    if (finalSystemPrompt.length > maxSystemPromptLength) {
      // If policy document is included, keep it and truncate other parts
      const policyDocMatch = finalSystemPrompt.match(/(Company Policy Document:[\s\S]+?)(?=\n\n|$)/);
      const contextMatch = finalSystemPrompt.match(/(IMPORTANT - Use this actual data:[\s\S]+?)(?=\n\n|$)/);
      
      // Keep essential parts
      let essentialParts = '';
      if (contextMatch) essentialParts += contextMatch[0] + '\n\n';
      if (policyDocMatch) essentialParts += policyDocMatch[0] + '\n\n';
      
      // Truncate capabilities/guidelines if needed
      const remainingLength = maxSystemPromptLength - essentialParts.length;
      const capabilitiesMatch = finalSystemPrompt.match(/(Your capabilities:[\s\S]+?)(?=\n\n|$)/);
      if (capabilitiesMatch) {
        const truncatedCapabilities = capabilitiesMatch[0].substring(0, Math.min(remainingLength - 200, capabilitiesMatch[0].length));
        finalSystemPrompt = essentialParts + truncatedCapabilities;
      } else {
        finalSystemPrompt = essentialParts + finalSystemPrompt.substring(0, remainingLength);
      }
      
      console.log(`[Agent] System prompt truncated from ${systemPrompt.length} to ${finalSystemPrompt.length} chars`);
    }
    
    // Check for truncated prompts and log warning
    if (finalSystemPrompt.length >= maxSystemPromptLength * 0.95) {
      console.warn(`[Agent] ⚠️  System prompt is near limit (${finalSystemPrompt.length}/${maxSystemPromptLength} chars). Some content may be truncated.`);
    }
    
    // Validate message structure before sending
    if (recentMessages.length === 0 && finalSystemPrompt.length === 0) {
      throw new Error('No messages to send to LLM');
    }
    
    const llmMessages: LLMMessage[] = [
      {
        role: 'system',
        content: finalSystemPrompt,
      },
      ...recentMessages,
    ];
    
    if (llmMessages[0].content.length === 0) {
      throw new Error('System prompt is empty');
    }

    // Generate response using LLM
    const useOllama = process.env.USE_OLLAMA !== 'false';
    const model = process.env.LLM_MODEL || 'tinyllama';
    
    const llmResponse = await generateChatCompletion({
      model,
      messages: llmMessages,
      temperature: 0.5, // Lower temperature for more focused responses
      max_tokens: 150, // Reduced from 200 to enforce brevity
      useLocal: useOllama,
    });

    if (!llmResponse || !llmResponse.content) {
      console.error('[Agent] ❌ LLM returned invalid response');
      throw new Error('LLM returned invalid response');
    }

    const answer = llmResponse.content.trim();
    
    // Log if answer seems truncated (very short or ends abruptly)
    if (answer.length < 10) {
      console.warn('[Agent] ⚠️  LLM response is unusually short, may be truncated');
    }

    // Add assistant response to state
    state.messages.push({
      role: 'assistant',
      content: answer,
      timestamp: new Date(),
    });

    // Keep only last 20 messages in state
    if (state.messages.length > 20) {
      state.messages = state.messages.slice(-20);
    }

    // Update session
    agentSessions.set(sessionId, state);

    return {
      answer,
      sessionId,
      calendarEvent,
    };
  } catch (error: any) {
    console.error('[Agent] Error running agentic chat:', error);
    throw error;
  }
}

// Get session state (for debugging)
export function getAgentSession(sessionId: string): AgentState | undefined {
  return agentSessions.get(sessionId);
}

// Clear session (for testing)
export function clearAgentSession(sessionId: string): void {
  agentSessions.delete(sessionId);
}
