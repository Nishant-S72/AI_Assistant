import * as fs from 'fs';
import * as path from 'path';
import { pool } from '../db';
import { v4 as uuidv4 } from 'uuid';

interface DummyMessage {
  sender: 'customer' | 'assistant';
  text: string;
  timestamp: string;
}

interface DummyContact {
  name: string;
  email: string;
  company?: string;
  phone?: string;
}

interface DummyThread {
  id: string;
  contact: DummyContact;
  subject: string;
  messages: DummyMessage[];
  tags?: string[];
  priority?: string;
}

export async function loadDummyInbox(): Promise<number> {
  const inboxPath = process.env.DUMMY_INBOX_PATH || './demo-inbox';
  const fullPath = path.resolve(process.cwd(), inboxPath);

  console.log(`📂 Loading dummy inbox from: ${fullPath}`);

  if (!fs.existsSync(fullPath)) {
    console.warn(`⚠️  Dummy inbox path not found: ${fullPath}`);
    return 0;
  }

  const files = fs.readdirSync(fullPath).filter((f) => f.endsWith('.json'));
  console.log(`📄 Found ${files.length} inbox files`);

  let threadsLoaded = 0;

  for (const file of files) {
    try {
      const filePath = path.join(fullPath, file);
      const content = fs.readFileSync(filePath, 'utf-8');
      const thread: DummyThread = JSON.parse(content);

      // Check if thread already exists
      const existing = await pool.query(
        `SELECT id FROM messages WHERE thread_id = $1 LIMIT 1`,
        [thread.id]
      );

      if (existing.rows.length > 0) {
        console.log(`⏭️  Thread ${thread.id} already exists, skipping`);
        continue;
      }

      // Check if contact exists, otherwise insert
      let contactResult = await pool.query(
        `SELECT id FROM contacts WHERE email = $1`,
        [thread.contact.email]
      );

      let contactId: string;
      if (contactResult.rows.length > 0) {
        contactId = contactResult.rows[0].id;
      } else {
        const insertResult = await pool.query(
          `INSERT INTO contacts (name, email, phone, company, tags, tone_pref)
           VALUES ($1, $2, $3, $4, $5, $6)
           RETURNING id`,
          [
            thread.contact.name,
            thread.contact.email,
            thread.contact.phone || null,
            thread.contact.company || null,
            JSON.stringify(thread.tags || []),
            'warm',
          ]
        );
        contactId = insertResult.rows[0].id;
      }

      // Insert messages
      for (const msg of thread.messages) {
        await pool.query(
          `INSERT INTO messages (contact_id, channel, thread_id, sender, body, created_at)
           VALUES ($1, $2, $3, $4, $5, $6)`,
          [
            contactId,
            'email',
            thread.id,
            msg.sender === 'customer' ? 'contact' : 'assistant',
            msg.text,
            new Date(msg.timestamp),
          ]
        );
      }

      threadsLoaded++;
      console.log(`✅ Loaded thread: ${thread.subject} (${thread.messages.length} messages)`);
    } catch (error: any) {
      console.error(`❌ Error loading ${file}:`, error.message);
    }
  }

  console.log(`🎉 Loaded ${threadsLoaded} dummy inbox threads`);
  return threadsLoaded;
}

// Run if called directly
if (require.main === module) {
  loadDummyInbox()
    .then((count) => {
      console.log(`Done. Loaded ${count} threads.`);
      process.exit(0);
    })
    .catch((error) => {
      console.error('Error:', error);
      process.exit(1);
    });
}

