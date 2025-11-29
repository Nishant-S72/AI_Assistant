/**
 * Chat API Route with Intent-Based Routing
 * Routes to: general_intent (conversational), policy_intent (RAG), or action_intent (agentic)
 */

import { Router, Request, Response } from 'express';
import { pool } from '../db';
import { generateChatCompletion, LLMMessage } from '../clients/llm';
import { checkPolicy } from '../policy/policyEngine';
import { classifyIntent, IntentType } from '../policy/intentClassifier';
import { query } from '../clients/vectorstore';
import * as fs from 'fs';
import * as path from 'path';
import { gzip } from 'zlib';
import { promisify } from 'util';
import { v4 as uuidv4 } from 'uuid';

const gzipAsync = promisify(gzip);
const router = Router();

interface ChatRequest {
  threadId?: string;
  userMessage: string;
  tone?: 'formal' | 'warm' | 'crisp';
  correlationId?: string;
}

interface ChatResponse {
  kind: 'assistant' | 'policy' | 'action';
  text: string;
  citations?: Array<{ id: string; score: number; textSnippet: string }>;
  suggestionId: string | null;
  intent: IntentType;
  intent_confidence: number;
  action_suggestion?: {
    action_type: string;
    confirm_needed: boolean;
    extracted_data?: any;
  };
  escalated?: boolean;
}

/**
 * Load prompt template from file
 */
function loadPromptTemplate(templateName: string): string {
  const possiblePaths = [
    path.join(__dirname, `../../prompts/${templateName}`),
    path.join(process.cwd(), `prompts/${templateName}`),
    path.join(process.cwd(), `backend/prompts/${templateName}`),
  ];

  for (const templatePath of possiblePaths) {
    if (fs.existsSync(templatePath)) {
      return fs.readFileSync(templatePath, 'utf-8');
    }
  }

  console.warn(`[Chat] Template not found: ${templateName}, using fallback`);
  return `Template ${templateName} not found. Please answer naturally.`;
}

/**
 * Get inbox/tasks context for conversational responses
 */
async function getInboxContext(): Promise<string> {
  try {
    await pool.query('SELECT 1');
    
    const inboxResult = await pool.query(`
      SELECT COUNT(*) as total, 
             COUNT(*) FILTER (WHERE read_at IS NULL) as unread,
             COUNT(*) FILTER (WHERE EXISTS (
               SELECT 1 FROM contacts c WHERE c.id = messages.contact_id AND c.tags::text LIKE '%lead%'
             )) as leads
      FROM messages
    `);
    
    const tasksResult = await pool.query(`
      SELECT 
        COUNT(*) FILTER (WHERE priority = 'P0') as p0,
        COUNT(*) FILTER (WHERE priority = 'P1') as p1,
        COUNT(*) FILTER (WHERE status = 'pending') as pending
      FROM tasks
    `);
    
    if (inboxResult.rows.length > 0 && tasksResult.rows.length > 0) {
      const inbox = inboxResult.rows[0];
      const tasks = tasksResult.rows[0];
      return `Inbox: ${inbox.total} messages (${inbox.unread} unread, ${inbox.leads} leads). Tasks: ${tasks.pending} pending (${tasks.p0} urgent).`;
    }
  } catch (error) {
    // Database unavailable
  }
  return 'Context unavailable.';
}

/**
 * Save prompt snapshot and audit log
 */
