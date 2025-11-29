import { Router, Request, Response } from 'express';
import { pool } from '../db';
import { generateChatCompletion } from '../clients/llm';

const router = Router();

// GET /api/contacts - List all contacts (parsed from inbox)
router.get('/', async (req: Request, res: Response) => {
  try {
    const { search, tag } = req.query;

    let query = `
      SELECT DISTINCT
        c.id,
        c.name,
        c.email,
        c.phone,
        c.company,
        c.tags,
        c.tone_pref,
        c.created_at,
        (SELECT COUNT(*) FROM messages m WHERE m.contact_id = c.id) as message_count,
        (SELECT COUNT(*) FROM tasks t WHERE t.contact_id = c.id AND t.status = 'pending') as pending_tasks,
        (SELECT MAX(created_at) FROM messages m WHERE m.contact_id = c.id) as last_message_at
      FROM contacts c
    `;

    const params: any[] = [];
    const conditions: string[] = [];

    if (search) {
      conditions.push(`(
        LOWER(c.name) LIKE LOWER($${params.length + 1}) OR 
        LOWER(c.email) LIKE LOWER($${params.length + 1}) OR 
        LOWER(c.company) LIKE LOWER($${params.length + 1})
      )`);
      params.push(`%${search}%`);
    }

    if (tag) {
      conditions.push(`c.tags::text LIKE $${params.length + 1}`);
      params.push(`%"${tag}"%`);
    }

    if (conditions.length > 0) {
      query += ` WHERE ${conditions.join(' AND ')}`;
    }

    query += ` ORDER BY last_message_at DESC NULLS LAST, c.name ASC`;

    const result = await pool.query(query, params);

    // Parse JSONB tags
    const contacts = result.rows.map((row: any) => ({
      ...row,
      tags: Array.isArray(row.tags) ? row.tags : (row.tags ? JSON.parse(row.tags) : []),
    }));

    res.json(contacts);
  } catch (error) {
    console.error('Error fetching contacts:', error);
    res.status(500).json({ error: 'Failed to fetch contacts' });
  }
});

// GET /api/contacts/:id - Get contact details
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const result = await pool.query(
      `SELECT 
        c.*,
        (SELECT COUNT(*) FROM messages m WHERE m.contact_id = c.id) as message_count,
        (SELECT COUNT(*) FROM tasks t WHERE t.contact_id = c.id AND t.status = 'pending') as pending_tasks,
        (SELECT MAX(created_at) FROM messages m WHERE m.contact_id = c.id) as last_message_at
       FROM contacts c
       WHERE c.id = $1`,
      [id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Contact not found' });
    }

    const contact = result.rows[0];
    // Parse JSONB tags
    contact.tags = Array.isArray(contact.tags) ? contact.tags : (contact.tags ? JSON.parse(contact.tags) : []);

    res.json(contact);
  } catch (error) {
    console.error('Error fetching contact:', error);
    res.status(500).json({ error: 'Failed to fetch contact' });
  }
});

// GET /api/contacts/:id/messages - Get all messages from a contact
router.get('/:id/messages', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { limit = '50', offset = '0' } = req.query;

    const result = await pool.query(
      `SELECT 
        m.id,
        m.thread_id,
        m.sender,
        m.body,
        m.channel,
        m.created_at,
        m.processed
       FROM messages m
       WHERE m.contact_id = $1
       ORDER BY m.created_at DESC
       LIMIT $2 OFFSET $3`,
      [id, parseInt(limit as string), parseInt(offset as string)]
    );

    res.json(result.rows);
  } catch (error) {
    console.error('Error fetching contact messages:', error);
    res.status(500).json({ error: 'Failed to fetch contact messages' });
  }
});

