/**
 * Script to create a dummy contact with 2 years of interaction history
 */

import { pool } from '../db';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  sender: 'contact' | 'assistant';
  body: string;
  created_at: Date;
}

async function createLongHistoryContact() {
  console.log('📝 Creating contact with 2 years of history...');

  const contactName = 'Sarah Johnson';
  const contactEmail = 'sarah.johnson@techcorp.com';
  const contactCompany = 'TechCorp Solutions';
  const contactPhone = '+1-555-0123';
  const contactTags = ['vip', 'lead', 'enterprise'];
  const contactTonePref = 'professional';

  // Check if contact already exists
  let contactResult = await pool.query(
    `SELECT id FROM contacts WHERE email = $1`,
    [contactEmail]
  );

  let contactId: string;
  if (contactResult.rows.length > 0) {
    contactId = contactResult.rows[0].id;
    console.log(`✅ Using existing contact: ${contactId}`);
    
    // Delete existing messages for this contact
    await pool.query(`DELETE FROM messages WHERE contact_id = $1`, [contactId]);
    await pool.query(`DELETE FROM tasks WHERE contact_id = $1`, [contactId]);
  } else {
    // Create new contact
    const insertResult = await pool.query(
      `INSERT INTO contacts (name, email, phone, company, tags, tone_pref)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id`,
      [
        contactName,
        contactEmail,
        contactPhone,
        contactCompany,
        JSON.stringify(contactTags),
        contactTonePref,
      ]
    );
    contactId = insertResult.rows[0].id;
    console.log(`✅ Created new contact: ${contactId}`);
  }

  // Generate 2 years of message history
  const now = new Date();
  const twoYearsAgo = new Date(now.getTime() - 2 * 365 * 24 * 60 * 60 * 1000);
  
  const messages: Message[] = [];
  const threadIds: string[] = [];

  // Create multiple conversation threads over 2 years
  const threadCount = 15; // 15 different conversation threads
  for (let t = 0; t < threadCount; t++) {
    const threadId = uuidv4();
    threadIds.push(threadId);
    
    // Spread threads over 2 years
    const threadStartDate = new Date(
      twoYearsAgo.getTime() + 
      (t / threadCount) * (now.getTime() - twoYearsAgo.getTime()) +
      Math.random() * 30 * 24 * 60 * 60 * 1000 // Random offset within month
    );

    // Each thread has 2-5 messages
    const messagesInThread = 2 + Math.floor(Math.random() * 4);
    
    for (let m = 0; m < messagesInThread; m++) {
      const messageDate = new Date(
        threadStartDate.getTime() + m * (Math.random() * 3 + 0.5) * 24 * 60 * 60 * 1000
      );

      let body = '';
      let sender: 'contact' | 'assistant' = m % 2 === 0 ? 'contact' : 'assistant';

      if (t === 0 && m === 0) {
        // First message - initial inquiry
        body = 'Hi, I\'m interested in learning more about your enterprise platform. We\'re a growing tech company and looking for a solution to manage our customer communications. Can you provide more information about pricing and features?';
      } else if (t === 1 && m === 0) {
        // Second thread - follow-up
        body = 'Thank you for the information. We\'d like to schedule a demo to see how this would work for our team. We have about 50 employees who would be using the system.';
      } else if (t === 2 && m === 0) {
        // Third thread - pricing discussion
        body = 'The pricing looks reasonable. We\'re particularly interested in the enterprise features. Can you tell me more about the integration capabilities with Salesforce?';
      } else if (t === 3 && m === 0) {
        // Fourth thread - technical questions
        body = 'We\'ve been testing the trial version and have some questions about the API. Our developers need to integrate this with our existing CRM. What kind of support do you provide?';
      } else if (t === 4 && m === 0) {
        // Fifth thread - contract discussion
        body = 'Our legal team has reviewed the contract. We\'re ready to move forward, but we need clarification on the SLA terms. Can we discuss this?';
      } else if (t === 5 && m === 0) {
        // Sixth thread - implementation
        body = 'We\'ve signed the contract! Our team is excited to get started. When can we begin the onboarding process? We\'d like to have this live within the next month.';
      } else if (t === 6 && m === 0) {
        // Seventh thread - feature request
        body = 'We\'ve been using the platform for a few months now and it\'s been great! However, we have a feature request - can you add custom workflow automation? This would really help our team.';
      } else if (t === 7 && m === 0) {
        // Eighth thread - expansion
        body = 'We\'re expanding our team and need to add 20 more user licenses. Can you help us with the upgrade process? Also, we\'re interested in the advanced analytics package.';
      } else if (t === 8 && m === 0) {
        // Ninth thread - issue report
        body = 'We\'re experiencing some performance issues with the dashboard loading slowly. Our team has noticed this over the past week. Can you investigate?';
      } else if (t === 9 && m === 0) {
        // Tenth thread - renewal discussion
        body = 'Our annual contract is coming up for renewal. We\'ve been very happy with the service. Can we discuss renewal terms and any new features that might be relevant?';
      } else if (t === 10 && m === 0) {
        // Eleventh thread - partnership inquiry
        body = 'We\'re interested in exploring a partnership opportunity. We have several clients who could benefit from your platform. Would you be open to a referral program?';
      } else if (t === 11 && m === 0) {
        // Twelfth thread - training request
        body = 'We\'re onboarding new team members and would like to schedule additional training sessions. Can you provide advanced training on the API and automation features?';
      } else if (t === 12 && m === 0) {
        // Thirteenth thread - feature feedback
        body = 'The new workflow automation feature is excellent! Our team has been using it extensively. We have some suggestions for improvements - can we schedule a call to discuss?';
      } else if (t === 13 && m === 0) {
        // Fourteenth thread - urgent issue
        body = 'URGENT: We\'re experiencing a critical issue with data synchronization. Some of our customer data isn\'t syncing properly. This is affecting our operations. Can you prioritize this?';
      } else if (t === 14 && m === 0) {
        // Fifteenth thread - recent inquiry
        body = 'We\'re evaluating additional features for next quarter. Can you provide information about the AI-powered insights and the new reporting dashboard? We\'re particularly interested in how this could help our sales team.';
      } else {
        // Generic responses
        const responses = [
          'Thank you for the quick response. This is very helpful.',
          'That makes sense. Let me discuss this with my team and get back to you.',
          'Perfect! We\'ll proceed with that approach.',
          'Great, we\'re looking forward to implementing this.',
          'Thanks for your support throughout this process.',
          'We appreciate the detailed explanation.',
          'This is exactly what we needed. Thank you!',
        ];
        body = responses[Math.floor(Math.random() * responses.length)];
      }

      messages.push({
        sender,
        body,
        created_at: messageDate,
      });
    }
  }

  // Insert all messages
  for (const message of messages) {
    await pool.query(
      `INSERT INTO messages (contact_id, channel, thread_id, sender, body, created_at)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [
        contactId,
        'email',
        threadIds[Math.floor(messages.indexOf(message) / 5)],
        message.sender,
        message.body,
        message.created_at,
      ]
    );
  }

  // Create some tasks over the 2-year period
  const tasks = [
    { title: 'Schedule enterprise demo', due_at: new Date(twoYearsAgo.getTime() + 30 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Provide Salesforce integration details', due_at: new Date(twoYearsAgo.getTime() + 60 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Review contract terms', due_at: new Date(twoYearsAgo.getTime() + 90 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Begin onboarding process', due_at: new Date(twoYearsAgo.getTime() + 120 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Add 20 user licenses', due_at: new Date(twoYearsAgo.getTime() + 200 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Investigate dashboard performance issue', due_at: new Date(twoYearsAgo.getTime() + 400 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Discuss contract renewal', due_at: new Date(twoYearsAgo.getTime() + 600 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Schedule advanced training', due_at: new Date(twoYearsAgo.getTime() + 650 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Resolve data sync issue', due_at: new Date(twoYearsAgo.getTime() + 700 * 24 * 60 * 60 * 1000), status: 'completed' },
    { title: 'Provide AI insights demo', due_at: new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000), status: 'pending' },
    { title: 'Follow up on partnership discussion', due_at: new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000), status: 'pending' },
  ];

  for (const task of tasks) {
    await pool.query(
      `INSERT INTO tasks (contact_id, title, due_at, status)
       VALUES ($1, $2, $3, $4)`,
      [contactId, task.title, task.due_at, task.status]
    );
  }

  console.log(`✅ Created ${messages.length} messages across ${threadCount} threads`);
  console.log(`✅ Created ${tasks.length} tasks`);
  console.log(`✅ Contact ID: ${contactId}`);
  console.log(`✅ Contact Email: ${contactEmail}`);
  
  return { contactId, contactEmail, messageCount: messages.length, taskCount: tasks.length };
}

// Run if called directly
if (require.main === module) {
  createLongHistoryContact()
    .then((result) => {
      console.log('\n🎉 Successfully created contact with 2 years of history!');
      console.log(`\nContact Details:`);
      console.log(`  ID: ${result.contactId}`);
      console.log(`  Email: ${result.contactEmail}`);
      console.log(`  Messages: ${result.messageCount}`);
      console.log(`  Tasks: ${result.taskCount}`);
      process.exit(0);
    })
    .catch((error) => {
      console.error('❌ Error creating contact:', error);
      process.exit(1);
    });
}

export { createLongHistoryContact };