async function saveAuditLog(
  correlationId: string,
  userMessage: string,
  intent: IntentType,
  intentConfidence: number,
  promptSnapshot: string,
  retrievedIds: string[],
  modelResponse: string,
  finalText: string,
  latencyMs: number,
  needsManualLabel: boolean = false
): Promise<string | null> {
  try {
    // Save gzipped prompt
    const storageDir = path.join(process.cwd(), 'backend/storage/prompts');
    if (!fs.existsSync(storageDir)) {
      fs.mkdirSync(storageDir, { recursive: true });
    }
    
    const gzipPath = path.join(storageDir, `${correlationId}.gz`);
    const gzipped = await gzipAsync(Buffer.from(promptSnapshot, 'utf-8'));
    fs.writeFileSync(gzipPath, gzipped);
    
    // Save to audit table
    const suggestionId = uuidv4();
    await pool.query(
      `INSERT INTO suggestions (id, prompt, retrieved_ids, model_response, final_text)
       VALUES ($1, $2, $3, $4, $5)`,
      [suggestionId, promptSnapshot.substring(0, 4000), JSON.stringify(retrievedIds), modelResponse, finalText]
    );
    
    await pool.query(
      `INSERT INTO events (type, correlation_id, prompt_ref, retrieved_ids, raw_model_response, final_text, latency_ms, payload)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [
        'chat_intent_routed',
        correlationId,
        gzipPath,
        JSON.stringify(retrievedIds),
        modelResponse,
        finalText,
        latencyMs,
        JSON.stringify({
          intent,
          intent_confidence: intentConfidence,
          needs_manual_label: needsManualLabel,
          user_message: userMessage.substring(0, 200),
        }),
      ]
    );
    
    return suggestionId;
  } catch (error: any) {
    console.error('[Chat] Failed to save audit log:', error.message);
    return null;
  }
}

/**
 * Handle general_intent - conversational assistant
 */
async function handleGeneralIntent(
  userMessage: string,
  correlationId: string,
  conversationHistory: LLMMessage[]
): Promise<{ text: string; suggestionId: string | null }> {
  const startTime = Date.now();
  
  const template = loadPromptTemplate('assistant_conversational.md');
  const context = await getInboxContext();
  
  const systemPrompt = template
    .replace('{context}', context)
    .replace('{user_message}', userMessage);
  
  const messages: LLMMessage[] = [
    { role: 'system', content: systemPrompt },
    ...conversationHistory.slice(-5),
    { role: 'user', content: userMessage },
  ];
  
  const temperature = parseFloat(process.env.LLM_GENERAL_TEMP || '0.3');
  const llmResponse = await generateChatCompletion({
    model: process.env.LLM_MODEL || 'tinyllama',
    messages,
    temperature,
    max_tokens: 200,
    useLocal: process.env.USE_OLLAMA !== 'false',
    correlationId,
  });
  
  const text = llmResponse.content.trim();
  const latencyMs = Date.now() - startTime;
  
  const suggestionId = await saveAuditLog(
    correlationId,
    userMessage,
    'general_intent',
    1.0,
    systemPrompt,
    [],
    text,
    text,
    latencyMs
  );
  
  return { text, suggestionId };
}

/**
 * Handle policy_intent - RAG with citations
 */
async function handlePolicyIntent(
  userMessage: string,
  correlationId: string,
  conversationHistory: LLMMessage[]
): Promise<{ text: string; citations: Array<{ id: string; score: number; textSnippet: string }>; suggestionId: string | null }> {
  const startTime = Date.now();
  
  // Retrieve policy chunks
  let retrievedChunks: Array<{ id: string; text: string; score: number; metadata: any }> = [];
  try {
    const vectorResults = await query(userMessage, 3);
    retrievedChunks = vectorResults.map(r => ({
      id: r.id,
      text: r.text,
      score: r.score,
      metadata: r.metadata || {},
    }));
  } catch (error: any) {
    console.warn('[Chat] Vector store query failed:', error.message);
  }
  
  // Build prompt from template
  const template = loadPromptTemplate('policy_chat_template.md');
  const chunksText = retrievedChunks.length > 0
    ? retrievedChunks.map((chunk, i) => `§${i + 1}. ${chunk.text.substring(0, 200)}... (ID: ${chunk.id}, Score: ${chunk.score.toFixed(2)})`).join('\n\n')
    : 'No relevant policy chunks found.';
  
  const systemPrompt = template
    .replace('{persona}', 'You are Soraya, a helpful AI assistant.')
    .replace('{tone}', 'warm')
    .replace('{retrieved_chunks}', chunksText)
    .replace('{conversation}', conversationHistory.length > 0 ? 'Previous conversation available.' : 'No previous messages.')
    .replace('{user_message}', userMessage);
  
  const messages: LLMMessage[] = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userMessage },
  ];
  
  const temperature = parseFloat(process.env.LLM_POLICY_TEMP || '0.1');
  const llmResponse = await generateChatCompletion({
    model: process.env.LLM_MODEL || 'tinyllama',
    messages,
    temperature,
    max_tokens: 250,
    useLocal: process.env.USE_OLLAMA !== 'false',
    correlationId,
  });
  
  let text = llmResponse.content.trim();
  
  // Fallback if no chunks found
  if (retrievedChunks.length === 0 && !text.includes('(Policy')) {
    text = `I couldn't find policy references, answering generally: ${text}`;
    console.warn('[Chat] Policy intent but no chunks retrieved');
  }
  
  const latencyMs = Date.now() - startTime;
  const citations = retrievedChunks.map(chunk => ({
    id: chunk.id,
    score: chunk.score,
    textSnippet: chunk.text.substring(0, 200) + (chunk.text.length > 200 ? '...' : ''),
  }));
  
  const suggestionId = await saveAuditLog(
    correlationId,
    userMessage,
    'policy_intent',
    1.0,
    systemPrompt,
    retrievedChunks.map(c => c.id),
    text,
    text,
    latencyMs
  );
  
  return { text, citations, suggestionId };
}

/**
 * Handle action_intent - extract entities and perform action
 */
async function handleActionIntent(
  userMessage: string,
  correlationId: string,
  conversationHistory: LLMMessage[]
): Promise<{ text: string; action_suggestion?: any; suggestionId: string | null }> {
  const startTime = Date.now();
  
  // Check policy safety first
  const policyCheck = checkPolicy(userMessage);
  if (policyCheck.action === 'ESCALATE') {
    return {
      text: 'This action requires human review due to sensitive content. I\'m escalating this to a human reviewer.',
      suggestionId: null,
    };
  }
  
  // Use action planner prompt
  const template = loadPromptTemplate('action_planner.md');
  const systemPrompt = template.replace('{user_message}', userMessage);
  
  const messages: LLMMessage[] = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userMessage },
  ];
  
  const temperature = parseFloat(process.env.LLM_ACTION_TEMP || '0.0');
  const llmResponse = await generateChatCompletion({
    model: process.env.LLM_MODEL || 'tinyllama',
    messages,
    temperature,
    max_tokens: 300,
    useLocal: process.env.USE_OLLAMA !== 'false',
    correlationId,
  });
  
  // Parse action JSON
  let actionData: any = null;
  try {
    const jsonMatch = llmResponse.content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      actionData = JSON.parse(jsonMatch[0]);
    }
  } catch (error) {
    console.warn('[Chat] Failed to parse action JSON, using fallback');
  }
  
  let text = llmResponse.content.trim();
  let actionSuggestion: any = null;
  
  if (actionData) {
    actionSuggestion = {
      action_type: actionData.action_type || 'other',
      confirm_needed: actionData.confirm_needed || false,
      extracted_data: {
        title: actionData.title,
        start: actionData.start,
        end: actionData.end,
        attendees: actionData.attendees || [],
      },
    };
    
    // If no confirmation needed and we have calendar event data, create it
    if (!actionData.confirm_needed && actionData.action_type === 'calendar_event' && actionData.title && actionData.start) {
      try {
        const calendarParseUrl = `http://localhost:${process.env.PORT || 3001}/api/calendar/parse`;
        const calendarResponse = await fetch(calendarParseUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: userMessage }),
        });
        
        if (calendarResponse.ok) {
          const calendarData = await calendarResponse.json() as { event: any };
          text = actionData.reply_text || `✅ I've added "${calendarData.event.title}" to your calendar.`;
          actionSuggestion.extracted_data.eventId = calendarData.event.id;
        }
      } catch (error: any) {
        console.warn('[Chat] Calendar creation failed:', error.message);
        text = actionData.reply_text || text;
      }
    } else {
      text = actionData.reply_text || text;
    }
  }
  
  const latencyMs = Date.now() - startTime;
  const suggestionId = await saveAuditLog(
    correlationId,
    userMessage,
    'action_intent',
    1.0,
    systemPrompt,
    [],
    llmResponse.content,
    text,
    latencyMs
  );
  
  return { text, action_suggestion: actionSuggestion, suggestionId };
}

