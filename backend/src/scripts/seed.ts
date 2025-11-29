import { pool } from '../db';
import { vectorStore } from '../services/vectorStore';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

interface DemoInbox {
  contact: {
    name: string;
    email: string;
    phone?: string;
    company?: string;
    tags: string[];
    tone_pref: string;
  };
  thread: Array<{
    sender: 'contact' | 'assistant';
    body: string;
    created_at?: string;
  }>;
}

export async function seedDemoData() {
  console.log('🌱 Seeding demo data...');

  // Load demo data files
  const demoDataPath = path.join(__dirname, '../../../demo-data');
  const leadData = JSON.parse(
    fs.readFileSync(path.join(demoDataPath, 'lead.json'), 'utf-8')
  ) as DemoInbox;
  const complaintData = JSON.parse(
    fs.readFileSync(path.join(demoDataPath, 'complaint.json'), 'utf-8')
  ) as DemoInbox;
  const meetingData = JSON.parse(
    fs.readFileSync(path.join(demoDataPath, 'meeting.json'), 'utf-8')
  ) as DemoInbox;

  const inboxes = [
    { name: 'lead', data: leadData },
    { name: 'complaint', data: complaintData },
    { name: 'meeting', data: meetingData },
  ];

  for (const inbox of inboxes) {
    const { contact, thread } = inbox.data;

    // Insert contact
    const contactResult = await pool.query(
      `INSERT INTO contacts (name, email, phone, company, tags, tone_pref)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT DO NOTHING
       RETURNING id`,
      [
        contact.name,
        contact.email,
        contact.phone || null,
        contact.company || null,
        JSON.stringify(contact.tags),
        contact.tone_pref || 'warm',
      ]
    );

    let contactId: string;
    if (contactResult.rows.length > 0) {
      contactId = contactResult.rows[0].id;
    } else {
      // Contact already exists, fetch it
      const existing = await pool.query(
        `SELECT id FROM contacts WHERE email = $1`,
        [contact.email]
      );
      contactId = existing.rows[0].id;
    }

    // Generate thread_id
    const threadId = uuidv4();

    // Insert messages
    for (const msg of thread) {
      const createdAt = msg.created_at
        ? new Date(msg.created_at)
        : new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000); // Random time in last 7 days

      await pool.query(
        `INSERT INTO messages (contact_id, channel, thread_id, sender, body, created_at)
         VALUES ($1, $2, $3, $4, $5, $6)
         ON CONFLICT DO NOTHING`,
        [contactId, 'email', threadId, msg.sender, msg.body, createdAt]
      );

      // Store message in vector store for RAG
      if (msg.sender === 'contact') {
        const msgId = uuidv4();
        await vectorStore.addDocument(msgId, msg.body, {
          type: 'message',
          contact_id: contactId,
          created_at: createdAt.toISOString(),
        });
      }
    }

    console.log(`✅ Seeded ${inbox.name} inbox for ${contact.name}`);
  }

  // Add some KB chunks to vector store
  const kbChunks = [
    {
      text: 'Our company offers a 30-day money-back guarantee on all products. Customers can request a refund by contacting support@example.com.',
      metadata: { type: 'kb', source: 'policy_doc' },
    },
    {
      text: 'For enterprise customers, we offer dedicated account managers and 24/7 priority support. Contact sales@example.com for more information.',
      metadata: { type: 'kb', source: 'sales_doc' },
    },
    {
      text: 'Product delivery typically takes 3-5 business days for standard shipping. Express shipping (1-2 days) is available for an additional fee.',
      metadata: { type: 'kb', source: 'shipping_doc' },
    },
  ];

  for (const chunk of kbChunks) {
    const chunkId = uuidv4();
    await vectorStore.addDocument(chunkId, chunk.text, {
      ...chunk.metadata,
      created_at: new Date().toISOString(),
    });
  }

  console.log('✅ Seeded knowledge base chunks');

  // Create some demo tasks
  await pool.query(
    `INSERT INTO tasks (contact_id, title, due_at, status)
     SELECT id, 'Follow up on pricing inquiry', NOW() + INTERVAL '2 days', 'pending'
     FROM contacts WHERE email = $1
     ON CONFLICT DO NOTHING`,
    [leadData.contact.email]
  );

  console.log('✅ Seeded demo tasks');

  console.log('🎉 Demo data seeding complete!');
}

// Run if called directly
if (require.main === module) {
  seedDemoData()
    .then(() => {
      console.log('Done');
      process.exit(0);
    })
    .catch((error) => {
      console.error('Error:', error);
      process.exit(1);
    });
}

