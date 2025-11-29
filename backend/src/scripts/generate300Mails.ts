/**
 * Generate 300 realistic mail messages for testing
 */

import { pool } from '../db';

const FIRST_NAMES = [
  'Sarah', 'Michael', 'Emily', 'David', 'Jessica', 'James', 'Amanda', 'Robert',
  'Jennifer', 'William', 'Lisa', 'Richard', 'Michelle', 'Joseph', 'Ashley',
  'Thomas', 'Melissa', 'Charles', 'Nicole', 'Christopher', 'Stephanie', 'Daniel',
  'Angela', 'Matthew', 'Kimberly', 'Anthony', 'Amy', 'Mark', 'Laura', 'Donald',
  'Rebecca', 'Steven', 'Sharon', 'Paul', 'Cynthia', 'Andrew', 'Kathleen', 'Joshua',
  'Samantha', 'Kenneth', 'Deborah', 'Kevin', 'Rachel', 'Brian', 'Carolyn', 'George',
  'Janet', 'Edward', 'Catherine', 'Ronald', 'Maria', 'Timothy', 'Heather', 'Jason',
  'Diane', 'Jeffrey', 'Ruth', 'Ryan', 'Shirley', 'Jacob', 'Brenda', 'Gary', 'Emma',
  'Nicholas', 'Olivia', 'Eric', 'Cynthia', 'Jonathan', 'Marie', 'Stephen', 'Janet',
  'Larry', 'Frances', 'Justin', 'Christine', 'Scott', 'Samantha', 'Brandon', 'Debra',
  'Benjamin', 'Rachel', 'Samuel', 'Carol', 'Frank', 'Janet', 'Gregory', 'Virginia',
  'Raymond', 'Maria', 'Alexander', 'Heather', 'Patrick', 'Diana', 'Jack', 'Julie',
  'Dennis', 'Joyce', 'Jerry', 'Victoria', 'Tyler', 'Madison', 'Aaron', 'Lauren',
  'Jose', 'Grace', 'Henry', 'Brittany', 'Adam', 'Megan', 'Douglas', 'Hannah',
  'Nathan', 'Alexis', 'Zachary', 'Natalie', 'Kyle', 'Stephanie', 'Noah', 'Kayla',
  'Ethan', 'Jasmine', 'Jeremy', 'Taylor', 'Hunter', 'Samantha', 'Christian', 'Rachel'
];

const LAST_NAMES = [
  'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
  'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Wilson', 'Anderson', 'Thomas',
  'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Thompson', 'White', 'Harris',
  'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker', 'Young', 'Allen',
  'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores', 'Green', 'Adams',
  'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell', 'Carter', 'Roberts',
  'Gomez', 'Phillips', 'Evans', 'Turner', 'Diaz', 'Parker', 'Cruz', 'Edwards',
  'Collins', 'Reyes', 'Stewart', 'Morris', 'Morales', 'Murphy', 'Cook', 'Rogers',
  'Gutierrez', 'Ortiz', 'Morgan', 'Cooper', 'Peterson', 'Bailey', 'Reed', 'Kelly',
  'Howard', 'Ramos', 'Kim', 'Cox', 'Ward', 'Richardson', 'Watson', 'Brooks',
  'Chavez', 'Wood', 'James', 'Bennett', 'Gray', 'Mendoza', 'Ruiz', 'Hughes',
  'Price', 'Alvarez', 'Castillo', 'Sanders', 'Patel', 'Myers', 'Long', 'Ross',
  'Foster', 'Jimenez', 'Powell', 'Jenkins', 'Perry', 'Russell', 'Sullivan', 'Bell',
  'Coleman', 'Butler', 'Henderson', 'Barnes', 'Gonzales', 'Fisher', 'Vasquez', 'Simmons'
];