/**
 * POST /api/chat - Main chat endpoint with intent-based routing
 */
router.post('/', async (req: Request, res: Response) => {
  try {
    const { threadId, userMessage, tone, correlationId: providedCorrelationId }: ChatRequest = req.body;

    if (!userMessage || typeof userMessage !== 'string') {
      return res.status(400).json({ error: 'userMessage is required' });
    }

    const correlationId = providedCorrelationId || uuidv4();
    const startTime = Date.now();

    // Classify intent
    const intentResult = await classifyIntent(userMessage);
    const confidenceThreshold = parseFloat(process.env.INTENT_RULES_CONFIDENCE_THRESHOLD || '0.75');
    const needsManualLabel = intentResult.confidence < confidenceThreshold;

    console.log(`[Chat] Intent: ${intentResult.intent} (confidence: ${intentResult.confidence.toFixed(2)})`);

    // Get conversation history (simplified - could load from DB using threadId)
    const conversationHistory: LLMMessage[] = [];

    let response: ChatResponse;

    // Route based on intent
    if (intentResult.intent === 'policy_intent') {
      const result = await handlePolicyIntent(userMessage, correlationId, conversationHistory);
      response = {
        kind: 'policy',
        text: result.text,
        citations: result.citations,
        suggestionId: result.suggestionId,
        intent: 'policy_intent',
        intent_confidence: intentResult.confidence,
      };
    } else if (intentResult.intent === 'action_intent') {
      const result = await handleActionIntent(userMessage, correlationId, conversationHistory);
      response = {
        kind: 'action',
        text: result.text,
        action_suggestion: result.action_suggestion,
        suggestionId: result.suggestionId,
        intent: 'action_intent',
        intent_confidence: intentResult.confidence,
      };
    } else {
      // general_intent
      const result = await handleGeneralIntent(userMessage, correlationId, conversationHistory);
      response = {
        kind: 'assistant',
        text: result.text,
        suggestionId: result.suggestionId,
        intent: 'general_intent',
        intent_confidence: intentResult.confidence,
      };
    }

    // Update audit log with needs_manual_label if confidence is low
    if (needsManualLabel && response.suggestionId) {
      try {
        await pool.query(
          `UPDATE events SET payload = jsonb_set(payload, '{needs_manual_label}', 'true'::jsonb)
           WHERE correlation_id = $1`,
          [correlationId]
        );
      } catch (error) {
        // Ignore update errors
      }
    }

    return res.json(response);
  } catch (error: any) {
    console.error('[Chat] Error:', error);
    return res.status(500).json({
      error: 'Failed to process chat',
      details: error.message || 'Unknown error',
    });
  }
});

/**
 * POST /api/chat/rag - Deprecated alias (always uses policy RAG)
 */
router.post('/rag', async (req: Request, res: Response) => {
  console.warn('[Chat] /api/chat/rag is deprecated. Use /api/chat instead.');
  
  try {
    const { threadId, userMessage, tone, rag = true }: any = req.body;
    
    if (!userMessage) {
      return res.status(400).json({ error: 'userMessage is required' });
    }

    const correlationId = uuidv4();
    const conversationHistory: LLMMessage[] = [];
    
    // Force policy intent flow
    const result = await handlePolicyIntent(userMessage, correlationId, conversationHistory);
    
    return res.json({
      reply: result.text,
      citations: result.citations,
      suggestionId: result.suggestionId,
      escalated: false,
    });
  } catch (error: any) {
    console.error('[Chat] RAG endpoint error:', error);
    return res.status(500).json({ error: 'Failed to process RAG chat', details: error.message });
  }
});

export default router;
