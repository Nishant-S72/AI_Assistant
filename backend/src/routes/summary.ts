import { Router, Request, Response } from 'express';
import { pool } from '../db';
import { computePriority } from '../lib/priority';
import { loadDummyInbox } from '../utils/loadDummyInbox';
import { generateChatCompletion, LLMMessage } from '../clients/llm';
import * as fs from 'fs';
import * as path from 'path';

const router = Router();

/**
 * GET /api/summary
 * Returns inbox summary with totals, tasks grouped by priority, and top leads
 */
router.get('/', async (req: Request, res: Response) => {
  const startTime = Date.now();
  try {
    // Check if database is available
    let dbAvailable = false;
    try {
      await pool.query('SELECT 1');
      dbAvailable = true;
    } catch (error) {
      console.warn('Database not available, using demo data');
    }

    let totals = {
      totalMessages: 0,
      unread: 0,
      leads: 0,
      complaints: 0,
    };

    let tasks: any[] = [];
    let topLeads: any[] = [];

    if (dbAvailable) {
      // Get message totals
      const messagesResult = await pool.query(`
        SELECT 
          COUNT(*) as total,
          COUNT(CASE WHEN processed = false THEN 1 END) as unread
        FROM messages
      `);
      totals.totalMessages = parseInt(messagesResult.rows[0]?.total || '0');
      totals.unread = parseInt(messagesResult.rows[0]?.unread || '0');

      // Get leads count (contacts with 'lead' tag)
      const leadsCountResult = await pool.query(`
        SELECT COUNT(*) as count
        FROM contacts
        WHERE tags::text LIKE '%lead%'
      `);
      totals.leads = parseInt(leadsCountResult.rows[0]?.count || '0');

      // Get complaints count (messages with complaint keywords)
      const complaintsResult = await pool.query(`
        SELECT COUNT(DISTINCT thread_id) as count
        FROM messages
        WHERE LOWER(body) LIKE '%complaint%' 
           OR LOWER(body) LIKE '%delay%'
           OR LOWER(body) LIKE '%late%'
           OR LOWER(body) LIKE '%angry%'
      `);
      totals.complaints = parseInt(complaintsResult.rows[0]?.count || '0');

      // Get tasks with priority computation and message context
      const tasksResult = await pool.query(`
        SELECT 
          t.*,
          c.name as contact_name,
          c.email as contact_email,
          c.tags as contact_tags,
          c.company as contact_company,
          (SELECT body FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as latest_message_body,
          (SELECT id FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as latest_message_id,
          (SELECT thread_id FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as thread_id
        FROM tasks t
        LEFT JOIN contacts c ON t.contact_id = c.id
        WHERE t.status = 'pending'
        ORDER BY t.due_at ASC NULLS LAST, t.created_at DESC
        LIMIT 50
      `);

      // Compute priority for each task
      tasks = tasksResult.rows.map((task: any) => {
        const contactTags = Array.isArray(task.contact_tags)
          ? task.contact_tags
          : typeof task.contact_tags === 'string'
            ? JSON.parse(task.contact_tags || '[]')
            : [];

        const priority = computePriority({
          task: {
            due_at: task.due_at,
            title: task.title,
            status: task.status,
          },
          message: {
            body: task.latest_message_body || '',
          },
          contact: {
            tags: contactTags,
            last_order_amount: 0, // TODO: Add last_order_amount to contacts table if needed
          },
        });

        return {
          ...task,
          priority,
          thread_id: task.thread_id,
          message_id: task.latest_message_id,
        };
      });

      // Get top leads (contacts with 'lead' tag, ordered by created_at)
      const topLeadsResult = await pool.query(`
        SELECT 
          c.id,
          c.name,
          c.email,
          c.company,
          c.tags,
          (SELECT COUNT(*) FROM messages m WHERE m.contact_id = c.id) as message_count
        FROM contacts c
        WHERE c.tags::text LIKE '%lead%'
        ORDER BY c.created_at DESC
        LIMIT 6
      `);

      topLeads = topLeadsResult.rows.map((lead: any) => ({
        id: lead.id,
        name: lead.name,
        company: lead.company,
        email: lead.email,
        message_count: parseInt(lead.message_count || '0'),
        last_order_amount: 0, // TODO: Add if available
      }));
    } else {
      // Demo mode: use dummy inbox data
      try {
        const dummyPath = process.env.DUMMY_INBOX_PATH || './demo-inbox';
        const files = fs.readdirSync(dummyPath).filter(f => f.endsWith('.json'));
        
        totals.totalMessages = files.length;
        totals.unread = files.length;
        totals.leads = files.filter(f => f.includes('lead')).length;
        totals.complaints = files.filter(f => f.includes('complaint')).length;

        // Load demo tasks from dummy inbox
        for (const file of files.slice(0, 10)) {
          const filePath = path.join(dummyPath, file);
          const content = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
          if (content.thread && content.thread.length > 0) {
            const latestMessage = content.thread[content.thread.length - 1];
            const priority = computePriority({
              message: {
                body: latestMessage.body || '',
              },
              contact: {
                tags: content.contact?.tags || [],
              },
            });

            tasks.push({
              id: `demo-${file}`,
              title: `Follow up: ${content.contact?.name || 'Contact'}`,
              due_at: new Date(Date.now() + Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
              status: 'pending',
              contact_name: content.contact?.name,
              contact_email: content.contact?.email,
              priority,
            });
          }
        }

        // Demo top leads
        topLeads = files
          .filter(f => f.includes('lead'))
          .slice(0, 6)
          .map((file, idx) => {
            const filePath = path.join(dummyPath, file);
            const content = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
            return {
              id: `demo-lead-${idx}`,
              name: content.contact?.name,
              company: content.contact?.company,
              email: content.contact?.email,
              message_count: content.thread?.length || 0,
              last_order_amount: 0,
            };
          });
      } catch (error) {
        console.warn('Could not load demo data:', error);
      }
    }

    // Group tasks by priority
    const tasksByPriority = {
      P0: tasks.filter(t => t.priority === 'P0').slice(0, 6),
      P1: tasks.filter(t => t.priority === 'P1').slice(0, 6),
      P2: tasks.filter(t => t.priority === 'P2').slice(0, 6),
    };

    const counts = {
      P0: tasks.filter(t => t.priority === 'P0').length,
      P1: tasks.filter(t => t.priority === 'P1').length,
      P2: tasks.filter(t => t.priority === 'P2').length,
    };

    // Get performance metrics
    let performance = {
      avgLatencyMs: null as number | null,
      suggestionsGenerated: 0,
      acceptanceRate: 0,
      messagesSent: 0,
    };

    if (dbAvailable) {
      try {
        // Average latency
        const latencyResult = await pool.query(
          `SELECT AVG(latency_ms) as avg_latency 
           FROM events 
           WHERE latency_ms IS NOT NULL 
           AND type = 'suggestion_generated'`
        );
        performance.avgLatencyMs = latencyResult.rows[0].avg_latency
          ? Math.round(parseFloat(latencyResult.rows[0].avg_latency))
          : null;

        // Suggestions generated
        const suggestionsResult = await pool.query(
          `SELECT COUNT(*) as count FROM suggestions`
        );
        performance.suggestionsGenerated = parseInt(suggestionsResult.rows[0].count || '0');

        // Acceptance rate
        const acceptedResult = await pool.query(
          `SELECT COUNT(*) as count 
           FROM suggestions 
           WHERE final_text IS NOT NULL 
           AND final_text = model_response 
           AND edited = false`
        );
        const accepted = parseInt(acceptedResult.rows[0].count || '0');
        performance.acceptanceRate = performance.suggestionsGenerated > 0
          ? Math.round((accepted / performance.suggestionsGenerated) * 100) / 100
          : 0;

        // Messages sent
        const sentResult = await pool.query(
          `SELECT COUNT(*) as count FROM events WHERE type = 'message_sent'`
        );
        performance.messagesSent = parseInt(sentResult.rows[0].count || '0');
      } catch (error) {
        console.warn('Could not fetch performance metrics:', error);
      }
    }

    // Get top P0 task for human-like summary
    const topP0Task = tasksByPriority.P0[0] || null;
    const urgentContext = topP0Task ? {
      contactName: topP0Task.contact_name || 'A customer',
      taskTitle: topP0Task.title || '',
      messageBody: topP0Task.latest_message_body || '',
    } : null;

    // Generate LLM summary - make it detailed and natural, but fast
    let summaryParagraph = '';
    let summaryGenerating = true;
    
    // Check cache first
    if ((global as any).summaryCache && (global as any).summaryCacheTimestamp) {
      const cacheAge = Date.now() - (global as any).summaryCacheTimestamp;
      if (cacheAge < 60000) { // 1 minute cache
        summaryParagraph = (global as any).summaryCache;
        summaryGenerating = false;
      }
    }
    
    // Generate detailed LLM summary if not cached
    if (!summaryParagraph) {
      try {
        // Build rich context for detailed summary
        const topP0Tasks = tasksByPriority.P0.slice(0, 3).map(t => `${t.contact_name || 'Contact'}: ${t.title}`).join(', ');
        const topLeadsList = topLeads.slice(0, 3).map(l => `${l.name}${l.company ? ` from ${l.company}` : ''}`).join(', ');
        
        const summaryPrompt = `Here's what's in the inbox right now:

${totals.totalMessages} total messages, ${totals.unread} unread. ${totals.leads} potential leads, ${totals.complaints} complaints flagged.

${counts.P0} urgent tasks (P0) need immediate attention${topP0Tasks ? ` - including: ${topP0Tasks}` : ''}. ${counts.P1} high-priority tasks (P1) due soon. ${counts.P2} normal tasks.

${urgentContext ? `Most urgent: ${urgentContext.contactName} has ${urgentContext.taskTitle}. ${urgentContext.messageBody ? `Their message: "${urgentContext.messageBody.substring(0, 200)}"` : ''}` : ''}

${topLeads.length > 0 ? `Top leads: ${topLeadsList}.` : ''}

Give me a concise summary of what's happening. Be specific about who needs attention and why. Keep it brief - under 250 words.`;

        const llmResponse = await generateChatCompletion({
          model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'tinyllama',
          messages: [
            {
              role: 'system',
              content: 'You\'re briefing someone about their inbox. Be natural, specific, and concise. Mention actual people and situations. No generic statements. Keep it under 250 words - be direct and brief.',
            },
            {
              role: 'user',
              content: summaryPrompt,
            },
          ] as LLMMessage[],
          temperature: 0.7, // Balanced for natural but coherent
          max_tokens: 200, // Limited to ~150 words (under 250 words requirement)
          useLocal: process.env.USE_OLLAMA !== 'false', // Default to Ollama if not explicitly false
        });

        summaryParagraph = llmResponse.content.trim();
        summaryGenerating = false;
        
        // Cache for 1 minute
        (global as any).summaryCache = summaryParagraph;
        (global as any).summaryCacheTimestamp = Date.now();
        
        console.log('[Summary] LLM summary generated (length:', summaryParagraph.length, ')');
      } catch (error: any) {
        console.error('[Summary] Failed to generate LLM summary:', error.message);
        console.error('[Summary] Error details:', error);
        // Don't use hardcoded fallback - return empty string so frontend can handle it
        summaryParagraph = '';
        summaryGenerating = false;
        // Log the error for debugging
        if (error.message?.includes('ECONNREFUSED') || error.message?.includes('fetch failed')) {
          console.error('[Summary] Ollama connection failed. Is Ollama running?');
        }
      }
    }

    const responseTime = Date.now() - startTime;
    console.log(`[Summary] Generated in ${responseTime}ms`);
    
    if (responseTime > 5000) {
      console.warn(`[Summary] Slow response: ${responseTime}ms`);
    }

    res.json({
      totals,
      tasks: {
        counts,
        P0: tasksByPriority.P0,
        P1: tasksByPriority.P1,
        P2: tasksByPriority.P2,
      },
      topLeads: topLeads.slice(0, 6),
      performance,
      urgentContext: urgentContext || undefined,
      summaryParagraph: summaryParagraph || null,
      summaryGenerating: false,
      simulated: !dbAvailable,
    });
  } catch (error: any) {
    console.error('Error fetching summary:', error);
    res.status(500).json({ error: 'Failed to fetch summary', details: error.message });
  }
});

// GET /api/summary/category - Generate category-specific summary
router.get('/category', async (req: Request, res: Response) => {
  try {
    const { type } = req.query;
    
    if (!type || !['urgent', 'high', 'unread', 'complaints', 'leads'].includes(type as string)) {
      return res.status(400).json({ error: 'Invalid category type' });
    }

    // Check if database is available
    let dbAvailable = false;
    try {
      await pool.query('SELECT 1');
      dbAvailable = true;
    } catch (error) {
      console.warn('Database not available');
    }

    let categoryData: any = {};
    let tasks: any[] = [];
    let topLeads: any[] = [];

    if (dbAvailable) {
      // Get relevant data based on category
      switch (type) {
        case 'urgent':
          const urgentTasksResult = await pool.query(`
            SELECT 
              t.*,
              c.name as contact_name,
              c.email as contact_email,
              c.tags as contact_tags,
              c.company as contact_company,
              (SELECT body FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as latest_message_body
            FROM tasks t
            LEFT JOIN contacts c ON t.contact_id = c.id
            WHERE t.status = 'pending'
            AND (t.due_at <= NOW() OR c.tags::text LIKE '%urgent%' OR c.tags::text LIKE '%vip%')
            ORDER BY t.due_at ASC NULLS LAST
            LIMIT 10
          `);
          tasks = urgentTasksResult.rows;
          categoryData = {
            count: tasks.length,
            tasks: tasks.map((t: any) => ({
              title: t.title,
              contact: t.contact_name,
              dueDate: t.due_at,
              message: t.latest_message_body?.substring(0, 200),
            })),
          };
          break;
        
        case 'high':
          const highTasksResult = await pool.query(`
            SELECT 
              t.*,
              c.name as contact_name,
              c.email as contact_email,
              (SELECT body FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as latest_message_body
            FROM tasks t
            LEFT JOIN contacts c ON t.contact_id = c.id
            WHERE t.status = 'pending'
            AND t.due_at BETWEEN NOW() AND NOW() + INTERVAL '3 days'
            ORDER BY t.due_at ASC
            LIMIT 10
          `);
          tasks = highTasksResult.rows;
          categoryData = {
            count: tasks.length,
            tasks: tasks.map((t: any) => ({
              title: t.title,
              contact: t.contact_name,
              dueDate: t.due_at,
            })),
          };
          break;
        
        case 'unread':
          const unreadResult = await pool.query(`
            SELECT 
              m.*,
              c.name as contact_name,
              c.email as contact_email,
              c.company as contact_company
            FROM messages m
            JOIN contacts c ON m.contact_id = c.id
            WHERE m.processed = false
            ORDER BY m.created_at DESC
            LIMIT 20
          `);
          categoryData = {
            count: unreadResult.rows.length,
            messages: unreadResult.rows.map((m: any) => ({
              contact: m.contact_name,
              company: m.contact_company,
              preview: m.body.substring(0, 150),
              date: m.created_at,
            })),
          };
          break;
        
        case 'complaints':
          const complaintsResult = await pool.query(`
            SELECT DISTINCT ON (m.thread_id)
              m.*,
              c.name as contact_name,
              c.email as contact_email,
              c.company as contact_company
            FROM messages m
            JOIN contacts c ON m.contact_id = c.id
            WHERE LOWER(m.body) LIKE '%complaint%' 
               OR LOWER(m.body) LIKE '%delay%'
               OR LOWER(m.body) LIKE '%late%'
               OR LOWER(m.body) LIKE '%angry%'
            ORDER BY m.thread_id, m.created_at DESC
            LIMIT 10
          `);
          categoryData = {
            count: complaintsResult.rows.length,
            complaints: complaintsResult.rows.map((c: any) => ({
              contact: c.contact_name,
              company: c.contact_company,
              issue: c.body.substring(0, 200),
              date: c.created_at,
            })),
          };
          break;
        
        case 'leads':
          const leadsResult = await pool.query(`
            SELECT 
              c.*,
              (SELECT COUNT(*) FROM messages m WHERE m.contact_id = c.id) as message_count
            FROM contacts c
            WHERE c.tags::text LIKE '%lead%'
            ORDER BY c.created_at DESC
            LIMIT 10
          `);
          topLeads = leadsResult.rows;
          categoryData = {
            count: topLeads.length,
            leads: topLeads.map((l: any) => ({
              name: l.name,
              company: l.company,
              email: l.email,
              messageCount: parseInt(l.message_count || '0'),
            })),
          };
          break;
      }
    }

    // Generate natural, LLM-powered summary instead of template
    let summaryText = '';
    
    try {
      // Build context for LLM based on category
      let contextPrompt = '';
      let systemPrompt = '';
      
      switch (type) {
        case 'urgent':
          systemPrompt = 'You\'re briefing someone about urgent items. Be natural and conversational. Mention specific people and situations. Keep it under 100 words.';
          if (categoryData.tasks && categoryData.tasks.length > 0) {
            const tasksList = categoryData.tasks.slice(0, 5).map((t: any, idx: number) => 
              `${idx + 1}. ${t.contact || 'Someone'}: ${t.title}${t.dueDate ? ` (due ${new Date(t.dueDate).toLocaleDateString()})` : ''}`
            ).join('\n');
            contextPrompt = `Here are ${categoryData.count} urgent items:\n\n${tasksList}\n\nWhat needs immediate attention?`;
          } else {
            contextPrompt = `There are ${categoryData.count || 0} urgent items requiring attention.`;
          }
          break;
          
        case 'high':
          systemPrompt = 'You\'re briefing someone about high-priority items. Be natural and conversational. Keep it under 100 words.';
          if (categoryData.tasks && categoryData.tasks.length > 0) {
            const tasksList = categoryData.tasks.slice(0, 5).map((t: any) => 
              `${t.contact || 'Someone'}: ${t.title}`
            ).join(', ');
            contextPrompt = `Here are ${categoryData.count} high-priority items due soon: ${tasksList}.`;
          } else {
            contextPrompt = `There are ${categoryData.count || 0} high-priority items due within the next few days.`;
          }
          break;
          
        case 'unread':
          systemPrompt = 'You\'re briefing someone about unread messages. Be natural and conversational. Mention who\'s waiting. Keep it under 100 words.';
          if (categoryData.messages && categoryData.messages.length > 0) {
            const senders = [...new Set(categoryData.messages.slice(0, 5).map((m: any) => m.contact))].join(', ');
            contextPrompt = `You have ${categoryData.count} unread messages from: ${senders}.`;
          } else {
            contextPrompt = `You have ${categoryData.count || 0} unread messages waiting.`;
          }
          break;
          
        case 'complaints':
          systemPrompt = 'You\'re briefing someone about customer complaints. Be natural and conversational. Mention who\'s having issues. Keep it under 100 words.';
          if (categoryData.complaints && categoryData.complaints.length > 0) {
            const complainers = [...new Set(categoryData.complaints.slice(0, 3).map((c: any) => c.contact))].join(', ');
            contextPrompt = `There are ${categoryData.count} complaints from: ${complainers}.`;
          } else {
            contextPrompt = `There are ${categoryData.count || 0} complaints that need attention.`;
          }
          break;
          
        case 'leads':
          systemPrompt = 'You\'re briefing someone about potential leads. Be natural and conversational. Mention interesting prospects. Keep it under 100 words.';
          if (categoryData.leads && categoryData.leads.length > 0) {
            const leadsList = categoryData.leads.slice(0, 3).map((l: any) => 
              `${l.name}${l.company ? ` from ${l.company}` : ''}`
            ).join(', ');
            contextPrompt = `You have ${categoryData.count} leads in the pipeline: ${leadsList}.`;
          } else {
            contextPrompt = `You have ${categoryData.count || 0} leads in the pipeline.`;
          }
          break;
          
        default:
          summaryText = 'No summary available.';
      }
      
      // Generate LLM summary if we have a prompt
      if (contextPrompt && systemPrompt) {
        const llmResponse = await generateChatCompletion({
          model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || 'phi3',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: contextPrompt },
          ] as LLMMessage[],
          temperature: 0.7,
          max_tokens: 120, // ~90 words (under 100 words requirement)
          useLocal: process.env.USE_OLLAMA !== 'false', // Default to Ollama if not explicitly false
        });
        
        summaryText = llmResponse.content.trim();
      }
    } catch (error: any) {
      console.warn('[Category Summary] LLM generation failed, using fallback:', error.message);
      // Simple fallback if LLM fails
      summaryText = categoryData.count > 0 
        ? `${categoryData.count} ${type} item${categoryData.count !== 1 ? 's' : ''} need${categoryData.count === 1 ? 's' : ''} attention.`
        : `No ${type} items at the moment.`;
    }

    res.json({
      category: type,
      summary: summaryText,
      data: categoryData,
    });
  } catch (error: any) {
    console.error('Error generating category summary:', error);
    res.status(500).json({ error: 'Failed to generate category summary', details: error.message });
  }
});

export default router;