const COMPANIES = [
  'TechCorp', 'Global Solutions', 'Innovate Inc', 'Digital Dynamics', 'Cloud Systems',
  'Data Analytics Pro', 'Future Tech', 'Smart Solutions', 'Enterprise Partners',
  'NextGen Industries', 'Alpha Corp', 'Beta Systems', 'Gamma Technologies', 'Delta Solutions',
  'Epsilon Group', 'Zeta Enterprises', 'Eta Innovations', 'Theta Labs', 'Iota Systems',
  'Kappa Industries', 'Lambda Corp', 'Mu Technologies', 'Nu Solutions', 'Xi Enterprises',
  'Omicron Systems', 'Pi Innovations', 'Rho Technologies', 'Sigma Solutions', 'Tau Corp',
  'Upsilon Industries', 'Phi Technologies', 'Chi Solutions', 'Psi Systems', 'Omega Corp',
  'Apex Industries', 'Summit Solutions', 'Peak Technologies', 'Vertex Systems', 'Nexus Corp',
  'Fusion Industries', 'Synergy Solutions', 'Catalyst Technologies', 'Momentum Systems',
  'Velocity Corp', 'Accelerate Inc', 'Thrive Industries', 'Prosper Solutions', 'Excel Tech',
  'Prime Systems', 'Elite Corp', 'Premium Solutions', 'Select Technologies', 'Prime Industries'
];

const SUBJECTS = [
  'Product Inquiry', 'Support Request', 'Partnership Opportunity', 'Billing Question',
  'Feature Request', 'Bug Report', 'Account Issue', 'Refund Request', 'Shipping Delay',
  'Product Demo', 'Pricing Information', 'Technical Support', 'Sales Inquiry',
  'Contract Renewal', 'Service Upgrade', 'Integration Help', 'API Access Request',
  'Custom Solution', 'Training Request', 'Documentation Need', 'Security Concern',
  'Performance Issue', 'Compatibility Question', 'Migration Help', 'Backup Request',
  'Data Export', 'Account Recovery', 'Password Reset', 'Subscription Change',
  'Cancellation Request', 'Feedback Submission', 'Complaint', 'Praise', 'Suggestion',
  'Meeting Request', 'Follow-up', 'Urgent Issue', 'Escalation', 'Thank You'
];

const MESSAGE_TEMPLATES = [
  'Hi, I\'m interested in learning more about your {product}. Can you provide more details?',
  'I\'m experiencing an issue with {feature}. It\'s not working as expected.',
  'I need help with {task}. Could someone assist me?',
  'I\'m interested in a partnership opportunity. Let\'s discuss how we can work together.',
  'I have a question about my {account_type} account. Can you clarify?',
  'I\'d like to request a refund for {item}. The reason is {reason}.',
  'There\'s been a delay with my order. Can you provide an update?',
  'I\'d like to schedule a demo of your {product}. When are you available?',
  'I need pricing information for {service}. Can you send me a quote?',
  'I\'m having trouble with {technical_issue}. Can your support team help?',
  'I\'m interested in purchasing {product}. What are the next steps?',
  'My contract is expiring soon. Can we discuss renewal options?',
  'I\'d like to upgrade my {service} plan. What are the options?',
  'I need help integrating {system} with your platform.',
  'I\'d like to request API access for {purpose}.',
  'I need a custom solution for {requirement}. Is this possible?',
  'I\'d like to schedule training for my team. When can we do this?',
  'I need documentation for {feature}. Where can I find it?',
  'I have a security concern about {issue}. Can you address this?',
  'I\'m experiencing performance issues with {component}.',
  'I have a question about compatibility with {system}.',
  'I need help migrating from {old_system} to your platform.',
  'I\'d like to request a backup of my data.',
  'I need to export my data. How can I do this?',
  'I can\'t access my account. Can you help me recover it?',
  'I need to reset my password. Can you send me instructions?',
  'I\'d like to change my subscription plan.',
  'I need to cancel my subscription. What\'s the process?',
  'I have some feedback about {feature}. Here are my thoughts...',
  'I\'m filing a complaint about {issue}. This needs to be addressed immediately.',
  'I wanted to thank you for {positive_experience}. Great work!',
  'I have a suggestion for improving {feature}.',
  'I\'d like to schedule a meeting to discuss {topic}.',
  'This is a follow-up to our previous conversation about {subject}.',
  'URGENT: I need immediate assistance with {critical_issue}.',
  'I need to escalate this issue. It\'s been unresolved for too long.',
  'Thank you for your help with {issue}. I really appreciate it!'
];

