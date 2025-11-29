import { pool } from '../db';
import { vectorStore } from '../services/vectorStore';
import { v4 as uuidv4 } from 'uuid';

interface EnrichedMessage {
  sender: 'contact' | 'assistant';
  body: string;
  created_at?: string;
}

interface EnrichedThread {
  contact: {
    name: string;
    email: string;
    phone?: string;
    company?: string;
    tags: string[];
    tone_pref: string;
  };
  subject?: string;
  messages: EnrichedMessage[];
}

export async function seedEnrichedData() {
  console.log('🌱 Seeding enriched demo data...');

  const threads: EnrichedThread[] = [
    // 1. Lead Inquiry - Bulk Order
    {
      contact: {
        name: 'Sarah Martinez',
        email: 'sarah.martinez@greenretail.com',
        phone: '+1-555-0101',
        company: 'Green Retail Co.',
        tags: ['lead', 'bulk-order', 'customization'],
        tone_pref: 'warm',
      },
      subject: 'Bulk Order Inquiry - 200 Vegan Leather Bags',
      messages: [
        {
          sender: 'contact',
          body: 'Hello, I\'m reaching out on behalf of Green Retail Co. We\'re interested in placing a bulk order for 200 vegan leather bags for our upcoming spring collection. Could you please provide pricing information, available colors, and estimated delivery time? We\'re looking to launch by March 15th.',
          created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          sender: 'assistant',
          body: 'Thank you for your interest in our vegan leather bags! I\'d be happy to help you with pricing and availability for your bulk order. Let me connect you with our sales team who can provide detailed pricing and delivery estimates.',
          created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000).toISOString(),
        },
        {
          sender: 'contact',
          body: 'That would be great! Also, we\'re interested in custom branding options. Can you include information about logo placement and minimum order quantities for customization?',
          created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ],
    },
    // 2. Shipping Complaint
    {
      contact: {
        name: 'Michael Chen',
        email: 'mchen@startup.io',
        phone: '+1-555-0202',
        company: 'Startup.io',
        tags: ['complaint', 'shipping', 'urgent'],
        tone_pref: 'formal',
      },
      subject: 'Delayed Shipment - Order #12345',
      messages: [
        {
          sender: 'contact',
          body: 'Hi, I placed an order (#12345) two weeks ago and it still hasn\'t arrived. The tracking shows it\'s been stuck in transit for 5 days. This is for an important client presentation next week. Can you please investigate and expedite?',
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          sender: 'assistant',
          body: 'I sincerely apologize for the delay with your order. I\'ve escalated this to our shipping team and they\'re investigating immediately. I\'ll send you an update within 2 hours with the current status and next steps.',
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
        },
        {
          sender: 'contact',
          body: 'Thank you for the quick response. I really need this resolved ASAP. Can you also provide options for express shipping if the original package is lost?',
          created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ],
    },
    // 3. Partnership Meeting Request
    {
      contact: {
        name: 'Emily Rodriguez',
        email: 'emily@techpartners.com',
        phone: '+1-555-0303',
        company: 'Tech Partners Inc.',
        tags: ['meeting', 'partnership', 'enterprise'],
        tone_pref: 'crisp',
      },
      subject: 'Partnership Discussion - Enterprise Integration',
      messages: [
        {
          sender: 'contact',
          body: 'Hi there! We\'re exploring potential partnerships with companies in your space. We have a platform that could integrate with your product and create value for both our customer bases. Would you be open to a 30-minute call next week to discuss?',
          created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          sender: 'assistant',
          body: 'Thank you for reaching out! We\'re always interested in exploring strategic partnerships. I\'ll check our calendar and send you some available time slots for next week.',
          created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000 + 4 * 60 * 60 * 1000).toISOString(),
        },
      ],
    },
    // 4. Product Question
    {
      contact: {
        name: 'David Kim',
        email: 'david.kim@designstudio.com',
        phone: '+1-555-0404',
        company: 'Design Studio',
        tags: ['question', 'product', 'technical'],
        tone_pref: 'warm',
      },
      subject: 'Question about Material Specifications',
      messages: [
        {
          sender: 'contact',
          body: 'I\'m considering your products for a design project and need to know the exact material composition and sustainability certifications. Do you have detailed spec sheets available? Also, are the materials suitable for outdoor use?',
          created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ],
    },
    // 5. Return Request
    {
      contact: {
        name: 'Jennifer White',
        email: 'j.white@email.com',
        phone: '+1-555-0505',
        company: undefined,
        tags: ['return', 'refund', 'customer-service'],
        tone_pref: 'warm',
      },
      subject: 'Return Request - Item Not as Described',
      messages: [
        {
          sender: 'contact',
          body: 'I received my order yesterday but the item doesn\'t match the description on your website. The color is completely different and the size is off. I\'d like to return it and get a refund. What\'s the process?',
          created_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          sender: 'assistant',
          body: 'I\'m sorry to hear the item didn\'t meet your expectations. We\'ll process your return immediately. I\'m sending you a prepaid return label via email. Once we receive the item, we\'ll issue a full refund within 3-5 business days.',
          created_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000 + 1 * 60 * 60 * 1000).toISOString(),
        },
      ],
    },
    // 6. Feature Request
    {
      contact: {
        name: 'Robert Taylor',
        email: 'rtaylor@enterprise.com',
        phone: '+1-555-0606',
        company: 'Enterprise Solutions',
        tags: ['feature-request', 'enterprise', 'feedback'],
        tone_pref: 'crisp',
      },
      subject: 'Feature Request - API Integration',
      messages: [
        {
          sender: 'contact',
          body: 'We\'re evaluating your platform for our enterprise needs. One critical requirement is API integration with our existing systems. Do you currently offer REST APIs? If not, is this on your roadmap?',
          created_at: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          sender: 'assistant',
          body: 'Great question! We do have REST APIs available for enterprise customers. I\'ll have our technical team send you the API documentation and we can schedule a technical walkthrough if you\'d like.',
          created_at: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000).toISOString(),
        },
        {
          sender: 'contact',
          body: 'Perfect! Please send the docs and I\'ll review with my team. We\'re looking to make a decision by end of month.',
          created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ],
    },
    // 7. Support Question
    {
      contact: {
        name: 'Lisa Anderson',
        email: 'lisa.anderson@smallbiz.com',
        phone: '+1-555-0707',
        company: 'Small Business Co.',
        tags: ['support', 'technical', 'help'],
        tone_pref: 'warm',
      },
      subject: 'Need Help with Setup',
      messages: [
        {
          sender: 'contact',
          body: 'I just purchased your product and I\'m having trouble with the initial setup. The installation guide isn\'t clear about step 3. Can someone walk me through it?',
          created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ],
    },
    // 8. Pricing Inquiry
    {
      contact: {
        name: 'James Wilson',
        email: 'jwilson@corp.com',
        phone: '+1-555-0808',
        company: 'Corp Industries',
        tags: ['pricing', 'enterprise', 'quote'],
        tone_pref: 'formal',
      },
      subject: 'Enterprise Pricing Inquiry',
      messages: [
        {
          sender: 'contact',
          body: 'We\'re a company of 500+ employees and interested in your enterprise plan. Can you provide detailed pricing for annual contracts? We\'re also interested in volume discounts and custom terms.',
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          sender: 'assistant',
          body: 'Thank you for your interest! I\'ll have our enterprise sales team prepare a customized quote based on your requirements. They\'ll reach out within 24 hours with pricing and contract options.',
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000 + 3 * 60 * 60 * 1000).toISOString(),
        },
      ],
    },
  ];

  for (const thread of threads) {
    const { contact, messages } = thread;

    // Insert contact
    let contactResult = await pool.query(
      `SELECT id FROM contacts WHERE email = $1`,
      [contact.email]
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
          contact.name,
          contact.email,
          contact.phone || null,
          contact.company || null,
          JSON.stringify(contact.tags),
          contact.tone_pref,
        ]
      );
      contactId = insertResult.rows[0].id;
    }

    // Generate thread_id
    const threadId = uuidv4();

    // Insert messages
    for (const msg of messages) {
      const createdAt = msg.created_at
        ? new Date(msg.created_at)
        : new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000);

      await pool.query(
        `INSERT INTO messages (contact_id, channel, thread_id, sender, body, created_at)
         VALUES ($1, $2, $3, $4, $5, $6)
         ON CONFLICT DO NOTHING`,
        [contactId, 'email', threadId, msg.sender, msg.body, createdAt]
      );

      // Store customer messages in vector store for RAG
      if (msg.sender === 'contact') {
        const msgId = uuidv4();
        try {
          await vectorStore.addDocument(msgId, msg.body, {
            type: 'message',
            contact_id: contactId,
            created_at: createdAt.toISOString(),
          });
        } catch (error) {
          console.warn('Could not add to vector store:', error);
        }
      }
    }

    console.log(`✅ Seeded thread for ${contact.name}`);
  }

  // Add knowledge base chunks
  const kbChunks = [
    {
      text: 'Our company offers a 30-day money-back guarantee on all products. Customers can request a refund by contacting support@example.com. Refunds are processed within 3-5 business days.',
      metadata: { type: 'kb', source: 'policy_doc', category: 'returns' },
    },
    {
      text: 'For enterprise customers, we offer dedicated account managers and 24/7 priority support. Contact sales@example.com for more information. Enterprise plans include custom integrations and SLA guarantees.',
      metadata: { type: 'kb', source: 'sales_doc', category: 'enterprise' },
    },
    {
      text: 'Product delivery typically takes 3-5 business days for standard shipping. Express shipping (1-2 days) is available for an additional fee. International shipping takes 7-14 business days.',
      metadata: { type: 'kb', source: 'shipping_doc', category: 'shipping' },
    },
    {
      text: 'We offer bulk order discounts: 10% off for orders of 50-99 units, 15% off for 100-199 units, and 20% off for 200+ units. Custom branding is available for orders of 100+ units.',
      metadata: { type: 'kb', source: 'pricing_doc', category: 'pricing' },
    },
    {
      text: 'Our products are made from 100% sustainable materials with certifications from FSC and OEKO-TEX. All materials are suitable for both indoor and outdoor use with proper care.',
      metadata: { type: 'kb', source: 'product_doc', category: 'materials' },
    },
    {
      text: 'We provide REST APIs for enterprise customers. API documentation is available in our developer portal. Technical support for API integration is included with enterprise plans.',
      metadata: { type: 'kb', source: 'api_doc', category: 'technical' },
    },
  ];

  for (const chunk of kbChunks) {
    const chunkId = uuidv4();
    try {
      await vectorStore.addDocument(chunkId, chunk.text, {
        ...chunk.metadata,
        created_at: new Date().toISOString(),
      });
    } catch (error) {
      console.warn('Could not add KB chunk:', error);
    }
  }

  console.log('✅ Seeded knowledge base chunks');

  // Create demo tasks
  const tasks = [
    { email: 'sarah.martinez@greenretail.com', title: 'Follow up on bulk order pricing', days: 2 },
    { email: 'mchen@startup.io', title: 'Resolve shipping delay issue', days: 0 },
    { email: 'emily@techpartners.com', title: 'Schedule partnership call', days: 3 },
    { email: 'jwilson@corp.com', title: 'Send enterprise pricing quote', days: 1 },
  ];

  for (const task of tasks) {
    const contactResult = await pool.query(
      `SELECT id FROM contacts WHERE email = $1`,
      [task.email]
    );
    if (contactResult.rows.length > 0) {
      await pool.query(
        `INSERT INTO tasks (contact_id, title, due_at, status)
         VALUES ($1, $2, NOW() + INTERVAL '${task.days} days', 'pending')
         ON CONFLICT DO NOTHING`,
        [contactResult.rows[0].id, task.title]
      );
    }
  }

  console.log('✅ Seeded demo tasks');
  console.log('🎉 Enriched demo data seeding complete!');
}

