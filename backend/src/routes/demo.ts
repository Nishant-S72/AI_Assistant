/**
 * Demo Routes
 * Fallback endpoints for dummy inbox when DB is unavailable
 */

import { Router, Request, Response } from 'express';
import * as fs from 'fs';
import * as path from 'path';

const router = Router();

// GET /api/demo/threads - Return dummy inbox threads as messages
router.get('/threads', async (req: Request, res: Response) => {
  try {
    const inboxPath = process.env.DUMMY_INBOX_PATH || './demo-inbox';
    const fullPath = path.resolve(process.cwd(), inboxPath);

    if (!fs.existsSync(fullPath)) {
      return res.json([]);
    }

    const files = fs.readdirSync(fullPath).filter((f) => f.endsWith('.json'));
    const threads: any[] = [];

    for (const file of files) {
      try {
        const filePath = path.join(fullPath, file);
        const content = fs.readFileSync(filePath, 'utf-8');
        const thread = JSON.parse(content);

        // Convert to message format
        const firstMessage = thread.messages[0];
        if (firstMessage) {
          threads.push({
            id: firstMessage.sender === 'customer' ? `msg-${thread.id}` : thread.id,
            thread_id: thread.id,
            sender: firstMessage.sender === 'customer' ? 'contact' : 'assistant',
            body: firstMessage.text,
            channel: 'email',
            created_at: firstMessage.timestamp,
            contact_name: thread.contact.name,
            contact_company: thread.contact.company,
            contact_email: thread.contact.email,
            message_count: thread.messages.length,
          });
        }
      } catch (error) {
        console.error(`Error reading ${file}:`, error);
      }
    }

    res.json(threads);
  } catch (error: any) {
    console.error('Error loading demo threads:', error);
    res.status(500).json({ error: 'Failed to load demo threads' });
  }
});

export default router;