const PRODUCTS = ['product', 'service', 'platform', 'software', 'solution', 'tool', 'system'];
const FEATURES = ['dashboard', 'reporting', 'analytics', 'API', 'integration', 'mobile app', 'web portal'];
const REASONS = ['defective item', 'wrong size', 'not as described', 'changed my mind', 'duplicate order'];
const ACCOUNT_TYPES = ['premium', 'enterprise', 'basic', 'trial', 'free'];
const TECHNICAL_ISSUES = ['login', 'upload', 'download', 'sync', 'connection', 'performance'];
const SYSTEMS = ['Salesforce', 'HubSpot', 'Slack', 'Microsoft Teams', 'Google Workspace', 'Zapier'];

function randomElement<T>(array: T[]): T {
  return array[Math.floor(Math.random() * array.length)];
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function generateEmail(firstName: string, lastName: string): string {
  const domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'company.com', 'business.com'];
  const formats = [
    `${firstName.toLowerCase()}.${lastName.toLowerCase()}`,
    `${firstName.toLowerCase()}${lastName.toLowerCase()}`,
    `${firstName[0].toLowerCase()}${lastName.toLowerCase()}`,
    `${firstName.toLowerCase()}${randomInt(1, 999)}`
  ];
  return `${randomElement(formats)}@${randomElement(domains)}`;
}

function generateMessageBody(template: string): string {
  return template
    .replace('{product}', randomElement(PRODUCTS))
    .replace('{feature}', randomElement(FEATURES))
    .replace('{task}', randomElement(['setup', 'configuration', 'troubleshooting', 'migration']))
    .replace('{account_type}', randomElement(ACCOUNT_TYPES))
    .replace('{item}', randomElement(['order', 'subscription', 'product', 'service']))
    .replace('{reason}', randomElement(REASONS))
    .replace('{service}', randomElement(['premium plan', 'enterprise package', 'basic tier']))
    .replace('{technical_issue}', randomElement(TECHNICAL_ISSUES))
    .replace('{system}', randomElement(SYSTEMS))
    .replace('{purpose}', randomElement(['development', 'testing', 'integration', 'automation']))
    .replace('{requirement}', randomElement(['custom workflow', 'special integration', 'unique feature']))
    .replace('{component}', randomElement(['dashboard', 'API', 'database', 'server']))
    .replace('{old_system}', randomElement(['legacy system', 'competitor platform', 'in-house solution']))
    .replace('{issue}', randomElement(['data breach', 'unauthorized access', 'privacy concern']))
    .replace('{positive_experience}', randomElement(['excellent support', 'great product', 'quick response']))
    .replace('{subject}', randomElement(['pricing', 'features', 'integration', 'partnership']))
    .replace('{critical_issue}', randomElement(['system down', 'data loss', 'security breach', 'payment failure']))
    .replace('{topic}', randomElement(['pricing', 'features', 'partnership', 'integration']));
}

