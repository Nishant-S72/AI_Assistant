import { Router, Request, Response } from 'express';
import { pool } from '../db';
import { PromptBuilder, storePrompt } from '../services/promptBuilder';
import { generateChatCompletion, LLMMessage } from '../clients/llm';
import { checkPolicy } from '../policy/policyEngine';
import { emailQueue } from '../workers/emailWorker';
import { v4 as uuidv4 } from 'uuid';

const router = Router();

// GET /api/messages - List messages with filters
router.get('/', async (req: Request, res: Response) => {
  try {
    const { folder = 'all' } = req.query;

    // Check if database is available
    try {
      await pool.query('SELECT 1');
    } catch (dbError) {
      // Database not available, try to return demo data
      console.warn('Database not available, trying demo endpoint');
      try {
        const demoRouter = await import('./demo');
        // Return empty array or redirect to demo endpoint
        return res.json([]);
      } catch {
        return res.status(503).json({ error: 'Database unavailable' });
      }
    }

    let query = `
      SELECT 
        m.id,
        m.thread_id,
        m.sender,
        m.body,
        m.channel,
        m.created_at,
        c.name as contact_name,
        c.company as contact_company,
        c.email as contact_email,
        (SELECT COUNT(*) FROM messages m2 WHERE m2.thread_id = m.thread_id) as message_count
      FROM messages m
      JOIN contacts c ON m.contact_id = c.id
    `;

    // Simple folder filtering based on contact tags or thread content
    if (folder === 'leads') {
      query += ` WHERE c.tags::text LIKE '%lead%'`;
    } else if (folder === 'tasks') {
      query += ` WHERE EXISTS (
        SELECT 1 FROM tasks t WHERE t.contact_id = c.id AND t.status = 'pending'
      )`;
    }

    query += ` ORDER BY m.created_at DESC`;

    let result;
    try {
      result = await pool.query(query);
    } catch (queryError: any) {
      // Database query failed, return empty array
      console.warn('Database query failed:', queryError.message);
      return res.json([]);
    }
    
    // If no results and in offline mode, try demo data
    if (result.rows.length === 0 && process.env.USE_DUMMY_INBOX === 'true') {
      try {
        const { loadDummyInbox } = await import('../utils/loadDummyInbox');
        await loadDummyInbox();
        // Retry query
        try {
          const retryResult = await pool.query(query);
          return res.json(retryResult.rows);
        } catch (retryError: any) {
          // Query still fails, return empty
          return res.json([]);
        }
      } catch (loadError: any) {
        // Continue with empty result
        console.warn('Could not load dummy inbox:', loadError.message);
      }
    }
    
    res.json(result.rows);
  } catch (error: any) {
    console.error('Error fetching messages:', error);
    // Return empty array instead of error if database issue
    if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND' || error.message?.includes('connect')) {
      return res.json([]);
    }
    res.status(500).json({ error: 'Failed to fetch messages', details: error.message });
  }
});

