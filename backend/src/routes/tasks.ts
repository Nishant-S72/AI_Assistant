import { Router, Request, Response } from 'express';
import { pool } from '../db';
import { v4 as uuidv4 } from 'uuid';
import { computePriority } from '../lib/priority';

const router = Router();

// GET /api/tasks
router.get('/', async (req: Request, res: Response) => {
  try {
    const { status } = req.query;

    let query = `
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
    `;

    if (status) {
      query += ` WHERE t.status = $1`;
    }

    query += ` ORDER BY t.created_at DESC`;

    const result = await pool.query(
      query,
      status ? [status] : []
    );

    // Compute priority for each task
    const tasksWithPriority = result.rows.map((task: any) => {
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
          last_order_amount: 0, // TODO: Add if available
        },
      });

      return {
        ...task,
        priority,
      };
    });

    res.json(tasksWithPriority);
  } catch (error) {
    console.error('Error fetching tasks:', error);
    res.status(500).json({ error: 'Failed to fetch tasks' });
  }
});

// POST /api/tasks
router.post('/', async (req: Request, res: Response) => {
  try {
    const { contact_id, title, due_at, status = 'pending' } = req.body;

    if (!title) {
      return res.status(400).json({ error: 'Title is required' });
    }

    const result = await pool.query(
      `INSERT INTO tasks (contact_id, title, due_at, status)
       VALUES ($1, $2, $3, $4)
       RETURNING *`,
      [contact_id || null, title, due_at || null, status]
    );

    // Log event
    await pool.query(
      `INSERT INTO events (type, payload) VALUES ($1, $2)`,
      [
        'task_created',
        JSON.stringify({
          taskId: result.rows[0].id,
          contactId: contact_id,
          title,
        }),
      ]
    );

    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error creating task:', error);
    res.status(500).json({ error: 'Failed to create task' });
  }
});

export default router;