// GET /api/contacts/:id/summary - Get LLM-generated interaction summary
router.get('/:id/summary', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    // Get contact info
    const contactResult = await pool.query(
      `SELECT name, email, company, tags, tone_pref FROM contacts WHERE id = $1`,
      [id]
    );

    if (contactResult.rows.length === 0) {
      return res.status(404).json({ error: 'Contact not found' });
    }

    const contact = contactResult.rows[0];
    const tags = Array.isArray(contact.tags) ? contact.tags : (contact.tags ? JSON.parse(contact.tags) : []);

    // Get ALL messages for deep analysis (or at least a large sample)
    const messagesResult = await pool.query(
      `SELECT sender, body, created_at, thread_id
       FROM messages 
       WHERE contact_id = $1 
       ORDER BY created_at ASC`,
      [id]
    );

    const allMessages = messagesResult.rows.map((m: any) => ({
      sender: m.sender,
      body: m.body,
      date: m.created_at,
      thread_id: m.thread_id,
    }));

    const totalMessageCount = allMessages.length;
    
    // Get recent messages for quick context
    const recentMessages = allMessages.slice(-10);

    // Get last 3 distinct conversation threads
    const threadsResult = await pool.query(
      `SELECT DISTINCT thread_id, MAX(created_at) as last_message_date
       FROM messages 
       WHERE contact_id = $1 
       GROUP BY thread_id 
       ORDER BY last_message_date DESC 
       LIMIT 3`,
      [id]
    );

    const last3Threads: Array<{ thread_id: string; messages: any[] }> = [];
    
    for (const threadRow of threadsResult.rows) {
      const threadMessagesResult = await pool.query(
        `SELECT sender, body, created_at 
         FROM messages 
         WHERE contact_id = $1 AND thread_id = $2 
         ORDER BY created_at ASC`,
        [id, threadRow.thread_id]
      );
      
      last3Threads.push({
        thread_id: threadRow.thread_id,
        messages: threadMessagesResult.rows.map((m: any) => ({
          sender: m.sender,
          body: m.body,
          date: m.created_at,
        })),
      });
    }

    // Get task summary
    const tasksResult = await pool.query(
      `SELECT COUNT(*) as total, 
              COUNT(*) FILTER (WHERE status = 'pending') as pending,
              COUNT(*) FILTER (WHERE status = 'completed') as completed
       FROM tasks 
       WHERE contact_id = $1`,
      [id]
    );

    const taskStats = tasksResult.rows[0];

    // Get first message to calculate relationship duration
    const firstMessageResult = await pool.query(
      `SELECT created_at FROM messages WHERE contact_id = $1 ORDER BY created_at ASC LIMIT 1`,
      [id]
    ).catch(() => ({ rows: [] }));
    
    const firstMessageDate = firstMessageResult.rows[0]?.created_at;
    const relationshipDuration = firstMessageDate 
      ? Math.floor((Date.now() - new Date(firstMessageDate).getTime()) / (1000 * 60 * 60 * 24))
      : 0;
    const relationshipYears = relationshipDuration > 365 ? Math.floor(relationshipDuration / 365) : 0;
    const relationshipMonths = relationshipDuration > 30 ? Math.floor((relationshipDuration % 365) / 30) : 0;
    const daysSinceLastMessage = recentMessages.length > 0 
      ? Math.floor((Date.now() - new Date(recentMessages[0].date).getTime()) / (1000 * 60 * 60 * 24))
      : -1;

    // Build relationship context string (used in both try and catch)
    const relationshipContext = relationshipYears > 0 
      ? `${relationshipYears} year${relationshipYears > 1 ? 's' : ''}${relationshipMonths > 0 ? ` and ${relationshipMonths} month${relationshipMonths > 1 ? 's' : ''}` : ''}`
      : relationshipMonths > 0 
        ? `${relationshipMonths} month${relationshipMonths > 1 ? 's' : ''}`
        : 'recent';

    // Generate LLM-powered insightful summary by analyzing full email history
    try {
      // Build complete email history for analysis
      // Use all messages but truncate very long ones to keep context manageable
      const emailHistory = allMessages
        .map((m) => {
          const date = new Date(m.date).toLocaleDateString();
          const who = m.sender === 'contact' ? contact.name : 'You';
          // Keep full message but limit to 600 chars to allow more messages in context
          const body = m.body.length > 600 ? m.body.substring(0, 600) + '...' : m.body;
          return `${date} - ${who}: ${body}`;
        })
        .join('\n\n');

      // If we have too many messages, use a sample (every Nth message) plus all recent ones
      let emailHistoryForLLM = emailHistory;
      if (allMessages.length > 50) {
        // Take every 3rd message from history + all messages from last 30 days
        const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
        const recentMessages = allMessages.filter(m => new Date(m.date).getTime() > thirtyDaysAgo);
        const sampledMessages = allMessages.filter((_, idx) => idx % 3 === 0);
        const combined = [...new Set([...sampledMessages, ...recentMessages])]
          .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
        
        emailHistoryForLLM = combined
          .map((m) => {
            const date = new Date(m.date).toLocaleDateString();
            const who = m.sender === 'contact' ? contact.name : 'You';
            const body = m.body.length > 600 ? m.body.substring(0, 600) + '...' : m.body;
            return `${date} - ${who}: ${body}`;
          })
          .join('\n\n');
      }

      // Completely free-form system prompt - just be a friend analyzing, but be concise
      const systemPrompt = `You're looking through someone's email history with a contact. You notice patterns, changes, what matters. Just share what you see. No format. No structure. Just genuine observations. Keep it under 250 words - be concise and direct.`;

      const lastContactText = daysSinceLastMessage >= 0 
        ? daysSinceLastMessage === 0 
          ? 'today' 
          : daysSinceLastMessage === 1 
            ? 'yesterday' 
            : `${daysSinceLastMessage} days ago`
        : 'recently';

      // Give LLM the full email history and let it find insights
      const userPrompt = `Here's the complete email history with ${contact.name}${contact.company ? ` from ${contact.company}` : ''}:

${emailHistoryForLLM || 'No messages yet.'}

We've been in touch for ${relationshipContext} (${totalMessageCount} total messages). ${tags.length > 0 ? `They're tagged: ${tags.join(', ')}. ` : ''}${contact.tone_pref ? `Communication style: ${contact.tone_pref}. ` : ''}Last message ${lastContactText}. ${taskStats.pending > 0 ? `${taskStats.pending} pending tasks. ` : ''}${taskStats.completed > 0 ? `${taskStats.completed} completed. ` : ''}

What do you notice?`;

      console.log('[Contact Summary] Generating LLM summary for:', contact.name);
      console.log('[Contact Summary] USE_OLLAMA:', process.env.USE_OLLAMA);
      console.log('[Contact Summary] Model:', process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama');
      console.log('[Contact Summary] LLM_BASE_URL:', process.env.LLM_BASE_URL || 'http://localhost:11434');
      
      // Default to Ollama if USE_OLLAMA is not explicitly false
      const useOllama = process.env.USE_OLLAMA !== 'false';
      console.log('[Contact Summary] Will use Ollama:', useOllama);
      
      const llmResponse = await generateChatCompletion({
        model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        max_tokens: 200, // Limited to ~150 words (under 250 words requirement)
        temperature: 0.7,
        useLocal: useOllama,
      });

      console.log('[Contact Summary] LLM response received, length:', llmResponse.content.length);
      console.log('[Contact Summary] Response preview:', llmResponse.content.substring(0, 100));

      // Use the LLM response completely as-is - no parsing, no extraction, nothing
      // The LLM has analyzed the email history and shared insights naturally
      let summary = llmResponse.content.trim();
      let recommendations: string[] = [];

      // Don't try to extract recommendations - if the LLM includes them naturally, that's fine
      // But don't force structure by parsing
      // Only if the response is extremely long (2000+ chars) might we consider splitting
      if (summary.length > 2000) {
        // Very long response - maybe split on natural breaks
        const paragraphs = summary.split(/\n\n+/);
        if (paragraphs.length > 3) {
          // Take first 3 paragraphs as summary, rest as potential recommendations
          summary = paragraphs.slice(0, 3).join('\n\n').trim();
          const rest = paragraphs.slice(3).join('\n\n').trim();
          if (rest.length > 50) {
            recommendations = [rest.substring(0, 300)];
          }
        }
      }

      // Use LLM response as-is - no cleanup, no parsing, nothing
      summary = llmResponse.content.trim();

      // Generate summaries for last 3 conversations using LLM only
      const conversationSummaries = await Promise.all(
        last3Threads.map(async (thread, idx) => {
          const threadMessagesText = thread.messages
            .map((m) => {
              const date = new Date(m.date).toLocaleDateString();
              const who = m.sender === 'contact' ? contact.name : 'You';
              return `${date} - ${who}: ${m.body}`;
            })
            .join('\n\n');

          // Completely free-form - just analyze the conversation
          const conversationResponse = await generateChatCompletion({
            model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama',
            messages: [
              { role: 'system', content: 'You\'re looking at an email conversation. Just share what you notice. No format, no structure. Be concise - under 50 words.' },
              { role: 'user', content: `Here's a conversation:\n\n${threadMessagesText}\n\nWhat happened?` },
            ],
            max_tokens: 80, // Limited to ~60 words for conversation summaries
            temperature: 0.7,
            useLocal: process.env.USE_OLLAMA !== 'false', // Default to Ollama if not explicitly false
          });

          return {
            thread_id: thread.thread_id,
            summary: conversationResponse.content.trim(),
            message_count: thread.messages.length,
            last_date: thread.messages[thread.messages.length - 1]?.date,
          };
        })
      );

      // Extract recommendations naturally from the summary if they exist
      // But don't force it - let the LLM decide
      const sentences = summary.split(/[.!?]\s+/);
      const maybeRecommendations = sentences
        .filter(s => {
          const lower = s.toLowerCase();
          return (lower.includes('you should') || lower.includes('maybe') || lower.includes('i\'d') || 
                 lower.includes('consider') || lower.includes('might want') || lower.includes('could')) &&
                 s.length > 20 && s.length < 200;
        })
        .slice(-3);

      const response = {
        summary: summary,
        recommendations: maybeRecommendations.length > 0 ? maybeRecommendations : [],
        recentConversations: conversationSummaries,
        messageCount: recentMessages.length,
        taskStats: {
          total: parseInt(taskStats.total || '0'),
          pending: parseInt(taskStats.pending || '0'),
          completed: parseInt(taskStats.completed || '0'),
        },
      };
      
      console.log('[Contact Summary] Sending response:', {
        summaryLength: response.summary.length,
        recommendationsCount: response.recommendations.length,
        conversationsCount: response.recentConversations.length,
        messageCount: response.messageCount
      });
      
      res.json(response);
    } catch (error: any) {
      console.error('[Contact Summary] Error generating LLM summary:', error);
      console.error('[Contact Summary] Error message:', error?.message || String(error));
      if (error?.stack) {
        console.error('[Contact Summary] Error stack:', error.stack.substring(0, 500));
      }
      
      // NO HARDCODED FALLBACKS - retry once or return error
      // Try one more time with simpler prompt
      try {
        console.log('[Contact Summary] Retrying with simpler prompt...');
        const simpleEmailHistory = allMessages.slice(-20).map((m) => {
          const date = new Date(m.date).toLocaleDateString();
          const who = m.sender === 'contact' ? contact.name : 'You';
          return `${date} - ${who}: ${m.body.substring(0, 300)}`;
        }).join('\n\n');

        const retryResponse = await generateChatCompletion({
          model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama',
          messages: [
            { role: 'system', content: 'Share observations about this email relationship. No format. Be concise - under 200 words.' },
            { role: 'user', content: `Email history with ${contact.name}:\n\n${simpleEmailHistory}\n\nWhat do you notice?` },
          ],
          max_tokens: 150, // Limited to ~110 words (under 250 words requirement)
          temperature: 0.7,
          useLocal: process.env.USE_OLLAMA !== 'false', // Default to Ollama if not explicitly false
        });

        // Generate conversation summaries with retry
        const conversationSummaries = await Promise.all(
          last3Threads.map(async (thread) => {
            try {
              const threadText = thread.messages.map((m) => {
                const date = new Date(m.date).toLocaleDateString();
                const who = m.sender === 'contact' ? contact.name : 'You';
                return `${date} - ${who}: ${m.body.substring(0, 400)}`;
              }).join('\n\n');

              const convResponse = await generateChatCompletion({
                model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama',
                messages: [
                  { role: 'system', content: 'What happened in this conversation? Be concise - under 50 words.' },
                  { role: 'user', content: threadText },
                ],
                max_tokens: 80, // Limited to ~60 words for conversation summaries
                temperature: 0.7,
                useLocal: process.env.USE_OLLAMA !== 'false', // Default to Ollama if not explicitly false
              });

              return {
                thread_id: thread.thread_id,
                summary: convResponse.content.trim(),
                message_count: thread.messages.length,
                last_date: thread.messages[thread.messages.length - 1]?.date,
              };
            } catch (convError) {
              // If conversation summary fails, skip it - don't hardcode
              console.warn(`[Contact Summary] Failed to summarize conversation, skipping:`, convError);
              return null;
            }
          })
        );

        res.json({
          summary: retryResponse.content.trim(),
          recommendations: [],
          recentConversations: conversationSummaries.filter(c => c !== null),
          messageCount: recentMessages.length,
          taskStats: {
            total: parseInt(taskStats.total || '0'),
            pending: parseInt(taskStats.pending || '0'),
            completed: parseInt(taskStats.completed || '0'),
          },
        });
      } catch (retryError: any) {
        // If retry also fails, return error response that frontend can handle
        // Return 200 with error message in summary field so frontend can display it
        console.error('[Contact Summary] Retry also failed:', retryError?.message || retryError);
        const errorMsg = retryError?.message || 'LLM service unavailable';
        const errorResponse = { 
          summary: `Unable to generate summary. Error: ${errorMsg}. Please ensure Ollama is running and phi3 model is installed.`,
          recommendations: [
            'Start Ollama: ollama serve',
            'Install model: ollama pull phi3',
            'Check Ollama is running: curl http://localhost:11434/api/tags'
          ],
          recentConversations: [],
          messageCount: 0,
          taskStats: { total: 0, pending: 0, completed: 0 },
        };
        
        console.log('[Contact Summary] Sending error response:', errorResponse);
        res.status(200).json(errorResponse);
        return; // Important: return early to prevent further execution
      }
    }
  } catch (error: any) {
    console.error('Error generating contact summary:', error);
    // Return 200 with error message in summary field so frontend can display it
    res.status(200).json({ 
      summary: `Error generating summary: ${error?.message || 'Unknown error'}. Please check Ollama is running.`,
      recommendations: ['Ensure Ollama is running: ollama serve', 'Install phi3: ollama pull phi3'],
      recentConversations: [],
      messageCount: 0,
      taskStats: { total: 0, pending: 0, completed: 0 },
    });
  }
});

export default router;