// GET /api/messages/:id - Get thread with contact and latest suggestion
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    // Get message
    const messageResult = await pool.query(
      `SELECT m.*, c.name as contact_name, c.company, c.email, c.phone, c.tags, c.tone_pref
       FROM messages m
       JOIN contacts c ON m.contact_id = c.id
       WHERE m.id = $1`,
      [id]
    );

    if (messageResult.rows.length === 0) {
      return res.status(404).json({ error: 'Message not found' });
    }

    const message = messageResult.rows[0];

    // Get all messages in thread
    const threadResult = await pool.query(
      `SELECT * FROM messages
       WHERE thread_id = $1
       ORDER BY created_at ASC`,
      [message.thread_id]
    );

    // Get latest suggestion
    const suggestionResult = await pool.query(
      `SELECT * FROM suggestions
       WHERE message_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [id]
    );

    res.json({
      message,
      thread: threadResult.rows,
      suggestion: suggestionResult.rows[0] || null,
      contact: {
        id: message.contact_id,
        name: message.contact_name,
        company: message.company,
        email: message.email,
        phone: message.phone,
        tags: message.tags,
        tone_pref: message.tone_pref,
      },
    });
  } catch (error) {
    console.error('Error fetching message:', error);
    res.status(500).json({ error: 'Failed to fetch message' });
  }
});

// POST /api/messages/:id/generate - Generate AI suggestion
router.post('/:id/generate', async (req: Request, res: Response) => {
  const correlationId = req.headers['x-request-id'] as string || uuidv4();
  const startTime = Date.now();
  
  try {
    const { id } = req.params;
    const { tone = 'warm' } = req.body;

    // Use local template if in offline mode, otherwise use full RAG
    let prompt: string;
    let retrievedIds: string[] = [];
    let metadata: any = {};

    if (process.env.USE_OLLAMA === 'true' && process.env.USE_DUMMY_INBOX === 'true') {
      // Use local template for offline mode
      const templatePath = require('path').join(__dirname, '../../../prompts/local_template.md');
      const fs = require('fs');
      let template = '';
      try {
        template = fs.readFileSync(templatePath, 'utf-8');
      } catch {
        template = `SYSTEM:\nYou are a polite and concise business assistant.\n\nCONTEXT:\n{thread_summary}\n\nUSER:\n{latest_customer_message}\n\nTASK:\nWrite a short, professional reply in the tone: {tone}.`;
      }

      // Get thread context
      const messageResult = await pool.query(
        `SELECT m.*, c.name as contact_name, c.company as contact_company
         FROM messages m
         JOIN contacts c ON m.contact_id = c.id
         WHERE m.id = $1`,
        [id]
      );

      if (messageResult.rows.length === 0) {
        return res.status(404).json({ error: 'Message not found' });
      }

      const message = messageResult.rows[0];
      const threadResult = await pool.query(
        `SELECT sender, body FROM messages WHERE thread_id = $1 ORDER BY created_at ASC`,
        [message.thread_id]
      );

      const threadMessages = threadResult.rows;
      // Take only last 1 message for fastest processing
      const recentMessages = threadMessages.slice(-1);
      const threadSummary = ''; // Skip summary for speed
      const latestMessage = recentMessages[recentMessages.length - 1]?.body?.substring(0, 150) || '';

      prompt = template
        .replace('{thread_summary}', threadSummary || 'No previous messages')
        .replace('{latest_customer_message}', latestMessage)
        .replace('{tone}', tone);
    } else {
      // Use full RAG prompt builder
      const result = await PromptBuilder.buildForMessage(id, tone);
      prompt = result.prompt;
      retrievedIds = result.retrievedIds;
      metadata = result.metadata;
    }

    // Generate completion using LLM abstraction
    const llmResponse = await generateChatCompletion({
      model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama',
      messages: [
        {
          role: 'system',
          content: 'You are a helpful assistant who writes natural, human-like replies. No templates, no corporate speak - just genuine, helpful responses that sound like a real person wrote them. Be concise - keep replies brief and to the point.',
        },
        {
          role: 'user',
          content: prompt,
        },
      ] as LLMMessage[],
      temperature: 0.5, // Optimized for tinyllama (was 0.3)
      max_tokens: 150, // Limited to ~110 words for email replies
      useLocal: process.env.USE_OLLAMA === 'true',
      correlationId,
    });

    const modelResponse = llmResponse.content;
    const latency = Date.now() - startTime;

    // Check policy
    const policyCheck = checkPolicy(modelResponse);
    if (policyCheck.action === 'ESCALATE') {
      // Still save suggestion but mark for escalation
      await pool.query(
        `INSERT INTO events (type, correlation_id, request_path, retrieved_ids, raw_model_response, latency_ms, payload) 
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          'policy_escalated',
          correlationId,
          req.path,
          JSON.stringify(retrievedIds),
          modelResponse.substring(0, 1000),
          latency,
          JSON.stringify({ messageId: id, reasons: policyCheck.reasons, confidence: policyCheck.confidence }),
        ]
      );
    }

    // Save suggestion
    const suggestionResult = await pool.query(
      `INSERT INTO suggestions (message_id, prompt, retrieved_ids, model_response, final_text)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING *`,
      [id, prompt.substring(0, 4000), JSON.stringify(retrievedIds), modelResponse, modelResponse]
    );

    // Store full prompt (gzipped or local file)
    let promptPath: string;
    if (process.env.USE_OLLAMA === 'true' && process.env.USE_DUMMY_INBOX === 'true') {
      // Save to local file for offline mode
      const fs = require('fs');
      const path = require('path');
      const storageDir = path.join(__dirname, '../../storage/prompts_local');
      if (!fs.existsSync(storageDir)) {
        fs.mkdirSync(storageDir, { recursive: true });
      }
      const threadId = (await pool.query('SELECT thread_id FROM messages WHERE id = $1', [id])).rows[0]?.thread_id || id;
      promptPath = path.join(storageDir, `${threadId}.txt`);
      fs.writeFileSync(promptPath, `PROMPT:\n${prompt}\n\nRESPONSE:\n${modelResponse}`);
    } else {
      promptPath = await storePrompt(suggestionResult.rows[0].id, prompt);
    }

    // Log audit event
    await pool.query(
      `INSERT INTO events (type, correlation_id, request_path, prompt_ref, retrieved_ids, raw_model_response, final_text, latency_ms, payload) 
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [
        'suggestion_generated',
        correlationId,
        req.path,
        promptPath,
        JSON.stringify(retrievedIds),
        modelResponse.substring(0, 1000),
        modelResponse,
        latency,
        JSON.stringify({
          messageId: id,
          suggestionId: suggestionResult.rows[0].id,
          adapter: llmResponse.adapter,
          metadata,
        }),
      ]
    );

    res.json({
      suggestion: suggestionResult.rows[0],
      policyCheck: {
        action: policyCheck.action === 'ESCALATE' ? 'ESCALATE_TO_HUMAN' : 'APPROVE',
        reasons: policyCheck.reasons,
      },
    });
  } catch (error: any) {
    const latency = Date.now() - startTime;
    console.error('Error generating suggestion:', error);
    
    // Log error event
    await pool.query(
      `INSERT INTO events (type, correlation_id, request_path, latency_ms, payload) 
       VALUES ($1, $2, $3, $4, $5)`,
      [
        'suggestion_error',
        correlationId,
        req.path,
        latency,
        JSON.stringify({ messageId: req.params.id, error: error.message }),
      ]
    ).catch(() => {}); // Don't fail on audit log error

    res.status(500).json({ error: 'Failed to generate suggestion', details: error.message });
  }
});

// POST /api/messages/:id/send - Send reply
router.post('/:id/send', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { text, suggestionId } = req.body;

    if (!text) {
      return res.status(400).json({ error: 'Text is required' });
    }

    // Get message and contact info
    const messageResult = await pool.query(
      `SELECT m.*, c.name as contact_name, c.email as contact_email
       FROM messages m
       JOIN contacts c ON m.contact_id = c.id
       WHERE m.id = $1`,
      [id]
    );

    if (messageResult.rows.length === 0) {
      return res.status(404).json({ error: 'Message not found' });
    }

    const message = messageResult.rows[0];

    // Check policy one more time
    const policyCheck = checkPolicy(text);
    if (policyCheck.action === 'ESCALATE') {
      return res.status(403).json({
        error: 'Message blocked by policy',
        policyCheck: {
          action: 'ESCALATE_TO_HUMAN',
          reasons: policyCheck.reasons,
        },
      });
    }

    // Save sent message
    const sentMessageResult = await pool.query(
      `INSERT INTO messages (contact_id, channel, thread_id, sender, body)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING *`,
      [message.contact_id, message.channel, message.thread_id, 'assistant', text]
    );

    // Update suggestion if provided
    if (suggestionId) {
      await pool.query(
        `UPDATE suggestions SET final_text = $1 WHERE id = $2`,
        [text, suggestionId]
      );
    }

    // Queue email job (simulated)
    await emailQueue.add('send-email', {
      messageId: id,
      contactId: message.contact_id,
      to: message.contact_email,
      subject: `Re: ${message.body.substring(0, 50)}...`,
      body: text,
    });

    // Log event
    await pool.query(
      `INSERT INTO events (type, payload) VALUES ($1, $2)`,
      [
        'message_sent',
        JSON.stringify({
          messageId: id,
          sentMessageId: sentMessageResult.rows[0].id,
          text,
          simulated: true,
        }),
      ]
    );

    res.json({
      success: true,
      message: sentMessageResult.rows[0],
      simulated: true,
    });
  } catch (error) {
    console.error('Error sending message:', error);
    res.status(500).json({ error: 'Failed to send message' });
  }
});

export default router;