async function generate300Mails() {
  try {
    console.log('🗑️  Clearing existing messages and contacts...');
    
    // Clear existing data
    await pool.query('DELETE FROM messages');
    await pool.query('DELETE FROM tasks');
    await pool.query('DELETE FROM suggestions');
    await pool.query('DELETE FROM contacts');
    
    console.log('✅ Cleared existing data');
    console.log('📧 Generating 300 mail messages...');
    
    const contacts = new Map<string, any>();
    const threads = new Map<string, string[]>();
    
    // Generate 300 messages
    for (let i = 0; i < 300; i++) {
      const firstName = randomElement(FIRST_NAMES);
      const lastName = randomElement(LAST_NAMES);
      const email = generateEmail(firstName, lastName);
      const company = randomElement(COMPANIES);
      const contactKey = email.toLowerCase();
      
      // Create or get contact
      let contactId: string;
      if (!contacts.has(contactKey)) {
        const tags = [];
        if (Math.random() < 0.2) tags.push('lead');
        if (Math.random() < 0.1) tags.push('vip');
        if (Math.random() < 0.15) tags.push('complaint');
        
        const contactResult = await pool.query(
          `INSERT INTO contacts (name, email, company, tags, created_at)
           VALUES ($1, $2, $3, $4, NOW())
           RETURNING id`,
          [firstName + ' ' + lastName, email, company, JSON.stringify(tags)]
        );
        contactId = contactResult.rows[0].id;
        contacts.set(contactKey, { id: contactId, name: firstName + ' ' + lastName, email, company, tags });
      } else {
        contactId = contacts.get(contactKey).id;
      }
      
      // Generate thread_id (some messages are part of threads)
      let threadId: string;
      const shouldCreateThread = Math.random() < 0.3 && threads.size > 0;
      if (shouldCreateThread && threads.size > 0) {
        // Add to existing thread
        const existingThreads = Array.from(threads.keys());
        threadId = randomElement(existingThreads);
        threads.get(threadId)!.push(contactId);
      } else {
        // Create new thread
        threadId = `thread_${Date.now()}_${i}`;
        threads.set(threadId, [contactId]);
      }
      
      // Generate message
      const template = randomElement(MESSAGE_TEMPLATES);
      const body = generateMessageBody(template);
      const sender = 'contact';
      const channel = randomElement(['email', 'support', 'sales', 'billing']);
      const processed = Math.random() < 0.3; // 30% processed
      
      // Random date within last 30 days
      const daysAgo = randomInt(0, 30);
      const createdAt = new Date();
      createdAt.setDate(createdAt.getDate() - daysAgo);
      createdAt.setHours(randomInt(9, 17), randomInt(0, 59), randomInt(0, 59));
      
      await pool.query(
        `INSERT INTO messages (thread_id, contact_id, sender, body, channel, processed, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [threadId, contactId, sender, body, channel, processed, createdAt]
      );
      
      // Create tasks for some messages
      if (Math.random() < 0.4) {
        const taskTitles = [
          `Follow up with ${firstName}`,
          `Respond to inquiry`,
          `Review message`,
          `Action required: ${randomElement(SUBJECTS)}`,
          `Urgent: Customer request`
        ];
        const dueDate = new Date();
        dueDate.setDate(dueDate.getDate() + randomInt(0, 7));
        
        await pool.query(
          `INSERT INTO tasks (contact_id, title, status, due_at, created_at)
           VALUES ($1, $2, 'pending', $3, NOW())`,
          [contactId, randomElement(taskTitles), dueDate]
        );
      }
      
      if ((i + 1) % 50 === 0) {
        console.log(`  Generated ${i + 1}/300 messages...`);
      }
    }
    
    console.log('✅ Successfully generated 300 mail messages!');
    console.log(`📊 Created ${contacts.size} unique contacts`);
    console.log(`🧵 Created ${threads.size} message threads`);
    
    // Get stats
    const stats = await pool.query(`
      SELECT 
        COUNT(*) as total_messages,
        COUNT(*) FILTER (WHERE processed = false) as unread,
        COUNT(DISTINCT contact_id) as unique_contacts,
        COUNT(DISTINCT thread_id) as threads
      FROM messages
    `);
    
    console.log('\n📈 Statistics:');
    console.log(`   Total messages: ${stats.rows[0].total_messages}`);
    console.log(`   Unread messages: ${stats.rows[0].unread}`);
    console.log(`   Unique contacts: ${stats.rows[0].unique_contacts}`);
    console.log(`   Threads: ${stats.rows[0].threads}`);
    
    process.exit(0);
  } catch (error: any) {
    console.error('❌ Error generating mail data:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  generate300Mails();
}

export { generate300Mails };

